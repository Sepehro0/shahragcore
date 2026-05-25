# -*- coding: utf-8 -*-
"""
Collection-Aware LLM Provider
-----------------------------
یک درگاه (facade) drop-in با همان interface `QwenClient`/`LLMProvider` که درخواست
generation را بر اساس «collection فعلی» به provider مناسب مسیردهی می‌کند.

جریان کار:
    1. در ابتدای هر درخواست/پایپ‌لاین، collection_name را با context manager یا
       متد set_current_collection ثبت می‌کنیم.
    2. در داخل کد، هرجا `qwen_client.generate_text/...` صدا زده شود، اینجا
       بر اساس `_current_collection` context-var، LLMProvider مربوطه از
       `CollectionLLMManager` استخراج و فراخوانی می‌شود.
    3. اگر context ست نشده باشد یا collection override نداشته باشد، از
       `default_provider` (تنظیمات گلوبال) استفاده می‌شود → رفتار پیش‌فرض سیستم.

این کلاس thread-safe و event-loop safe است: از `contextvars.ContextVar`
استفاده می‌کند که per-task مقدار مستقل دارد.
"""

from __future__ import annotations

import contextvars
import logging
from contextlib import contextmanager
from typing import Any, AsyncGenerator, Dict, Optional

from services.collection_llm_manager import CollectionLLMManager
from services.llm_provider import LLMProvider
from services.qwen_client import GenerationResponse

logger = logging.getLogger(__name__)


class CollectionAwareLLMProvider:
    """
    Drop-in جایگزین برای `QwenClient` با امکان routing به ازای collection.

    Parameters
    ----------
    manager : CollectionLLMManager
        مدیر override های هر collection.
    default_provider : LLMProvider
        provider پیش‌فرض برای collection بدون override یا وقتی context ست نشده.
    """

    _context_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
        "collection_aware_llm_current_collection", default=None
    )

    def __init__(self, manager: CollectionLLMManager, default_provider: LLMProvider):
        self.manager = manager
        self.default_provider = default_provider

    # ------------------------------------------------------------------
    # Context handling
    # ------------------------------------------------------------------

    def set_current_collection(self, collection_name: Optional[str]):
        """
        collection فعلی را ست می‌کند و یک token برای بازگرداندن مقدار قبلی
        برمی‌گرداند. معمولا از `use_collection()` به جای این استفاده کنید.
        """
        return self._context_var.set(collection_name)

    def reset_current_collection(self, token) -> None:
        try:
            self._context_var.reset(token)
        except Exception as e:
            logger.debug(f"reset_current_collection failed: {e}")

    def get_current_collection(self) -> Optional[str]:
        return self._context_var.get()

    @contextmanager
    def use_collection(self, collection_name: Optional[str]):
        """
        Context manager برای ست کردن موقتی collection فعلی.

        مثال:
            with qwen_client.use_collection("budget_financial"):
                await qwen_client.generate_text(...)
        """
        token = self._context_var.set(collection_name)
        try:
            yield collection_name
        finally:
            try:
                self._context_var.reset(token)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Provider resolution
    # ------------------------------------------------------------------

    def _resolve(self, collection_name: Optional[str] = None) -> LLMProvider:
        name = collection_name or self._context_var.get()
        if not name:
            return self.default_provider
        try:
            return self.manager.resolve_provider(name)
        except Exception as e:
            logger.warning(
                f"⚠️ Failed to resolve LLM provider for collection '{name}': {e}. "
                f"Falling back to default provider."
            )
            return self.default_provider

    # ------------------------------------------------------------------
    # Compatibility attributes (mimic QwenClient/LLMProvider)
    # ------------------------------------------------------------------

    @property
    def provider(self) -> str:
        return self._resolve().provider

    @property
    def model_name(self) -> str:
        try:
            return getattr(self._resolve(), "model_name", "unknown")
        except Exception:
            return "unknown"

    @property
    def auto_fallback(self) -> bool:
        return getattr(self.default_provider, "auto_fallback", True)

    @auto_fallback.setter
    def auto_fallback(self, value: bool) -> None:
        try:
            self.default_provider.auto_fallback = bool(value)
        except Exception as e:
            logger.debug(f"cannot set auto_fallback on default: {e}")

    def set_provider(self, provider: str) -> str:
        """
        سوییچ provider گلوبال (برای collection های بدون override).
        """
        return self.default_provider.set_provider(provider)

    # ------------------------------------------------------------------
    # QwenClient-compatible generation API
    # ------------------------------------------------------------------

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
        *,
        collection_name: Optional[str] = None,
    ) -> GenerationResponse:
        provider = self._resolve(collection_name)
        return await provider.generate_text(
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
        *,
        collection_name: Optional[str] = None,
    ) -> GenerationResponse:
        provider = self._resolve(collection_name)
        return await provider.generate_response(
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
        *,
        collection_name: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        provider = self._resolve(collection_name)
        async for chunk in provider.generate_stream(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        ):
            yield chunk

    async def health_check(self) -> bool:
        try:
            return await self._resolve().health_check()
        except Exception:
            return False

    async def is_available(self) -> bool:
        return await self.health_check()

    async def close(self) -> None:
        """بستن default provider و تمام cache در manager."""
        try:
            await self.default_provider.close()
        except Exception as e:
            logger.debug(f"close default_provider: {e}")
        try:
            await self.manager.close_all()
        except Exception as e:
            logger.debug(f"close manager.close_all: {e}")

    def get_usage_stats(self) -> Dict[str, Any]:
        stats = {
            "current_collection": self.get_current_collection(),
            "default": self.default_provider.get_usage_stats(),
            "per_collection_overrides": self.manager.list_overrides_public(),
        }
        return stats
