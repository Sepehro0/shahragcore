# -*- coding: utf-8 -*-
"""
پردازش سه فایل PDF ضوابط و ایجاد کالکشن zavabet
- سند اول (Consulting): موافقت‌نامه و شرایط عمومی همسان قراردادهای خدمات مشاوره
- سند دوم (EPC): موافقت‌نامه، شرایط عمومی و خصوصی پیمان‌های مهندسی، تأمین کالا و اجرا
- سند سوم (PC): موافقت‌نامه، شرایط عمومی و خصوصی پیمان‌های تأمین مصالح و تجهیزات

روش پردازش:
1. استخراج متن مستقیم از PDF با pdfplumber (بدون OCR)
2. اصلاح RTL/bidi با AdvancedPDFTableProcessor.fix_rtl_text
3. استخراج جداول با AdvancedPDFTableProcessor
4. Chunking هوشمند با IntelligentChunker (ContentType.LEGAL_DOCUMENT)
5. Embedding با heydariAI/persian-embeddings (1024 dim)
6. ذخیره در ChromaDB در کالکشن zavabet
"""

import sys
import os
import io
import re
import logging
import time
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import defaultdict

import fitz  # PyMuPDF - for OCR page rendering

sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("process_zavabet.log", encoding="utf-8", mode="w"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────

COLLECTION_NAME = "zavabet"
CHROMA_DB_PATH = "/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
EMBEDDING_MODEL = "heydariAI/persian-embeddings"
EMBEDDING_DIM = 1024

DATA_DIR = "/home/user01/qwen-api/enhanced_rag_system_dev/archive/data_files"

PDF_FILES = [
    {
        "path": os.path.join(DATA_DIR, "موافقت_نامه_و_شرایط_عمومی_همسان_قراردادهای_خدمات_مشاوره.pdf"),
        "doc_type": "consulting",
        "doc_title": "موافقت‌نامه و شرایط عمومی همسان قراردادهای خدمات مشاوره",
        "circular_ref": "بخشنامه ۱۴۰۱/۴۷۶۶۴۵ مورخ ۱۴۰۱/۰۹/۰۷",
        "short_name": "Consulting",
    },
    {
        "path": os.path.join(DATA_DIR, "موافقت_نامه،_شرایط_عمومی_و_خصوصی_پیمان_های_مهندسی،_تأمین_کالا_و.pdf"),
        "doc_type": "epc",
        "doc_title": "قرارداد همسان مهندسی، تأمین کالا، اجرا برای کارهای صنعتی",
        "circular_ref": "بخشنامه ۱۴۰۳/۳۷۰۳۰۹ مورخ ۱۴۰۳/۰۷/۲۸",
        "short_name": "EPC",
    },
    {
        "path": os.path.join(DATA_DIR, "موافقت_نامه،_شرایط_عمومی_و_خصوصی_پیمان_های_تأمین_مصالح_و_تجهیزات،.pdf"),
        "doc_type": "pc",
        "doc_title": "قرارداد همسان تأمین کالا، اجرا برای کارهای صنعتی",
        "circular_ref": "بخشنامه ۱۴۰۳/۴۰۲۴۶۲ مورخ ۱۴۰۳/۰۶/۰۵",
        "short_name": "PC",
    },
]

# ─────────────────────────────────────────────────────────
# Text extraction helpers
# ─────────────────────────────────────────────────────────

def normalize_arabic_to_persian(text: str) -> str:
    """تبدیل کاراکترهای عربی به فارسی + اعداد عربی-هندی به فارسی + NFKC normalization"""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    # حروف عربی به فارسی
    arabic_to_persian = {"ي": "ی", "ك": "ک", "ة": "ه", "ى": "ی"}
    # اعداد عربی-هندی (٠-٩) به فارسی (۰-۹) تا مدل LLM آن‌ها را صحیح بخواند
    arabic_indic_to_persian = {
        '٠': '۰', '١': '۱', '٢': '۲', '٣': '۳', '٤': '۴',
        '٥': '۵', '٦': '۶', '٧': '۷', '٨': '۸', '٩': '۹'
    }
    result = []
    for c in text:
        if c in arabic_indic_to_persian:
            result.append(arabic_indic_to_persian[c])
        elif c in arabic_to_persian:
            result.append(arabic_to_persian[c])
        else:
            result.append(c)
    return "".join(result)


def fix_rtl_numbers_in_text(text: str) -> str:
    """
    اصلاح اعداد معکوس شده ناشی از RTL در PDF
    
    در PDF های RTL فارسی، اعداد چند رقمی گاهی معکوس ذخیره می‌شوند:
    مثال: ۴۲ روز → "24 روز" در متن خام
    مثال: ۲۵ درصد → "52 درصد" در متن خام
    
    این تابع با استفاده از pattern اعداد-کلمه آن‌ها را شناسایی و برمی‌گرداند.
    """
    if not text:
        return text
    
    # الگوهای اعداد دورقمی که با واژه‌های توضیحی در پرانتز همراهند
    # مثال: 42 (چهلودو) یا 25 (بیستوپنج)
    def reverse_if_needed(m):
        num_str = m.group(1)
        desc = m.group(2)
        
        # اگر عدد دو رقمی است، بررسی کن آیا معکوس است
        if len(num_str) == 2:
            reversed_num = num_str[::-1]
            # تطابق با کلمه فارسی توضیحی
            persian_numbers = {
                '24': ('چهلودو', '42'), '52': ('بیستوپنج', '25'),
                '63': ('شصتوسه', '36'), '17': ('هفتادویک', '71'),
                '48': ('چهل', '84'), '91': ('نودویک', '19'),
                '12': ('بیستویک', '21'), '42': ('چهلودو', '42'),
                '25': ('بیستوپنج', '25'),
            }
            key = num_str
            if key in persian_numbers:
                fa_word, correct_num = persian_numbers[key]
                if fa_word in desc:
                    return f"{correct_num} ({desc})"
        return m.group(0)
    
    # الگو: عدد (متن فارسی داخل پرانتز)
    pattern = re.compile(r'\b(\d{2,3})\s*\(([^)]{3,30})\)')
    text = pattern.sub(reverse_if_needed, text)
    
    return text


def _fix_rtl_digit_sequences(text: str) -> str:
    """
    در PDF های فارسی RTL، اعداد چند رقمی به دلیل مرتب‌سازی RTL معکوس می‌شوند.
    مثال: "37" بعد از RTL sort به "73" تبدیل می‌شود.
    این تابع تمام دنباله‌های ۲+ رقمی را برمی‌گرداند.
    """
    # مطابقت اعداد ۲+ رقمی (Western, Arabic-Indic, Persian)
    return re.sub(r'[0-9٠-٩۰-۹]{2,}', lambda m: m.group()[::-1], text)


def extract_page_text_by_chars(page) -> str:
    """
    استخراج متن صفحه با ترتیب‌دهی مجدد کاراکترها بر اساس موقعیت (RTL)
    
    الگوریتم:
    1. گروه‌بندی کاراکترها بر اساس y (خطوط)
    2. در هر خط: مرتب‌سازی کاراکترها به صورت نزولی x (RTL) → متن فارسی صحیح
    3. اصلاح اعداد معکوس شده: دنباله‌های ۲+ رقم را برمی‌گردانیم
       (در PDF های RTL، اعداد در x صعودی ذخیره می‌شوند، پس پس از RTL sort معکوس می‌شوند)
    """
    chars = page.chars
    if not chars:
        return ""

    # گروه‌بندی کاراکترها بر اساس خط (y position با tolerance)
    y_tolerance = 3
    lines: Dict[float, list] = defaultdict(list)
    for char in chars:
        y_key = round(char["y0"] / y_tolerance) * y_tolerance
        lines[y_key].append(char)

    result_lines = []
    for y in sorted(lines.keys()):
        # مرتب‌سازی RTL (نزولی x) برای متن فارسی صحیح
        sorted_chars = sorted(lines[y], key=lambda c: -c["x0"])
        if not sorted_chars:
            continue

        line_text = "".join(normalize_arabic_to_persian(c["text"]) for c in sorted_chars).strip()
        if line_text:
            # اصلاح اعداد معکوس شده
            line_text = _fix_rtl_digit_sequences(line_text)
            result_lines.append(line_text)

    return "\n".join(result_lines)


def clean_text(text: str) -> str:
    """پاکسازی و نرمال‌سازی متن"""
    if not text:
        return ""
    # اصلاح اعداد معکوس شده
    text = fix_rtl_numbers_in_text(text)
    # حذف خطوط تکراری فقط عدد (شماره صفحه)
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # حذف خطوط با فقط اعداد (شماره صفحه)
        if re.match(r"^\d{1,3}$", stripped):
            continue
        # حذف خطوط بسیار کوتاه که احتمالاً header/footer هستند
        if len(stripped) < 2:
            continue
        cleaned.append(stripped)
    return "\n".join(cleaned)


# ─────────────────────────────────────────────────────────
# OCR-based extraction (fallback for broken font encoding)
# ─────────────────────────────────────────────────────────

def is_text_garbled(text: str, sample_size: int = 500) -> bool:
    """
    تشخیص متن خراب ناشی از encoding نادرست فونت B Nazanin
    
    در PDFهای با encoding شکسته، اعراب عربی (U+064B–U+0654) به‌جای
    حروف اصلی استفاده می‌شوند. نسبت بالای اعراب = متن خراب.
    """
    if not text:
        return False
    sample = text[:sample_size]
    total_arabic = sum(1 for c in sample if '\u0600' <= c <= '\u06FF')
    if total_arabic < 20:
        return False
    # اعراب: harakat (tashkeel) characters
    diacritics = sum(1 for c in sample if '\u064B' <= c <= '\u0654')
    ratio = diacritics / total_arabic if total_arabic > 0 else 0
    # در متن سالم فارسی نسبت اعراب معمولاً زیر ۵٪ است
    # در متن خراب B Nazanin این نسبت به ۲۰–۵۰٪ می‌رسد
    return ratio > 0.15


def extract_page_with_ocr(fitz_page, ocr_reader, dpi: int = 150) -> str:
    """
    استخراج متن یک صفحه PDF با EasyOCR (برای PDFهای با فونت خراب)
    
    الگوریتم:
    1. رندر صفحه به تصویر با DPI مشخص
    2. اجرای OCR با مدل فارسی/انگلیسی
    3. مرتب‌سازی نتایج: بر اساس Y (بالا→پایین) و X نزولی (RTL)
    4. تبدیل اعداد عربی-هندی به فارسی
    """
    import numpy as np
    from PIL import Image
    
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = fitz_page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    img_bytes = pix.tobytes("png")
    img_np = np.array(Image.open(io.BytesIO(img_bytes)))
    
    results = ocr_reader.readtext(img_np, detail=1, paragraph=False)
    if not results:
        return ""
    
    # مرتب‌سازی: گروه‌بندی خطوط بر اساس Y با tolerance
    y_tolerance = 20
    lines: Dict[int, list] = defaultdict(list)
    for bbox, text, conf in results:
        if conf < 0.3 or not text.strip():
            continue
        top_y = int(bbox[0][1])
        y_key = round(top_y / y_tolerance) * y_tolerance
        lines[y_key].append((bbox[0][0], text))
    
    sorted_text_lines = []
    for y_key in sorted(lines.keys()):
        # در هر خط از راست به چپ (نزولی X)
        line_items = sorted(lines[y_key], key=lambda item: -item[0])
        line_str = " ".join(item[1] for item in line_items).strip()
        if line_str:
            sorted_text_lines.append(line_str)
    
    page_text = "\n".join(sorted_text_lines)
    return normalize_arabic_to_persian(page_text)


_ocr_reader_cache = None

def get_ocr_reader():
    """بارگذاری OCR reader (singleton با cache)"""
    global _ocr_reader_cache
    if _ocr_reader_cache is None:
        import easyocr
        logger.info("  🔤 Loading EasyOCR (fa+en)...")
        _ocr_reader_cache = easyocr.Reader(['fa', 'en'], gpu=True)
        logger.info("  ✅ EasyOCR loaded")
    return _ocr_reader_cache


def extract_pdf_content_with_ocr(pdf_path: str) -> str:
    """
    استخراج کامل متن PDF با OCR (برای فایل‌هایی که encoding فونت خراب دارند)
    
    ترتیب: صفحه به صفحه، رندر → OCR → ترکیب نتایج
    """
    import fitz as _fitz
    
    ocr_reader = get_ocr_reader()
    doc = _fitz.open(pdf_path)
    total_pages = len(doc)
    logger.info(f"  🔤 OCR extraction: {total_pages} pages...")
    
    page_texts = []
    for page_idx in range(total_pages):
        page = doc[page_idx]
        page_text = extract_page_with_ocr(page, ocr_reader, dpi=150)
        if page_text:
            page_texts.append(f"\n--- صفحه {page_idx + 1} ---\n{clean_text(page_text)}")
        logger.info(f"  📄 OCR page {page_idx + 1}/{total_pages}: {len(page_text)} chars")
    
    doc.close()
    return "\n".join(page_texts)


def extract_pdf_content(pdf_path: str, table_processor) -> Tuple[str, List[Dict]]:
    """
    استخراج کامل محتوای PDF:
    - متن با روش char-position (بهترین نتیجه برای فارسی)
    - در صورت تشخیص encoding خراب (مثل B Nazanin): fallback به OCR
    - جداول با AdvancedPDFTableProcessor
    
    Returns:
        (full_text, tables_list)
    """
    import pdfplumber

    logger.info(f"  📄 Opening PDF with pdfplumber...")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    page_texts = []
    needs_ocr = False

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        total_pages = len(pdf.pages)
        logger.info(f"  📋 Total pages: {total_pages}")

        # بررسی اولیه: آیا encoding فونت خراب است؟
        # صفحه اول اغلب جلد/بخشنامه است و ممکن است font متفاوت داشته باشد
        # بنابراین صفحات میانی (2 تا 6) را بررسی می‌کنیم
        garbled_pages = 0
        check_pages = min(6, total_pages)
        for i in range(1, check_pages):   # از صفحه 2 (index=1) شروع می‌کنیم
            page_text = extract_page_text_by_chars(pdf.pages[i])
            if is_text_garbled(page_text, sample_size=len(page_text)):
                garbled_pages += 1

        # اگر اکثر صفحات بررسی‌شده خراب هستند → OCR
        if garbled_pages >= max(1, (check_pages - 1) // 2):
            logger.warning(f"  ⚠️ Garbled font encoding detected (B Nazanin broken CMap)")
            logger.warning(f"     → Switching to OCR-based extraction")
            needs_ocr = True
        else:
            logger.info(f"  ✅ Font encoding OK → using direct text extraction")

        if not needs_ocr:
            for i, page in enumerate(pdf.pages):
                # روش اول: char-position (بهترین برای فارسی)
                char_text = extract_page_text_by_chars(page)

                # روش دوم: extract_text fallback
                if not char_text or len(char_text) < 50:
                    raw_text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                    char_text = table_processor.fix_rtl_text(raw_text)

                char_text = clean_text(char_text)
                if char_text:
                    page_texts.append(f"\n--- صفحه {i+1} ---\n{char_text}")
                    logger.debug(f"  Page {i+1}: {len(char_text)} chars")

    if needs_ocr:
        # OCR extraction (برای PDFهای با encoding خراب مثل قراردادهای مشاوره)
        full_text = extract_pdf_content_with_ocr(pdf_path)
        tables = []
        logger.info(f"  ℹ️ Table extraction skipped (OCR mode, tables not reliably extractable)")
    else:
        full_text = "\n".join(page_texts)

        # استخراج جداول
        logger.info(f"  📊 Extracting tables...")
        try:
            tables = table_processor.extract_tables_advanced(pdf_bytes)
            logger.info(f"  ✅ {len(tables)} tables extracted")
        except Exception as e:
            logger.warning(f"  ⚠️ Table extraction error: {e}")
            tables = []

    return full_text, tables


def table_to_text(table: Dict, doc_short_name: str) -> str:
    """تبدیل جدول به متن ساختاریافته"""
    lines = [f"[جدول - سند {doc_short_name} - صفحه {table.get('page', '?')}]"]

    headers = table.get("headers", [])
    if headers:
        header_paths = [h.get("full_path", "") for h in headers]
        lines.append("ستون‌ها: " + " | ".join(p for p in header_paths if p))

    rows = table.get("rows", [])
    for row in rows[:30]:  # max 30 rows per table
        cells = [str(c) for c in row.get("cells", []) if c and str(c).strip()]
        if cells:
            lines.append(" | ".join(cells))

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────
# Smart article-based chunking for legal documents
# ─────────────────────────────────────────────────────────

def _fix_fidic_heading_order(text: str) -> str:
    """
    در قراردادهای FIDIC فارسی، عنوان هر ماده (مثل «ماده ۶۷ - خاتمۀ پیمان بنا بر مصلحت کارفرما»)
    در حاشیه راست صفحه قرار می‌گیرد. پس از استخراج RTL، این عنوان یک یا دو خط پایین‌تر از
    اولین جمله محتوای آن ماده ظاهر می‌شود. این تابع هر عنوان را یک خط بالاتر منتقل می‌کند
    تا chunking صحیح انجام شود.

    مثال (قبل از اصلاح):
      کارفرما می‌تواند بنا به مصلحت خود و بدون اعلام دلیل...
      ماده ۶۷ - خاتمۀ پیمان بنا بر مصلحت کارفرما
      از تأخیر در اتمام...

    مثال (بعد از اصلاح):
      ماده ۶۷ - خاتمۀ پیمان بنا بر مصلحت کارفرما
      کارفرما می‌تواند بنا به مصلحت خود و بدون اعلام دلیل...
      از تأخیر در اتمام...
    """
    # الگوی شناسایی عنوان ماده با محتوای معنادار (نه فقط شماره یا دش)
    heading_re = re.compile(r'^ماده\s+\d+\s*[-–]\s*\S.{5,}', re.UNICODE)
    # الگوی شماره صفحه (عددی ۱-۳ رقمی یا فارسی)
    page_num_re = re.compile(r'^[\d۰-۹]{1,3}$')

    lines = text.split('\n')
    result: List[str] = []

    for line in lines:
        stripped = line.strip()
        if heading_re.match(stripped):
            # به عقب برو و آخرین خط محتوایی (غیر خالی، غیر شماره‌صفحه، غیر عنوان) را بردار
            moved = []
            j = len(result) - 1
            while j >= 0:
                prev = result[j].strip()
                if not prev:
                    j -= 1
                    continue
                if page_num_re.match(prev):
                    # شماره صفحه را حذف کن (در جای خود نگه دار تا بعد پاکسازی شود)
                    j -= 1
                    continue
                if heading_re.match(prev):
                    # عنوان دیگری → متوقف شو
                    break
                # این یک خط محتوایی است → آن را بردار
                moved.insert(0, result.pop(j))
                # فقط یک خط محتوایی را جابه‌جا کن (اولین جمله ماده جدید)
                break
            result.append(line)       # عنوان اول
            result.extend(moved)      # سپس محتوا
        else:
            result.append(line)

    return '\n'.join(result)


def smart_chunk_legal_text(
    text: str,
    doc_info: Dict,
    chunk_size: int = 800,
    overlap: int = 100,
) -> List[Dict[str, Any]]:
    """
    Chunking هوشمند برای اسناد حقوقی:
    - ترجیحاً هر ماده یک chunk جداگانه
    - برای مواد طولانی، با overlap تقسیم می‌شود
    - متادیتا شامل شماره ماده، نوع سند و صفحه
    """
    chunks = []
    chunk_idx = 0

    # الگوهای تشخیص ماده و بند
    article_pattern = re.compile(
        r"(?:^|\n)\s*(ماده\s+\d+|ماده\s+[۰-۹]+|بند\s+\d+[-\.]?\d*|تبصره\s*\d*)",
        re.MULTILINE,
    )

    # تقسیم متن به صفحات برای حفظ اطلاعات صفحه
    pages = re.split(r"--- صفحه (\d+) ---", text)

    current_page = 1
    full_segments = []

    for i, part in enumerate(pages):
        if re.match(r"^\d+$", part.strip()):
            current_page = int(part.strip())
        else:
            cleaned = part.strip()
            if cleaned:
                full_segments.append((current_page, cleaned))

    # Build flat_text while tracking char-position → page mapping
    flat_parts = []
    pos_to_page = []  # list of (start_char_pos, page_num)
    current_pos = 0
    for page_num, seg_text in full_segments:
        pos_to_page.append((current_pos, page_num))
        flat_parts.append(seg_text)
        current_pos += len(seg_text) + 1  # +1 for the "\n" join

    flat_text = "\n".join(flat_parts)

    # اصلاح ترتیب عناوین مواد در قراردادهای FIDIC
    # در این PDF ها، عنوان هر ماده در حاشیه راست چاپ می‌شود و
    # پس از استخراج RTL، عنوان یک خط بعد از اولین محتوای آن ماده ظاهر می‌شود.
    # این تابع عنوان را به قبل از محتوای آن منتقل می‌کند.
    flat_text = _fix_fidic_heading_order(flat_text)

    def _page_for_pos(pos: int) -> int:
        """Return page number for a character position in flat_text."""
        result = 1
        for start, pg in pos_to_page:
            if start <= pos:
                result = pg
            else:
                break
        return result

    # پیدا کردن مواد
    article_matches = list(article_pattern.finditer(flat_text))

    if len(article_matches) > 3:
        # chunking بر اساس مواد
        for j, match in enumerate(article_matches):
            start = match.start()
            end = article_matches[j + 1].start() if j + 1 < len(article_matches) else len(flat_text)
            article_text = flat_text[start:end].strip()

            if not article_text or len(article_text) < 20:
                continue

            article_header = match.group(1).strip()
            page_num = _page_for_pos(start)

            # اگر ماده خیلی بزرگ است، تقسیم کن
            if len(article_text) > chunk_size * 2:
                sub_chunks = _split_long_text(article_text, chunk_size, overlap)
                for k, sub in enumerate(sub_chunks):
                    chunks.append({
                        "text": sub,
                        "chunk_index": chunk_idx,
                        "metadata": {
                            **doc_info,
                            "article": article_header,
                            "page": page_num,
                            "sub_chunk": k,
                            "chunk_type": "article_part",
                        },
                    })
                    chunk_idx += 1
            else:
                chunks.append({
                    "text": article_text,
                    "chunk_index": chunk_idx,
                    "metadata": {
                        **doc_info,
                        "article": article_header,
                        "page": page_num,
                        "sub_chunk": 0,
                        "chunk_type": "article",
                    },
                })
                chunk_idx += 1
    else:
        # چون مواد کمی پیدا شد، از sliding window استفاده کن
        logger.info("  ⚠️ Few articles found, falling back to sliding window chunking")
        sub_chunks = _split_long_text(flat_text, chunk_size, overlap)
        for k, sub in enumerate(sub_chunks):
            chunks.append({
                "text": sub,
                "chunk_index": chunk_idx,
                "metadata": {
                    **doc_info,
                    "page": _page_for_pos(0),
                    "sub_chunk": k,
                    "chunk_type": "sliding_window",
                },
            })
            chunk_idx += 1

    return chunks


def _split_long_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """تقسیم متن طولانی با sliding window"""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:].strip())
            break

        # پیدا کردن نقطه شکست مناسب (پایان جمله یا خط)
        break_point = end
        for sep in ["\n", ".", "،", " "]:
            pos = text.rfind(sep, start + chunk_size // 2, end)
            if pos > start:
                break_point = pos + 1
                break

        chunk = text[start:break_point].strip()
        if chunk:
            chunks.append(chunk)
        start = break_point - overlap
        if start < 0:
            start = 0

    return chunks


# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────

def main():
    logger.info("=" * 70)
    logger.info("🚀 شروع ساخت کالکشن zavabet (روش: پردازش مستقیم PDF)")
    logger.info("=" * 70)

    import pdfplumber
    import chromadb
    from processors.advanced_pdf_table_processor import AdvancedPDFTableProcessor
    from processors.intelligent_chunker import IntelligentChunker, ContentType
    from sentence_transformers import SentenceTransformer

    # ─── init ───────────────────────────────────────────
    table_processor = AdvancedPDFTableProcessor()
    chunker = IntelligentChunker(use_langchain=True)

    logger.info(f"🔄 Loading embedding model: {EMBEDDING_MODEL}")
    embed_model = SentenceTransformer(EMBEDDING_MODEL)
    logger.info(f"✅ Embedding model loaded (dim={embed_model.get_sentence_embedding_dimension()})")

    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    # ─── process PDFs ───────────────────────────────────
    all_chunk_dicts: List[Dict[str, Any]] = []
    global_chunk_offset = 0

    for pdf_info in PDF_FILES:
        pdf_path = pdf_info["path"]
        short_name = pdf_info["short_name"]
        doc_type = pdf_info["doc_type"]

        logger.info("")
        logger.info(f"{'='*60}")
        logger.info(f"📄 Processing: {short_name}")
        logger.info(f"   {pdf_path}")
        logger.info(f"{'='*60}")

        if not os.path.exists(pdf_path):
            logger.error(f"❌ File not found: {pdf_path}")
            continue

        start_time = time.time()
        filename = os.path.basename(pdf_path)

        try:
            # استخراج متن و جداول
            full_text, tables = extract_pdf_content(pdf_path, table_processor)
            logger.info(f"  ✅ Text: {len(full_text):,} chars, Tables: {len(tables)}")

            if not full_text.strip():
                logger.error(f"  ❌ No text extracted! Skipping.")
                continue

            doc_info = {
                "doc_type": doc_type,
                "doc_title": pdf_info["doc_title"],
                "circular_ref": pdf_info["circular_ref"],
                "short_name": short_name,
                "source_file": filename,
                "collection": COLLECTION_NAME,
            }

            # Chunking متن اصلی با الگوریتم هوشمند قانونی
            logger.info(f"  ✂️ Chunking text...")
            text_chunks = smart_chunk_legal_text(
                full_text,
                doc_info,
                chunk_size=700,
                overlap=100,
            )
            logger.info(f"  ✅ {len(text_chunks)} text chunks")

            # اضافه کردن chunks جداول
            table_chunks = []
            for t_idx, table in enumerate(tables):
                t_text = table_to_text(table, short_name)
                if t_text and len(t_text) > 30:
                    table_chunks.append({
                        "text": t_text,
                        "chunk_index": len(text_chunks) + t_idx,
                        "metadata": {
                            **doc_info,
                            "page": table.get("page", 0),
                            "chunk_type": "table",
                            "table_index": t_idx,
                        },
                    })

            logger.info(f"  ✅ {len(table_chunks)} table chunks")

            # reindex با global offset
            all_new = text_chunks + table_chunks
            for chunk_dict in all_new:
                chunk_dict["chunk_index"] = global_chunk_offset + chunk_dict["chunk_index"]

            global_chunk_offset += len(all_new)
            all_chunk_dicts.extend(all_new)

            elapsed = time.time() - start_time
            logger.info(f"  ⏱️ {elapsed:.1f}s | Cumulative chunks: {len(all_chunk_dicts)}")

        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            continue

    if not all_chunk_dicts:
        logger.error("❌ No chunks collected. Aborting.")
        return False

    logger.info("")
    logger.info(f"🔄 Generating embeddings for {len(all_chunk_dicts)} chunks...")
    embed_start = time.time()

    texts_to_embed = [c["text"] for c in all_chunk_dicts]
    batch_size = 32
    all_embeddings = []

    for i in range(0, len(texts_to_embed), batch_size):
        batch = texts_to_embed[i: i + batch_size]
        embs = embed_model.encode(batch, show_progress_bar=False).tolist()
        all_embeddings.extend(embs)
        logger.info(f"  Embedded {min(i + batch_size, len(texts_to_embed))}/{len(texts_to_embed)}")

    logger.info(f"  ✅ Embeddings done in {time.time() - embed_start:.1f}s")

    # ─── save to ChromaDB ────────────────────────────────
    logger.info("")
    logger.info(f"💾 Saving {len(all_chunk_dicts)} chunks to ChromaDB collection: {COLLECTION_NAME}")

    try:
        chroma_client.delete_collection(COLLECTION_NAME)
        logger.info(f"  🗑️ Deleted existing collection")
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        metadata={
            "description": "ضوابط نظام فنی و اجرایی کشور - Consulting, EPC, PC",
            "sources": "consulting, epc, pc",
            "processing_type": "direct_pdf_text",
            "embedding_model": EMBEDDING_MODEL,
            "embedding_dim": str(EMBEDDING_DIM),
            "hnsw:space": "cosine",
        },
    )

    ids = []
    documents = []
    embeddings = []
    metadatas = []
    skipped = 0

    for i, (chunk_dict, emb) in enumerate(zip(all_chunk_dicts, all_embeddings)):
        text = chunk_dict["text"].strip()
        if not text or len(text) < 10:
            skipped += 1
            continue

        chunk_id = f"{COLLECTION_NAME}_{chunk_dict['chunk_index']}"
        ids.append(chunk_id)
        documents.append(text)
        embeddings.append(emb)

        meta = {k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                for k, v in chunk_dict["metadata"].items()
                if v is not None}
        metadatas.append(meta)

    if skipped:
        logger.warning(f"  ⚠️ Skipped {skipped} empty chunks")

    save_batch_size = 100
    total_saved = 0
    for i in range(0, len(ids), save_batch_size):
        end = min(i + save_batch_size, len(ids))
        collection.add(
            ids=ids[i:end],
            documents=documents[i:end],
            embeddings=embeddings[i:end],
            metadatas=metadatas[i:end],
        )
        total_saved += end - i
        logger.info(f"  💾 Saved batch {i//save_batch_size + 1}: {end-i} chunks (total: {total_saved})")

    logger.info("")
    logger.info("=" * 70)
    logger.info("✅ کالکشن zavabet با موفقیت ساخته شد!")
    logger.info(f"   📦 Collection: {COLLECTION_NAME}")
    logger.info(f"   📝 Total chunks saved: {total_saved}")
    logger.info(f"   🔢 Embedding dim: {EMBEDDING_DIM}")
    logger.info(f"   🤖 Model: {EMBEDDING_MODEL}")
    logger.info(f"   📄 Source PDFs: {len(PDF_FILES)}")
    logger.info("=" * 70)

    # ─── quick search test ───────────────────────────────
    logger.info("\n🔍 Running quick search test...")
    test_queries = [
        "مسئولیت طراحی در قرارداد EPC",
        "صحه‌گذاری اسناد فنی پیمانکار",
        "سقف تغییرات مبلغ پیمان ۲۵ درصد",
    ]

    for query in test_queries:
        try:
            q_emb = embed_model.encode(query).tolist()
            results = collection.query(
                query_embeddings=[q_emb],
                n_results=2,
                include=["documents", "metadatas", "distances"],
            )
            best = results["documents"][0][0] if results["documents"][0] else "N/A"
            dist = results["distances"][0][0] if results["distances"][0] else 1.0
            sname = results["metadatas"][0][0].get("short_name", "?") if results["metadatas"][0] else "?"
            logger.info(f"  Query: '{query}'")
            logger.info(f"  Best [{sname}] (dist={dist:.3f}): {best[:120]}")
        except Exception as e:
            logger.error(f"  Search test failed: {e}")

    logger.info("\n✅ همه چیز آماده است!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
