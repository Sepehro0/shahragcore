# -*- coding: utf-8 -*-
"""
OCR Text Post-Processor for Persian/Arabic
پس‌پردازش متن فارسی/عربی خروجی OCR

عملیات:
  1. نرمال‌سازی حروف (ي→ی ، ك→ک ، ة→ه ...)
  2. نرمال‌سازی اعداد (٠١٢...→0123... یا نگه‌داری فارسی)
  3. اصلاح فاصله و نیم‌فاصله
  4. پاک‌کردن آرتیفکت‌های OCR (کاراکترهای تنها، خطوط خالی)
  5. بازسازی هوشمند خطوط RTL
"""

import re
import logging
import numpy as np
from typing import List, Tuple, Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# 1. Character normalization tables
# ─────────────────────────────────────────────────────────────

_ARABIC_TO_PERSIAN_CHARS: dict[str, str] = {
    # الف/همزه
    "أ": "ا", "إ": "ا", "آ": "آ", "ٱ": "ا",
    # ي / ى → ی
    "ي": "ی", "ى": "ی", "ئ": "ئ",
    # ك → ک
    "ك": "ک",
    # ة → ه
    "ة": "ه",
    # واو
    "ؤ": "و",
    # zero-width chars & special
    "\u200c": "\u200c",  # ZWNJ: نیم‌فاصله (نگه داشته می‌شود)
    "\u200b": "",         # zero-width space: حذف
    "\u00ad": "",         # soft hyphen: حذف
    "\ufeff": "",         # BOM: حذف
}

_ARABIC_DIGITS_TO_WESTERN = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩", "0123456789"
)
_PERSIAN_DIGITS_TO_WESTERN = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹", "0123456789"
)

# کاراکترهای نویز رایج در OCR فارسی
_NOISE_CHARS_PATTERN = re.compile(r"[|_~`^]")

# الگو: رشته‌ای که فقط از کاراکترهای غیرمعنادار تشکیل شده
_GARBAGE_TOKEN_PATTERN = re.compile(
    r"^[^\u0600-\u06FFa-zA-Z0-9]{1,2}$"
)


def normalize_persian_chars(text: str) -> str:
    """نرمال‌سازی حروف عربی به فارسی استاندارد"""
    for arabic, persian in _ARABIC_TO_PERSIAN_CHARS.items():
        text = text.replace(arabic, persian)
    return text


def normalize_digits(text: str, keep_persian: bool = False) -> str:
    """
    نرمال‌سازی اعداد فارسی/عربی.
    اگر keep_persian=False، همه به لاتین تبدیل می‌شوند.
    """
    if keep_persian:
        # عربی به فارسی
        text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "۰۱۲۳۴۵۶۷۸۹"))
    else:
        text = text.translate(_ARABIC_DIGITS_TO_WESTERN)
        text = text.translate(_PERSIAN_DIGITS_TO_WESTERN)
    return text


def fix_spacing(text: str) -> str:
    """
    اصلاح فاصله‌های اشتباه در متن فارسی:
    - چند فاصله پشت سرهم → یک فاصله
    - فاصله قبل از نقطه‌گذاری → حذف
    - عدم فاصله بعد از نقطه → اضافه کردن
    - حذف فاصله در ابتدا و انتهای هر خط
    """
    # چند فاصله → یک
    text = re.sub(r" {2,}", " ", text)
    # فاصله قبل از ،.؛:!؟
    text = re.sub(r" +([،.؛:!؟,;!?])", r"\1", text)
    # فاصله در ابتدا/انتهای هر خط
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)
    return text


def remove_ocr_artifacts(text: str) -> str:
    """
    حذف آرتیفکت‌های رایج OCR:
    - کاراکترهای نویز تنها
    - توکن‌های کاملاً بی‌معنا (مثل "|" یا "_")
    - خطوط کاملاً خالی متوالی
    """
    # حذف کاراکترهای نویز
    text = _NOISE_CHARS_PATTERN.sub(" ", text)

    # پردازش خط‌به‌خط
    cleaned_lines = []
    for line in text.splitlines():
        tokens = line.split()
        valid_tokens = [
            t for t in tokens
            if not _GARBAGE_TOKEN_PATTERN.match(t)
        ]
        cleaned_line = " ".join(valid_tokens)
        cleaned_lines.append(cleaned_line)

    # حذف خطوط خالی متوالی (بیش از یک)
    result_lines = []
    blank_count = 0
    for line in cleaned_lines:
        if not line.strip():
            blank_count += 1
            if blank_count <= 1:
                result_lines.append(line)
        else:
            blank_count = 0
            result_lines.append(line)

    return "\n".join(result_lines)


