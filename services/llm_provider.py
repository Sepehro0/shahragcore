# -*- coding: utf-8 -*-
"""
LLM Provider Router
------------------
یک لایه یکپارچه روی `QwenClient` و `OpenRouterClient` که:

1. از interface موجود (`generate_text`, `generate_response`, `generate_stream`,
   `is_available`, `health_check`, `close`, `get_usage_stats`, `model_name`)
   به طور ۱۰۰٪ پشتیبانی می‌کند → drop-in replacement برای `QwenClient`.
2. امکان سوییچ زنده بین provider ها (`local` ↔ `openrouter`) را فراهم می‌کند.
3. اگر provider فعلی در دسترس نباشد (و `auto_fallback=True` باشد)، به provider
   دیگر fallback می‌کند تا consumer ها دچار اختلال نشوند.

حالت پیش‌فرض (`provider="local"`) عینا همان رفتار فعلی سیستم است؛ هیچ
call-site ای نباید هیچ تغییری احساس کند.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, Optional

from services.qwen_client import GenerationResponse, QwenClient

logger = logging.getLogger(__name__)

# Provider identifiers
PROVIDER_LOCAL = "local"
PROVIDER_OPENROUTER = "openrouter"
_VALID_PROVIDERS = {PROVIDER_LOCAL, PROVIDER_OPENROUTER}


def _normalize_provider(name: Optional[str]) -> str:
    p = (name or PROVIDER_LOCAL).strip().lower()
    if p not in _VALID_PROVIDERS:
        logger.warning(f"⚠️ Unknown LLM provider '{name}', falling back to 'local'")
        return PROVIDER_LOCAL
    return p


class LLMProvider:
    """
    Router/facade برای انتخاب بین Qwen محلی و OpenRouter.

    Parameters
    ----------
    provider : str
        "local" یا "openrouter". پیش‌فرض: "local".
    local_client : Optional[QwenClient]
        اگر ندهید، به صورت lazy ساخته می‌شود.
    openrouter_client_factory : Optional[Callable[[], OpenRouterClient]]
        factory برای ساخت OpenRouterClient در هنگام نیاز. اگر ندهید، تلاش
        می‌شود با خواندن `config.settings` ساخته شود.
    auto_fallback : bool
        اگر provider انتخابی در دسترس نباشد، آیا به provider دیگر برگردد؟
        پیش‌فرض: True (برای حفظ پایداری).
    """

    def __init__(
        self,
        provider: str = PROVIDER_LOCAL,
        local_client: Optional[QwenClient] = None,
        openrouter_client: Optional[Any] = None,
        auto_fallback: bool = True,
    ):
        self._provider = _normalize_provider(provider)
        self._local_client = local_client
        self._openrouter_client = openrouter_client
        self.auto_fallback = auto_fallback

        # Track the last active client so that attributes like model_name reflect reality.
        self._last_active: Optional[Any] = None

        logger.info(
            f"🔀 LLMProvider initialized "
            f"(provider={self._provider}, auto_fallback={self.auto_fallback})"
        )

    # ------------------------------------------------------------------
    # Client lifecycle / lazy init
    # ------------------------------------------------------------------

    def _ensure_local(self) -> QwenClient:
        if self._local_client is None:
            self._local_client = QwenClient()
            logger.info("🔀 LLMProvider: created lazy local QwenClient")
        return self._local_client

    def _ensure_openrouter(self):
        """ساخت lazy کلاینت OpenRouter از روی تنظیمات یا raise در صورت نبود کلید."""
        if self._openrouter_client is not None:
            return self._openrouter_client

        # Lazy import to avoid import cost when not needed
        from services.openrouter_client import OpenRouterClient

        api_key = None
        model = None
        base_url = None
        site_url = None
        app_name = None
        timeout = 120
        max_retries = 3
        extra_body = None

        try:
            from config.settings import settings  # type: ignore

            llm_cfg = getattr(settings, "llm", None)
            if llm_cfg is not None:
                api_key = getattr(llm_cfg, "openrouter_api_key", None)
                model = getattr(llm_cfg, "openrouter_model", None) or model
                base_url = getattr(llm_cfg, "openrouter_base_url", None) or base_url
                site_url = getattr(llm_cfg, "openrouter_site_url", None)
                app_name = getattr(llm_cfg, "openrouter_app_name", None)
                timeout = getattr(llm_cfg, "openrouter_timeout", timeout) or timeout
                max_retries = getattr(llm_cfg, "openrouter_max_retries", max_retries) or max_retries
                extra_body = getattr(llm_cfg, "openrouter_extra_body", None)
        except Exception as e:
            logger.warning(f"⚠️ LLMProvider: failed to load OpenRouter config from settings: {e}")

        # Fallback to env var if settings didn't provide a key
        if not api_key:
            import os
            api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            raise RuntimeError(
                "OpenRouter provider requested but no API key found. "
                "Set OPENROUTER_API_KEY or configure settings.llm.openrouter_api_key."
            )

        kwargs = {
            "api_key": api_key,
            "model": model or "openai/gpt-4o-mini",
            "base_url": base_url or "https://openrouter.ai/api/v1",
            "site_url": site_url,
            "app_name": app_name,
            "timeout": int(timeout),
            "max_retries": int(max_retries),
            "extra_body": extra_body,
        }
        self._openrouter_client = OpenRouterClient(**kwargs)
        logger.info(
            f"🔀 LLMProvider: created lazy OpenRouterClient (model={kwargs['model']})"
        )
        return self._openrouter_client

    def _get_primary(self):
        if self._provider == PROVIDER_OPENROUTER:
            try:
                client = self._ensure_openrouter()
            except Exception as e:
                logger.error(f"❌ Could not initialize OpenRouter client: {e}")
                if self.auto_fallback:
                    logger.warning("↩️ Falling back to local Qwen client")
                    client = self._ensure_local()
                else:
                    raise
        else:
            client = self._ensure_local()
        self._last_active = client
        return client

    def _get_fallback(self, primary):
        """برمی‌گرداند client دیگر را اگر قابل ساخت باشد، وگرنه None."""
        try:
            if primary is self._local_client:
                return self._ensure_openrouter()
            return self._ensure_local()
        except Exception as e:
            logger.debug(f"LLMProvider: fallback client not available: {e}")
            return None

    # ------------------------------------------------------------------
    # Public: switching / introspection
    # ------------------------------------------------------------------

    def set_provider(self, provider: str) -> str:
        """تغییر provider فعال. نام provider نرمال‌شده را برمی‌گرداند."""
        new_provider = _normalize_provider(provider)
        if new_provider == self._provider:
            return self._provider
        logger.info(f"🔀 Switching LLM provider: {self._provider} → {new_provider}")
        self._provider = new_provider
        # Pre-warm the new primary client so errors (missing key) surface early.
        try:
            self._get_primary()
        except Exception as e:
            logger.warning(f"⚠️ New provider not ready yet: {e}")
        return self._provider

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model_name(self) -> str:
        """نام مدل فعال (برای لاگ/گزارش)."""
        client = self._last_active
        if client is None:
            try:
                client = self._get_primary()
            except Exception:
                return "unknown"
        return getattr(client, "model_name", "unknown")

    def get_active_client(self):
        """دسترسی مستقیم به client فعال (برای استفاده‌های خاص)."""
        return self._get_primary()

    def get_provider_info(self) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "provider": self._provider,
            "auto_fallback": self.auto_fallback,
            "model_name": self.model_name,
        }
        try:
            client = self._get_primary()
            if hasattr(client, "get_usage_stats"):
                info["active_stats"] = client.get_usage_stats()
        except Exception as e:
            info["error"] = str(e)
        return info

    # ------------------------------------------------------------------
    # Drop-in QwenClient-compatible API
    # ------------------------------------------------------------------

    async def _with_fallback(self, method_name: str, *args, **kwargs) -> GenerationResponse:
        primary = self._get_primary()
        method = getattr(primary, method_name)
        try:
            result: GenerationResponse = await method(*args, **kwargs)
        except Exception as e:
            logger.error(f"❌ {method_name} on {primary.__class__.__name__} raised: {e}")
            if not self.auto_fallback:
                raise
            fallback = self._get_fallback(primary)
            if fallback is None:
                raise
            logger.warning(f"↩️ Falling back to {fallback.__class__.__name__} for {method_name}")
            self._last_active = fallback
            return await getattr(fallback, method_name)(*args, **kwargs)

        # If primary returned a failed response, try fallback too
        if not getattr(result, "success", True) and self.auto_fallback:
            fallback = self._get_fallback(primary)
            if fallback is not None:
                logger.warning(
                    f"↩️ Primary {primary.__class__.__name__} returned failure; "
                    f"retrying with fallback {fallback.__class__.__name__}"
                )
                self._last_active = fallback
                try:
                    fb_result = await getattr(fallback, method_name)(*args, **kwargs)
                    if getattr(fb_result, "success", False):
                        return fb_result
                except Exception as e:
                    logger.error(f"Fallback also failed: {e}")
        return result

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> GenerationResponse:
        return await self._with_fallback(
            "generate_text",
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
        response_model: Any = None,
    ) -> GenerationResponse:
        return await self._with_fallback(
            "generate_response",
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            response_model=response_model,
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> AsyncGenerator[str, None]:
        primary = self._get_primary()
        try:
            produced_any = False
            async for chunk in primary.generate_stream(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            ):
                # Heuristic: if the very first chunk is an "Error: ..." message and we can
                # fallback, switch immediately. Otherwise forward as-is.
                if (
                    not produced_any
                    and isinstance(chunk, str)
                    and chunk.startswith("Error:")
                    and self.auto_fallback
                ):
                    fallback = self._get_fallback(primary)
                    if fallback is not None:
                        logger.warning(
                            f"↩️ Stream primary errored early; switching to "
                            f"{fallback.__class__.__name__}"
                        )
                        self._last_active = fallback
                        async for fb_chunk in fallback.generate_stream(
                            prompt=prompt,
                            system_prompt=system_prompt,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            top_p=top_p,
                        ):
                            yield fb_chunk
                        return
                produced_any = True
                yield chunk
        except (asyncio.CancelledError, GeneratorExit):
            raise
        except Exception as e:
            logger.error(f"❌ Primary stream failed: {e}")
            if not self.auto_fallback:
                raise
            fallback = self._get_fallback(primary)
            if fallback is None:
                raise
            logger.warning(f"↩️ Streaming with fallback {fallback.__class__.__name__}")
            self._last_active = fallback
            async for chunk in fallback.generate_stream(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            ):
                yield chunk

    async def health_check(self) -> bool:
        try:
            client = self._get_primary()
            return await client.health_check()
        except Exception as e:
            logger.debug(f"LLMProvider health_check failed: {e}")
            return False

    async def is_available(self) -> bool:
        return await self.health_check()

    async def close(self):
        """بستن هر دو client - ایمن در صورت عدم ساخت."""
        for client in (self._local_client, self._openrouter_client):
            if client is None:
                continue
            try:
                await client.close()
            except Exception as e:
                logger.debug(f"LLMProvider close error for {client.__class__.__name__}: {e}")

    def get_usage_stats(self) -> Dict[str, Any]:
        """آمار ترکیبی از client های فعال."""
        stats: Dict[str, Any] = {
            "provider": self._provider,
            "auto_fallback": self.auto_fallback,
        }
        if self._local_client is not None:
            try:
                stats["local"] = self._local_client.get_usage_stats()
            except Exception:
                pass
        if self._openrouter_client is not None:
            try:
                stats["openrouter"] = self._openrouter_client.get_usage_stats()
            except Exception:
                pass
        return stats


# ----------------------------------------------------------------------
# Factory helpers
# ----------------------------------------------------------------------

def build_llm_provider_from_settings(
    qwen_client: Optional[QwenClient] = None,
) -> LLMProvider:
    """
    ساخت LLMProvider با بارگذاری کامل تنظیمات.

    - اگر QwenClient از قبل وجود داشته باشد (مثلاً از parent system) همان مصرف می‌شود.
    - provider و auto_fallback از تنظیمات خوانده می‌شود.
    """
    provider_name = PROVIDER_LOCAL
    auto_fallback = True
    try:
        from config.settings import settings  # type: ignore

        llm_cfg = getattr(settings, "llm", None)
        if llm_cfg is not None:
            provider_name = _normalize_provider(getattr(llm_cfg, "provider", PROVIDER_LOCAL))
    except Exception as e:
        logger.debug(f"build_llm_provider_from_settings: settings not available ({e})")

    return LLMProvider(
        provider=provider_name,
        local_client=qwen_client,
        auto_fallback=auto_fallback,
    )
