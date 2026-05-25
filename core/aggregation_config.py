# -*- coding: utf-8 -*-
"""
Aggregation Config – پیکربندی هم‌افزایی چندبُعدی (temporal / grouping) برای کالکشن‌ها
=================================================================================

این ماژول یک لایهٔ انتزاعی برای رفتار ویژهٔ کالکشن‌هایی فراهم می‌کند که داده‌هایشان
در امتداد یک بُعد «زمانی/دسته‌ای» قابل تجمیع هستند (مثلاً جدول‌های بودجه که برای هر
«قلم» مقادیری در سال‌های مختلف دارند).

خدمات اصلی:

1. ``get_aggregation_config(collection_name)`` → پیکربندی مؤثر برای یک کالکشن را برمی‌گرداند
   (ترکیب built-in + dynamic store). اگر کالکشن پیکربندی نداشته باشد ``None`` می‌دهد.
2. تعریف built-in برای ``budget_tables`` و ``budget_financial``.
3. پذیرش پیکربندی پویا (از طریق API) برای هر کالکشن (به‌ویژه ``col_*``).

ساختار پیکربندی (همان ساختار در dynamic store ذخیره می‌شود تحت کلید
``aggregation_config`` یا ``api_v1_metadata.aggregation_config``):

.. code:: python

    {
        "enabled": True,
        # نام فیلدی در metadata که قلم/موجودیت اصلی را گروه‌بندی می‌کند
        "grouping_field": "node_name",
        # نام فیلدی در metadata که بُعد زمانی را نگه می‌دارد
        "temporal_field": "year",
        # لیست فیلدها (به ترتیب اولویت) که مقدار عددی از آن‌ها خوانده می‌شود
        "value_fields": ["computed_value", "raw_amount"],
        # برچسب واحد برای نمایش مجموع (اختیاری)
        "unit_label": "میلیون ریال",
        # بازهٔ مجاز مقادیر temporal – برای نرمال‌سازی مقدار از روی query
        "temporal_min": 1350,
        "temporal_max": 1450,
        # شکستی که regex سال‌یابی را بخواهد یا نه – برای بُعد غیر «سال جلالی»
        "temporal_kind": "jalali_year",  # "jalali_year" | "int"
    }

این پیکربندی سپس به دو محل می‌خورد:
- ``_expand_budget_results_for_years`` که اکنون ``_expand_results_by_dimension`` است
  و رفتار چندسالهٔ قبلی را به هر کالکشن با پیکربندی منتقل می‌کند.
- ``aggregation_verifier.compute_verified_sum`` که از روی sources یک جمع قطعی
  محاسبه می‌کند و در صورت اختلاف با خروجی LLM آن را اصلاح می‌کند.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Built-in configurations
# ---------------------------------------------------------------------------
# این‌ها رفتار پیش‌فرض برای کالکشن‌های سیستمی را حفظ می‌کنند تا تغییرات قبلی
# (مربوط به budget_tables) بدون regression باقی بمانند.
_BUILTIN_CONFIGS: Dict[str, Dict[str, Any]] = {
    "budget_tables": {
        "enabled": True,
        "grouping_field": "node_name",
        "temporal_field": "year",
        "value_fields": ["computed_value", "raw_amount"],
        "unit_label": "میلیون ریال",
        "temporal_min": 1350,
        "temporal_max": 1450,
        "temporal_kind": "jalali_year",
        # کد طبقه‌بندی fast-path را برای این کالکشن‌ها کاملاً غیرفعال می‌کنیم
        # تا اعداد سال‌گونه (۴۰۳، ۹۸، ۱۴۰۳، ...) به‌اشتباه classification نشوند.
        "disable_classification_fastpath": True,
    },
    "budget_financial": {
        "enabled": True,
        "grouping_field": "node_name",
        "temporal_field": "year",
        "value_fields": ["computed_value", "raw_amount"],
        "unit_label": "میلیون ریال",
        "temporal_min": 1350,
        "temporal_max": 1450,
        "temporal_kind": "jalali_year",
        "disable_classification_fastpath": True,
    },
}


# پیش‌فرض‌هایی که هنگام ادغام با پیکربندی کاربر برای col_* استفاده می‌شوند
_DEFAULTS_FOR_DYNAMIC: Dict[str, Any] = {
    "enabled": True,
    "grouping_field": None,  # کاربر باید تعیین کند
    "temporal_field": None,  # کاربر باید تعیین کند
    "value_fields": ["value", "amount", "computed_value", "raw_amount"],
    "unit_label": "",
    "temporal_min": None,
    "temporal_max": None,
    "temporal_kind": "int",  # پیش‌فرض – اگر کاربر سال جلالی می‌خواهد خودش تغییر دهد
    "disable_classification_fastpath": False,
}


def _normalize_config(cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """اطمینان از اعتبار پیکربندی. اگر ``enabled=False`` یا فیلدهای ضروری
    خالی باشند ``None`` برمی‌گرداند تا استفاده‌کننده آن را نادیده بگیرد.
    """
    if not cfg or not isinstance(cfg, dict):
        return None
    if cfg.get("enabled") is False:
        return None

    grouping = cfg.get("grouping_field")
    temporal = cfg.get("temporal_field")
    if not grouping or not temporal:
        return None

    # normalize value_fields
    value_fields = cfg.get("value_fields") or cfg.get("value_field")
    if isinstance(value_fields, str):
        value_fields = [value_fields]
    if not value_fields:
        value_fields = _DEFAULTS_FOR_DYNAMIC["value_fields"]

    return {
        "enabled": True,
        "grouping_field": grouping,
        "temporal_field": temporal,
        "value_fields": list(value_fields),
        "unit_label": cfg.get("unit_label", ""),
        "temporal_min": cfg.get("temporal_min"),
        "temporal_max": cfg.get("temporal_max"),
        "temporal_kind": cfg.get("temporal_kind", "int"),
        "disable_classification_fastpath": bool(
            cfg.get("disable_classification_fastpath", False)
        ),
    }


def _load_dynamic_config(collection_name: str) -> Optional[Dict[str, Any]]:
    """بارگذاری پیکربندی aggregation از dynamic store.

    پیکربندی می‌تواند در دو محل قرار گرفته باشد:
      1) در ریشهٔ config به کلید ``aggregation_config``
      2) درون ``api_v1_metadata.aggregation_config``
    """
    try:
        from config.dynamic_collection_store import get_collection_config

        cfg = get_collection_config(collection_name)
        if not cfg:
            return None

        # ترجیح ریشه به درون metadata
        agg = cfg.get("aggregation_config")
        if not agg:
            api_meta = cfg.get("api_v1_metadata") or {}
            agg = api_meta.get("aggregation_config")

        if not agg:
            return None

        merged = {**_DEFAULTS_FOR_DYNAMIC, **agg}
        return _normalize_config(merged)
    except Exception as e:
        logger.debug(f"[AGG-CFG] Dynamic store lookup failed for {collection_name}: {e}")
        return None


def get_aggregation_config(collection_name: Optional[str]) -> Optional[Dict[str, Any]]:
    """بازگرداندن پیکربندی aggregation برای یک کالکشن.

    ترتیب جستجو:
      1) built-in (برای کالکشن‌های سیستمی مثل ``budget_tables``)
      2) dynamic store (برای کالکشن‌هایی که از طریق API ساخته می‌شوند مثل ``col_*``)

    اگر چیزی پیدا نشد ``None`` برمی‌گردد و مسیر معمولی اجرا می‌شود.
    """
    if not collection_name:
        return None

    builtin = _BUILTIN_CONFIGS.get(collection_name)
    if builtin:
        return _normalize_config(builtin)

    return _load_dynamic_config(collection_name)


def extract_numeric_value(metadata: Dict[str, Any], value_fields: List[str]) -> Optional[float]:
    """مقدار عددی را از متادیتا بر اساس اولویت ``value_fields`` استخراج می‌کند.

    - ``None``/خالی/رشتهٔ نامعتبر → ``None``
    - اعداد صفر نیز معتبر هستند (برای کالکشن‌هایی که صفر معنای «ثبت‌شده ولی بدون
      مقدار» دارد).
    """
    if not metadata:
        return None
    for field in value_fields:
        if field in metadata:
            raw = metadata.get(field)
            if raw is None or raw == "":
                continue
            try:
                return float(raw)
            except (TypeError, ValueError):
                continue
    return None


__all__ = [
    "get_aggregation_config",
    "extract_numeric_value",
]