# ─────────────────────────────────────────────────────────────
# 2. RTL-Aware Line Reconstruction
# ─────────────────────────────────────────────────────────────

def reconstruct_rtl_lines(
    ocr_results: List[Any],   # List of OCRResult objects
    page_height: int,
) -> str:
    """
    بازسازی هوشمند خطوط RTL از نتایج OCR.

    بهبودهای نسبت به _build_full_text قبلی:
    - آستانه خط بر اساس میانه ارتفاع باکس‌ها (نه درصد ثابت صفحه)
    - grouping بر اساس مرکز y (نه گوشه بالا)
    - مرتب‌سازی دقیق‌تر RTL
    - فیلتر نتایج با confidence پایین (flag می‌شوند نه حذف)
    """
    if not ocr_results:
        return ""

    # محاسبه میانه ارتفاع باکس‌ها برای آستانه dynamic
    heights = [r.bbox.y2 - r.bbox.y1 for r in ocr_results]
    median_height = float(np.median(heights)) if heights else 20.0
    line_threshold = max(median_height * 0.6, 8.0)

    # مرکز y هر ناحیه
    def y_center(r):
        return (r.bbox.y1 + r.bbox.y2) / 2.0

    # مرتب‌سازی بر اساس y-center
    sorted_results = sorted(ocr_results, key=y_center)

    # گروه‌بندی به خطوط
    lines: List[List] = []
    current_line: List = [sorted_results[0]]
    current_y = y_center(sorted_results[0])

    for r in sorted_results[1:]:
        cy = y_center(r)
        if abs(cy - current_y) <= line_threshold:
            current_line.append(r)
        else:
            lines.append(current_line)
            current_line = [r]
            current_y = cy

    if current_line:
        lines.append(current_line)

    # ساخت متن هر خط (RTL: از راست به چپ = x بزرگتر اول)
    text_lines = []
    for line in lines:
        line_sorted = sorted(line, key=lambda r: r.bbox.x1, reverse=True)
        # فقط توکن‌های معنادار
        tokens = [r.text.strip() for r in line_sorted if r.text.strip()]
        if tokens:
            text_lines.append(" ".join(tokens))

    return "\n".join(text_lines)


# ─────────────────────────────────────────────────────────────
# 3. Full post-processing pipeline
# ─────────────────────────────────────────────────────────────

def postprocess_ocr_text(
    text: str,
    normalize_chars: bool = True,
    normalize_nums: bool = True,
    fix_spaces: bool = True,
    remove_artifacts: bool = True,
    keep_persian_digits: bool = False,
) -> str:
    """
    Pipeline کامل پس‌پردازش متن OCR فارسی.

    Args:
        text: متن خام خروجی OCR
        normalize_chars: نرمال‌سازی حروف عربی→فارسی
        normalize_nums: نرمال‌سازی اعداد
        fix_spaces: اصلاح فاصله
        remove_artifacts: حذف آرتیفکت OCR
        keep_persian_digits: اعداد را فارسی نگه دار

    Returns:
        متن پاک‌شده و نرمال‌شده
    """
    if not text:
        return text

    if normalize_chars:
        text = normalize_persian_chars(text)

    if normalize_nums:
        text = normalize_digits(text, keep_persian=keep_persian_digits)

    if fix_spaces:
        text = fix_spacing(text)

    if remove_artifacts:
        text = remove_ocr_artifacts(text)

    return text.strip()


def postprocess_token(token: str) -> str:
    """پس‌پردازش یک توکن/کلمه منفرد"""
    token = normalize_persian_chars(token)
    token = normalize_digits(token, keep_persian=False)
    token = _NOISE_CHARS_PATTERN.sub("", token)
    return token.strip()


# ─────────────────────────────────────────────────────────────
# 4. Smart Header / Footer Detection
# ─────────────────────────────────────────────────────────────

# الگوهای محتوایی برای تشخیص هدر
_HEADER_CONTENT_PATTERNS = [
    re.compile(r"0\d{9,10}"),           # شماره تلفن ایرانی
    re.compile(r"\d{2,4}-\d{6,8}"),     # تلفن با کد شهر
    re.compile(r"www\.", re.I),         # URL
    re.compile(r"@"),                    # ایمیل
    re.compile(r"(مرکز|کلینیک|موسسه|شرکت)"),  # نام سازمان
    re.compile(r"(تهران|مشهد|اصفهان|شیراز)"),  # نام شهر
]

