# -*- coding: utf-8 -*-
"""
Dynamic Title Extractor - استخراج‌کننده داینامیک عناوین
استخراج واقعی و داینامیک عناوین از PDF بدون نیاز به داده استاتیک
"""

import re
import logging
import unicodedata
from typing import Dict, Any, List, Optional, Tuple
import pdfplumber
from bidi.algorithm import get_display
import arabic_reshaper

logger = logging.getLogger(__name__)


class DynamicTitleExtractor:
    """
    استخراج‌کننده داینامیک عناوین
    استخراج واقعی عناوین از جداول PDF به صورت کاملاً داینامیک
    """
    
    def __init__(self, pdf_path: str):
        """مقداردهی اولیه"""
        self.pdf_path = pdf_path
        self.extracted_structure = {
            'parts': {},      # {code: title}
            'sections': {},   # {code: title}
            'clauses': {},    # {code: title}
            'items': {}       # {code: title}
        }
        
        # الگوهای تشخیص سطح
        self.level_patterns = {
            'part': r'^100000$',               # 100000
            'section': r'^1[1-6]0000$',        # 110000-160000
            'clause': r'^1[1-6]\d{2}00$',      # 110100-160100
            'item': r'^1[1-6]\d{4}$'           # 110101-160199
        }
        
        # استخراج ساختار
        self._extract_structure()
    
    def normalize_persian_text(self, text: str) -> str:
        """تبدیل کاراکترهای presentation form به فارسی استاندارد"""
        if not text:
            return ""
        
        normalized = unicodedata.normalize('NFKC', text)
        
        arabic_to_persian = {
            'ي': 'ی', 'ك': 'ک', 'ﻱ': 'ی', 'ﻙ': 'ک',
            'ﺍ': 'ا', 'ﺏ': 'ب', 'ﺕ': 'ت', 'ﺙ': 'ث',
            'ﺝ': 'ج', 'ﺡ': 'ح', 'ﺥ': 'خ', 'ﺩ': 'د',
            'ﺫ': 'ذ', 'ﺭ': 'ر', 'ﺯ': 'ز', 'ﺱ': 'س',
            'ﺵ': 'ش', 'ﺹ': 'ص', 'ﺽ': 'ض', 'ﻁ': 'ط',
            'ﻅ': 'ظ', 'ﻉ': 'ع', 'ﻍ': 'غ', 'ﻑ': 'ف',
            'ﻕ': 'ق', 'ﻝ': 'ل', 'ﻡ': 'م', 'ﻥ': 'ن',
            'ﻩ': 'ه', 'ﻭ': 'و'
        }
        
        result = []
        for char in normalized:
            result.append(arabic_to_persian.get(char, char))
        
        return ''.join(result)
    
    def fix_rtl_text(self, text: str) -> str:
        """
        رفع کامل مشکل RTL/Reversed text با الگوریتم بهبود یافته برای عناوین طولانی
        
        مثال:
        Input:  "ﻞﮐ ﻊﻤﺟ | ﻲﺻﺎﺼﺘﺧﺍ | ﻲﻣﻮﻤﻋ"
        Output: "جمع کل | اختصاصی | عمومی"
        """
        if not text or not isinstance(text, str):
            return ""
        
        try:
            # 1. Convert presentation forms to standard
            normalized = self.normalize_persian_text(text)
            
            # 2. برای عناوین طولانی، الگوریتم هوشمندتر استفاده کن
            if len(normalized) > 100:  # عنوان طولانی
                return self._fix_long_title(normalized)
            
            # 3. برای متن‌های کوتاه، روش قبلی
            return self._fix_short_text(normalized)
            
        except Exception as e:
            logger.warning(f"RTL fix failed for '{text[:30]}': {e}")
            return text
    
    def _fix_long_title(self, text: str) -> str:
        """رفع مشکل RTL برای عناوین طولانی با الگوریتم هوشمند"""
        # برای عناوین طولانی، از الگوریتم تشخیص ترتیب کلمات استفاده کن
        return self._smart_word_order_fix(text)
    
    def _smart_word_order_fix(self, text: str) -> str:
        """الگوریتم هوشمند برای تشخیص و تصحیح ترتیب کلمات"""
        # تقسیم متن به کلمات
        words = text.split()
        
        # تشخیص کلمات کلیدی که معمولاً در ابتدای جمله می‌آیند
        start_keywords = ['مالیات', 'درآمد', 'حاصل', 'فعالیت', 'واحدهای', 'شرکت', 'موسسات']
        end_keywords = ['اقتصادی', 'اجتماعی', 'فرهنگی', 'موضوع', 'بند', 'ماده', 'قانون']
        
        # اگر متن با کلمات انتهایی شروع می‌شود و با کلمات ابتدایی تمام می‌شود، احتمالاً معکوس است
        first_words = words[:3] if len(words) >= 3 else words
        last_words = words[-3:] if len(words) >= 3 else words
        
        start_matches = sum(1 for word in first_words if any(keyword in word for keyword in start_keywords))
        end_matches = sum(1 for word in last_words if any(keyword in word for keyword in end_keywords))
        
        # اگر بیشتر کلمات انتهایی در ابتدا هستند، متن معکوس است
        if end_matches > start_matches and len(words) > 5:
            # معکوس کردن ترتیب کلمات
            reversed_words = words[::-1]
            
            # هر کلمه را جداگانه fix کن (فقط کاراکترها)
            fixed_words = []
            for word in reversed_words:
                if re.match(r'^[\d,\.]+$', word):
                    fixed_words.append(word)  # اعداد را دست نزن
                else:
                    # فقط کاراکترها را معکوس کن، نه ترتیب کلمات
                    fixed_words.append(word[::-1])
            
            return ' '.join(fixed_words)
        else:
            # متن احتمالاً درست است، فقط کاراکترها را fix کن
            fixed_words = []
            for word in words:
                if re.match(r'^[\d,\.]+$', word):
                    fixed_words.append(word)
                else:
                    fixed_words.append(word[::-1])
            return ' '.join(fixed_words)
    
    def _fix_short_text(self, text: str) -> str:
        """رفع مشکل RTL برای متن‌های کوتاه"""
        # Split by separators, reverse each part (both words and characters)
        parts = []
        for part in re.split(r'(\s*[|،,]\s*)', text):
            if part.strip() and not re.match(r'^\s*[|،,]\s*$', part):
                # This is content, reverse both word order and character order
                words = part.split()
                reversed_words = []
                for word in words:
                    # اگر کلمه عدد است، reverse نکن
                    if re.match(r'^[\d,\.]+$', word):
                        reversed_words.append(word)
                    else:
                        # کلمه فارسی → reverse characters
                        reversed_words.append(word[::-1])
                # Reverse word order
                reversed_words = reversed_words[::-1]
                parts.append(' '.join(reversed_words))
            else:
                # This is separator
                parts.append(part)
        
        return ''.join(parts)
    
    def _detect_level(self, code: str) -> str:
        """تشخیص سطح کد"""
        for level, pattern in self.level_patterns.items():
            if re.match(pattern, code):
                return level
        return 'unknown'
    
    def _extract_structure(self):
        """استخراج ساختار از PDF"""
        logger.info(f"🔍 استخراج ساختار از PDF: {self.pdf_path}")
        
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    self._process_page(page, page_num + 1)
            
            logger.info(f"✅ استخراج ساختار کامل شد:")
            logger.info(f"   - Parts: {len(self.extracted_structure['parts'])}")
            logger.info(f"   - Sections: {len(self.extracted_structure['sections'])}")
            logger.info(f"   - Clauses: {len(self.extracted_structure['clauses'])}")
            logger.info(f"   - Items: {len(self.extracted_structure['items'])}")
            
        except Exception as e:
            logger.error(f"خطا در استخراج ساختار: {e}")
    
    def _process_page(self, page, page_num: int):
        """پردازش یک صفحه"""
        
        # استخراج جداول
        tables = page.extract_tables()
        
        for table in tables:
            if table and len(table) > 0:
                self._process_table(table, page_num)
    
    def _process_table(self, table: List[List], page_num: int):
        """پردازش جدول"""
        
        for row_idx, row in enumerate(table):
            if not row:
                continue
            
            # جستجوی کد در تمام ستون‌ها
            codes_found = []
            titles_found = []
            
            for col_idx, cell in enumerate(row):
                if cell:
                    cell_str = str(cell).strip()
                    
                    # جستجوی کدهای 6 رقمی
                    codes = re.findall(r'\b\d{6}\b', cell_str)
                    for code in codes:
                        codes_found.append((col_idx, code))
                    
                    # جستجوی متن فارسی (عناوین) - including presentation forms
                    if re.search(r'[\u0600-\u06FF\uFB50-\uFEFF]', cell_str):
                        title = self._extract_title(cell_str)
                        if title:
                            titles_found.append((col_idx, title))
            
            # پردازش کدهای پیدا شده
            for code_col, code in codes_found:
                level = self._detect_level(code)
                
                if level != 'unknown':
                    # پیدا کردن نزدیک‌ترین عنوان
                    title = self._find_nearest_title(code_col, titles_found)
                    
                    if title:
                        # ذخیره در ساختار
                        if level == 'part':
                            self.extracted_structure['parts'][code] = title
                        elif level == 'section':
                            self.extracted_structure['sections'][code] = title
                        elif level == 'clause':
                            self.extracted_structure['clauses'][code] = title
                        elif level == 'item':
                            self.extracted_structure['items'][code] = title
                        
                        logger.debug(f"   ✅ {code} ({level}): {title}")
    
    def _find_nearest_title(self, code_col: int, titles: List[Tuple[int, str]]) -> Optional[str]:
        """پیدا کردن نزدیک‌ترین عنوان به کد"""
        if not titles:
            return None
        
        # پیدا کردن نزدیک‌ترین عنوان بر اساس فاصله ستون
        min_distance = float('inf')
        nearest_title = None
        
        for title_col, title in titles:
            distance = abs(code_col - title_col)
            if distance < min_distance:
                min_distance = distance
                nearest_title = title
        
        return nearest_title
    
    def _extract_title(self, text: str) -> Optional[str]:
        """استخراج عنوان از متن - با رفع مشکل RTL"""
        if not text:
            return None
        
        # حذف whitespace اضافی
        text = text.strip()
        
        # اگر متن فارسی/عربی دارد (including presentation forms)
        if re.search(r'[\u0600-\u06FF\uFB50-\uFEFF]', text):
            # اعمال fix_rtl_text برای رفع مشکل visual-order encoding در PDF
            clean_text = text.strip(':،').strip()
            
            # حذف whitespace اضافی
            clean_text = re.sub(r'\s+', ' ', clean_text)
            
            # فقط اگر حداقل 3 کاراکتر فارسی/عربی داشته باشد
            persian_chars = len(re.findall(r'[\u0600-\u06FF\uFB50-\uFEFF]', clean_text))
            if persian_chars >= 3:
                # Fix RTL text before returning
                return self.fix_rtl_text(clean_text)
        
        return None
    
    def get_title(self, code: str) -> Optional[str]:
        """دریافت عنوان برای کد"""
        # جستجو در همه سطوح
        for level in ['parts', 'sections', 'clauses', 'items']:
            if code in self.extracted_structure[level]:
                return self.extracted_structure[level][code]
        
        return None
    
    def get_all_parts(self) -> Dict[str, str]:
        """دریافت همه قسمت‌ها"""
        return self.extracted_structure['parts'].copy()
    
    def get_all_sections(self) -> Dict[str, str]:
        """دریافت همه بخش‌ها"""
        return self.extracted_structure['sections'].copy()
    
    def get_all_clauses(self) -> Dict[str, str]:
        """دریافت همه بندها"""
        return self.extracted_structure['clauses'].copy()
    
    def get_all_items(self) -> Dict[str, str]:
        """دریافت همه ردیف‌ها"""
        return self.extracted_structure['items'].copy()
    
    def get_full_structure(self) -> Dict[str, Dict[str, str]]:
        """دریافت کل ساختار"""
        return {
            'parts': self.get_all_parts(),
            'sections': self.get_all_sections(),
            'clauses': self.get_all_clauses(),
            'items': self.get_all_items()
        }
    
    def print_structure(self):
        """چاپ ساختار استخراج شده"""
        print("\n📊 ساختار استخراج شده:")
        print("="*80)
        
        print(f"\n📋 قسمت‌ها ({len(self.extracted_structure['parts'])}):")
        for code, title in sorted(self.extracted_structure['parts'].items()):
            print(f"   • {code}: {title}")
        
        print(f"\n📋 بخش‌ها ({len(self.extracted_structure['sections'])}):")
        for code, title in sorted(self.extracted_structure['sections'].items()):
            print(f"   • {code}: {title}")
        
        print(f"\n📋 بندها ({len(self.extracted_structure['clauses'])}):")
        for code, title in sorted(self.extracted_structure['clauses'].items()):
            print(f"   • {code}: {title}")
        
        print(f"\n📋 ردیف‌ها ({len(self.extracted_structure['items'])}) - نمایش 10 مورد اول:")
        items = sorted(self.extracted_structure['items'].items())
        for code, title in items[:10]:
            print(f"   • {code}: {title}")
        if len(items) > 10:
            print(f"   ... و {len(items) - 10} ردیف دیگر")
