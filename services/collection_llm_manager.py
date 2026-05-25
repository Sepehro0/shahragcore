# -*- coding: utf-8 -*-
"""
Collection-Level LLM Configuration Manager
مدیریت تنظیمات LLM به ازای هر collection.

هدف: هر collection می‌تواند به طور مستقل انتخاب کند که مرحله text-generation
روی چه مدلی اجرا شود:
    - local (Qwen محلی)
    - openrouter (هر مدلی که روی OpenRouter موجود باشد)

حالت پیش‌فرض برای تمام collection هایی که override نداشته باشند، همان تنظیمات
گلوبال سیستم (که آن هم پیش‌فرض روی local است) باقی می‌ماند.

Persistence: فایل JSON در مسیر collections_config/collection_llm_overrides.json
(همان الگوی dynamic_collection_store.py).
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.llm_provider import (
    LLMProvider,
    PROVIDER_LOCAL,
    PROVIDER_OPENROUTER,
)
from services.qwen_client import QwenClient

logger = logging.getLogger(__name__)

# ---------- Persistence ----------
DEFAULT_STORE_DIR = Path(
    "/home/user01/qwen-api/enhanced_rag_system_dev/collections_config"
)
DEFAULT_STORE_FILE = DEFAULT_STORE_DIR / "collection_llm_overrides.json"

_VALID_PROVIDERS = {PROVIDER_LOCAL, PROVIDER_OPENROUTER}


@dataclass
class CollectionLLMOverride:
    """
    Override تنظیمات LLM برای یک collection مشخص.

    Fields:
      - collection_name : نام collection
      - provider        : "local" | "openrouter"
      - model           : نام مدل (برای openrouter اجباری، برای local اختیاری)
      - api_key         : اختیاری - اگر بخواهید برای این collection کلید متفاوتی بدهید
      - base_url        : اختیاری - برای override کردن endpoint
      - site_url/app_name : headers اختیاری OpenRouter (leaderboard)
      - timeout, max_retries : تنظیمات شبکه
      - temperature/top_p/max_tokens : tuning پیش‌فرض (اختیاری)
      - auto_fallback   : آیا در خطا به provider دیگر برگردد؟ (پیش‌فرض False برای override)
      - enabled         : فعال/غیرفعال کردن بدون حذف config
      - updated_at      : timestamp آخرین تغییر
      - notes           : یادداشت آزاد (اختیاری)
    """

    collection_name: str
    provider: str = PROVIDER_LOCAL
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    site_url: Optional[str] = None
    app_name: Optional[str] = None
    timeout: Optional[int] = None
    max_retries: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    auto_fallback: bool = False
    enabled: bool = True
    updated_at: Optional[str] = None
    notes: Optional[str] = None
    extra_body: Optional[Dict[str, Any]] = field(default=None)

    # ---- Helpers ----

    def normalize(self) -> "CollectionLLMOverride":
        """مقداردهی صحیح فیلدها + validation سبک."""
        self.provider = (self.provider or PROVIDER_LOCAL).strip().lower()
        if self.provider not in _VALID_PROVIDERS:
            logger.warning(
                f"⚠️ Unknown provider '{self.provider}' for collection "
                f"'{self.collection_name}', defaulting to 'local'"
            )
            self.provider = PROVIDER_LOCAL
        if self.updated_at is None:
            self.updated_at = datetime.utcnow().isoformat()
        return self

    def fingerprint(self) -> str:
        """
        شناسه یکتا از روی ویژگی‌های موثر بر ساخت LLMProvider.
        اگر دو override همین fingerprint را داشته باشند، هر دو یک LLMProvider
        واحد را به اشتراک می‌گذارند (cache).
        """
        parts = [
            self.provider,
            self.model or "",
            self.base_url or "",
            # api_key را با bool نگهداری می‌کنیم تا کلیدها در حافظه هش نشوند
            "key1" if self.api_key else "key0",
            self.site_url or "",
            self.app_name or "",
            str(self.timeout or ""),
            str(self.max_retries or ""),
            "fb1" if self.auto_fallback else "fb0",
        ]
        if self.extra_body:
            try:
                parts.append(json.dumps(self.extra_body, sort_keys=True, ensure_ascii=False))
            except Exception:
                parts.append(str(self.extra_body))
        return "|".join(parts)

    def to_public_dict(self) -> Dict[str, Any]:
        """نسخه‌ای امن برای نمایش/API (بدون افشای api_key)."""
        d = asdict(self)
        if d.get("api_key"):
            d["api_key"] = "***"  # redact
        return d


class CollectionLLMManager:
    """
    مدیریت override های LLM به ازای هر collection + cache کردن LLMProvider
    متناظر با هر config.

    Parameters
    ----------
    base_qwen_client : QwenClient
        کلاینت محلی مشترک (برای استفاده به عنوان local client در هر LLMProvider
        ساخته‌شده). به این ترتیب instance های چندگانه QwenClient ساخته نمی‌شوند.
    default_provider : LLMProvider
        provider پیش‌فرض سیستم برای collection هایی که override ندارند.
    storage_path : Optional[Path]
        مسیر فایل persistence. None → مسیر پیش‌فرض.
    autosave : bool
        اگر True باشد، هر تغییر فوراً روی دیسک ذخیره می‌شود.
    """

    def __init__(
        self,
        base_qwen_client: QwenClient,
        default_provider: LLMProvider,
        storage_path: Optional[Path] = None,
        autosave: bool = True,
    ):
        self.base_qwen_client = base_qwen_client
        self.default_provider = default_provider
        self.storage_path = Path(storage_path) if storage_path else DEFAULT_STORE_FILE
        self.autosave = autosave

        self._overrides: Dict[str, CollectionLLMOverride] = {}
        self._provider_cache: Dict[str, LLMProvider] = {}
        self._lock = threading.RLock()

        self._load_from_disk()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_from_disk(self) -> None:
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.storage_path.exists():
                return
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            loaded = 0
            for name, cfg in (data.get("collections") or {}).items():
                try:
                    override = CollectionLLMOverride(
                        collection_name=name,
                        **{k: v for k, v in cfg.items() if k != "collection_name"},
                    ).normalize()
                    self._overrides[name] = override
                    loaded += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to load LLM override for '{name}': {e}"
                    )
            if loaded:
                logger.info(
                    f"📥 CollectionLLMManager: loaded {loaded} override(s) "
                    f"from {self.storage_path}"
                )
        except Exception as e:
            logger.warning(f"Failed to load CollectionLLMManager store: {e}")

    def _save_to_disk(self) -> None:
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": 1,
                "updated_at": datetime.utcnow().isoformat(),
                "collections": {
                    name: asdict(ov) for name, ov in self._overrides.items()
                },
            }
            tmp_path = self.storage_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.storage_path)
        except Exception as e:
            logger.error(f"Failed to save CollectionLLMManager store: {e}")

    # ------------------------------------------------------------------
    # Public: CRUD on overrides
    # ------------------------------------------------------------------

    def set_override(
        self,
        collection_name: str,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        site_url: Optional[str] = None,
        app_name: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        auto_fallback: Optional[bool] = None,
        enabled: Optional[bool] = None,
        notes: Optional[str] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> CollectionLLMOverride:
        """
        ثبت یا به‌روزرسانی override برای یک collection.

        اگر قبلاً override ای وجود داشته باشد، فیلدهای داده‌شده merge می‌شوند و
        بقیه فیلدهای قبلی حفظ می‌شوند (رفتار PATCH-like).
        """
        if not collection_name:
            raise ValueError("collection_name is required")

        with self._lock:
            existing = self._overrides.get(collection_name)
            if existing is None:
                existing = CollectionLLMOverride(collection_name=collection_name)

            # Apply provided fields (merge style)
            if provider is not None:
                existing.provider = provider
            if model is not None:
                existing.model = model
            if api_key is not None:
                existing.api_key = api_key
            if base_url is not None:
                existing.base_url = base_url
            if site_url is not None:
                existing.site_url = site_url
            if app_name is not None:
                existing.app_name = app_name
            if timeout is not None:
                existing.timeout = int(timeout)
            if max_retries is not None:
                existing.max_retries = int(max_retries)
            if temperature is not None:
                existing.temperature = float(temperature)
            if top_p is not None:
                existing.top_p = float(top_p)
            if max_tokens is not None:
                existing.max_tokens = int(max_tokens)
            if auto_fallback is not None:
                existing.auto_fallback = bool(auto_fallback)
            if enabled is not None:
                existing.enabled = bool(enabled)
            if notes is not None:
                existing.notes = notes
            if extra_body is not None:
                existing.extra_body = extra_body

            existing.updated_at = datetime.utcnow().isoformat()
            existing.normalize()

            # Validate openrouter configuration
            if existing.provider == PROVIDER_OPENROUTER:
                if not existing.model:
                    raise ValueError(
                        "OpenRouter override requires a 'model' (e.g. 'openai/gpt-4o-mini')."
                    )

            # Invalidate cached provider for this fingerprint (if it existed)
            old_fp = None
            if collection_name in self._overrides:
                old_fp = self._overrides[collection_name].fingerprint()
            self._overrides[collection_name] = existing

            # If the new fingerprint differs from the old one, cleanup old cache entry
            new_fp = existing.fingerprint()
            if old_fp and old_fp != new_fp:
                self._drop_cached_provider(old_fp)

            if self.autosave:
                self._save_to_disk()

            logger.info(
                f"✅ LLM override set for '{collection_name}': "
                f"provider={existing.provider} model={existing.model or '(default)'}"
            )
            return existing

    def remove_override(self, collection_name: str) -> bool:
        """حذف override یک collection. True اگر وجود داشت."""
        with self._lock:
            ov = self._overrides.pop(collection_name, None)
            if ov is None:
                return False
            # Cleanup cache if nothing else is using that fingerprint
            fp = ov.fingerprint()
            still_used = any(o.fingerprint() == fp for o in self._overrides.values())
            if not still_used:
                self._drop_cached_provider(fp)
            if self.autosave:
                self._save_to_disk()
            logger.info(f"🗑️ Removed LLM override for '{collection_name}'")
            return True

    def get_override(self, collection_name: str) -> Optional[CollectionLLMOverride]:
        with self._lock:
            return self._overrides.get(collection_name)

    def list_overrides(self) -> List[CollectionLLMOverride]:
        with self._lock:
            return list(self._overrides.values())

    def list_overrides_public(self) -> List[Dict[str, Any]]:
        return [ov.to_public_dict() for ov in self.list_overrides()]

    # ------------------------------------------------------------------
    # Public: provider resolution
    # ------------------------------------------------------------------

    def has_override(self, collection_name: Optional[str]) -> bool:
        if not collection_name:
            return False
        with self._lock:
            ov = self._overrides.get(collection_name)
            return ov is not None and ov.enabled

    def resolve_provider(self, collection_name: Optional[str]) -> LLMProvider:
        """
        LLMProvider مربوط به collection را برمی‌گرداند.
        - اگر override فعالی نباشد → default_provider.
        - اگر override فعال باشد → LLMProvider اختصاصی (cache-شده).
        """
        if not collection_name:
            return self.default_provider

        with self._lock:
            override = self._overrides.get(collection_name)
            if override is None or not override.enabled:
                return self.default_provider

            # برای override ای که "local" است و هیچ فیلد خاصی ندارد، مستقیم
            # default_provider را برمی‌گردانیم (بهینه‌سازی: LLMProvider اضافی نسازیم).
            if override.provider == PROVIDER_LOCAL and not override.model:
                return self.default_provider

            fp = override.fingerprint()
            cached = self._provider_cache.get(fp)
            if cached is not None:
                return cached

            provider = self._build_provider_for_override(override)
            self._provider_cache[fp] = provider
            return provider

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_provider_for_override(
        self, override: CollectionLLMOverride
    ) -> LLMProvider:
        """
        ساخت یک LLMProvider جدید منطبق با override.
        QwenClient مشترک (base_qwen_client) به عنوان local client پاس داده می‌شود
        تا instance های تکراری QwenClient ساخته نشوند.
        """
        # Lazy imports to avoid heavy cost when never used
        from services.openrouter_client import OpenRouterClient

        openrouter_client = None
        if override.provider == PROVIDER_OPENROUTER:
            # اگر api_key در override نبود، از تنظیمات گلوبال استفاده کن
            api_key = override.api_key
            base_url = override.base_url
            site_url = override.site_url
            app_name = override.app_name
            timeout = override.timeout
            max_retries = override.max_retries
            model = override.model
            extra_body = override.extra_body

            if not api_key:
                try:
                    from config.settings import settings  # type: ignore

                    llm_cfg = getattr(settings, "llm", None)
                    if llm_cfg is not None:
                        api_key = getattr(llm_cfg, "openrouter_api_key", None)
                        if not base_url:
                            base_url = getattr(llm_cfg, "openrouter_base_url", None)
                        if not site_url:
                            site_url = getattr(llm_cfg, "openrouter_site_url", None)
                        if not app_name:
                            app_name = getattr(llm_cfg, "openrouter_app_name", None)
                        if timeout is None:
                            timeout = getattr(llm_cfg, "openrouter_timeout", None)
                        if max_retries is None:
                            max_retries = getattr(llm_cfg, "openrouter_max_retries", None)
                        if extra_body is None:
                            extra_body = getattr(llm_cfg, "openrouter_extra_body", None)
                except Exception:
                    pass
            if not api_key:
                api_key = os.getenv("OPENROUTER_API_KEY")

            if not api_key:
                raise RuntimeError(
                    f"Collection '{override.collection_name}' is configured with "
                    f"OpenRouter but no API key is available. Set OPENROUTER_API_KEY "
                    f"or pass api_key when creating the override."
                )

            openrouter_client = OpenRouterClient(
                api_key=api_key,
                model=model or "openai/gpt-4o-mini",
                base_url=base_url or "https://openrouter.ai/api/v1",
                site_url=site_url,
                app_name=app_name,
                timeout=int(timeout) if timeout else 120,
                max_retries=int(max_retries) if max_retries else 3,
                extra_body=extra_body,
            )

        provider = LLMProvider(
            provider=override.provider,
            local_client=self.base_qwen_client,
            openrouter_client=openrouter_client,
            auto_fallback=override.auto_fallback,
        )
        logger.info(
            f"🧩 Built dedicated LLMProvider for '{override.collection_name}' "
            f"(provider={override.provider}, model={override.model or 'default'})"
        )
        return provider

    def _drop_cached_provider(self, fingerprint: str) -> None:
        provider = self._provider_cache.pop(fingerprint, None)
        if provider is None:
            return
        # Best-effort async close is left to the caller's event loop lifecycle;
        # we do not await here (sync method). Resource will be released on
        # connector GC; for strict cleanup use `close_all()` below.
        logger.debug(f"Dropped cached LLMProvider fp={fingerprint[:40]}...")

    async def close_all(self) -> None:
        """بستن تمام provider های cache‌شده (best-effort)."""
        with self._lock:
            providers = list(self._provider_cache.values())
            self._provider_cache.clear()
        for p in providers:
            try:
                await p.close()
            except Exception as e:
                logger.debug(f"close_all error: {e}")

    # ------------------------------------------------------------------
    # Debug / Introspection
    # ------------------------------------------------------------------

    def describe(self, collection_name: Optional[str]) -> Dict[str, Any]:
        """توضیح کامل تنظیمات فعال برای یک collection (برای endpoint های ادمین)."""
        info: Dict[str, Any] = {
            "collection_name": collection_name,
            "has_override": False,
            "resolved_provider": self.default_provider.provider,
            "resolved_model": getattr(self.default_provider, "model_name", "unknown"),
        }
        if collection_name and collection_name in self._overrides:
            ov = self._overrides[collection_name]
            info["has_override"] = True
            info["override"] = ov.to_public_dict()
            try:
                prov = self.resolve_provider(collection_name)
                info["resolved_provider"] = prov.provider
                info["resolved_model"] = getattr(prov, "model_name", "unknown")
            except Exception as e:
                info["error"] = str(e)
        return info