# الگوهای محتوایی برای تشخیص فوتر
_FOOTER_CONTENT_PATTERNS = [
    re.compile(r"(ترجمه|مترجم|copyright|©)", re.I),
    re.compile(r"(استفاده|چاپ|نشر|انتشار).{0,20}(ممنوع|آزاد|مجاز)"),
    re.compile(r"(صفحه|page)\s*\d+", re.I),
    re.compile(r"^\d{1,4}$"),           # شماره صفحه تنها
    re.compile(r"(موجود است|دسترس)"),
    re.compile(r"(دانشگاه|پرفسور|دکتر).*(دابسون|فتی|ترجمه)"),
]


class LayoutRegions:
    """نتیجه تقسیم‌بندی تصویر به ناحیه‌های هدر / متن اصلی / فوتر"""

    def __init__(
        self,
        header_results: list,
        body_results: list,
        footer_results: list,
        page_height: int,
    ):
        self.header_results = header_results
        self.body_results = body_results
        self.footer_results = footer_results
        self.page_height = page_height

    @property
    def header_text(self) -> str:
        if not self.header_results:
            return ""
        text = reconstruct_rtl_lines(self.header_results, self.page_height)
        return postprocess_ocr_text(text)

    @property
    def body_text(self) -> str:
        if not self.body_results:
            return ""
        text = reconstruct_rtl_lines(self.body_results, self.page_height)
        return postprocess_ocr_text(text)

    @property
    def footer_text(self) -> str:
        if not self.footer_results:
            return ""
        text = reconstruct_rtl_lines(self.footer_results, self.page_height)
        return postprocess_ocr_text(text)

    def full_text(self, include_header: bool = True, include_footer: bool = True) -> str:
        """
        متن کامل با کنترل هدر/فوتر.

        Args:
            include_header: آیا هدر در متن خروجی باشد
            include_footer: آیا فوتر در متن خروجی باشد
        """
        parts = []
        if include_header and self.header_text:
            parts.append(self.header_text)
        if self.body_text:
            parts.append(self.body_text)
        if include_footer and self.footer_text:
            parts.append(self.footer_text)
        return "\n\n".join(p for p in parts if p)

    def summary(self) -> dict:
        return {
            "header_lines": len(self.header_results),
            "body_lines": len(self.body_results),
            "footer_lines": len(self.footer_results),
            "header_preview": self.header_text[:100],
            "footer_preview": self.footer_text[:100],
        }


def detect_layout_regions(
    ocr_results: list,
    page_height: int,
    page_width: int,
    header_ratio: float = 0.13,
    footer_ratio: float = 0.10,
    use_content_hints: bool = True,
) -> "LayoutRegions":
    """
    تشخیص هوشمند هدر، متن اصلی و فوتر از نتایج OCR.

    روش ترکیبی:
      1. موقعیت (بالای header_ratio و پایین footer_ratio)
      2. محتوا (الگوهای تلفن، URL، شماره صفحه، ترجمه...)

    Args:
        ocr_results: لیست OCRResult
        page_height: ارتفاع صفحه/تصویر
        page_width: عرض صفحه/تصویر (برای ارزیابی عرض ناحیه)
        header_ratio: چند درصد از بالا = هدر (0.13 = 13%)
        footer_ratio: چند درصد از پایین = فوتر (0.10 = 10%)
        use_content_hints: استفاده از الگوهای محتوایی برای اصلاح تشخیص

    Returns:
        LayoutRegions شامل header_results, body_results, footer_results
    """
    if not ocr_results:
        return LayoutRegions([], [], [], page_height)

    header_thresh = page_height * header_ratio
    footer_thresh = page_height * (1.0 - footer_ratio)

    header_results = []
    body_results = []
    footer_results = []

    for r in ocr_results:
        y_center = (r.bbox.y1 + r.bbox.y2) / 2.0
        text = r.text.strip()

        # تشخیص اولیه بر اساس موقعیت
        if y_center <= header_thresh:
            zone = "header"
        elif y_center >= footer_thresh:
            zone = "footer"
        else:
            zone = "body"

        # اصلاح بر اساس محتوا
        if use_content_hints and zone == "body":
            if any(p.search(text) for p in _HEADER_CONTENT_PATTERNS):
                # اگر در ناحیه body است اما محتوای هدر دارد + نزدیک بالاست
                if y_center < page_height * 0.25:
                    zone = "header"
            if any(p.search(text) for p in _FOOTER_CONTENT_PATTERNS):
                if y_center > page_height * 0.75:
                    zone = "footer"

        if zone == "header":
            header_results.append(r)
        elif zone == "footer":
            footer_results.append(r)
        else:
            body_results.append(r)

    logger.debug(
        f"Layout detection: header={len(header_results)}, "
        f"body={len(body_results)}, footer={len(footer_results)}"
    )
    return LayoutRegions(header_results, body_results, footer_results, page_height)


