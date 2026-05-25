# -*- coding: utf-8 -*-
"""
Text Utilities Module
ابزارهای پردازش و نرمال‌سازی متن فارسی
"""

import re
import unicodedata
import logging
from typing import Set

logger = logging.getLogger(__name__)


class TextNormalizer:
    """کلاس برای نرمال‌سازی متن فارسی"""
    
    # Stopwords برای similarity calculation
    SIMILARITY_STOPWORDS = {
        "برای", "در", "از", "به", "و", "یا", "که", "چه", "چطور", "چگونه",
        "می", "شود", "است", "را", "تا", "با", "این", "آن", "یک", "اگر",
        "لطفا", "لطفاً", "پاسخ", "بده", "بدهید", "کنید", "کن", "شما", "ما",
        "من", "چیست", "کدام", "کجا", "چرا", "آیا", "هست", "هستند", "باشد",
        "باشند", "دارد", "دارند", "کنم", "کنیم", "بگویید", "بگو", "توضیح", "توضیحات"
    }
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """نرمال‌سازی متن فارسی"""
        if not text or str(text) in ['nan', 'None', '']:
            return ""
        
        text = str(text)
        
        persian_nums = '۰۱۲۳۴۵۶۷۸۹'
        arabic_nums = '٠١٢٣٤٥٦٧٨٩'
        english_nums = '0123456789'
        
        translation_map = {
            ord('ي'): 'ی',
            ord('ى'): 'ی',
            ord('ئ'): 'ی',
            ord('ك'): 'ک',
            ord('ۀ'): 'ه',
            ord('ة'): 'ه',
            ord('أ'): 'ا',
            ord('إ'): 'ا',
            ord('ٱ'): 'ا',
            ord('ؤ'): 'و',
            ord('\u200c'): ' ',  # zero width non-joiner -> space
            ord('\u200f'): '',   # right-to-left mark
            ord('\ufeff'): '',   # BOM
        }
        
        translate_digits = str.maketrans(persian_nums + arabic_nums, english_nums * 2)
        text = text.translate(translate_digits)
        text = text.translate(translation_map)
        
        # normalize extra spaces created after replacing zero-width characters
        text = ' '.join(text.split())
        
        return text.strip()
    
    @staticmethod
    def fix_persian_text_for_display(text: str) -> str:
        """Fix Persian text for proper display (remove presentation forms and fix visual-order text)"""
        if not text:
            return ""
        try:
            # مرحله 1: تبدیل presentation forms به حروف استاندارد
            fixed_text = ""
            has_presentation_forms = False
            
            for char in text:
                code_point = ord(char)
                # اگر کاراکتر در بازه presentation forms است
                if 0xFB50 <= code_point <= 0xFDFF or 0xFE70 <= code_point <= 0xFEFF:
                    has_presentation_forms = True
                    # استفاده از NFKC normalization
                    try:
                        normalized = unicodedata.normalize('NFKC', char)
                        fixed_text += normalized
                    except:
                        fixed_text += char
                else:
                    fixed_text += char
            
            if has_presentation_forms:
                text = fixed_text
            
            # مرحله 2: تشخیص متن معکوس (visual-order) و برگرداندن آن به logical-order
            words = text.split()
            if len(words) >= 4:
                reversed_pattern_count = 0
                
                for word in words:
                    if len(word) <= 1:
                        continue
                    
                    first_char = word[0]
                    last_char = word[-1]
                    
                    common_endings = ['ا', 'و', 'ی', 'ه', 'ن', 'ت', 'د', 'ر', 'ش', 'س']
                    common_starts_middles = ['ب', 'پ', 'ت', 'ث', 'ج', 'چ', 'ح', 'خ', 'د', 'ذ', 'ر', 'ز', 'ژ', 'س', 'ش', 'ص', 'ض', 'ط', 'ظ', 'ع', 'غ', 'ف', 'ق', 'ک', 'گ', 'ل', 'م', 'ن', 'و', 'ه', 'ی']
                    
                    if first_char in common_endings and last_char in common_starts_middles:
                        reversed_pattern_count += 1
                
                if reversed_pattern_count / len(words) > 0.5:
                    reversed_words = words[::-1]
                    text = ' '.join(reversed_words)
                    logger.debug(f"Visual-order text detected ({reversed_pattern_count}/{len(words)} words match pattern) and converted to logical-order")
            
            return text
        except Exception as e:
            logger.warning(f"Failed to fix Persian text: {e}")
            return text
    
    @staticmethod
    def normalize_colloquial_static(text: str) -> str:
        """تبدیل استاتیک عبارات محاوره‌ای به رسمی"""
        # ترتیب مهم است: کلمات طولانی‌تر اول
        colloquial_map = {
            'میتونم': 'می‌توانم',
            'میتونید': 'می‌توانید',
            'میتونن': 'می‌توانند',
            'نمیشه': 'نمی‌شود',
            'میشه': 'می‌شود',
            'چطوری': 'چگونه',
            'بگین': 'بگویید',
            'بگید': 'بگویید',
            'نیستن': 'نیستند',
            'هستن': 'هستند',
            'دارن': 'دارند',
            'داره': 'دارد',
            'پورتفو': 'پرتفوی',
            'پرتفو': 'پرتفوی',
            'کیه': 'کیست',
            'چیه': 'چیست',
            'چیاست': 'چیست',  # جدید: "روی چیاست" -> "روی چیست"
            'چیان': 'چیست',  # جدید: "چیان" -> "چیست" (قبل از "چیا" باید باشد)
            'چیا': 'چه',  # جدید: "روی چیا" -> "روی چه" (بعد از "چیان")
            'میکنه': 'می‌کند',  # جدید: "میکنه" -> "می‌کند"
            'میکنم': 'می‌کنم',  # جدید
            'میکنید': 'می‌کنید',  # جدید
            'میکنن': 'می‌کنند',  # جدید
            'سرمایه گذارای': 'سرمایه‌گذاران',  # جدید: "سرمایه گذارای" -> "سرمایه‌گذاران"
            'سرمایه گذاری': 'سرمایه‌گذاری',  # بهبود: فاصله
            'تون': 'تان',
            'مون': 'مان', 
            'شون': 'شان',
        }
        
        result = text
        # استفاده از word boundaries برای دقت بیشتر
        for colloquial, formal in colloquial_map.items():
            # Replace با word boundary برای کلمات کامل
            pattern = r'\b' + re.escape(colloquial) + r'\b'
            result = re.sub(pattern, formal, result)
            # همچنین replace ساده برای کلمات ترکیبی
            result = result.replace(colloquial, formal)
        
        # تبدیل پسوندهای محاوره‌ای در کلمات ترکیبی
        result = re.sub(r'(\w+)تون\b', r'\1 تان', result)
        result = re.sub(r'(\w+)مون\b', r'\1 مان', result)
        result = re.sub(r'(\w+)شون\b', r'\1 شان', result)
        
        # بهبود: تبدیل "چیاست" که در انتهای جمله است
        result = re.sub(r'چیاست\s*[؟?]*\s*$', 'چیست؟', result)
        result = re.sub(r'چیاست\s+', 'چیست ', result)
        
        # بهبود: تبدیل "چیا" در انتهای جمله به "چیست"
        result = re.sub(r'\s+چیا\s*[؟?]*\s*$', ' چیست؟', result)
        
        # بهبود: تبدیل "چیان" در انتهای جمله به "چیست"
        result = re.sub(r'\s+چیان\s*[؟?]*\s*$', ' چیست؟', result)
        
        # بهبود: تبدیل سوالات ناقص (بدون فعل سوالی) به سوال کامل
        # مثال: "ایمیل صندوق باور" -> "ایمیل صندوق باور چیست؟"
        if not re.search(r'[؟?]', result) and not re.search(r'\b(چیست|چیه|چیاست|چیا|چیان|چطور|چگونه|کجا|کی|چرا|آیا|چه)\b', result):
            # اگر سوال علامت ندارد و فعل سوالی ندارد، اضافه کردن "چیست؟"
            if len(result.split()) <= 5:  # فقط برای سوالات کوتاه
                result = result.rstrip('؟?') + ' چیست؟'
        
        return result
    
    @staticmethod
    def tokenize_meaningful(text: str, stopwords: Set[str] = None) -> Set[str]:
        """Tokenize متن و فیلتر کردن stopwords"""
        if stopwords is None:
            stopwords = TextNormalizer.SIMILARITY_STOPWORDS
        
        normalized = TextNormalizer.normalize_colloquial_static(text)
        tokens = normalized.split()
        filtered = [tok for tok in tokens if len(tok) > 2 and tok not in stopwords]
        return set(filtered or tokens)

