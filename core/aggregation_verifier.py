# -*- coding: utf-8 -*-
"""
Aggregation Verifier – اصلاح قطعی جمع‌های عددی در پاسخ LLM
===========================================================

مشکلی که این ماژول حل می‌کند:
    LLMها هنگام جمع چند عدد بزرگ (مثلاً «مجموع X در سال‌های ۱۳۹۸ تا ۱۴۰۳»)
    گاهی یک رقم اشتباه می‌کنند (مثلاً به‌جای ۱۰۹٬۵۸۲٬۹۵۰ عدد ۱۱۹٬۵۸۲٬۹۵۰
    می‌نویسد). چون مقادیر خام در `metadata` sourceها حضور دارند، می‌توانیم
    یک جمع **قطعی (deterministic)** محاسبه و در صورت اختلاف، پاسخ را
    اصلاح کنیم.

این ماژول کاملاً generic است و برای هر کالکشنی که ``aggregation_config``
داشته باشد کار می‌کند (builtin یا dynamic از طریق API).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from core.aggregation_config import (
    extract_numeric_value,
    get_aggregation_config,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Number utilities
# ---------------------------------------------------------------------------

_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_ENGLISH_DIGITS = "0123456789"
_DIGIT_TRANSLATION = str.maketrans(
    _PERSIAN_DIGITS + _ARABIC_DIGITS,
    _ENGLISH_DIGITS + _ENGLISH_DIGITS,
)


def _normalize_digits(text: str) -> str:
    return text.translate(_DIGIT_TRANSLATION) if text else text


# فقط اعداد «بزرگ» را استخراج می‌کنیم تا بخش‌های دیگر پاسخ را بی‌دلیل دست‌کاری نکنیم.
# این regex رشته‌هایی با جداکنندهٔ سه‌رقمی `,` یا `،` یا فاصله/بدون جداکننده را می‌گیرد.
_BIG_NUMBER_RE = re.compile(
    r"(?<![\d])(\d{1,3}(?:[,\u066C،\s]\d{3})+|\d{7,})(?![\d])"
)


def _parse_big_number(token: str) -> Optional[int]:
    cleaned = re.sub(r"[,\u066C،\s]", "", token)
    if not cleaned or not cleaned.isdigit():
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _format_int_fa(value: int) -> str:
    """۱۰۹۵۸۲۹۵۰ → «۱۰۹٬۵۸۲٬۹۵۰» (جداکنندهٔ فارسی و ارقام فارسی)."""
    s = f"{abs(int(value)):,}".replace(",", "٬")
    # English → Persian digits
    trans = str.maketrans(_ENGLISH_DIGITS, _PERSIAN_DIGITS)
    s = s.translate(trans)
    if value < 0:
        s = "−" + s
    return s


# ---------------------------------------------------------------------------
# Core aggregation
# ---------------------------------------------------------------------------

def _group_sources_by_entity(
    sources: Iterable[Dict[str, Any]],
    grouping_field: str,
    temporal_field: str,
    value_fields: List[str],
) -> Dict[str, Dict[Any, Tuple[float, Dict[str, Any]]]]:
    """sources را به ساختار ``{entity: {temporal_key: (value, metadata)}}``
    تبدیل می‌کند. اگر چند sourceٔ تکراری با یک (entity, temporal) وجود داشت،
    اولی نگه داشته می‌شود (معمولاً بالاترین امتیاز).
    """
    grouped: Dict[str, Dict[Any, Tuple[float, Dict[str, Any]]]] = {}
    for src in sources or []:
        md = (src.get("metadata") or {}) if isinstance(src, dict) else {}
        entity = md.get(grouping_field)
        temporal = md.get(temporal_field)
        if entity is None or temporal is None:
            continue
        value = extract_numeric_value(md, value_fields)
        if value is None:
            continue
        entity_key = str(entity)
        bucket = grouped.setdefault(entity_key, {})
        if temporal not in bucket:
            bucket[temporal] = (value, md)
    return grouped


def _best_matching_entity(
    grouped: Dict[str, Dict[Any, Tuple[float, Dict[str, Any]]]],
    requested_temporals: Optional[List[Any]],
) -> Optional[str]:
    """Entity با بیشترین پوشش در بازهٔ خواسته‌شده را انتخاب می‌کند. در صورت
    تساوی، entityای با بیشترین تعداد sourceٔ مجزا برنده می‌شود.
    """
    if not grouped:
        return None

    def _score(entity: str) -> Tuple[int, int]:
        entries = grouped[entity]
        if requested_temporals:
            covered = sum(1 for t in requested_temporals if t in entries)
        else:
            covered = len(entries)
        return covered, len(entries)

    best_entity = max(grouped.keys(), key=_score)
    covered, total = _score(best_entity)
    if covered < 2:
        return None  # جمع کردن کمتر از ۲ مقدار ارزش تأیید ندارد
    return best_entity


def compute_verified_sum(
    collection_name: str,
    sources: List[Dict[str, Any]],
    query: str,
    requested_temporals: Optional[List[Any]] = None,
) -> Optional[Dict[str, Any]]:
    """در صورت امکان، یک جمع قطعی بر اساس metadata منابع محاسبه می‌کند.

    خروجی ``None`` یعنی شرایط تأیید فراهم نیست (کالکشن پیکربندی ندارد،
    کمتر از ۲ مقدار موجود است، و غیره).

    خروجی non-None شامل:
      - ``entity``: نام قلم/موجودیتی که جمع برای آن محاسبه شد
      - ``values``: لیست ``(temporal, value, is_deduction)``
      - ``total``: جمع نهایی (با اعمال علامت ``is_deduction`` اگر وجود داشت)
      - ``unit_label``: برچسب واحد
      - ``config``: پیکربندی استفاده‌شده (برای log/trace)
    """
    config = get_aggregation_config(collection_name)
    if not config:
        return None

    grouping_field = config["grouping_field"]
    temporal_field = config["temporal_field"]
    value_fields = config["value_fields"]

    grouped = _group_sources_by_entity(
        sources=sources,
        grouping_field=grouping_field,
        temporal_field=temporal_field,
        value_fields=value_fields,
    )

    entity = _best_matching_entity(grouped, requested_temporals)
    if not entity:
        return None

    entries = grouped[entity]

    # اگر requested_temporals داده شده، فقط آن‌ها را بررسی کن؛
    # در غیر این صورت همهٔ مقادیر موجود.
    if requested_temporals:
        items = [(t, entries[t][0], entries[t][1]) for t in requested_temporals if t in entries]
    else:
        items = [(t, entries[t][0], entries[t][1]) for t in sorted(entries.keys())]

    if len(items) < 2:
        return None

    total = 0.0
    normalized: List[Tuple[Any, float, bool]] = []
    for temporal, value, md in items:
        is_deduction = bool(md.get("is_deduction"))
        signed = -value if is_deduction else value
        total += signed
        normalized.append((temporal, value, is_deduction))

    return {
        "entity": entity,
        "values": normalized,
        "total": total,
        "unit_label": config.get("unit_label", ""),
        "config": config,
    }


# ---------------------------------------------------------------------------
# LLM-output correction
# ---------------------------------------------------------------------------

def _extract_big_numbers(text: str) -> List[int]:
    """تمام اعداد «بزرگ» موجود در پاسخ LLM را به شکل عدد صحیح برمی‌گرداند."""
    if not text:
        return []
    normalized = _normalize_digits(text)
    numbers: List[int] = []
    for m in _BIG_NUMBER_RE.finditer(normalized):
        n = _parse_big_number(m.group(0))
        if n is not None:
            numbers.append(n)
    return numbers


def _answer_mentions_correct_total(answer: str, total: int, tolerance: int = 0) -> bool:
    numbers = _extract_big_numbers(answer)
    if not numbers:
        return False
    target = int(round(abs(total)))
    return any(abs(n - target) <= tolerance for n in numbers)


def _build_correction_note(
    entity: str,
    values: List[Tuple[Any, float, bool]],
    total: float,
    unit_label: str,
) -> str:
    """یک یادداشت فارسی کوتاه برای افزودن به پاسخ می‌سازد."""
    lines: List[str] = [
        "",
        "---",
        "",
        "### 🔎 بازبینی محاسبه (از روی دادهٔ منبع)",
        "",
        f"قلم: «{entity}»",
        "",
        "اقلام استفاده‌شده:",
    ]
    for temporal, value, is_deduction in values:
        sign = "−" if is_deduction else "+"
        lines.append(
            f"- {temporal}: {sign} {_format_int_fa(int(round(value)))}"
            + (f" {unit_label}" if unit_label else "")
            + (" (کسر می‌شود)" if is_deduction else "")
        )
    unit_suffix = f" {unit_label}" if unit_label else ""
    lines += [
        "",
        f"**مجموع دقیق: {_format_int_fa(int(round(total)))}{unit_suffix}**",
        "",
        "_این مقدار به‌صورت قطعی از روی داده‌های بازیابی‌شده محاسبه شده و جایگزین"
        " جمع پیشین در پاسخ است._",
    ]
    return "\n".join(lines)


def verify_and_correct_answer(
    *,
    collection_name: Optional[str],
    answer: str,
    sources: List[Dict[str, Any]],
    query: str,
    requested_temporals: Optional[List[Any]] = None,
    tolerance_ratio: float = 0.001,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """پاسخ LLM را بر اساس جمع قطعیِ محاسبه‌شده بازبینی می‌کند.

    استراتژی:
      1) جمع قطعی را محاسبه می‌کند.
      2) اگر LLM دقیقاً همین عدد را در متن پاسخ ذکر کرده باشد → پاسخ را تغییر
         نمی‌دهد ولی metadata تأیید را برمی‌گرداند.
      3) اگر ذکر نکرده باشد، یک «یادداشت بازبینی» (شامل اقلام و جمع صحیح) به
         انتهای پاسخ پیوست می‌کند.

    خروجی: ``(possibly_modified_answer, verification_info | None)``

    ``verification_info`` در صورت None بودن یعنی شرایط بازبینی فراهم نشد و
    پاسخ دست‌نخورده باقی مانده.
    """
    if not answer or not sources:
        return answer, None

    try:
        info = compute_verified_sum(
            collection_name=collection_name,
            sources=sources,
            query=query,
            requested_temporals=requested_temporals,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[AGG-VERIFY] compute_verified_sum failed: {e}")
        return answer, None

    if not info:
        return answer, None

    total = info["total"]
    int_total = int(round(total))
    # اگر جمع صفر است، بازبینی را رها کن (چیزی برای اصلاح نیست)
    if int_total == 0:
        return answer, info

    tolerance = max(1, int(abs(int_total) * tolerance_ratio))
    matched = _answer_mentions_correct_total(answer, int_total, tolerance=tolerance)

    verification_info = {
        **info,
        "llm_had_correct_total": matched,
        "applied_correction": False,
    }

    if matched:
        logger.info(
            "[AGG-VERIFY] LLM total matched exact computed sum "
            f"(entity='{info['entity'][:40]}', total={int_total:,})"
        )
        return answer, verification_info

    note = _build_correction_note(
        entity=info["entity"],
        values=info["values"],
        total=total,
        unit_label=info.get("unit_label", ""),
    )
    corrected = (answer.rstrip() + "\n" + note).strip()
    verification_info["applied_correction"] = True
    logger.warning(
        "[AGG-VERIFY] Appended correction note — LLM total did not match "
        f"(entity='{info['entity'][:40]}', computed_total={int_total:,})"
    )
    return corrected, verification_info


__all__ = [
    "compute_verified_sum",
    "verify_and_correct_answer",
]
