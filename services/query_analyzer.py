# -*- coding: utf-8 -*-
"""
Query Analyzer - تحلیل دقیق و جامع سوالات فارسی
این ماژول مسئول استخراج اطلاعات از سوال است:
- شناسایی نوع سوال (چقدر، چه دستگاهی، از چه راه‌هایی)
- استخراج نام دستگاه/سازمان
- استخراج عنوان جزء درآمد
- استخراج سال‌ها

🔧 بهبود: استفاده از SmartColumnDetector برای تشخیص هوشمند ستون‌ها
"""

import re
from typing import Dict, Any, List, Optional
import logging

# Import smart column detector
try:
    from .smart_column_detector import SmartColumnDetector, detect_columns, ColumnDetectionResult
    SMART_DETECTOR_AVAILABLE = True
except ImportError:
    SMART_DETECTOR_AVAILABLE = False

# Import hybrid entity mapper
try:
    from .hybrid_entity_mapper import HybridEntityMapper
    HYBRID_MAPPER_AVAILABLE = True
except ImportError:
    HYBRID_MAPPER_AVAILABLE = False

logger = logging.getLogger(__name__)


def get_device_column_name(table_name: str) -> str:
    """
    برگرداندن نام صحیح ستون دستگاه اجرایی بر اساس جدول
    
    Note: جداول مختلف از کاراکترهای متفاوت استفاده می‌کنند:
    - manabe_sheet1: عنوان_دستگاه_اجرایی (با ی فارسی)
    - masaref2_sheet1: عنوان_دستگاه_اجرايي (با ي عربی)
    """
    if table_name in ('masaref2_sheet1', 'masaref_sheet1'):
        return 'عنوان_دستگاه_اجرايي'  # با ي عربی
    else:
        return 'عنوان_دستگاه_اجرایی'  # با ی فارسی (default برای manabe_sheet1)


def get_parent_column_name(table_name: str) -> str:
    """
    برگرداندن نام صحیح ستون دستگاه اصلی بر اساس جدول
    """
    if table_name in ('masaref2_sheet1', 'masaref_sheet1'):
        return 'عنوان_دستگاه_اصلي'  # با ي عربی
    else:
        return 'عنوان_دستگاه_اصلی'  # با ی فارسی


def build_device_filter_sql(safe_value: str, table_name: str = None) -> str:
    """
    ساخت فیلتر SQL برای ستون‌های دستگاه بر اساس نوع جدول
    
    Args:
        safe_value: مقدار جستجو (باید escape شده باشد)
        table_name: نام جدول (برای تعیین نوع ستون‌ها)
    
    Returns:
        شرط SQL برای فیلتر کردن بر اساس ستون‌های دستگاه
    """
    # تعیین نوع ستون‌ها بر اساس جدول
    if table_name in ('masaref2_sheet1', 'masaref_sheet1'):
        # برای masaref: فقط ستون‌های عربی
        return (
            f"("
            f"TRANSLATE(\"عنوان_دستگاه_اجرايي\", 'يكيۀةأإٱ', 'یکیهههاا') ILIKE '%{safe_value}%' "
            f"OR TRANSLATE(\"عنوان_دستگاه_اصلي\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%{safe_value}%'"
            f")"
        )
    elif table_name == 'manabe_sheet1':
        # 🔧 CRITICAL FIX: استفاده از LIKE ساده به جای TRANSLATE برای اجتناب از PostgreSQL bug در OR
        return (
            f"("
            f"\"عنوان_دستگاه_اجرایی\" LIKE '%{safe_value}%' "
            f"OR \"عنوان_دستگاه_اصلی\" LIKE '%{safe_value}%'"
            f")"
        )
    else:
        # برای سایر جداول: استفاده از هر دو نوع برای سازگاری (fallback)
        return (
            f"("
            f"TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱ', 'یکیهههاا') ILIKE '%{safe_value}%' "
            f"OR TRANSLATE(\"عنوان_دستگاه_اجرايي\", 'يكيۀةأإٱ', 'یکیهههاا') ILIKE '%{safe_value}%' "
            f"OR TRANSLATE(\"عنوان_دستگاه_اصلی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%{safe_value}%' "
            f"OR TRANSLATE(\"عنوان_دستگاه_اصلي\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%{safe_value}%'"
            f")"
        )


class QueryAnalyzer:
    """تحلیلگر جامع سوالات مالی"""
    
    def __init__(self, collection_name: str = None, entity_mapper: Optional['HybridEntityMapper'] = None):
        """
        Args:
            collection_name: نام collection برای استفاده از entity mappings
            entity_mapper: HybridEntityMapper برای dynamic entity mapping (اختیاری)
        """
        self.collection_name = collection_name
        self.entity_mapper = entity_mapper
        
        # نقشه نرمال‌سازی کاراکترهای فارسی/عربی
        # ⚠️ CRITICAL: "آ" را به "ا" تبدیل نمی‌کنیم چون در فارسی متفاوت هستند
        # مثال: "درآمد" نباید به "درامد" تبدیل شود
        self.char_normalization_map = str.maketrans({
            'ي': 'ی',  # ی عربی به ی فارسی
            'ك': 'ک',  # ک عربی به ک فارسی
            'ة': 'ه',  # تاء مربوطه به ه
            'ۀ': 'ه',  # ه با همزه به ه
            'أ': 'ا',  # الف با همزه بالا به الف
            'إ': 'ا',  # الف با همزه پایین به الف
            'ٱ': 'ا',  # الف وصل به الف
            # 'آ': 'ا'  # ⚠️ حذف شد - آ و ا در فارسی متفاوت هستند
        })
        
        # کلمات توقف که entity نیستند
        self.stop_words = {
            'در', 'سال', 'های', 'سالهای', 'سالها', 'چقدر', 'مجموعا', 'چگونه',
            'چه', 'است', 'هست', 'کل', 'مجموع', 'جمع', 'درآمد', 'درامد', 'اختصاصی',
            'خصوصی', 'عمومی', 'ملی', 'ملي', 'استانی', 'استاني', 'چند', 'میلیارد', 'ميليارد',
            'استان', 'تمام', 'تمامی',
            'از', 'راه', 'راهی', 'راههایی', 'راه‌های', 'طریق', 'روش', 'هایی', 'کسب', 
            'کرده', 'داشته', 'تا', 'الی', 'می', 'می‌شود', 'می شود', 'مي', 'شده', 'گردد',
            'بوده', 'بود', 'و', 'یا', 'به', 'با', 'که', 'این', 'آن', 'برای', 'توسط',
            'دستگاهی', 'دستگاه', 'دستگاهها', 'وصول', 'شد', 'خواهد', 'شده', 'قانون', 'ثبت', 'صدور',
            # کلمات محاوره‌ای و درخواستی
            'بگو', 'بگید', 'بگویید', 'بده', 'بدید', 'بدهید', 'بهم', 'بهت', 'بهش',
            'رو', 'را', 'میخوام', 'میخواهم', 'میخوای', 'میخواهی', 'لطفا', 'لطفاً',
            # کلمات پرسشی
            'کدام', 'کجا', 'چرا', 'چطور', 'چند', 'چی', 'چیست',
            # کلمات ترتیبی و تطبیقی
            'بیشترین', 'کمترین', 'برترین', 'بالاترین', 'پایینترین', 'اولین', 'آخرین',
            'بیشتر', 'کمتر', 'بالاتر', 'پایینتر', 'ترین', 'تر',
            # کلمات مربوط به زیان/سود/هزینه - بهبود: منابع=درآمد، مصارف=هزینه
            'زیان', 'زیانده', 'ضرر', 'سود', 'سودآور', 'تراز', 'هزینه', 'هزينه', 'اعتبار',
            'منابع', 'مصارف', 'تملک', 'تملك', 'دارایی', 'دارايي', 'سرمایه', 'سرمايه',  # کلمات مالی که entity نیستند
            # کلمات ربطی و حروف اضافه
            'بخشی', 'قسمتی', 'مقداری', 'هرکدام', 'هریک', 'همه', 'تمام', 'سهم', 'نسبت',
            'دارند', 'دارد', 'داشته', 'ندارد', 'ندارند', 'را', 'رو', 'ان', 'آن',
            'افزایش', 'کاهش', 'رشد', 'کاهشی', 'افزایشی', 'قبلی', 'قبل',  # کلمات مقایسه‌ای
            'خود', 'بیشتری', 'کمتری', 'تغییر',  # کلمات مقایسه‌ای اضافه
            # کلمات مرتبط با دستگاه
            'اجرایی', 'اجرايي', 'منتصب', 'وابسته', 'زیرمجموعه', 'هستند', 'باشند', 'می‌باشند',
            # 🔧 CRITICAL FIX: کلمات سلسله مراتبی که نباید به عنوان entity extract بشن
            'بخش', 'قسمت', 'بند', 'جزء', 'جزو', 'فصل', 'ماده'
        }
        
        # کلیدواژه‌های جزء درآمد (که در عنوان_جزء می‌آیند)
        self.income_component_keywords = {
            'حاصل', 'خدمات', 'فروش', 'عوارض', 'مالیات', 'مالیاتی', 'کارمزد', 
            'بهداشتی', 'درمانی', 'آموزشی', 'اموزشی', 'فرهنگی', 'گمرکی', 'تجاری',
            'صنعتی', 'کشاورزی', 'استانداردسازی', 'آزمایشگاهی', 'قضایی', 'ثبتی',
            'مخابراتی', 'تحقیقاتی', 'پژوهشی', 'رفاهی', 'الکترونیکی',
            'اجاره', 'اجار', 'ساختمان', 'ساختمانها', 'زمین', 'اراضی',
            'معاینه', 'فنی', 'جرایم', 'خسارات', 'واگذاری', 'مالکیت',
            'متفرقه', 'متفرقه‌ها', 'کمکهای', 'كمكهاي', 'اجتماعی', 'اجتماعي', 'ناشی', 'ناشي',
        }
    
    def normalize_text(self, text: str) -> str:
        """نرمال‌سازی متن فارسی"""
        if not text:
            return ''
        # حذف zero-width و right-to-left marks
        text = text.replace('\u200c', ' ').replace('\u200f', ' ')
        # نرمال‌سازی کاراکترها
        text = text.translate(self.char_normalization_map)
        # حذف فاصله‌های اضافی
        text = ' '.join(text.split())
        # اصلاح عبارات رایج با فاصله اضافی
        text = re.sub(r'در\s+ا\s*مد', 'درآمد', text, flags=re.IGNORECASE)
        text = re.sub(r'در\s+امد', 'درآمد', text, flags=re.IGNORECASE)
        text = re.sub(r'در\s+آمد', 'درآمد', text, flags=re.IGNORECASE)
        
        # اصلاح کلمات فارسی که به "در" چسبیده‌اند (مثل "تبریزدر" -> "تبریز در")
        # اما "درآمد" و کلماتی که "در" بخشی از آن‌هاست (مثل "مخدر") را نادیده می‌گیریم
        # فقط اگر "در" در انتهای کلمه باشد و بعد از آن space یا سال باشد
        text = re.sub(r'([آ-ی]{3,})(در)(?=\s+سال)', r'\1 \2', text, flags=re.IGNORECASE)
        
        # 🆕 اصلاح typo های رایج در نام سازمان‌ها
        text = self._fix_common_typos(text)
        
        return text
    
    def _fix_common_typos(self, text: str) -> str:
        """تصحیح typo های رایج در نام سازمان‌ها و عبارات"""
        # typo های رایج
        typo_fixes = {
            'پژوهکشده': 'پژوهشکده',  # کشده -> شکده
            'دانشکاه': 'دانشگاه',      # کاه -> گاه
            'وزرات': 'وزارت',          # رات -> ارت
            'سازمن': 'سازمان',         # من -> مان
        }
        
        for typo, correct in typo_fixes.items():
            # استفاده از word boundary برای match دقیق
            pattern = r'\b' + re.escape(typo) + r'\b'
            text = re.sub(pattern, correct, text, flags=re.IGNORECASE)
        
        # 🆕 Alias mapping - نام‌های متداول به نام‌های رسمی
        # این mapping برای سازمان‌هایی است که با نام‌های مختلف شناخته می‌شوند
        # نکته: باید از طولانی‌تر به کوتاه‌تر اعمال شود تا overlap نداشته باشیم
        alias_mapping = [
            ('سازمان گمرک', 'گمرک جمهوری اسلامی ایران'),
            # نکته: "گمرک" تنها را جایگزین نمی‌کنیم چون ممکن است بخشی از نام دیگری باشد
        ]
        
        for alias, official in alias_mapping:
            # استفاده از word boundary برای match دقیق
            pattern = r'\b' + re.escape(alias) + r'\b'
            text = re.sub(pattern, official, text, flags=re.IGNORECASE)
        
        return text
    
    def normalize_for_sql(self, text: str) -> str:
        """
        نرمال‌سازی متن برای استفاده در SQL ILIKE
        
        🔧 CRITICAL: Database از کاراکترهای عربی استفاده می‌کند (ي و ك)
        ولی TRANSLATE در SQL آن‌ها را به فارسی تبدیل می‌کند (ی و ک)
        پس search term هم باید به فارسی تبدیل شود تا match کند
        """
        if not text:
            return ''
        # حذف zero-width و right-to-left marks
        text = text.replace('\u200c', ' ').replace('\u200f', ' ')
        # تبدیل کاراکترهای عربی به فارسی (همان کاری که TRANSLATE در SQL انجام می‌دهد)
        text = text.translate(self.char_normalization_map)
        # حذف فاصله‌های اضافی
        text = ' '.join(text.split())
        return text
    
    def adjust_entity_filter_for_table(self, entity_filter: str, table_name: str) -> str:
        """
        تصحیح entity_filter برای table های مختلف
        
        Args:
            entity_filter: فیلتر entity ساخته شده
            table_name: نام جدول (مثل 'manabe_sheet1')
            
        Returns:
            فیلتر اصلاح شده
        """
        if not entity_filter or not table_name:
            return entity_filter
        
        # برای manabe_sheet1، عنوان_دستگاه باید به عنوان_دستگاه_اجرایی تبدیل بشه
        if table_name == 'manabe_sheet1':
            entity_filter = entity_filter.replace('"عنوان_دستگاه"', '"عنوان_دستگاه_اجرایی"')
        
        return entity_filter
    
    def _extract_keywords_from_component(self, component: str) -> List[str]:
        """
        استخراج کلمات کلیدی از component برای matching بهتر
        
        مثال: "بخش درآمدهای مالیاتی" → ["بخش", "مالیات"]
        
        Args:
            component: عبارت component
            
        Returns:
            لیست کلمات کلیدی (بدون کلمات توقف و کلمات کوچک)
        """
        if not component:
            return []
        
        # کلمات توقف که باید نادیده گرفته شوند
        stop_words_local = {
            'از', 'به', 'در', 'و', 'یا', 'که', 'این', 'آن', 'برای', 'با',
            'های', 'ها', 'ی', 'ه', 'اول', 'دوم', 'سوم', 'چهارم', 'پنجم',
            'ششم', 'هفتم', 'هشتم', 'نهم', 'دهم', ':', '-', '–'
        }
        
        # تبدیل به کلمات
        words = component.split()
        
        # فیلتر کردن کلمات
        keywords = []
        for word in words:
            # حذف کاراکترهای خاص
            word = word.strip(':-–')
            
            # skip کلمات توقف
            if word in stop_words_local or len(word) < 3:
                continue
            
            # نرمال‌سازی: حذف "های" یا "ها" از انتهای کلمات
            if word.endswith('های'):
                word = word[:-3]
            elif word.endswith('ها'):
                word = word[:-2]
            elif word.endswith('ی') and len(word) > 4:
                # "مالیاتی" → "مالیات"
                word = word[:-1]
            
            # اضافه کردن به لیست کلمات کلیدی
            if word and len(word) >= 3:
                keywords.append(word)
        
        logger.info(f"   📝 Extracted keywords from '{component}': {keywords}")
        return keywords
    
    def _detect_hierarchy_level_from_query(self, query: str, income_component: Optional[str]) -> Optional[str]:
        """
        تشخیص سطح سلسله مراتب از query
        
        اگر کاربر کلمه "بخش" یا "قسمت" یا "بند" یا "جزء" رو به کار برده،
        می‌فهمیم که می‌خواد در کدوم ستون جستجو کنیم.
        
        Returns:
            'بخش' | 'قسمت' | 'بند' | 'جزء' | None
        """
        if not query:
            return None
        
        # 🔧 IMPROVEMENT: حتی بدون income_component، اگر hierarchy keyword داریم، تشخیص بده
        # مثال: "منابع حاصل از بند درامد های حاصل از خدمات"
        # Note: این check فقط برای log است، ادامه کد برای همه cases کار می‌کنه
        
        query_lower = query.lower()
        component_lower = income_component.lower() if income_component else ''

        # 🆕 تشخیص "مالیات بر X" به عنوان سطح "بند"
        # مثال: "مالیات بر واردات" → در ستون عنوان_بند وجود دارد
        if income_component and re.search(r'مالیات\s+بر\s+', income_component):
            return 'بند'
        
        # 🆕 تشخیص "واگذاری دارایی مالی" به عنوان سطح "قسمت"
        # مثال: "منابع حاصل از واگذاری دارایی های مالی" → قسمت سوم در DB
        if income_component and re.search(r'واگذاری\s+دارایی', income_component, re.IGNORECASE):
            return 'قسمت'
        if re.search(r'واگذاری\s+دارای?ی?\s*(?:های?)?\s*مالی', query_lower, re.IGNORECASE):
            return 'قسمت'
        
        # 🆕 تشخیص "کمکهای اجتماعی" و "متفرقه" به عنوان سطح "بخش"
        # مثال: "درآمدهاي ناشي از كمكهاي اجتماعي" → بخش دوم در DB
        if income_component and re.search(r'کمکهای\s+اجتماعی|كمكهاي\s+اجتماعي', income_component, re.IGNORECASE):
            return 'بخش'
        if re.search(r'کمکهای\s+اجتماعی|كمكهاي\s+اجتماعي|كمكها[ي]\s+اجتماعي', query_lower, re.IGNORECASE):
            return 'بخش'
        if income_component and re.search(r'^متفرقه$', income_component.strip(), re.IGNORECASE):
            return 'بخش'
        if re.search(r'درآمد(?:های|هاي|ها)?\s+متفرقه', query_lower, re.IGNORECASE):
            return 'بخش'
        
        # بررسی اینکه آیا کلمه "بخش" در query یا component وجود دارد
        # و این "بخش" قبل از component آمده است (یعنی بخش از سلسله مراتب است)
        # مثال: "درامد های حاصل از بخش درامد های مالیاتی" → hierarchy_level = 'بخش'
        
        # پیدا کردن موقعیت component در query (اگر موجود باشد)
        component_pos = query_lower.find(component_lower) if component_lower else -1
        if component_pos == -1:
            # اگر component در query پیدا نشد یا وجود نداره، بررسی می‌کنیم که آیا کلمات کلیدی سلسله مراتب وجود دارد
            # مثال: "منابع حاصل از بند درامد های حاصل از خدمات"
            #  → "بند" وجود داره، پس hierarchy_level = 'بند'
            if 'بخش' in query_lower:
                return 'بخش'
            elif 'قسمت' in query_lower:
                return 'قسمت'
            elif 'بند' in query_lower:
                return 'بند'
            elif 'جزء' in query_lower or 'جزو' in query_lower:
                return 'جزء'
            return None
        
        # قسمت query قبل از component
        before_component = query_lower[:component_pos]
        
        # بررسی وجود کلمات کلیدی سلسله مراتب قبل از component
        # اولویت: نزدیک‌ترین کلمه کلیدی به component
        
        # پیدا کردن موقعیت هر کلمه کلیدی
        bakhsh_pos = before_component.rfind('بخش')  # آخرین موقعیت
        qesmat_pos = before_component.rfind('قسمت')
        band_pos = before_component.rfind('بند')
        jozv_pos = max(before_component.rfind('جزء'), before_component.rfind('جزو'))
        
        # پیدا کردن نزدیک‌ترین کلمه کلیدی
        positions = {
            'بخش': bakhsh_pos,
            'قسمت': qesmat_pos,
            'بند': band_pos,
            'جزء': jozv_pos
        }
        
        # فیلتر کردن موقعیت‌های -1 (not found)
        valid_positions = {k: v for k, v in positions.items() if v != -1}
        
        if valid_positions:
            # انتخاب نزدیک‌ترین کلمه کلیدی (با بیشترین موقعیت)
            closest_keyword = max(valid_positions, key=valid_positions.get)
            logger.info(f"   🎯 Detected hierarchy level: {closest_keyword} (position: {valid_positions[closest_keyword]})")
            return closest_keyword
        
        # اگر هیچ کلمه کلیدی قبل از component پیدا نشد، بررسی می‌کنیم که آیا در خود component وجود دارد
        if 'بخش' in component_lower:
            # اگر "بخش" در خود component هست (مثلاً "بخش درآمدهای مالیاتی")
            # پس می‌فهمیم که کاربر از سطح "بخش" صحبت می‌کند
            return 'بخش'
        elif 'قسمت' in component_lower:
            return 'قسمت'
        elif 'بند' in component_lower:
            return 'بند'
        elif 'جزء' in component_lower or 'جزو' in component_lower:
            return 'جزء'
        
        return None
    
    def extract_years(self, query: str) -> List[str]:
        """استخراج سال‌ها از query"""
        # پیدا کردن range
        range_match = re.search(r'(?P<start>\d{2,4})\s*(?:تا|-)\s*(?P<end>\d{2,4})', query)
        years: List[str] = []
        
        if range_match:
            start = self._normalize_year_token(range_match.group('start'))
            end = self._normalize_year_token(range_match.group('end'))
            if not start or not end:
                return []
            start_year = min(int(start), int(end))
            end_year = max(int(start), int(end))
            years = [str(year) for year in range(start_year, end_year + 1)]
        else:
            tokens = re.findall(r'\d{2,4}', query)
            for token in tokens:
                normalized = self._normalize_year_token(token)
                if normalized:
                    years.append(normalized)
        
        return sorted(set(years))
    
    def _normalize_year_token(self, token: str) -> Optional[str]:
        """نرمال‌سازی سال (تبدیل ۲-رقمی و ۳-رقمی به ۴-رقمی)"""
        if not token.isdigit():
            return None
        length = len(token)
        if length == 4:
            return token if token.startswith(('13', '14')) else None
        if length == 3:
            value = int(token)
            if 300 <= value <= 499:
                return str(value + 1000)
            return None
        if length == 2:
            value = int(token)
            base = 1300 if value >= 50 else 1400
            return str(base + value)
        return None
    
    def analyze_query(self, query: str, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """
        تحلیل جامع query
        
        Args:
            query: سوال کاربر
            collection_name: نام collection (برای entity mapping)
        
        Returns:
            {
                'query_type': 'amount' | 'device' | 'sources' | 'amount_and_device',
                'query_category': 'simple_sum' | 'top_n' | 'breakdown' | 'cross_table',
                'years': List[str],
                'entity_names': List[str],  # نام دستگاه/سازمان
                'income_component': Optional[str],  # عنوان جزء درآمد
                'income_type': 'اختصاصی' | 'عمومی' | 'ملی' | 'استانی' | 'کل',
                'filters': {
                    'entity_filter': Optional[str],  # شرط SQL برای entity
                    'component_filter': Optional[str]  # شرط SQL برای component
                },
                'aggregation': {
                    'needs_groupby': bool,
                    'group_fields': List[str],
                    'needs_sort': bool,
                    'sort_direction': 'DESC' | 'ASC' | None,
                    'limit': Optional[int]
                },
                'dimensions': {
                    'asks_total': bool,
                    'asks_national_provincial': bool,
                    'asks_sources': bool,
                    'asks_share': bool
                },
                'cross_table': {
                    'needs_income': bool,
                    'needs_cost': bool,
                    'calculation_type': Optional[str]
                }
            }
        """
        # ⭐ NEW: تصحیح غلط‌املایی‌های رایج قبل از تحلیل
        original_query = query
        try:
            from services.budget_typo_corrector import correct_budget_query
            typo_result = correct_budget_query(query)
            if typo_result['corrected'] != query:
                logger.info(f"🔧 [QUERY_ANALYZER] Typo corrected: '{query}' -> '{typo_result['corrected']}'")
                query = typo_result['corrected']
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"⚠️ [QUERY_ANALYZER] Typo correction failed: {e}")
        
        normalized = self.normalize_text(query)
        query_lower = normalized.lower()
        
        # تشخیص نوع سوال (legacy)
        query_type = self._detect_query_type(query_lower)
        
        # تشخیص دسته‌بندی اصلی سوال
        query_category = self._detect_query_category(query_lower)
        
        # استخراج سال‌ها
        years = self.extract_years(normalized)
        
        # استخراج عبارت جزء درآمد
        income_component = self._extract_income_component(normalized)
        
        # استخراج نام دستگاه/سازمان
        logger.info(f"🔍 Starting entity extraction...")
        # IMPORTANT: Use ORIGINAL query (before typo correction) for entity extraction
        # Typo corrector normalizes آ→ا which breaks regex patterns like آزمایشگاه
        entity_names = self._extract_entity_names(original_query, income_component, collection_name)
        
        # فیلتر کردن entity هایی که در واقع component هستند
        # 🔧 CRITICAL FIX: اگر entity یک سازمان/شرکت/نهاد شناخته شده باشد، آن را حذف نکن
        # حتی اگر کلمات component در آن وجود داشته باشد
        # مثال: "شرکت فرهنگی و ورزشی استقلال" - "فرهنگی" component keyword هست ولی entity باید حفظ شود
        org_prefixes = {'شرکت', 'سازمان', 'موسسه', 'مؤسسه', 'بنیاد', 'صندوق', 'دانشگاه', 
                       'مرکز', 'ستاد', 'نهاد', 'بانک', 'بانك', 'وزارت', 'معاونت', 'هیات',
                       'فرهنگستان', 'پارک', 'پارك', 'جمعیت', 'کمیته', 'کميته', 'انستیتو', 'پژوهشکده',
                       'پژوهشگاه', 'آزمایشگاه', 'اداره', 'شورا', 'شورای', 'شوراي'}
        
        def _is_organization_entity(entity: str) -> bool:
            """بررسی اینکه entity یک سازمان/نهاد شناخته شده باشد"""
            entity_words = entity.strip().split()
            if entity_words:
                return entity_words[0].lower() in org_prefixes
            return False
        
        if income_component:
            component_words = set(income_component.lower().split())
            entity_names = [
                entity for entity in entity_names
                if _is_organization_entity(entity)  # سازمان‌ها همیشه حفظ شوند
                or (
                    not any(word in entity.lower() for word in component_words)
                    and entity.lower() not in self.income_component_keywords
                )
            ]
        
        # همچنین فیلتر کردن کلمات component که به عنوان entity استخراج شده‌اند
        # 🔧 FIX: سازمان‌ها از این فیلتر مستثنی هستند
        entity_names = [
            entity for entity in entity_names
            if _is_organization_entity(entity) or entity.lower() not in self.income_component_keywords
        ]
        
        logger.info(f"   ✅ Extracted {len(entity_names)} entities: {entity_names}")
        
        # تشخیص نوع درآمد
        income_type = self._detect_income_type(query_lower)
        logger.debug(f"   Income type: {income_type}")
        
        # ساخت فیلترهای SQL
        logger.info(f"🔍 Building SQL filters...")
        filters = self._build_sql_filters(entity_names, income_component, normalized, collection_name)
        if filters.get('entity_filter'):
            logger.info(f"   ✅ Entity filter created ({len(filters['entity_filter'])} chars)")
        if filters.get('component_filter'):
            logger.info(f"   ✅ Component filter created")
        
        # تشخیص نیاز به aggregation
        aggregation = self._detect_aggregation_type(query_lower, entity_names, income_component)
        
        # تشخیص ابعاد مختلف
        dimensions = self._detect_multi_dimension(query_lower)
        
        # تشخیص نیاز به cross-table
        cross_table = self._detect_cross_table_need(query_lower)
        
        # محاسبه Confidence Score برای نتایج استاتیک
        confidence = self._calculate_confidence_score(
            entity_names=entity_names,
            years=years,
            income_component=income_component,
            query=normalized,
            query_category=query_category
        )
        
        # تشخیص جزئیات comparison (برای سوالات مقایسه‌ای)
        comparison_info = None
        if query_category == 'comparison':
            comparison_info = self._detect_comparison_info(query_lower, years, entity_names)
        
        # 🆕 تشخیص سطح سلسله‌مراتبی (برای manabe queries)
        hierarchy = self.detect_hierarchy_level(query)
        
        result = {
            'query_type': query_type,
            'query_category': query_category,
            'years': years,
            'entity_names': entity_names,
            'income_component': income_component,
            'income_type': income_type,
            'filters': filters,
            'aggregation': aggregation,
            'dimensions': dimensions,
            'cross_table': cross_table,
            'comparison_info': comparison_info,  # اطلاعات مقایسه‌ای
            'hierarchy': hierarchy,  # 🆕 سطح سلسله‌مراتبی
            'confidence': confidence  # اضافه کردن confidence score
        }
        
        logger.info(f"📊 Query Analysis - Confidence: {confidence:.2f}")
        logger.info(f"📊 Query Analysis: {result}")
        return result
    
    async def analyze(self, query: str, collection_name: str = None, domain_info: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        متد اصلی برای تحلیل query (wrapper برای analyze_query)
        
        Args:
            query: سوال کاربر
            collection_name: نام collection
            domain_info: اطلاعات domain
        
        Returns:
            {
                'intent_type': str,
                'requires_multi_hop': bool,
                'complexity_score': float,
                'entities': List[str],
                'query_category': str,
                ...
            }
        """
        try:
            # ⭐ CRITICAL: اول چک کنیم که query غیرمالی نباشد
            # این کار قبل از هر چیزی باید انجام شود
            normalized = self.normalize_text(query)
            query_lower = normalized.lower()
            
            # تشخیص domain بر اساس domain_info یا کلمات کلیدی
            domain_type = domain_info.get('domain', 'general') if domain_info else 'general'
            
            # 🔧 CRITICAL FIX: تشخیص خودکار domain مالی بر اساس کلمات کلیدی - BEFORE non_financial check
            financial_keywords = [
                'درآمد', 'درامد', 'هزینه', 'هزينه', 'بودجه', 'اعتبار', 'اعتبارات',
                'مصارف', 'منابع', 'تملک', 'تملك', 'دارایی', 'دارايي', 'سرمایه',
                'ملی', 'ملي', 'استانی', 'استاني', 'عمومی', 'عمومي', 'اختصاصی',
                'متفرقه', 'یارانه', 'وزارت', 'سازمان', 'بنیاد', 'بنياد', 'دانشگاه',
                'معاونت', 'ستاد', 'فرهنگستان', 'شرکت', 'شركت'
            ]
            has_financial_keywords = any(kw in query_lower for kw in financial_keywords)
            
            # برای collection های بودجه یا query های مالی، از analyze_query کامل استفاده کن
            is_budget_collection = collection_name and ('budget' in collection_name.lower() or 'finance' in collection_name.lower())
            
            # 🔧 CRITICAL FIX: اگر financial keywords دارد یا budget collection است، non_financial check را skip کن
            quick_category = self._detect_query_category(query_lower)
            
            if quick_category == 'non_financial' and not has_financial_keywords and not is_budget_collection:
                # فقط اگر واقعاً غیرمالی است (بدون financial keywords و نه budget collection)، early return
                return {
                    'intent_type': 'non_financial',
                    'requires_multi_hop': False,
                    'complexity_score': 0.9,
                    'entities': [],
                    'query_category': 'non_financial',
                    'is_non_financial': True
                }
            
            # 🔧 تشخیص نهایی: financial or not
            is_financial = domain_type == 'financial' or has_financial_keywords or is_budget_collection
            
            if is_financial:
                # برای domain مالی، از analyze_query کامل استفاده می‌کنیم
                analysis = self.analyze_query(query, collection_name)
                
                # تبدیل به فرمت مورد نیاز
                return {
                    'intent_type': analysis.get('query_category', 'unknown'),
                    'requires_multi_hop': (
                        len(analysis.get('entity_names', [])) > 1 or
                        analysis.get('dimensions', {}).get('asks_sources', False) or
                        analysis.get('cross_table', {}).get('needs_income', False) or
                        analysis.get('query_category') in ['breakdown', 'cross_table']
                    ),
                    'complexity_score': analysis.get('confidence', 0.5),
                    'entities': analysis.get('entity_names', []),
                    'query_category': analysis.get('query_category', 'simple_sum'),
                    'years': analysis.get('years', []),
                    'filters': analysis.get('filters', {}),
                    'aggregation': analysis.get('aggregation', {}),
                    'dimensions': analysis.get('dimensions', {}),
                    'original_analysis': analysis
                }
            else:
                # برای domain های دیگر، تحلیل ساده‌تر
                normalized = self.normalize_text(query)
                query_lower = normalized.lower()
                
                # تشخیص سوالات چند بخشی
                multi_part_keywords = [" و ", " چطور", " چه", " کجا", " کی", " چرا", " چگونه", " چه مدت", " چه نوع"]
                multi_part_count = sum(1 for kw in multi_part_keywords if kw in query_lower)
                has_multiple_questions = multi_part_count >= 2 or query_lower.count("؟") >= 2
                
                question_markers = ["چیه", "چیست", "چطور", "چگونه", "چه", "کجا", "کی", "چرا"]
                question_count = sum(1 for marker in question_markers if marker in query_lower)
                is_multi_part_query = question_count >= 2 or (multi_part_count >= 1 and len(query.split()) >= 10)
                
                # تشخیص complexity
                complexity_score = 0.3  # پایه
                if is_multi_part_query:
                    complexity_score += 0.3
                if has_multiple_questions:
                    complexity_score += 0.2
                if len(query.split()) > 15:
                    complexity_score += 0.2
                complexity_score = min(complexity_score, 1.0)
                
                # تشخیص intent
                if "چطور" in query_lower or "چگونه" in query_lower:
                    intent_type = "how"
                elif "چیه" in query_lower or "چیست" in query_lower:
                    intent_type = "what"
                elif "چرا" in query_lower:
                    intent_type = "why"
                elif "کجا" in query_lower:
                    intent_type = "where"
                elif "کی" in query_lower:
                    intent_type = "when"
                else:
                    intent_type = "general"
                
                return {
                    'intent_type': intent_type,
                    'requires_multi_hop': is_multi_part_query or has_multiple_questions or complexity_score >= 0.6,
                    'complexity_score': complexity_score,
                    'entities': [],
                    'query_category': 'general',
                    'is_multi_part': is_multi_part_query,
                    'has_multiple_questions': has_multiple_questions
                }
        
        except Exception as e:
            logger.warning(f"Query analyzer failed: {e}")
            return None
    
    def _detect_query_type(self, query_lower: str) -> str:
        """تشخیص نوع سوال"""
        asks_amount = bool(re.search(r'چقدر|مقدار|مبلغ|میزان', query_lower))
        asks_device = bool(re.search(r'چه\s+دستگاه|کدام\s+دستگاه|توسط\s+چه|وصول\s*کننده|دستگاهی', query_lower))
        asks_sources = bool(re.search(r'از\s+چه\s+راه|چه\s+روش|چگونه|منابع|راه\s*های', query_lower))
        
        if asks_sources:
            return 'sources'
        if asks_amount and asks_device:
            return 'amount_and_device'
        if asks_device:
            return 'device'
        return 'amount'
    
    def _is_income_query(self, query_lower: str) -> bool:
        """تشخیص اینکه query درباره درآمد است یا هزینه"""
        # کلمات کلیدی درآمد
        income_keywords = ['درآمد', 'درامد', 'در امد', 'درامدهای', 'درآمدهای']
        # کلمات کلیدی هزینه
        cost_keywords = ['هزینه', 'هزينه', 'اعتبار', 'مصارف', 'تملک دارایی']
        
        has_income = any(kw in query_lower for kw in income_keywords)
        has_cost = any(kw in query_lower for kw in cost_keywords)
        
        # اگر هر دو وجود داشت، اولویت با درآمد است (چون معمولاً سوالات درآمدی هستند)
        if has_income:
            return True
        if has_cost and not has_income:
            return False
        
        # اگر هیچکدام نبود، بر اساس context تصمیم می‌گیریم
        # اگر component keywords وجود داشت، احتمالاً درآمد است
        has_component_kw = any(kw in query_lower for kw in self.income_component_keywords)
        if has_component_kw:
            return True
        
        return True  # default به درآمد
    
    def _extract_income_component(self, query: str) -> Optional[str]:
        """استخراج عبارت جزء درآمد (مثل 'خدمات گمرکی')"""
        query_lower = query.lower()
        
        # 🔧 CRITICAL FIX: بررسی context برای کلمات مشترک مثل "صنعتی", "فرهنگی"
        # اگر این کلمات بعد از نام سازمان/شرکت بیایند، entity هستند نه component
        # مثال: "دانشگاه صنعتی قم" - "صنعتی" entity است نه component
        # مثال: "شرکت فرهنگی و ورزشی استقلال" - "فرهنگی" entity است نه component
        org_context_pattern = r'(?:شرکت|سازمان|موسسه|بنیاد|دانشگاه|مرکز|ستاد|نهاد|بانک|وزارت|معاونت|فرهنگستان|پارک|جمعیت|کمیته|پژوهشکده|پژوهشگاه)\s+.*?(?:صنعتی|فرهنگی|کشاورزی|بهداشتی|درمانی|آموزشی|اموزشی|تجاری|ثبتی|پژوهشی|رفاهی)'
        if re.search(org_context_pattern, query_lower):
            # کلمات component-like در context یک سازمان هستند → exclude them
            # پیدا کردن کلمات component-like که در context سازمان هستند
            context_keywords = set()
            for kw in ['صنعتی', 'فرهنگی', 'کشاورزی', 'بهداشتی', 'درمانی', 'آموزشی', 'اموزشی', 'تجاری', 'ثبتی', 'پژوهشی', 'رفاهی']:
                if re.search(rf'(?:شرکت|سازمان|موسسه|بنیاد|دانشگاه|مرکز|ستاد|نهاد|بانک|وزارت|معاونت|فرهنگستان|پارک)\s+.*?{kw}', query_lower):
                    context_keywords.add(kw)
            temp_keywords = self.income_component_keywords - context_keywords
            has_component_kw = any(kw in query_lower for kw in temp_keywords)
        else:
            # بررسی وجود کلیدواژه‌های component
            has_component_kw = any(kw in query_lower for kw in self.income_component_keywords)
        
        if not has_component_kw:
            return None
        
        # الگوهای مختلف برای استخراج
        patterns = [
            # 🔧 NEW: "واگذاری دارایی های مالی" - قبل از سایر patterns باشد
            r'(?:منابع\s+)?(?:حاصل\s+از\s+)?(واگذاری\s+دارای?ی?\s*(?:های?)?\s*مالی)(?:\s+در\s+سال|\s+توسط|$)',
            r'(واگذاری\s+دارایی\s+(?:های\s+)?مالی)',
            # 🔧 NEW: "کمکهای اجتماعی" و "درآمدهاي ناشي از كمكهاي اجتماعي"
            r'(?:درآمد(?:های|ها|هاي)?\s+)?(?:ناشی|ناشي)\s+از\s+(کمکهای\s+اجتماعی|كمكهاي\s+اجتماعي|كمكها[ي]\s+اجتماعي)',
            r'(کمکهای\s+اجتماعی|كمكهاي\s+اجتماعي)(?:\s+در\s+سال|\s+توسط|$)',
            # 🔧 NEW: "درآمدهای متفرقه" - standalone
            r'(?:درآمد(?:های|ها|هاي)?\s+)(متفرقه)(?:\s+در\s+سال|\s+توسط|$)',
            r'(?:^|\s)(متفرقه)(?:\s+در\s+سال|\s+توسط|\s+منابع|\s+مصارف|$)',
            # "در امد عمومی حاصل از معاینه فنی" - الگوی خاص
            r'(?:در\s*ا\s*مد|درآمد|درامد)(?:\s+های)?\s+(?:عمومی|ملی|استانی|اختصاصی)?\s*حاصل\s+از\s+(معاینه\s+فنی)(?:\s+در\s+سال|\s+توسط|$)',
            # "درآمد حاصل از اجاره"
            r'(?:درآمد|درامد)(?:\s+های)?\s+(?:ملی|استانی|اختصاصی|عمومی)?\s*حاصل\s+از\s+([آ-ی\s]+?)(?:\s+در\s+سال|\s+توسط|$)',
            # "درآمد حاصل از خدمات گمرکی"
            r'(?:درآمد|درامد)\s+حاصل\s+از\s+([آ-ی\s]+?)(?:\s+در\s+سال|\s+توسط|$)',
            # "درآمدهای مالیاتی" - الگوی خاص برای مالیاتی (با یا بدون فاصله قبل از های)
            r'(?:درآمد|درامد)\s*(?:های|ها)?\s+(مالیاتی)(?:\s+در\s+سال|\s+توسط|$)',
            # "درآمدهای مالیات بر واردات / مالیات بر درآمد / مالیات بر ثروت" - الگوی خاص "مالیات بر X"
            r'(?:درآمد|درامد)(?:های|ها)?\s+(مالیات\s+بر\s+[آ-ی]+(?:\s+[آ-ی]+)*)(?:\s+در\s+سال|\s+توسط|$)',
            # "مالیات بر واردات" بدون "درآمد" - standalone
            r'(?<!\w)(مالیات\s+بر\s+[آ-ی]+(?:\s+[آ-ی]+)*)(?:\s+در\s+سال|\s+توسط|$)',
            # "معاینه فنی" - الگوی خاص (باید group داشته باشد)
            r'(?:حاصل\s+از\s+)?(معاینه\s+فنی)(?:\s+در\s+سال|\s+توسط|$)',
            # "خدمات گمرکی"
            r'(?:حاصل\s+از\s+)?([آ-ی\s]*(?:خدمات|فروش|عوارض|مالیات|کارمزد|اجاره|اجار)\s+[آ-ی]+?)(?:\s+در\s+سال|\s+توسط|$)',
            # پترن برای فقط "اجاره"
            r'(?:حاصل\s+از\s+)?(اجاره|اجار)(?:\s+در\s+سال|\s+توسط|$)',
            # پترن کلی‌تر (🔧 CRITICAL: negative lookahead برای جلوگیری از match با "دانشگاه صنعتی")
            r'(?:حاصل\s+از\s+)?(?!دانشگاه\s+)([آ-ی\s]+(?:گمرکی|آموزشی|اموزشی|بهداشتی|درمانی|فرهنگی|تجاری|صنعتی|کشاورزی|ثبتی|مخابراتی|تحقیقاتی|پژوهشی|رفاهی|الکترونیکی|اجاره|اجار|معاینه\s+فنی|جرایم\s+و\s+خسارات|واگذاری\s+دارایی|مالکیت\s+دولت))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                phrase = match.group(1).strip()
                # نرمال‌سازی فاصله‌ها
                phrase = ' '.join(phrase.split())
                # حذف کلمات توقف از ابتدا و انتها
                words = phrase.split()
                while words and words[0] in self.stop_words:
                    words.pop(0)
                while words and words[-1] in self.stop_words:
                    words.pop()
                if words:
                    return ' '.join(words)
        
        return None
    
    def _extract_entity_names(self, query: str, income_component: Optional[str], collection_name: Optional[str] = None) -> List[str]:
        """استخراج نام دستگاه/سازمان با تشخیص عبارات چند کلمه‌ای"""
        
        # 🔧 FIX: حذف کلمات پرسشی که توسط preprocessor اضافه شده‌اند
        # مثال: "دانشگاه پیام نور چیست؟ در سال 1403" → "دانشگاه پیام نور در سال 1403"
        _question_suffixes = [
            r'\s+چیست[؟?]?',        # چیست، چیست؟
            r'\s+چیه[؟?]?',         # چیه
            r'\s+چطوره[؟?]?',       # چطوره
            r'\s+چگونه\s+است[؟?]?', # چگونه است
            r'\s+کدام\s+است[؟?]?',  # کدام است
            r'\s+چند\s+است[؟?]?',   # چند است
            r'\s+چقدر\s+است[؟?]?',  # چقدر است
            r'\s+است[؟?]?$',        # است (در انتهای جمله)
            r'[؟?]\s*',             # علامت سوال
        ]
        _cleaned_query = query
        for _pat in _question_suffixes:
            _cleaned_query = re.sub(_pat, '', _cleaned_query, flags=re.IGNORECASE)
        _cleaned_query = _cleaned_query.strip()
        query = _cleaned_query
        
        # الگوهای شناخته شده برای سازمان‌ها
        # نکته: باید از کلمات پرسشی و ترتیبی جلوگیری کنیم
        known_patterns = [
            # ===== Special cases - باید قبل از patterns عمومی باشند =====
            # فرهنگستان‌ها (full match - با نام کشور اگر موجود بود)
            (r'فرهنگستان\s+علوم\s+پزشکی\s+ایران', True),  # فرهنگستان علوم پزشکی ایران - full match (اول چک کن)
            (r'فرهنگستان\s+علوم\s+پزشكي\s+ايران', True),  # فرهنگستان علوم پزشکی ایران - با ی عربی
            (r'فرهنگستان\s+علوم\s+ایران', True),  # فرهنگستان علوم ایران - full match
            (r'فرهنگستان\s+علوم\s+ايران', True),  # فرهنگستان علوم ایران - با ی عربی
            (r'فرهنگستان\s+هنر\s+ایران', True),  # فرهنگستان هنر ایران - full match
            (r'فرهنگستان\s+هنر\s+ايران', True),  # با ی عربی
            (r'فرهنگستان\s+زبان\s+و\s+ادب\s+فارسی', True),  # فرهنگستان زبان و ادب فارسی - full match
            (r'فرهنگستان\s+زبان\s+و\s+ادب\s+فارسي', True),  # با ی عربی
            # fallback برای موارد بدون کشور (فقط اگر نام کامل‌تر match نکرد)
            (r'فرهنگستان\s+هنر', True),  # فرهنگستان هنر - short match
            (r'فرهنگستان\s+علوم', True),  # فرهنگستان علوم - short match
            (r'فرهنگستان\s+زبان', True),  # فرهنگستان زبان - short match
            (r'فرهنگستان\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+)*)(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),  # fallback
            
            # بنیادها (full match for known ones)
            (r'بنیاد\s+ایران\s*شناسی', True),  # بنیاد ایران شناسی - full match
            (r'بنياد\s+ايران\s*شناسي', True),  # بنیاد ایران شناسی - با ی عربی
            (r'بنیاد\s+ملی\s+نخبگان', True),  # بنیاد ملی نخبگان - full match
            
            # معاونت‌ها (full match for known ones)
            (r'معاونت\s+علمي?\s*[،و]?\s*فناوري\s*و\s*اقتصاد\s+دانش\s+بنيان', True),  # معاونت علمی و فناوری و اقتصاد دانش بنیان
            (r'معاونت\s+علمی?\s*[،و]?\s*فناوری', True),  # معاونت علمی و فناوری - full match
            (r'معاونت\s+علمي?\s*[،و]?\s*فناوري', True),  # با ی عربی
            
            # وزارتخانه‌ها (full match) - باید قبل از pattern عمومی باشند
            (r'وزارت\s+نفت', True),  # وزارت نفت
            (r'وزارت\s+کشور', True),  # وزارت کشور
            (r'وزارت\s+اطلاعات', True),  # وزارت اطلاعات
            (r'وزارت\s+ورزش\s+و\s+جوانان', True),
            (r'وزارت\s+نیرو', True),
            (r'وزارت\s+صنعت[،]\s*معدن\s+و\s+تجارت', True),
            (r'وزارت\s+بهداشت', True),  # وزارت بهداشت
            # 🔧 FIX: وزارت امور اقتصادی و دارایی (نام‌های مختلف)
            (r'وزارت\s+امور\s+اقتصادی\s+و\s+دارایی', True),  # نام رسمی کامل
            (r'وزارت\s+امور\s+اقتصادي\s+و\s+دارايي', True),  # با ی عربی
            (r'وزارت\s+اقتصاد\s+و\s+دارایی', True),  # نام کوتاه (alias) - should map to full name
            (r'وزارت\s+اقتصاد\s+و\s+دارايي', True),  # با ی عربی
            (r'وزارت\s+امور\s+اقتصادی', True),  # بدون "و دارایی"
            (r'وزارت\s+امور\s+اقتصادي', True),  # با ی عربی
            # 🔧 CRITICAL: وزارت تعاون، کار و رفاه اجتماعی (نام‌های مختلف)
            (r'وزارت\s+تعاون[،,]?\s*کار\s+و\s+رفاه(?:\s+اجتماعی)?', True),
            (r'وزارت\s+کار\s+و\s+رفاه', True),  # نام کوتاه
            (r'وزارت\s+رفاه', True),  # نام خیلی کوتاه
            
            # گمرک (full match)
            (r'گمرك\s+جمهوري\s+اسلامي\s+ايران', True),
            (r'گمرک\s+جمهوری\s+اسلامی\s+ایران', True),
            
            # ستادها (full match)
            (r'ستاد\s+مبارزه\s+با\s+مواد\s+مخدر', True),
            (r'ستاد\s+کل\s+نیروهای\s+مسلح', True),
            (r'ستاد\s+كل\s+نيروهاي\s+مسلح', True),  # با ی عربی
            (r'ستاد\s+مرکزی\s+راهیان\s+نور', True),  # ستاد مرکزی راهیان نور
            (r'ستاد\s+مركزي\s+راهيان\s+نور', True),  # با ی عربی
            
            # اورژانس و فوریت های پزشکی (full match)
            (r'اورژانس\s+(?:تهران|استان\s+[آ-ی]+|[آ-ی]+)', True),  # اورژانس تهران، اورژانس استان تهران
            (r'فوریت\s*های?\s+پزشکی\s+(?:تهران|استان\s+[آ-ی]+|[آ-ی]+)', True),  # فوریت های پزشکی تهران
            (r'فوريت\s*هاي?\s+پزشكي\s+(?:تهران|استان\s+[آ-ی]+|[آ-ی]+)', True),  # با ی عربی
            
            # هیات‌ها (full match)
            (r'هیات\s+عالی\s+گزینش', True),
            (r'هیأت\s+عالی\s+گزینش', True),
            (r'هيات\s+عالي\s+گزينش', True),  # با ی عربی
            
            # سازمان امور مالیاتی (full match) - CRITICAL: باید قبل از pattern عمومی سازمان باشد
            (r'سازمان\s+امور\s+مالیاتی\s+کشور', True),  # سازمان امور مالیاتی کشور
            (r'سازمان\s+امور\s+مالياتي\s+كشور', True),  # با ی عربی
            (r'سازمان\s+امور\s+مالیاتی', True),  # سازمان امور مالیاتی
            (r'سازمان\s+امور\s+مالياتي', True),  # با ی عربی
            
            # سازمان برنامه و بودجه (full match) - 🔧 FIX: شامل "و" در نام
            (r'سازمان\s+برنامه\s+و\s+بودجه\s+کشور', True),  # سازمان برنامه و بودجه کشور
            (r'سازمان\s+برنامه\s+و\s+بودجه\s+كشور', True),  # با ک عربی
            (r'سازمان\s+برنامه\s+و\s+بودجه', True),  # سازمان برنامه و بودجه (کوتاه)
            
            # سازمان سنجش (full match)
            (r'سازمان\s+سنجش\s+آموزش\s+کشور\s+موضوع\s+بند\s*["\']?ج["\']?\s+تبصره', True),  # عنوان کامل با بند ج
            (r'سازمان\s+سنجش\s+آموزش\s+کشور', True),
            (r'سازمان\s+سنجش\s+آموزش\s+كشور', True),  # با ک عربی
            (r'سازمان\s+سنجش\s+بند\s*["\']?ج["\']?', True),  # نسخه با بند ج
            (r'سازمان\s+سنجش', True),  # نسخه کوتاه
            
            # شرکت‌ها و بانک‌ها (full match)
            (r'بانک\s+ملی\s+ایران', True),  # بانک ملی ایران (full name)
            (r'بانك\s+ملي\s+ايران', True),  # با ی عربی
            (r'بانک\s+ملی', True),  # بانک ملی (short name)
            (r'بانك\s+ملي', True),  # با ی عربی
            (r'بانک\s+سپه', True),  # بانک سپه
            (r'بانك\s+سپه', True),  # با ی عربی
            (r'بانک\s+صادرات', True),  # بانک صادرات
            (r'بانك\s+صادرات', True),  # با ی عربی
            (r'بانک\s+تجارت', True),  # بانک تجارت
            (r'بانك\s+تجارت', True),  # با ی عربی
            (r'بانک\s+([آ-ی]+)', False),  # بانک‌های دیگر - pattern عمومی
            (r'بانك\s+([آ-ی]+)', False),  # با ک عربی
            (r'شرکت\s+دولتی\s+پست\s*بانک', True),  # شرکت دولتی پست بانک
            (r'شركت\s+دولتي\s+پست\s*بانك', True),  # با ی عربی
            (r'پست\s*بانک', True),  # پست بانک (نام کوتاه) - باید به عنوان یک entity کامل شناخته شود
            (r'پست\s*بانك', True),  # پست بانک با ک عربی
            (r'شرکت\s+فرهنگی\s+و\s+ورزشی\s+استقلال', True),
            
            # نهادها (full match)
            (r'نهاد\s+ریاست\s+جمهوری', True),
            (r'نهاد\s+رهبری', True),
            
            # ===== الگوهای عمومی =====
            # نهادها
            (r'نهاد\s+([آ-ی]+(?:\s+[آ-ی]+){0,2})', False),
            
            # وزارتخانه‌ها
            (r'وزارت\s+(?!ها)([آ-ی]+(?:\s*،\s*[آ-ی]+)*(?:\s+و\s+[آ-ی]+)?(?:\s+[آ-ی]+){0,1})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و\s+(?!در)|؟)', False),
            
            # سازمان‌ها
            (r'سازمان\s+(?!ها|بیشترین|کمترین)([آ-ی]+(?:\s+[آ-ی]+){0,2})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            
            # موسسات
            (r'انستیتو\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,2})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            
            # شرکت‌ها - 🔧 FIX: اجازه "و" داخل نام شرکت (مثل "شرکت فرهنگی و ورزشی استقلال")
            (r'شرکت\s+(?!ها)([آ-ی]+(?:\s+(?:و\s+)?[آ-ی]+){0,5})(?=\s+در\b|\s+سال\b|\s+چقدر|\s+چه\b|\s+توسط|\s+از\b|\s+به\b|\s*؟|$)', False),
            
            # بنیادها
            (r'بنیاد\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,3})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            
            # جمعیت‌ها
            (r'جمعیت\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,2})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            
            # دانشگاه‌ها (full match for known ones first)
            (r'دانشگاه\s+تهران', True),  # دانشگاه تهران
            (r'دانشگاه\s+تبریز', True),  # دانشگاه تبریز
            (r'دانشگاه\s+امیرکبیر', True),  # دانشگاه امیرکبیر
            # 🔧 CRITICAL: دانشگاه + صنعتی/کشاورزی + نام شهر (باید قبل از pattern عمومی باشد)
            (r'دانشگاه\s+(?:صنعتی|کشاورزی)\s+[آ-ی]+', True),  # دانشگاه صنعتی قم
            # 🔧 CRITICAL: دانشگاه علوم پزشکی + نام شهر
            (r'دانشگاه\s+علوم\s+پزشکی\s+[آ-ی]+', True),  # دانشگاه علوم پزشکی تهران
            (r'دانشگاه\s+علوم\s+پزشكي\s+[آ-ی]+', True),  # با ی عربی
            # 🔧 CRITICAL: دانشگاه + رشته/حوزه + نام شهر (مثل "دانشگاه هنر شیراز"، "دانشگاه هنر اصفهان")
            (r'دانشگاه\s+هنر\s+(?:اسلامی\s+)?[آ-ی]+', True),  # دانشگاه هنر شیراز، دانشگاه هنر اسلامی تبریز
            (r'دانشگاه\s+هنر\s+(?:اسلامي\s+)?[آ-ی]+', True),  # با ی عربی
            (r'دانشگاه\s+هنر', True),  # دانشگاه هنر (بدون شهر)
            # 🔧 دانشگاه پیام نور (بدون شهر - باید قبل از pattern با شهر باشد)
            (r'دانشگاه\s+پیام\s*نور', True),
            (r'دانشگاه\s+پيام\s*نور', True),  # با ی عربی
            # 🔧 دانشگاه + فنی/حرفه‌ای/آزاد + شهر
            (r'دانشگاه\s+(?:فنی|حرفه\s*ای|آزاد|پیام\s*نور|جامع\s+علمی)\s+[آ-ی]+', True),
            # generic pattern
            (r'دانشگاه\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,2})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            
            # آزمایشگاه‌ها (support both آ and ا)
            (r'[آا]زمایشگاه\s+(?:ملی\s+)?(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,3})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            
            # گمرک‌ها
            (r'گمرک\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,2})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            
            # مراکز
            (r'مرکز\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,3})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            
            # پارک‌ها - "پارک علم و فناوری یزد" تا 5 کلمه
            (r'پارک\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,5})(?=\s+در\s|\s+سال\s|\s+چقدر|\s+چه\s|\s+توسط|\s+؟|$)', False),
            
            # ستادها
            (r'ستاد\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,4})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            
            # معاونت‌ها
            (r'معاونت\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,3})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            
            # پژوهشکده‌ها
            # ⭐ پژوهکشده (typo) - باید قبل از پژوهشکده باشد
            (r'پژوهکشده\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+)?)(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            (r'پژوهشکده\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+)?)(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            (r'پژوهشكده\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+)?)(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            
            # شورا‌ها (full match for known ones first)
            (r'شورای\s+نگهبان', True),  # شورای نگهبان
            (r'شوراي\s+نگهبان', True),  # با ی عربی
            (r'شورای\s+عالی\s+(?:امنیت\s+ملی|انقلاب\s+فرهنگی|فضای\s+مجازی)', True),
            (r'شورای\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,3})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            (r'شوراي\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,3})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            
            # کمیته‌ها (full match for known ones first)
            (r'کمیته\s+ملی\s+المپیک\s+ایران', True),  # کمیته ملی المپیک ایران (exact, no پارا)
            (r'کمیته\s+ملی\s+پارا\s*المپیک\s+ایران', True),  # کمیته ملی پارا المپیک ایران
            (r'كميته\s+ملي\s+المپيك\s+ايران', True),  # با ی عربی
            (r'كميته\s+ملي\s+پارا\s*المپيك\s+ايران', True),  # با ی عربی
            (r'کمیته\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,3})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            
            # صندوق‌ها
            (r'صندوق\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,3})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            
            # اداره‌ها
            (r'اداره\s+کل\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,3})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            (r'اداره\s+(?!ها|کل)([آ-ی]+(?:\s+[آ-ی]+){0,3})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            
            # فرهنگستان‌ها
            (r'فرهنگستان\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,3})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            
            # پژوهشگاه‌ها
            (r'پژوهشگاه\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,3})(?=\s|$|در|سال|چقدر|چه|توسط|از|به|و|؟)', False),
            
            # موسسه‌ها - 🔧 FIX: کپچر فقط کلمات قبل از اولین stopword
            (r'موسسه\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,3}?)(?=\s+(?:در|سال|چقدر|چه|توسط|از|به|و|هزینه|درآمد|اعتبار|منابع|مصارف|جاری|سرمایه|عمومی|اختصاصی|کل|ملی|دولتی|خصوصی|است|بود|داشت|داشته|چند|کدام|کجا|چیست|چطور|چرا|کی|ای|ها)\b|$|؟)', False),
            (r'مؤسسه\s+(?!ها)([آ-ی]+(?:\s+[آ-ی]+){0,3}?)(?=\s+(?:در|سال|چقدر|چه|توسط|از|به|و|هزینه|درآمد|اعتبار|منابع|مصارف|جاری|سرمایه|عمومی|اختصاصی|کل|ملی|دولتی|خصوصی|است|بود|داشت|داشته|چند|کدام|کجا|چیست|چطور|چرا|کی|ای|ها)\b|$|؟)', False),
        ]
        
        # حذف بخش‌های سال - باید word boundary استفاده کنیم تا کلمات قبل را حذف نکند
        # نکته مهم: باید فاصله قبل از "در" را حفظ کنیم تا entity ها خراب نشوند
        # 🔧 FIX: سال\s*(?:های|هاي)? به جای سال(?:های|هاي)? تا "سال های" (با فاصله) هم match شود
        query_clean = re.sub(
            r'\s+در\s+سال\s*(?:های|هاي)?\s+\d{2,4}(?:\s*(?:تا|-)\s*\d{2,4})?',
            ' ',  # یک فاصله باقی می‌ماند
            query,
            flags=re.IGNORECASE
        )
        query_clean = re.sub(
            r'\s+سال\s*(?:های|هاي)?\s+\d{2,4}(?:\s*(?:تا|-)\s*\d{2,4})?',
            ' ',  # یک فاصله باقی می‌ماند
            query_clean,
            flags=re.IGNORECASE
        )
        # حذف "در" که ممکن است بعد از حذف "در سال" باقی مانده باشد
        query_clean = re.sub(
            r'\s+در\s+(?!سال)',  # "در" که قبل از "سال" نیست
            ' ',
            query_clean,
            flags=re.IGNORECASE
        )
        # حذف "سال" یا "سال‌ها" که به entity چسبیده است
        query_clean = re.sub(
            r'\b(سال|سالها|سال‌ها|سالهای|سال‌های)\b\s*$',
            ' ',
            query_clean,
            flags=re.IGNORECASE
        )
        query_clean = re.sub(
            r'\b(سال|سالها|سال‌ها|سالهای|سال‌های)\b\s+(در|تا|از|به)',
            r' \2',
            query_clean,
            flags=re.IGNORECASE
        )
        
        # حذف بخش component
        if income_component:
            query_clean = query_clean.replace(income_component, ' ')
        
        # همیشه حذف کلمات مرتبط با درآمد و هزینه قبل از استخراج entity
        # ⭐ NEW: اضافه کردن "حاضل" (غلط‌املایی رایج "حاصل")
        query_clean = re.sub(r'درآمد|درامد|حاصل\s+از|حاضل\s+از|حاصل|حاضل', ' ', query_clean, flags=re.IGNORECASE)
        
        # حذف کلمات مالی که entity نیستند
        # این کار مهم است تا entity های واقعی درست استخراج شوند
        
        # 🔧 CRITICAL: حذف "اعتبارات تملک دارایی" با تمام ترکیبات
        # باید قبل از regex های جداگانه باشد
        query_clean = re.sub(
            r'اعتبارات?\s*تملک\s*دارای?ی?\s*(?:های?)?\s*(?:سرمایه\s*ای?)?\s*(?:عمومی|اختصاصی|متفرقه)?',
            ' ', query_clean, flags=re.IGNORECASE
        )
        
        # حذف "اعتبارات هزینه ای"
        # 🔧 بهبود: "ای" دو کاراکتر است، باید (?:ای|اي|ی|ي)? باشد نه [یاي]?
        query_clean = re.sub(
            r'(?:اعتبارات?|برآورد|براورد)\s+هزینه\s*(?:ای|اي|ی|ي)?\s*(?:عمومی|اختصاصی|متفرقه)?',
            ' ', query_clean, flags=re.IGNORECASE
        )
        
        # حذف "تملک دارایی" (اگر به تنهایی باقی مانده)
        query_clean = re.sub(
            r'تملک\s*دارای?ی?\s*(?:های?)?\s*(?:سرمایه\s*ای?)?\s*(?:عمومی|اختصاصی|متفرقه)?',
            ' ', query_clean, flags=re.IGNORECASE
        )
        
        # حذف "براورد" با یا بدون "اعتبارات"
        query_clean = re.sub(
            r'براورد\s*(?:اعتبارات?)?',
            ' ', query_clean, flags=re.IGNORECASE
        )
        
        # حذف کلمات مالی عمومی
        query_clean = re.sub(
            r'بودجه|منابع|مصارف|اعتبار',
            ' ', query_clean, flags=re.IGNORECASE
        )
        
        # حذف بخش‌های پرسشی و توضیحی - قبل از entity extraction
        # این کار مهم است تا entity ها با کلمات اضافی استخراج نشوند
        query_clean = re.sub(
            r'از\s+چه\s+جز\s*ها?ی?\s+[آ-ی\s]*\b(وصول|کسب|بود|است|هست|بودند?)\b',  # از چه جزهایی وصول شده است
            ' ',
            query_clean,
            flags=re.IGNORECASE
        )
        query_clean = re.sub(
            r'از\s+چه\s+راه\s*ها?ی?\s+[آ-ی\s]*\b(کسب|بود|است|هست|بودند?|داشته)\b',  # از چه راههایی کسب کرده است
            ' ',
            query_clean,
            flags=re.IGNORECASE
        )
        query_clean = re.sub(
            r'چه\s+مواردی\s+بودند?',  # چه مواردی بودند
            ' ',
            query_clean,
            flags=re.IGNORECASE
        )
        query_clean = re.sub(
            r'کدام\s+بند\s+بود\s+[آ-ی\s]*',  # کدام بند بوده است
            ' ',
            query_clean,
            flags=re.IGNORECASE
        )
        query_clean = re.sub(
            r'مربوط\s+به\s+[آ-ی\s]*',  # مربوط به کدام بند
            ' ',
            query_clean,
            flags=re.IGNORECASE
        )
        # 🔧 CRITICAL: حذف کلمات سوالی با handling typo ها
        # چقدر، چند، چیه، کجا و typo های رایج آنها
        # 🐛 BUG FIX: استفاده از word boundary برای "کی" تا "پزشکی" خراب نشود
        query_clean = re.sub(
            r'چقدر|چثدر|چگدر|چ+قدر|چند|چندتا|چنده|چیه|چیست|چیسنت|چیا|چیو|چطور|چجور|چگونه|کجا|کجاست|(?<![آ-ی])کی(?![آ-ی])|(?<![آ-ی])کیه(?![آ-ی])|کدام|کداما',
            ' ',
            query_clean,
            flags=re.IGNORECASE
        )
        # حذف عبارات سوالی ترکیبی
        query_clean = re.sub(
            r'چه\s+بخش|چه\s+قسمت|از\s+چه\s+راه|هرکدام|چقدر\s+سهم|توسط\s+چه|چه\s+دستگاه|چه\s+موقع|چه\s+زمان',
            ' ',
            query_clean,
            flags=re.IGNORECASE
        )
        # حذف کلمات ربطی و اضافی
        query_clean = re.sub(
            r'\b(بودند?|است|هست|بود|شده|گردد|می\s+شود|خواهد|مربوط|کدام)\b',
            ' ',
            query_clean,
            flags=re.IGNORECASE
        )
        
        # حذف stop words رایج که می‌توانند در entity extraction اشتباه ایجاد کنند
        # این کار قبل از entity extraction انجام می‌شود
        # اما "با" را حذف نمی‌کنیم چون ممکن است بخشی از entity باشد (مثل "ستاد مبارزه با مواد مخدر")
        query_clean = re.sub(r'\s+در\s+', ' ', query_clean)  # remove standalone "در"
        query_clean = re.sub(r'\s+از\s+', ' ', query_clean)  # remove standalone "از"
        query_clean = re.sub(r'\s+به\s+', ' ', query_clean)  # remove standalone "به"
        # "با" را حذف نمی‌کنیم - ممکن است بخشی از entity باشد
        
        # حذف stop words اضافی قبل از استخراج entity
        # این کار برای جلوگیری از تطبیق بیش از حد در الگوها انجام می‌شود
        query_clean = re.sub(
            r'\b(مجموعا|داشته|بوده|است|هست|بود|گردد|شده|می\s+شود|خواهد)\b',
            ' ',
            query_clean,
            flags=re.IGNORECASE
        )
        
        # نرمال‌سازی
        query_clean = self.normalize_text(query_clean)
        
        # جستجوی الگوهای شناخته شده
        entity_phrases = []
        
        # ابتدا special cases (full match patterns) را در query اصلی (قبل از cleaning و normalization) جستجو کنیم
        # این کار برای حفظ entity‌های کامل مثل "ستاد مبارزه با مواد مخدر" است
        special_case_found = False
        
        for pattern_info in known_patterns:
            if isinstance(pattern_info, tuple):
                pattern, use_full_match = pattern_info
                if use_full_match:  # فقط full match patterns (special cases)
                    # جستجو در query اصلی (بدون normalization) برای حفظ کامل entity
                    matches = list(re.finditer(pattern, query, re.IGNORECASE))
                    if matches:
                        for match in matches:
                            phrase = match.group(0)
                            phrase = ' '.join(phrase.split())  # فقط normalize spaces
                            # فقط normalization کاراکترهای ی/ي و ک/ك را اعمال می‌کنیم
                            # اما "مخدر" را به "مخ" تبدیل نمی‌کنیم
                            if phrase and phrase not in entity_phrases:
                                entity_phrases.append(phrase)
                                special_case_found = True
                                logger.info(f"🔍 Found special case entity (before normalization): {phrase}")
                    
                    # اگر در query اصلی پیدا نشد، در query_clean هم جستجو کن
                    if not matches:
                        matches_clean = list(re.finditer(pattern, query_clean, re.IGNORECASE))
                        if matches_clean:
                            for match in matches_clean:
                                phrase = match.group(0)
                                phrase = ' '.join(phrase.split())
                                if phrase and phrase not in entity_phrases:
                                    entity_phrases.append(phrase)
                                    special_case_found = True
                                    logger.info(f"🔍 Found special case entity (in cleaned query): {phrase}")
        
        # اگر special case پیدا شد، از آن استفاده کن (skip patterns عمومی)
        if special_case_found:
            logger.info(f"🔍 Found special case entities: {entity_phrases}")
        else:
            # 🔧 CRITICAL FIX: اگر special case پیدا نشد، patterns عمومی را در query_clean جستجو کنیم
            # 🐛 BUG FIX: indentation اصلاح شد - قبلاً فقط آخرین pattern چک می‌شد!
            for pattern_info in known_patterns:
                # فقط patterns غیر special case
                if isinstance(pattern_info, tuple):
                    pattern, use_full_match = pattern_info
                    if use_full_match:
                        continue  # skip special cases (already checked)
                else:
                    # backward compatibility for old format
                    pattern = pattern_info
                    use_full_match = False
                
                # 🔧 FIX: این بخش باید داخل حلقه for باشد (نه بیرون آن)
                if use_full_match:
                    # برای الگوهای بدون capturing group، از search استفاده می‌کنیم
                    matches = re.finditer(pattern, query_clean, re.IGNORECASE)
                    for match in matches:
                        phrase = match.group(0)  # full match
                        phrase = ' '.join(phrase.split())
                        phrase = phrase.translate(self.char_normalization_map)
                        phrase_words = phrase.split()
                        all_stop_words = all(word.lower() in self.stop_words for word in phrase_words)
                        single_stop_word = len(phrase_words) == 1 and phrase_words[0].lower() in self.stop_words
                        if phrase and not (all_stop_words or single_stop_word):
                            entity_phrases.append(phrase)
                else:
                    # برای الگوهای با capturing group، باید prefix را اضافه کنیم
                    matches = re.finditer(pattern, query_clean, re.IGNORECASE)
                    for match in matches:
                        full_match = match.group(0)  # full match شامل prefix
                        phrase = full_match
                        phrase = ' '.join(phrase.split())
                        phrase = phrase.translate(self.char_normalization_map)
                        phrase_words = phrase.split()
                        all_stop_words = all(word.lower() in self.stop_words for word in phrase_words)
                        single_stop_word = len(phrase_words) == 1 and phrase_words[0].lower() in self.stop_words
                        if phrase and not (all_stop_words or single_stop_word):
                            entity_phrases.append(phrase)
        
        # اگر entity phrase پیدا شد، آن را برگردان
        if entity_phrases:
            logger.info(f"🔍 Extracted Entity Phrases: {entity_phrases}")
            # Clean up: حذف کلمات اضافی از entity
            cleaned_phrases = []
            for phrase in entity_phrases:
                # حذف "سال" از ابتدا و انتها
                cleaned = phrase.strip()
                cleaned = re.sub(r'^\s*(سال|سالها|سال‌ها)\s+', '', cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r'\s+(سال|سالها|سال‌ها)\s*$', '', cleaned, flags=re.IGNORECASE)
                # حذف کلمات پرسشی و اضافی - بهبود برای حذف دقیق‌تر
                cleaned = re.sub(r'\s+(چه|جز|جزء|جزهایی|جزها|چه\s+جز|چه\s+جزء)\s*$', '', cleaned, flags=re.IGNORECASE)
                # NOTE: 'راه' removed from this list — it's part of "وزارت راه و شهرسازی" entity name
                cleaned = re.sub(r'\s+(مربوط|بودند?|است|هست|بود|کدام|مواردی|های)\s*$', '', cleaned, flags=re.IGNORECASE)
                # 🔧 FIX: پس از حذف "های"، "سال" که در انتها باقی مانده را هم حذف کن
                cleaned = re.sub(r'\s+(سال|سالها|سال‌ها)\s*$', '', cleaned, flags=re.IGNORECASE)
                # حذف از ابتدا
                cleaned = re.sub(r'^(چه|جز|جزء|جزهایی|جزها|مربوط|بودند?|های)\s+', '', cleaned, flags=re.IGNORECASE)
                # حذف "چه" که در انتها باقی مانده
                cleaned = re.sub(r'\s+چه\s*$', '', cleaned, flags=re.IGNORECASE)
                cleaned = cleaned.strip()
                if cleaned and cleaned not in ['سال', 'سالها', 'سال‌ها', 'چه', 'جز', 'مربوط']:
                    cleaned_phrases.append(cleaned)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_phrases = []
            for phrase in cleaned_phrases:
                if phrase not in seen:
                    seen.add(phrase)
                    unique_phrases.append(phrase)
            if len(unique_phrases) != len(entity_phrases):
                logger.info(f"   Removed {len(entity_phrases) - len(unique_phrases)} duplicate/cleaned entities")
            
            # 🔧 CRITICAL: اعمال entity mapping برای تبدیل entity ها به variant های database
            # استفاده از HybridEntityMapper اگر موجود باشد، در غیر این صورت static mapping
            if collection_name:
                try:
                    mapped_phrases = []
                    for phrase in unique_phrases:
                        # اولویت 1: استفاده از HybridEntityMapper (dynamic + static)
                        if self.entity_mapper:
                            mapped_variants = self.entity_mapper.map_entity(phrase, table_name="masaref2_sheet1", use_dynamic=True)
                            logger.debug(f"📋 [HYBRID] Entity mapped: '{phrase}' -> {len(mapped_variants)} variants")
                        else:
                            # اولویت 2: استفاده از static mapping (backward compatibility)
                            from config.collection_instructions import CollectionInstructions
                            mapped_variants = CollectionInstructions.map_entity(phrase, collection_name)
                            logger.debug(f"📋 [STATIC] Entity mapped: '{phrase}' -> {len(mapped_variants)} variants")
                        
                        # استفاده از اولین variant (که معمولاً دقیق‌ترین است)
                        if mapped_variants and len(mapped_variants) > 0:
                            mapped_phrases.append(mapped_variants[0])
                            if len(mapped_variants) > 1:
                                logger.info(f"📋 Entity mapped: '{phrase}' -> '{mapped_variants[0]}' (from {len(mapped_variants)} variants)")
                        else:
                            mapped_phrases.append(phrase)
                    unique_phrases = mapped_phrases
                except Exception as e:
                    logger.debug(f"Entity mapping failed: {e}")
            
            # اگر special case پیدا شد، فقط همان را برگردان (نه fallback)
            if special_case_found and unique_phrases:
                logger.info(f"✅ Returning special case entities: {unique_phrases}")
                return unique_phrases
            elif unique_phrases:
                return unique_phrases
        
        # fallback: استخراج token به token (روش قبلی)
        tokens = re.findall(r'[آ-یA-Za-z0-9]+', query_clean)
        
        entity_tokens = []
        for token in tokens:
            token_lower = token.lower()
            # حذف stop words، اعداد، و کلمات کوتاه
            if token_lower in self.stop_words or token.isdigit() or len(token) <= 2:
                continue
            # حذف کلمات component
            if token_lower in self.income_component_keywords:
                continue
            # نرمال‌سازی
            normalized = token.translate(self.char_normalization_map)
            entity_tokens.append(normalized)
        
        return entity_tokens
    
    def _detect_income_type(self, query_lower: str) -> str:
        """تشخیص نوع درآمد (اختصاصی، عمومی، ملی، استانی، کل)
        
        🔧 FIX: استفاده از word boundary برای جلوگیری از false positive
        مثال: "استاندارد" نباید با "استانی" اشتباه گرفته شود
        """
        import re
        
        # تابع کمکی برای چک کردن کلمه به صورت مستقل (نه بخشی از کلمه دیگر)
        def has_word(query: str, word: str) -> bool:
            # استفاده از word boundary: کلمه باید مستقل باشد
            # مثال: "استانی" باید match شود ولی "استاندارد" نباید
            pattern = rf'(?<![آ-ی]){re.escape(word)}(?![آ-ی])'
            return bool(re.search(pattern, query))
        
        # چک کردن استانی - باید دقیق باشد و "استاندارد" را شامل نشود
        has_estani = has_word(query_lower, 'استانی') or has_word(query_lower, 'استاني')
        has_melli = has_word(query_lower, 'ملی') or has_word(query_lower, 'ملي')
        
        if 'اختصاص' in query_lower:
            if has_melli:
                return 'ملی_اختصاصی'
            if has_estani:
                return 'استانی_اختصاصی'
            return 'اختصاصی'
        if 'عمومی' in query_lower or 'عمومي' in query_lower:
            if has_melli:
                return 'ملی_عمومی'
            if has_estani:
                return 'استانی_عمومی'
            return 'عمومی'
        if has_melli:
            return 'ملی'
        if has_estani:
            return 'استانی'
        return 'کل'
    
    def _build_sql_filters(
        self,
        entity_names: List[str],
        income_component: Optional[str],
        normalized_query: str,
        collection_name: Optional[str] = None
    ) -> Dict[str, Optional[str]]:
        """
        ساخت فیلترهای SQL
        
        🔧 بهبود: استفاده از SmartColumnDetector برای تشخیص هوشمند ستون‌ها
        """
        filters = {
            'entity_filter': None,
            'component_filter': None
        }
        
        # 🔧 NEW: استفاده از SmartColumnDetector برای تشخیص هوشمند
        if SMART_DETECTOR_AVAILABLE:
            try:
                detection_result = detect_columns(normalized_query, "manabe_sheet1")
                
                # اگر hierarchy level تشخیص داده شده، از WHERE clause هوشمند استفاده کن
                if detection_result.hierarchy_level and detection_result.where_clause != "1=1":
                    filters['component_filter'] = detection_result.where_clause
                    logger.info(f"🎯 SmartColumnDetector: Using hierarchy-aware filter")
                    logger.info(f"   Level: {detection_result.hierarchy_level}")
                    logger.info(f"   Column: {detection_result.primary_column}")
                    logger.info(f"   Terms: {detection_result.search_terms}")
                    
                    # فقط entity filter رو اضافه کن (اگر موجود باشه)
                    if entity_names:
                        filters['entity_filter'] = self._build_entity_filter_only(entity_names, normalized_query)
                    
                    return filters
                    
            except Exception as e:
                logger.warning(f"SmartColumnDetector failed: {e}, falling back to legacy method")

        # فیلتر component (عنوان_جزء)
        # CRITICAL: برای component های چندکلمه‌ای، همیشه از exact phrase استفاده می‌کنیم
        # بهبود: حذف خط تیره و فاصله‌های اضافی برای جستجوی انعطاف‌پذیرتر
        if income_component:
            # حذف خط تیره و فاصله‌های اضافی از phrase
            cleaned_phrase = income_component.replace('\u200c', ' ').replace('\u200f', ' ').replace('-', ' ')
            cleaned_phrase = ' '.join(cleaned_phrase.split())  # normalize multiple spaces
            safe_phrase = cleaned_phrase.replace("'", "''")
            
            # استفاده از REGEXP_REPLACE برای حذف خط تیره و فاصله‌های اضافی از column
            # Note: backslash باید escape شود در SQL string
            def _normalize_column(col_name: str) -> str:
                return (
                    f"REGEXP_REPLACE(REPLACE(REPLACE(REPLACE(TRANSLATE({col_name}, 'يكيۀةأإٱ', 'یکیهههاا'), "
                    f"E'\\u200c', ' '), E'\\u200f', ' '), '-', ' '), E'\\\\s+', ' ', 'g')"
                )
            
            # 🎯 CRITICAL FIX: تشخیص سطح سلسله مراتب (hierarchy level) از query
            # اگر کاربر کلمه "بخش" یا "قسمت" یا "بند" یا "جزء" رو به کار برده،
            # فقط در همان ستون جستجو می‌کنیم (نه در همه ستون‌ها با OR)
            hierarchy_level = self._detect_hierarchy_level_from_query(normalized_query, income_component)
            
            # بررسی اینکه آیا component چندکلمه‌ای است
            component_words = cleaned_phrase.split()
            if len(component_words) > 1:
                # استفاده از exact phrase برای component های چندکلمه‌ای
                jozv_norm = _normalize_column('"عنوان_جزء"')
                bakhsh_norm = _normalize_column('"عنوان_بخش"')
                band_norm = _normalize_column('"عنوان_بند"')
                qesmat_norm = _normalize_column('"عنوان_قسمت"')
                
                # 🎯 اگر hierarchy level مشخص شده، فقط در همان ستون جستجو کن
                if hierarchy_level == 'بخش':
                    # 🔧 CRITICAL FIX: استخراج کلمات کلیدی از component برای matching بهتر
                    # مثال: "بخش درآمدهای مالیاتی" → کلمات کلیدی: "بخش", "مالیات"
                    keywords = self._extract_keywords_from_component(cleaned_phrase)
                    
                    if len(keywords) >= 2:
                        # اگر چند کلمه کلیدی داریم، از pattern AND استفاده می‌کنیم
                        # مثال: %بخش% AND %مالیات%
                        keyword_conditions = [f"{bakhsh_norm} ILIKE '%{kw}%'" for kw in keywords]
                        filters['component_filter'] = ' AND '.join(keyword_conditions)
                        logger.info(f"   🎯 Searching in عنوان_بخش with keywords: {keywords}")
                    else:
                        # اگر فقط یک کلمه کلیدی داریم یا نتوانستیم استخراج کنیم، از phrase کامل استفاده می‌کنیم
                        filters['component_filter'] = f"{bakhsh_norm} ILIKE '%{safe_phrase}%'"
                        logger.info(f"   🎯 Searching ONLY in عنوان_بخش (hierarchy level: بخش)")
                        
                elif hierarchy_level == 'قسمت':
                    # 🔧 FIX: برای "واگذاری دارایی" از fuzzy matching استفاده کن
                    if re.search(r'واگذاری', cleaned_phrase, re.IGNORECASE):
                        key_words_q = [w for w in cleaned_phrase.split() if len(w) > 2 and w not in ['های', 'هاي', 'از', 'در', 'به', 'حاصل', 'منابع']]
                        if len(key_words_q) >= 2:
                            kw_q_conditions = [f"{qesmat_norm} ILIKE '%{w.replace(chr(39), chr(39)+chr(39))}%'" for w in key_words_q]
                            kw_b_conditions = [f"{bakhsh_norm} ILIKE '%{w.replace(chr(39), chr(39)+chr(39))}%'" for w in key_words_q]
                            filters['component_filter'] = f"({' AND '.join(kw_q_conditions)}) OR ({' AND '.join(kw_b_conditions)})"
                        else:
                            filters['component_filter'] = f"{qesmat_norm} ILIKE '%{safe_phrase}%' OR {bakhsh_norm} ILIKE '%{safe_phrase}%'"
                    else:
                        filters['component_filter'] = f"{qesmat_norm} ILIKE '%{safe_phrase}%'"
                    logger.info(f"   🎯 Searching in عنوان_قسمت (hierarchy level: قسمت)")
                elif hierarchy_level == 'بند':
                    filters['component_filter'] = f"{band_norm} ILIKE '%{safe_phrase}%'"
                    logger.info(f"   🎯 Searching ONLY in عنوان_بند (hierarchy level: بند)")
                elif hierarchy_level == 'جزء':
                    filters['component_filter'] = f"{jozv_norm} ILIKE '%{safe_phrase}%'"
                    logger.info(f"   🎯 Searching ONLY in عنوان_جزء (hierarchy level: جزء)")
                else:
                    # اگر سطح سلسله مراتب مشخص نیست، در چند ستون جستجو کن (رفتار قبلی)
                    filters['component_filter'] = (
                        f"{jozv_norm} ILIKE '%{safe_phrase}%' "
                        f"OR {bakhsh_norm} ILIKE '%{safe_phrase}%' "
                        f"OR {qesmat_norm} ILIKE '%{safe_phrase}%'"
                    )
                    logger.info(f"   ℹ️ No specific hierarchy level detected, searching in multiple columns")
                
                logger.info(f"   ✅ Using exact phrase for multi-word component: '{income_component}' -> '{cleaned_phrase}'")
            else:
                # برای component های تک کلمه‌ای هم از exact phrase استفاده می‌کنیم
                jozv_norm = _normalize_column('"عنوان_جزء"')
                bakhsh_norm = _normalize_column('"عنوان_بخش"')
                band_norm = _normalize_column('"عنوان_بند"')
                qesmat_norm = _normalize_column('"عنوان_قسمت"')
                
                # 🎯 اگر hierarchy level مشخص شده، فقط در همان ستون جستجو کن
                if hierarchy_level == 'بخش':
                    filters['component_filter'] = f"{bakhsh_norm} ILIKE '%{safe_phrase}%'"
                    logger.info(f"   🎯 Searching ONLY in عنوان_بخش (hierarchy level: بخش)")
                elif hierarchy_level == 'قسمت':
                    filters['component_filter'] = f"{qesmat_norm} ILIKE '%{safe_phrase}%'"
                    logger.info(f"   🎯 Searching ONLY in عنوان_قسمت (hierarchy level: قسمت)")
                elif hierarchy_level == 'بند':
                    filters['component_filter'] = f"{band_norm} ILIKE '%{safe_phrase}%'"
                    logger.info(f"   🎯 Searching ONLY in عنوان_بند (hierarchy level: بند)")
                elif hierarchy_level == 'جزء':
                    filters['component_filter'] = f"{jozv_norm} ILIKE '%{safe_phrase}%'"
                    logger.info(f"   🎯 Searching ONLY in عنوان_جزء (hierarchy level: جزء)")
                else:
                    filters['component_filter'] = (
                        f"{jozv_norm} ILIKE '%{safe_phrase}%' "
                        f"OR {bakhsh_norm} ILIKE '%{safe_phrase}%'"
                    )

        # فیلتر entity (عنوان_دستگاه)
        if entity_names:
            entity_conditions: List[str] = []
            
            logger.info(f"🔍 Entity Filter Generation:")
            logger.info(f"   Entity Names: {entity_names}")
            logger.info(f"   Normalized Query: {normalized_query[:100]}")

            # IMPORTANT: Special case for "وزارت کشور" - must use exact phrase matching
            # This prevents false positives like "وزارت بهداشت ... کشور" from matching
            # بررسی دقیق: آیا 'وزارت کشور' به عنوان یک عبارت کامل وجود دارد؟
            has_ministry_country_exact = any('وزارت کشور' == name.strip() for name in entity_names)
            
            # بررسی: آیا 'وزارت' و 'کشور' جداگانه وجود دارند و در query کنار هم هستند؟
            has_وزارت = any('وزارت' in name.lower() for name in entity_names)
            has_کشور = any('کشور' in name.lower() for name in entity_names)
            query_has_وزارت_کشور = 'وزارت کشور' in normalized_query or 'وزارت  کشور' in normalized_query
            
            if has_ministry_country_exact or (has_وزارت and has_کشور and query_has_وزارت_کشور):
                # برای "وزارت کشور"، همیشه از exact phrase استفاده کن
                safe_name = 'وزارت کشور'.replace("'", "''")
                entity_conditions.append(
                    "("
                    f"TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱ', 'یکیهههاا') ILIKE '%{safe_name}%' "
                    f"OR TRANSLATE(\"عنوان_دستگاه_اصلی\", 'يكيۀةأإٱ', 'یکیهههاا') ILIKE '%{safe_name}%')"
                )
            else:
                # For other entities, use normal logic
                # CRITICAL FIX: For multi-word entities, ONLY use exact phrase matching
                # This prevents false positives like "بنیاد ملی نخبگان" matching "بنیاد سعدی"
                # Check if we have multi-word: either multiple items OR single item with space
                has_multi_word = len(entity_names) > 1 or any(' ' in name for name in entity_names)
                
                if has_multi_word:
                    # 🔧 CRITICAL FIX: اگر یکی از entity ها subset دیگری باشه، فقط طولانی‌ترین رو استفاده کن
                    # مثال: ['فرهنگستان علوم ایران', 'فرهنگستان علوم'] -> 'فرهنگستان علوم ایران'
                    filtered_entities = []
                    for i, entity in enumerate(entity_names):
                        is_subset = False
                        for j, other in enumerate(entity_names):
                            if i != j and entity in other:
                                is_subset = True
                                break
                        if not is_subset:
                            filtered_entities.append(entity)
                    
                    if not filtered_entities:
                        filtered_entities = [entity_names[0]]  # fallback
                    
                    logger.info(f"   🔧 Filtered entities (removed subsets): {entity_names} -> {filtered_entities}")
                    
                    # Build the phrase - بهبود: استخراج phrase کامل از query با کلمات میانی
                    if len(filtered_entities) == 1 and ' ' in filtered_entities[0]:
                        # Entity کامل استخراج شده (مثل "ستاد مبارزه با مواد مخدر")
                        # از آن به صورت مستقیم استفاده می‌کنیم
                        joined_phrase = filtered_entities[0]  # Already a phrase like "بنیاد سعدی" or "ستاد مبارزه با مواد مخدر"
                        logger.info(f"   ✅ Using complete entity phrase: '{joined_phrase}'")
                    elif len(filtered_entities) == 1:
                        # Single entity (possibly without space)
                        joined_phrase = filtered_entities[0]
                        logger.info(f"   ✅ Using single filtered entity: '{joined_phrase}'")
                    else:
                        # Entity‌های جداگانه - استخراج phrase کامل از query با کلمات میانی
                        joined_phrase = self._extract_phrase_with_middle_words(filtered_entities, normalized_query)
                        if not joined_phrase:
                            joined_phrase = ' '.join(filtered_entities)  # fallback
                    
                    logger.info(f"   Multi-word entity - Joined Phrase: '{joined_phrase}'")
                    
                    # 🔧 CRITICAL: اعمال entity mapping برای تبدیل entity به variant های database
                    # استفاده از همه variants برای جستجو (نه فقط اولین variant)
                    # map_entity خودش original entity را اول برمی‌گرداند
                    mapped_variants = [joined_phrase]  # fallback: اگر mapping نباشد
                    if collection_name:
                        try:
                            # اولویت 1: استفاده از HybridEntityMapper (dynamic + static)
                            if self.entity_mapper:
                                all_variants = self.entity_mapper.map_entity(joined_phrase, table_name="masaref2_sheet1", use_dynamic=True)
                                logger.debug(f"📋 [HYBRID] Entity mapped in filter: '{joined_phrase}' -> {len(all_variants)} variants")
                            else:
                                # اولویت 2: استفاده از static mapping (backward compatibility)
                                from config.collection_instructions import CollectionInstructions
                                all_variants = CollectionInstructions.map_entity(joined_phrase, collection_name)
                                logger.debug(f"📋 [STATIC] Entity mapped in filter: '{joined_phrase}' -> {len(all_variants)} variants")
                            
                            if all_variants and len(all_variants) > 0:
                                # map_entity خودش original entity را اول برمی‌گرداند
                                mapped_variants = all_variants
                                logger.info(f"📋 Entity mapped in filter: '{joined_phrase}' -> {len(mapped_variants)} variants: {mapped_variants[:3]}...")
                        except Exception as e:
                            logger.debug(f"Entity mapping in filter failed: {e}")
                    
                    # CRITICAL: Always use exact phrase for multi-word entities
                    # این بار از همه variants استفاده می‌کنیم (original + mapped)
                    # 🔧 CRITICAL: نرمالایز کردن original phrase برای استفاده در fuzzy matching
                    normalized_phrase = self.normalize_text(joined_phrase)
                    
                    if mapped_variants:
                        logger.info(f"   ✅ Using EXACT PHRASE for {len(mapped_variants)} variant(s)")
                        # ساخت شرط OR برای همه variants
                        variant_conditions = []
                        
                        # 🔧 DYNAMIC FIX: تشخیص هوشمند اینکه آیا باید parent column هم چک شود
                        # وزارتخانه‌ها و سازمان‌های بزرگ به عنوان دستگاه اصلی (parent) ثبت شده‌اند
                        # وقتی کاربر "درآمد وزارت نفت" می‌پرسد، باید همه زیرمجموعه‌ها که parent آنها "وزارت نفت" است هم جمع شوند
                        words_count = len(joined_phrase.split())
                        
                        # تشخیص parent entities: وزارتخانه‌ها و نهادهای بزرگ
                        # 🔧 FIX: اضافه کردن شورا، کمیته، صندوق، بانک و سایر نهادهای مادر
                        parent_entity_prefixes = [
                            'وزارت', 'سازمان', 'نهاد', 'ستاد', 'بنیاد', 'معاونت',
                            'شورای', 'شوراي', 'شورا', 'کمیته', 'کميته', 'صندوق',
                            'بانک', 'بانك', 'دانشگاه', 'مرکز', 'فرهنگستان',
                            'پژوهشگاه', 'پژوهشکده', 'هیات', 'هیأت'
                        ]
                        is_parent_entity = any(joined_phrase.strip().startswith(prefix) for prefix in parent_entity_prefixes)
                        
                        # برای parent entities (مثل وزارتخانه‌ها)، ALWAYS check parent column
                        # برای entity های طولانی (3+ کلمه) هم parent را چک کن
                        check_parent_column = words_count >= 3 or is_parent_entity
                        
                        for variant in mapped_variants:
                            # 🔧 CRITICAL: نرمالایز کردن search term برای match با TRANSLATE
                            normalized_variant = self.normalize_text(variant)
                            safe_variant = normalized_variant.replace("'", "''")
                            
                            # 🔧 FIX: استفاده از TRANSLATE روی مقدار ILIKE هم
                            # تا کاراکترهای آ/أ/إ در search term هم normalize شوند
                            if check_parent_column:
                                # برای entity های طولانی: هر دو ستون را چک کن
                                variant_conditions.append(
                                    f"(TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_variant}%', 'يكيۀةأإٱآ', 'یکیهههااا') "
                                    f"OR TRANSLATE(\"عنوان_دستگاه_اصلی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_variant}%', 'يكيۀةأإٱآ', 'یکیهههااا'))"
                                )
                            else:
                                # برای entity های کوتاه (مثل "وزارت نفت"): فقط عنوان_دستگاه_اجرایی را چک کن
                                variant_conditions.append(
                                    f"TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_variant}%', 'يكيۀةأإٱآ', 'یکیهههااا')"
                                )
                        
                        # 🔧 اضافه کردن شرط wildcard-based برای phrases چند کلمه‌ای
                        # 🔧 FIX: از wildcard بین کلمات استفاده کن تا "و" و کلمات اضافی بین کلمات entity هم match شوند
                        # مثال: "وزارت آموزش پرورش" -> '%وزارت%آموزش%پرورش%' تا "وزارت آموزش و پرورش" هم match شود
                        # ⚠️ IMPORTANT: 
                        # - فقط برای 3 کلمه wildcard بساز (مثل "وزارت آموزش پرورش" -> '%وزارت%آموزش%پرورش%')
                        # - برای 2 کلمه (مثل "وزارت نیرو") wildcard باعث false positive میشه
                        # - برای 4+ کلمه (مثل "کمیته ملی المپیک ایران") exact match کافی است
                        #   و wildcard باعث false positive با "کمیته ملی پارا المپیک ایران" میشه
                        #   برای 4+ کلمه، exact match کافی است و wildcard باعث false positive میشه
                        words = normalized_phrase.split()
                        # کلمات عمومی که ممکن است در دیتابیس نباشند
                        generic_prefixes = {'شرکت', 'شركت', 'سازمان', 'موسسه', 'مؤسسه', 'بنیاد', 'صندوق'}
                        
                        # 🔧 FIX: اضافه کردن fuzzy pattern فقط وقتی کلمات مشترک حذف شده‌اند
                        # حذف کلمات common و استفاده از کلمات کلیدی
                        common_words = ['و', 'از', 'به', 'با', 'در', 'که', 'این', 'آن', 'یا', 'امور']
                        significant_words = [w for w in words if len(w) > 1 and w not in common_words]
                        
                        # 🔧 CRITICAL FIX: fuzzy pattern فقط زمانی اضافه می‌شود که کلمات مشترک از عبارت
                        # حذف شده باشند - مثال: "وزارت علوم" نیازی به fuzzy ندارد (false positive ایجاد می‌کند)
                        # مثال صحیح: "وزارت امور اقتصادی و دارایی" چون 'امور' و 'و' حذف شده، fuzzy لازم است
                        words_meaningful = [w for w in words if len(w) > 1]
                        _needs_fuzzy = len(significant_words) < len(words_meaningful)
                        # 🔧 FIX: fuzzy pattern برای entities با 3+ کلمه نیز اضافه می‌شود
                        _should_add_fuzzy = (_needs_fuzzy or len(significant_words) >= 3) and len(significant_words) >= 2
                        
                        if _should_add_fuzzy:
                            # Pattern: %کلمه1%کلمه2%کلمه3%
                            fuzzy_pattern = '%' + '%'.join(w.replace("'", "''") for w in significant_words) + '%'
                            if check_parent_column:
                                entity_conditions.append(
                                    "("
                                    f"TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('{fuzzy_pattern}', 'يكيۀةأإٱآ', 'یکیهههااا') "
                                    f"OR TRANSLATE(\"عنوان_دستگاه_اصلی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('{fuzzy_pattern}', 'يكيۀةأإٱآ', 'یکیهههااا'))"
                                )
                            else:
                                variant_conditions.append(
                                    f"TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('{fuzzy_pattern}', 'يكيۀةأإٱآ', 'یکیهههااا')"
                                )
                            logger.info(f"   🔍 Added fuzzy keyword pattern: {fuzzy_pattern[:100]}")
                        
                        # 🔧 FIX: اضافه کردن شرط بدون پیشوند عمومی (برای همه طول‌ها)
                        # مثال: "سازمان پژوهشگاه فضایی ایران" → DB دارد "پژوهشگاه فضایی ایران" (بدون سازمان)
                        generic_org_prefixes_set = {'سازمان', 'شركت', 'موسسه', 'مؤسسه', 'صندوق', 'نهاد', 'ستاد'}
                        if words and words[0] in generic_org_prefixes_set and len(words) > 2:
                            phrase_no_prefix = ' '.join(words[1:])
                            safe_no_prefix = phrase_no_prefix.replace("'", "''")
                            if check_parent_column:
                                variant_conditions.append(
                                    f"(TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_no_prefix}%', 'يكيۀةأإٱآ', 'یکیهههااا') "
                                    f"OR TRANSLATE(\"عنوان_دستگاه_اصلی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_no_prefix}%', 'يكيۀةأإٱآ', 'یکیهههااا'))"
                                )
                            else:
                                variant_conditions.append(
                                    f"TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_no_prefix}%', 'يكيۀةأإٱآ', 'یکیهههااا')"
                                )
                            logger.info(f"   🔍 Added condition without generic prefix: '{phrase_no_prefix}'")
                        
                        if len(words) == 3:
                            # ساخت wildcard pattern از کلمات entity
                            # 🔧 FIX: فقط برای entity های 3 کلمه‌ای wildcard بساز
                            # برای 4+ کلمه (مثل "کمیته ملی المپیک ایران") exact match کافی است
                            # و wildcard مثل '%کمیته%ملی%المپیک%ایران%' باعث false positive با "پارا المپیک" میشه
                            key_words = []
                            for w in words:
                                if len(w) > 1:  # حذف کلمات تک‌حرفی
                                    key_words.append(w.replace("'", "''"))
                            if len(key_words) >= 2:
                                wildcard_pattern = '%' + '%'.join(key_words) + '%'
                                if check_parent_column:
                                    variant_conditions.append(
                                        f"(TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('{wildcard_pattern}', 'يكيۀةأإٱآ', 'یکیهههااا') "
                                        f"OR TRANSLATE(\"عنوان_دستگاه_اصلی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('{wildcard_pattern}', 'يكيۀةأإٱآ', 'یکیهههااا'))"
                                    )
                                else:
                                    variant_conditions.append(
                                        f"TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('{wildcard_pattern}', 'يكيۀةأإٱآ', 'یکیهههااا')"
                                    )
                                logger.info(f"   🔍 Added wildcard pattern: {wildcard_pattern[:100]}...")
                                
                                # 🔧 FIX: اضافه کردن wildcard بدون کلمات عمومی (شرکت، سازمان، ...)
                                # مثال: "شرکت بازرگانی گاز ایران" -> '%بازرگانی%گاز%ایران%'
                                # چون در دیتابیس ممکن است "بازرگاني گاز ايران" (بدون شرکت) باشد
                                non_generic_words = [w for w in key_words if w not in generic_prefixes]
                                if len(non_generic_words) >= 2 and len(non_generic_words) < len(key_words):
                                    wildcard_no_prefix = '%' + '%'.join(non_generic_words) + '%'
                                    if check_parent_column:
                                        variant_conditions.append(
                                            f"(TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('{wildcard_no_prefix}', 'يكيۀةأإٱآ', 'یکیهههااا') "
                                            f"OR TRANSLATE(\"عنوان_دستگاه_اصلی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('{wildcard_no_prefix}', 'يكيۀةأإٱآ', 'یکیهههااا'))"
                                        )
                                    else:
                                        variant_conditions.append(
                                            f"TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('{wildcard_no_prefix}', 'يكيۀةأإٱآ', 'یکیهههااا')"
                                        )
                                    logger.info(f"   🔍 Added wildcard (no prefix): {wildcard_no_prefix[:100]}...")
                        
                        # ترکیب همه conditions با OR
                        entity_conditions.append("(" + " OR ".join(variant_conditions) + ")")
                        
                        # 🔧 CRITICAL FIX: حذف fuzzy matching برای جلوگیری از false positives
                        # مثال: "فرهنگستان علوم ایران" نباید با "فرهنگستان علوم پزشکی ایران" match بشه
                        # fuzzy matching فقط برای phrases بسیار طولانی (5+ کلمه) با کلمات کلیدی مهم اعمال میشه
                        words = normalized_phrase.split()
                        if len(words) >= 2 and len(words) <= 3:
                            # برای phrases کوتاه (2-3 کلمه)، fuzzy matching را غیرفعال کن
                            # این از false positives جلوگیری می‌کند
                            logger.info(f"   ⚠️ Skipping fuzzy match for short phrase ({len(words)} words): '{normalized_phrase}'")
                        elif len(words) > 3 and len(words) < 5:
                            # برای phrases متوسط (4 کلمه)، فقط لاگ کن و skip کن
                            logger.info(f"   ⚠️ Skipping fuzzy match for medium phrase ({len(words)} words): '{normalized_phrase}'")
                        elif len(words) >= 5:
                            # برای phrases طولانی (بیش از 3 کلمه)، از کلمات کلیدی مهم استفاده می‌کنیم
                            # کلمات کلیدی مهم: سازندگی، مرکزی، ملی، استانی، و غیره
                            important_keywords = ['سازندگی', 'مرکزی', 'ملی', 'استانی', 'کشور', 'استان']
                            found_keywords = [w for w in words if w in important_keywords]
                            
                            if found_keywords:
                                # استفاده از کلمات کلیدی مهم برای fuzzy matching
                                keyword = found_keywords[0].replace("'", "''")
                                word1 = words[0].replace("'", "''")
                                logger.info(f"   🔍 Adding fuzzy condition with keyword: '{word1}' + '{keyword}'")
                                entity_conditions.append(
                                    "("
                                    f"(TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱ', 'یکیهههاا') ILIKE '%{word1}%' "
                                    f"AND TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱ', 'یکیهههاا') ILIKE '%{keyword}%') "
                                    f"OR (TRANSLATE(\"عنوان_دستگاه_اصلی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%{word1}%' "
                                    f"AND TRANSLATE(\"عنوان_دستگاه_اصلی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%{keyword}%'))"
                                )
                            else:
                                # اگر کلمه کلیدی مهم پیدا نشد، fuzzy matching را حذف می‌کنیم
                                logger.info(f"   ⚠️ Long phrase ({len(words)} words) without important keywords - skipping fuzzy match")
                else:
                    # Single word entity - use it directly
                    for name in entity_names:
                        # 🔧 CRITICAL: نرمالایز کردن search term برای match با TRANSLATE
                        normalized_name = self.normalize_text(name)
                        safe_name = normalized_name.replace("'", "''")
                        entity_conditions.append(
                            "("
                            f"TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱ', 'یکیهههاا') ILIKE '%{safe_name}%' "
                            f"OR TRANSLATE(\"عنوان_دستگاه_اصلی\", 'يكيۀةأإٱ', 'یکیهههاا') ILIKE '%{safe_name}%')"
                        )

            if entity_conditions:
                # برای کاهش نتایج ناخواسته، اگر عبارت کامل موجود بود، آن را در اولویت قرار می‌دهیم
                filters['entity_filter'] = " OR ".join(entity_conditions)
                logger.info(f"   📝 Final Entity Filter:")
                logger.info(f"      Number of conditions: {len(entity_conditions)}")
                logger.info(f"      Filter (first 300 chars): {filters['entity_filter'][:300]}")

        return filters
    
    def _build_entity_filter_only(
        self,
        entity_names: List[str],
        normalized_query: str
    ) -> Optional[str]:
        """
        ساخت فقط entity filter (بدون component filter)
        
        این متد زمانی استفاده می‌شود که SmartColumnDetector
        component filter را ساخته و فقط entity filter لازم است.
        """
        if not entity_names:
            return None
        
        entity_conditions: List[str] = []
        
        # بررسی multi-word entity
        has_multi_word = len(entity_names) > 1 or any(' ' in name for name in entity_names)
        
        if has_multi_word:
            # 🔧 CRITICAL FIX: اگر یکی از entity ها subset دیگری باشه، فقط طولانی‌ترین رو استفاده کن
            # مثال: ['فرهنگستان علوم ایران', 'فرهنگستان علوم'] -> 'فرهنگستان علوم ایران'
            filtered_entities = []
            for i, entity in enumerate(entity_names):
                is_subset = False
                for j, other in enumerate(entity_names):
                    if i != j and entity in other:
                        is_subset = True
                        break
                if not is_subset:
                    filtered_entities.append(entity)
            
            if not filtered_entities:
                # اگر همه subset بودند (مثلاً "الف" و "الف")، از اولین استفاده کن
                filtered_entities = [entity_names[0]]
            
            # ساخت phrase
            if len(filtered_entities) == 1:
                joined_phrase = filtered_entities[0]
            elif len(filtered_entities) == 1 and ' ' in filtered_entities[0]:
                joined_phrase = filtered_entities[0]
            else:
                joined_phrase = self._extract_phrase_with_middle_words(filtered_entities, normalized_query)
                if not joined_phrase:
                    joined_phrase = ' '.join(filtered_entities)
            
            if joined_phrase:
                # 🔧 CRITICAL: نرمالایز کردن search term برای match با TRANSLATE
                normalized_phrase = self.normalize_text(joined_phrase)
                safe_phrase = normalized_phrase.replace("'", "''")
                
                # 🔧 FIX: استخراج کلمات کلیدی برای fuzzy search
                # حذف کلمات common و استفاده از significant words فقط
                words = normalized_phrase.split()
                common_words = ['و', 'از', 'به', 'با', 'در', 'که', 'این', 'آن', 'یا', 'امور']
                significant_words = [w for w in words if len(w) > 1 and w not in common_words]
                
                # اضافه کردن شرط phrase کامل (exact match)
                entity_conditions.append(
                    "("
                    f"TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_phrase}%', 'يكيۀةأإٱآ', 'یکیهههااا') "
                    f"OR TRANSLATE(\"عنوان_دستگاه_اصلی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_phrase}%', 'يكيۀةأإٱآ', 'یکیهههااا'))"
                )
                
                # 🔧 FIX: اضافه کردن شرط بدون پیشوند عمومی سازمانی
                # مثال: "سازمان پژوهشگاه فضایی ایران" → DB دارد "پژوهشگاه فضایی ایران" (بدون سازمان)
                generic_org_prefixes_list = ['سازمان', 'شرکت', 'شركت', 'موسسه', 'مؤسسه', 'صندوق', 'نهاد', 'ستاد']
                words_of_phrase = normalized_phrase.split()
                if words_of_phrase and words_of_phrase[0] in generic_org_prefixes_list and len(words_of_phrase) > 2:
                    phrase_without_prefix = ' '.join(words_of_phrase[1:])
                    safe_without_prefix = phrase_without_prefix.replace("'", "''")
                    entity_conditions.append(
                        "("
                        f"TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_without_prefix}%', 'يكيۀةأإٱآ', 'یکیهههااا') "
                        f"OR TRANSLATE(\"عنوان_دستگاه_اصلی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_without_prefix}%', 'يكيۀةأإٱآ', 'یکیهههااا'))"
                    )
                    logger.info(f"   🔍 Added condition without generic prefix: '{phrase_without_prefix}'")
                
                # 🔧 CRITICAL FIX: fuzzy pattern فقط زمانی اضافه می‌شود که کلمات مشترک حذف شده باشند
                # "وزارت علوم" → 2 کلمه، هیچ‌کدام حذف نشده → exact phrase کافی است
                # "وزارت امور اقتصادی و دارایی" → 'امور' و 'و' حذف شده → fuzzy لازم است
                words_meaningful = [w for w in words if len(w) > 1]
                _needs_fuzzy = len(significant_words) < len(words_meaningful)
                # 🔧 FIX: fuzzy pattern برای entities با 3+ کلمه نیز اضافه می‌شود
                # مثال: "آزمایشگاه نقشه برداری مغز" → DB: "آزمایشگاه ملی نقشه برداری مغز"
                _should_add_fuzzy = (_needs_fuzzy or len(significant_words) >= 3) and len(significant_words) >= 2
                
                if _should_add_fuzzy:
                    # Pattern: %کلمه1%کلمه2%کلمه3%
                    fuzzy_pattern = '%' + '%'.join(w.replace("'", "''") for w in significant_words) + '%'
                    entity_conditions.append(
                        "("
                        f"TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('{fuzzy_pattern}', 'يكيۀةأإٱآ', 'یکیهههااا') "
                        f"OR TRANSLATE(\"عنوان_دستگاه_اصلی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('{fuzzy_pattern}', 'يكيۀةأإٱآ', 'یکیهههااا'))"
                    )
                    logger.info(f"   🔍 Added fuzzy wildcard pattern for multi-word entity: '{fuzzy_pattern}'")
                
                # اگر phrase دو کلمه‌ای باشه، شرط AND با کلمات جداگانه هم اضافه کن
                # این برای handle کردن typo ها مفیده
                words = normalized_phrase.split()
                if len(words) == 2:
                    word1 = words[0].replace("'", "''")
                    word2 = words[1].replace("'", "''")
                    # استفاده از بخش اصلی کلمه اول (حداقل 3 حرف اول) برای fuzzy matching
                    word1_prefix = word1[:max(3, len(word1)-2)] if len(word1) > 3 else word1
                    # 🔧 CRITICAL FIX: استفاده از prefix کلمه دوم هم برای handle کردن typo ها
                    word2_prefix = word2[:max(3, len(word2)-2)] if len(word2) > 3 else word2
                    # 🔧 CRITICAL FIX: استفاده از LIKE ساده به جای TRANSLATE برای اجتناب از PostgreSQL bug در OR
                    entity_conditions.append(
                        "("
                        f"(\"عنوان_دستگاه_اجرایی\" LIKE '%{word1_prefix}%' "
                        f"AND \"عنوان_دستگاه_اجرایی\" LIKE '%{word2_prefix}%') "
                        f"OR (\"عنوان_دستگاه_اصلی\" LIKE '%{word1_prefix}%' "
                        f"AND \"عنوان_دستگاه_اصلی\" LIKE '%{word2_prefix}%'))"
                    )
                
        else:
            # Single word entity
            for name in entity_names:
                # 🔧 CRITICAL: نرمالایز کردن search term برای match با TRANSLATE
                normalized_name = self.normalize_text(name)
                safe_name = normalized_name.replace("'", "''")
                entity_conditions.append(
                    "("
                    f"TRANSLATE(\"عنوان_دستگاه_اجرایی\", 'يكيۀةأإٱ', 'یکیهههاا') ILIKE '%{safe_name}%' "
                    f"OR TRANSLATE(\"عنوان_دستگاه_اصلی\", 'يكيۀةأإٱ', 'یکیهههاا') ILIKE '%{safe_name}%')"
                )
        
        if entity_conditions:
            return " OR ".join(entity_conditions)
        return None
    
    def _extract_phrase_with_middle_words(self, entity_names: List[str], query: str) -> Optional[str]:
        """
        استخراج phrase کامل از query با کلمات میانی
        مثال: ['سازمان', 'استاندارد'] + query -> 'سازمان ملی استاندارد'
        
        این متد به صورت داینامیک کار می‌کند و نیازی به mapping استاتیک ندارد
        """
        if len(entity_names) < 2:
            return None
        
        # پیدا کردن موقعیت اولین و آخرین entity در query
        first_entity = entity_names[0]
        last_entity = entity_names[-1]
        
        first_pos = query.find(first_entity)
        last_pos = query.find(last_entity)
        
        if first_pos == -1 or last_pos == -1:
            return None
        
        # اگر ترتیب عوض شده، آن را تصحیح کن
        if last_pos < first_pos:
            first_entity, last_entity = last_entity, first_entity
            first_pos, last_pos = last_pos, first_pos
        
        # استخراج متن بین دو entity
        start = first_pos
        end = last_pos + len(last_entity)
        extracted = query[start:end].strip()
        
        # بررسی اینکه extracted معقول باشد (کمتر از 50 کاراکتر و شامل هر دو entity)
        if len(extracted) <= 50 and first_entity in extracted and last_entity in extracted:
            # نرمال‌سازی فاصله‌ها
            extracted = ' '.join(extracted.split())
            logger.info(f"   ✅ Extracted phrase with middle words: '{extracted}'")
            return extracted
        
        return None
    
    def _detect_query_category(self, query_lower: str) -> str:
        """
        تشخیص دسته‌بندی اصلی سوال
        
        Returns:
            'non_financial': سوال غیرمالی (تاریخچه، تعریف، توضیح، ...)
            'simple_sum': جمع ساده با فیلتر (سوالات فعلی)
            'top_n': بیشترین/کمترین (نیاز به ORDER + LIMIT)
            'breakdown': تفکیک چند بعدی
            'cross_table': محاسبات بین جداولی
            'comparison': مقایسه چند سال یا چند entity (جدید!)
        """
        # ⭐ تشخیص سوالات غیرمالی (جدید!)
        # این سوالات نباید به database بروند
        non_financial_keywords = [
            r'\bتاریخچه\b',           # تاریخچه وزارت نفت
            r'\bتاریخ\b.*\b(تشکیل|تأسیس|ایجاد)\b',  # تاریخ تشکیل
            r'\b(تشکیل|تأسیس|ایجاد)\b.*\bشد',     # چه زمانی تشکیل شد
            r'\bمعرفی\b',              # معرفی سازمان
            r'\bچیست\b',               # وزارت نفت چیست
            r'\bچی\s+است\b',           # چی است
            r'\bکیست\b',               # وزیر نفت کیست - ✅ اضافه شد
            r'\bکی\s+است\b',           # وزیر کی است - ✅ اضافه شد
            r'\bچه\s+کسی\b',           # چه کسی
            r'\bچگونه\b.*\b(کار|عمل|می\s*توان|تماس)\b',  # چگونه کار می‌کند / تماس - ✅ بهبود یافت
            r'\bچرا\b',                 # چرا ایجاد شد
            r'\bکجا\b',                 # کجا قرار دارد
            r'\bکی\b',                  # کی تشکیل شد
            r'\bتعریف\b',               # تعریف وزارت
            r'\bتوضیح\b.*\b(بده|دهید)\b',  # توضیح بده
            r'\bوظایف\b',               # وظایف وزارت
            r'\bوظیفه\b',               # وظیفه اصلی
            r'\bاهداف\b',               # اهداف سازمان
            r'\bساختار\b.*\b(سازمانی|تشکیلاتی)\b',  # ساختار سازمانی
            r'\bنمودار\b.*\b(سازمانی|تشکیلاتی)\b',  # نمودار سازمانی
            r'\bمسئول\b',               # مسئول چه کسی است
            r'\bمسئولیت\b',             # مسئولیت‌های
            r'\bآدرس\b',                # آدرس وزارت
            r'\bمکان\b',                # مکان سازمان
            r'\bتلفن\b',                # شماره تلفن
            r'\bتماس\b.*\b(بگیر|گرفت)\b',  # تماس بگیرم - ✅ بهبود یافت
            r'\bوب\s*سایت\b',          # وب سایت
            r'\bسایت\b',                # سایت
            r'\bمعاون\b.*\bکیست\b',    # معاون کیست
            r'\b(وزیر|رئیس|مدیر)\b.*\bکیست\b',  # وزیر/رئیس/مدیر کیست - ✅ بهبود یافت
            r'\bرئیس\b.*\bکیست\b',     # رئیس کیست
        ]
        
        # 🔧 CRITICAL FIX: اگر query شامل کلمات غیرمالی باشد، ولی فقط اگر financial keywords نداشته باشد
        # مثال: "درامد بانک ملی چیست؟" باید financial باشه چون "درامد" داره
        if any(re.search(pattern, query_lower) for pattern in non_financial_keywords):
            # چک کنیم آیا financial keywords داره یا نه
            financial_keywords_check = [
                'درآمد', 'درامد', 'هزینه', 'هزينه', 'بودجه', 'اعتبار', 'اعتبارات',
                'مصارف', 'منابع', 'تملک', 'تملك', 'دارایی', 'دارايي', 'سرمایه'
            ]
            has_financial = any(kw in query_lower for kw in financial_keywords_check)
            if not has_financial:
                # فقط اگر واقعاً financial keywords نداره، non_financial برگردون
                return 'non_financial'
            # در غیر این صورت، ادامه بده و category دیگری رو پیدا کن
        
        # تشخیص comparison (مقایسه چند سال یا entity)
        # الگوهای comparison:
        comparison_patterns = [
            r'\bمقایسه\b',                         # مقایسه درآمد
            r'افزایش|کاهش|رشد',                    # افزایش/کاهش داشته
            r'نسبت\s+به',                          # نسبت به سال قبل
            r'در\s+مقایسه\s+با',                   # در مقایسه با
            r'بیشتر.*یا.*کمتر',                    # بیشتر یا کمتر
            r'چقدر\s+بیشتر|چقدر\s+کمتر',          # چقدر بیشتر/کمتر
            r'تفاوت',                              # تفاوت
            r'تغییر',                              # تغییر کرده
            r'قبلی|قبل',                           # سال قبلی
            r'بعدی|بعد',                           # سال بعدی
            r'بیشتری\s+داشته\s+یا',               # مصارف بیشتری داشته یا
            r'بیشتر\s+بوده\s+یا',                  # بیشتر بوده یا
            r'بیشتر\s+است\s+یا',                   # بیشتر است یا
            r'کمتر\s+بوده\s+یا',                   # کمتر بوده یا
            r'کمتر\s+است\s+یا',                    # کمتر است یا
            r'کدام.*بیشتر',                        # کدام یک بیشتر است
            r'کدام.*کمتر',                         # کدام یک کمتر است
            r'بقیه\s+بیشتر',                       # از بقیه بیشتر است
            r'\bتراز\b',                           # تراز مالی (balance)
            r'سود\s+و\s+زیان',                     # سود و زیان
        ]
        
        if any(re.search(pattern, query_lower) for pattern in comparison_patterns):
            return 'comparison'
        
        # تشخیص cross-table (زیان، سود، مقایسه درآمد و هزینه)
        if re.search(r'زیان|سود|مقایسه\s+درآمد\s+و\s+هزینه|درآمد\s+و\s+هزینه', query_lower):
            return 'cross_table'
        
        # تشخیص breakdown - سوالات تفکیک/جزئیات
        # الگوهای breakdown:
        breakdown_patterns = [
            r'از\s+چه\s+جز\s*ه?ا?ی?',  # از چه جزهایی، از چه جز هایی
            r'از\s+چه\s+راه',           # از چه راه
            r'چه\s+مواردی',              # چه مواردی
            r'کدام\s+بند',               # کدام بند
            r'چه\s+بند',                 # چه بند
            r'کدام\s+جز',                # کدام جزء
            r'چه\s+جز\s*ه?ا?ی?',        # چه جزهایی
            r'چه\s+بخشی',                # چه بخشی
            r'چه\s+قسمتی',               # چه قسمتی
            r'منابع\s+درآمد',           # منابع درآمد
            r'راه\s*های?\s+درآمد',      # راههای درآمد
        ]
        
        if any(re.search(pattern, query_lower) for pattern in breakdown_patterns):
            return 'breakdown'
        
        # تشخیص breakdown (چند سوال در یک query)
        # مثال: "چقدر درآمد؟ چه بخشی ملی؟ از چه راه‌ها؟"
        question_count = len(re.findall(r'\?', query_lower))
        if question_count >= 2:
            return 'breakdown'
        
        # یا اگر سوال طولانی باشد و چند بعد می‌خواهد
        asks_multiple = (
            ('چه بخش' in query_lower or 'چه قسمت' in query_lower) and
            ('از چه راه' in query_lower or 'منابع' in query_lower)
        )
        if asks_multiple:
            return 'breakdown'
        
        # تشخیص top_n (بیشترین، کمترین، برترین)
        if re.search(r'بیشترین|کمترین|برترین|بالاترین|پایین\s*ترین|کدام\s+سازمان|کدام\s+دستگاه|پر\s*هزینه|پر\s*درآمد|پرهزینه|پردرآمد|زیان\s*ده|زیانده|ارزان\s*ترین|گران\s*ترین', query_lower):
            return 'top_n'
        
        return 'simple_sum'
    
    def _detect_aggregation_type(
        self,
        query_lower: str,
        entity_names: List[str],
        income_component: Optional[str]
    ) -> Dict[str, Any]:
        """
        تشخیص نوع aggregation و نیاز به مرتب‌سازی/گروه‌بندی
        """
        needs_groupby = False
        group_fields: List[str] = []
        needs_sort = False
        sort_direction: Optional[str] = None
        limit: Optional[int] = None

        top_n_pattern = (
            r'بیشترین|کمترین|برترین|بالاترین|پایین\s*ترین|کدام\s+سازمان|کدام\s+دستگاه|'
            r'پر\s*هزینه|پر\s*درآمد|پرهزینه|پردرآمد|پرخرج|پر\s*خرج|زیان\s*ده|زیانده|'
            r'ارزان\s*ترین|گران\s*ترین'
        )

        if re.search(top_n_pattern, query_lower):
            needs_groupby = True
            group_fields = ['عنوان_دستگاه_اجرایی', 'عنوان_دستگاه_اصلی']
            needs_sort = True
            desc_markers = (
                'بیشترین', 'برترین', 'بالاترین', 'پر هزینه', 'پرهزینه', 'پرخرج', 'پر خرج',
                'پر درآمد', 'پردرآمد', 'بیشترین هزینه', 'بیشترین درآمد', 'گرانترین', 'گران ترین',
                'سودآورترین', 'سود آورترین'
            )
            asc_markers = (
                'کمترین', 'کم هزینه', 'کم‌هزینه', 'کم خرج', 'کم‌خرج', 'پایین ترین', 'پایین‌ترین',
                'ارزانترین', 'ارزان ترین', 'زیان ده', 'زیانده', 'زیان‌ده‌ترین'
            )
            if any(marker in query_lower for marker in desc_markers):
                sort_direction = 'DESC'
            elif any(marker in query_lower for marker in asc_markers):
                sort_direction = 'ASC'
            else:
                sort_direction = 'DESC'
            # استخراج عدد از query (مثلاً "5 دستگاه", "10 سازمان")
            number_pattern = r'(\d+)\s*(?:دستگاه|سازمان|مورد|رتبه|تا)'
            number_match = re.search(number_pattern, query_lower)
            if number_match:
                limit = int(number_match.group(1))
                # حداکثر 100 تا
                limit = min(limit, 100)
            else:
                plural_pattern = r'(?:دستگاه|سازمان)(?:\s|‌)*(?:ها|های)'
                singular_question_pattern = r'کدام\s+(?:سازمان|دستگاه)'
                if re.search(plural_pattern, query_lower):
                    limit = 5
                elif re.search(singular_question_pattern, query_lower):
                    limit = 1
                else:
                    limit = 10

        # الگوهای breakdown که نیاز به GROUP BY دارند
        breakdown_patterns = [
            r'از\s+چه\s+جز\s*ه?ا?ی?',      # از چه جزهایی، از چه جز هایی
            r'از\s+چه\s+راه',               # از چه راه
            r'چه\s+مواردی',                 # چه مواردی
            r'کدام\s+بند',                  # کدام بند
            r'چه\s+بند',                    # چه بند
            r'کدام\s+جز',                   # کدام جزء
            r'چه\s+جز\s*ه?ا?ی?',          # چه جزهایی
            r'چه\s+بخشی',                   # چه بخشی
            r'چه\s+قسمتی',                  # چه قسمتی
            r'منابع\s+درآمد',              # منابع درآمد
            r'راه\s*های?\s+درآمد',         # راههای درآمد
            r'منابع',                       # منابع
            r'breakdown',                   # breakdown
            r'تفکیک',                       # تفکیک
        ]
        
        is_breakdown_query = any(re.search(pattern, query_lower) for pattern in breakdown_patterns)
        
        if is_breakdown_query:
            needs_groupby = True
            # تشخیص اینکه چه فیلدهایی باید group شوند
            if any(re.search(pattern, query_lower) for pattern in [
                r'از\s+چه\s+جز', r'چه\s+جز', r'کدام\s+جز', r'جز\s*ها'
            ]):
                # سوال درباره جزء درآمد
                group_fields = ['عنوان_جزء']
            elif any(re.search(pattern, query_lower) for pattern in [
                r'کدام\s+بند', r'چه\s+بند', r'بند'
            ]):
                # سوال درباره بند
                group_fields = ['عنوان_بند']
            elif 'منابع' in query_lower or 'از چه راه' in query_lower or 'چه بخش' in query_lower or 'چه مواردی' in query_lower:
                # سوال عمومی درباره منابع/راه‌ها - هر دو جزء و بند
                group_fields = ['عنوان_جزء', 'عنوان_بند']
            else:
                group_fields = ['عنوان_دستگاه_اجرایی']
            needs_sort = True
            sort_direction = 'DESC'

        if income_component and re.search(r'توسط\s+چه|چه\s+دستگاه|وصول', query_lower):
            needs_groupby = True
            group_fields = ['عنوان_دستگاه_اجرایی', 'عنوان_دستگاه_اصلی']
            needs_sort = True
            sort_direction = 'DESC'

        return {
            'needs_groupby': needs_groupby,
            'group_fields': group_fields,
            'needs_sort': needs_sort,
            'sort_direction': sort_direction,
            'limit': limit
        }

    def _detect_multi_dimension(self, query_lower: str) -> Dict[str, bool]:
        """
        تشخیص ابعاد مختلف در سوال
        
        Returns:
            {
                'asks_total': bool,
                'asks_national_provincial': bool,
                'asks_sources': bool,
                'asks_share': bool
            }
        """
        return {
            'asks_total': bool(re.search(r'مجموع|کل|چقدر|میزان', query_lower)),
            'asks_national_provincial': bool(re.search(r'ملی|استانی|چه\s+بخش', query_lower)),
            'asks_sources': bool(re.search(r'از\s+چه\s+راه|منابع|چگونه|چه\s+روش', query_lower)),
            'asks_share': bool(re.search(r'سهم|درصد|چند\s+درصد', query_lower))
        }
    
    def _calculate_confidence_score(
        self,
        entity_names: List[str],
        years: List[str],
        income_component: Optional[str],
        query: str,
        query_category: str
    ) -> float:
        """
        محاسبه Confidence Score برای نتایج استاتیک
        
        Returns:
            float بین 0.0 تا 1.0
        """
        score = 1.0
        
        # Factor 1: Entity extraction (40% weight)
        if not entity_names:
            #  *= 0.2  # اگر entity پیدا نشد، confidence خیلی پایین است
            logger.debug("   ⚠️  No entities found - confidence penalty")
        elif len(entity_names) > 3:
            score *= 0.7  # چند entity ممکن است مشکل باشد
            logger.debug(f"   ⚠️  Multiple entities ({len(entity_names)}) - confidence penalty")
        elif any(' ' in name for name in entity_names):
            # موجودیت‌های چندکلمه‌ای معمولاً خوب استخراج می‌شوند
            score *= 1.0
            logger.debug("   ✅ Multi-word entities detected - good confidence")
        else:
            score *= 0.9
            logger.debug("   ✅ Single-word entities - good confidence")
        
        # Factor 2: Year extraction (20% weight)
        has_year_in_query = bool(re.search(r'\d{2,4}', query))
        if has_year_in_query and not years:
            score *= 0.3  # سال در query هست ولی پیدا نشد
            logger.debug("   ⚠️  Year in query but not extracted - confidence penalty")
        elif not has_year_in_query and years:
            score *= 0.8  # سال پیدا شد ولی در query نبود (ممکن است اشتباه باشد)
            logger.debug("   ⚠️  Year extracted but not in query - minor penalty")
        elif years:
            score *= 1.0  # سال‌ها درست استخراج شدند
            logger.debug(f"   ✅ Years correctly extracted: {years}")
        
        # Factor 3: Query complexity (20% weight)
        word_count = len(query.split())
        if word_count > 25:
            score *= 0.6  # سوالات خیلی طولانی ممکن است پیچیده باشند
            logger.debug(f"   ⚠️  Very long query ({word_count} words) - complexity penalty")
        elif word_count > 15:
            score *= 0.8
            logger.debug(f"   ⚠️  Long query ({word_count} words) - minor penalty")
        elif word_count < 5:
            score *= 0.7  # سوالات خیلی کوتاه ممکن است مبهم باشند
            logger.debug(f"   ⚠️  Very short query ({word_count} words) - ambiguity penalty")
        else:
            logger.debug(f"   ✅ Query length OK ({word_count} words)")
        
        # Factor 4: Component extraction (10% weight)
        if 'حاصل از' in query.lower() or any(kw in query.lower() for kw in ['خدمات', 'فروش', 'عوارض']):
            if not income_component:
                score *= 0.5  # component در query هست ولی پیدا نشد
                logger.debug("   ⚠️  Component keywords in query but not extracted - penalty")
            else:
                logger.debug(f"   ✅ Component correctly extracted: {income_component}")
        
        # Factor 5: Query category detection (10% weight)
        if query_category == 'breakdown' and word_count < 10:
            score *= 0.7  # breakdown queries معمولاً طولانی‌تر هستند
            logger.debug("   ⚠️  Breakdown query but too short - inconsistency penalty")
        elif query_category == 'top_n' and not entity_names:
            # top_n queries ممکن است entity نداشته باشند (OK)
            score *= 1.0
            logger.debug("   ✅ Top-N query without entity - acceptable")
        
        final_score = min(max(score, 0.0), 1.0)
        logger.info(f"   📊 Final Confidence Score: {final_score:.2f}")
        return final_score
    
    def _detect_cross_table_need(self, query_lower: str) -> Dict[str, Any]:
        """
        تشخیص نیاز به JOIN بین جداول
        
        Returns:
            {
                'needs_income': bool,
                'needs_cost': bool,
                'calculation_type': 'balance' | 'ratio' | None
            }
        """
        # تشخیص صریح زیان/سود
        has_loss_profit = bool(re.search(r'زیان|زیانده|ضرر|سود|سودآور|تراز', query_lower))
        
        # اگر زیان/سود داریم، حتماً نیاز به income و cost داریم
        if has_loss_profit:
            return {
                'needs_income': True,
                'needs_cost': True,
                'calculation_type': 'balance'
            }
        
        # تشخیص معمولی
        needs_income = 'درآمد' in query_lower or 'درامد' in query_lower
        needs_cost = 'هزینه' in query_lower or 'هزينه' in query_lower or 'اعتبار' in query_lower
        
        calculation_type = None
        if needs_income and needs_cost:
            if 'زیان' in query_lower or 'سود' in query_lower or 'تراز' in query_lower:
                calculation_type = 'balance'
            elif 'نسبت' in query_lower or 'رابطه' in query_lower:
                calculation_type = 'ratio'
        
        return {
            'needs_income': needs_income,
            'needs_cost': needs_cost,
            'calculation_type': calculation_type
        }
    
    def _detect_comparison_info(
        self,
        query_lower: str,
        years: List[str],
        entity_names: List[str]
    ) -> Dict[str, Any]:
        """
        تشخیص جزئیات سوال مقایسه‌ای
        
        Args:
            query_lower: query نرمال شده
            years: سال‌های استخراج شده
            entity_names: entity های استخراج شده
        
        Returns:
            {
                'comparison_type': 'year_over_year' | 'entity_vs_entity' | 'trend',
                'base_year': str,           # سال پایه
                'compare_years': List[str], # سال‌های مقایسه
                'base_entity': str,         # entity پایه
                'compare_entity': str,      # entity مقایسه
                'metric': 'change' | 'percentage' | 'difference',
                'direction': 'increase' | 'decrease' | 'both'
            }
        """
        result = {
            'comparison_type': None,
            'base_year': None,
            'compare_years': [],
            'base_entity': None,
            'compare_entity': None,
            'comparison_entities': [],       # لیست کامل entity های مقایسه (2 یا بیشتر)
            'comparison_column': None,       # ستون سلسله‌مراتبی برای مقایسه
            'comparison_hierarchy_level': None,  # سطح سلسله‌مراتب (بخش/قسمت/بند/جزء/دستگاه)
            'metric': 'change',
            'direction': 'both'
        }
        
        # ========== 0. تشخیص تراز (balance) ==========
        # تراز = درآمد - مصارف برای یک entity
        balance_patterns = [
            r'\bتراز\b',
            r'درآمد.*(?:منهای|منهاي|کم).*مصارف',
            r'مصارف.*(?:منهای|منهاي|کم).*درآمد',
            r'سود\s+و\s+زیان',
        ]
        if any(re.search(p, query_lower) for p in balance_patterns):
            result['comparison_type'] = 'balance'
            if entity_names:
                result['base_entity'] = entity_names[0]
                result['comparison_entities'] = entity_names[:1]
            if years:
                result['base_year'] = years[0]
                result['compare_years'] = years[1:]
            logger.info(f"📊 Balance (تراز) comparison detected: entity={result['base_entity']}")
            return result
        
        # ========== تابع کمکی: تشخیص ستون سلسله‌مراتبی از متن entity ==========
        def _detect_hierarchy_column(entities_text: str) -> tuple:
            """تشخیص ستون و سطح سلسله‌مراتب از متن entity"""
            text_lower = entities_text.lower()
            if 'قسمت' in text_lower:
                return '"عنوان_قسمت"', 'قسمت'
            elif 'بخش' in text_lower:
                return '"عنوان_بخش"', 'بخش'
            elif 'بند' in text_lower:
                return '"عنوان_بند"', 'بند'
            elif 'جزء' in text_lower or 'جز' in text_lower:
                return '"عنوان_جزء"', 'جزء'
            else:
                return None, 'دستگاه'
        
        # ========== 1. مقایسه مستقیم X با Y ==========
        # الگوهای "مقایسه X با Y"، "X را با Y مقایسه کن"
        direct_compare_patterns = [
            r'مقایسه\s+(?:درآمد\s+|مصارف\s+|هزینه\s+)?(.+?)\s+با\s+(.+?)(?:\s+در\s+سال|\s+در\s+|\s*$|\s*؟|\s*\?)',
            r'(.+?)\s+(?:رو|را)\s+با\s+(.+?)\s+(?:رو\s+)?مقایسه',
            r'(?:درآمد|مصارف|هزینه)\s+(.+?)\s+با\s+(.+?)(?:\s+در|\s+سال|\s*$|\s*؟|\s*\?)',
        ]
        
        for pattern in direct_compare_patterns:
            match = re.search(pattern, query_lower)
            if match:
                raw_entity1 = match.group(1).strip()
                raw_entity2 = match.group(2).strip()
                # پاک کردن کلمات اضافی از entity names
                clean_words = ['درآمد', 'مصارف', 'هزینه', 'اعتبار', 'بودجه', 'کل', 'جمع']
                for w in clean_words:
                    raw_entity1 = raw_entity1.replace(w, '').strip()
                    raw_entity2 = raw_entity2.replace(w, '').strip()
                raw_entity2 = re.sub(r'\s*(در|سال|چقدر|است|هست|بوده|می‌?باشد)\s*$', '', raw_entity2).strip()
                
                # حذف سال از entity names
                raw_entity1 = re.sub(r'\s*در\s+سال\s+\d{4}\s*', '', raw_entity1).strip()
                raw_entity2 = re.sub(r'\s*در\s+سال\s+\d{4}\s*', '', raw_entity2).strip()
                raw_entity1 = re.sub(r'\s*\b1[34]\d{2}\b\s*', '', raw_entity1).strip()
                raw_entity2 = re.sub(r'\s*\b1[34]\d{2}\b\s*', '', raw_entity2).strip()
                # حذف "رو" از انتهای entity names
                raw_entity1 = re.sub(r'\s+(?:رو|را)\s*$', '', raw_entity1).strip()
                raw_entity2 = re.sub(r'\s+(?:رو|را)\s*$', '', raw_entity2).strip()
                
                if raw_entity1 and raw_entity2 and len(raw_entity1) > 1 and len(raw_entity2) > 1:
                    result['comparison_type'] = 'entity_comparison'
                    result['base_entity'] = raw_entity1
                    result['compare_entity'] = raw_entity2
                    result['comparison_entities'] = [raw_entity1, raw_entity2]
                    
                    # تشخیص ستون سلسله‌مراتبی
                    combined = f"{raw_entity1} {raw_entity2}"
                    col, level = _detect_hierarchy_column(combined)
                    result['comparison_column'] = col
                    result['comparison_hierarchy_level'] = level
                    logger.info(f"📊 Direct comparison: '{raw_entity1}' vs '{raw_entity2}', level={level}, col={col}")
                    break
        
        # ========== 2. مقایسه entity ها با "بیشتر...یا" ==========
        entity_comparison_patterns = [
            r'بیشتر.*یا',
            r'کمتر.*یا',
            r'بیشتری\s+داشته\s+یا',
            r'کمتری\s+داشته\s+یا',
        ]
        
        if not result['comparison_type'] and any(re.search(p, query_lower) for p in entity_comparison_patterns):
            result['comparison_type'] = 'entity_vs_entity'
            if len(entity_names) >= 2:
                result['base_entity'] = entity_names[0]
                result['compare_entity'] = entity_names[1]
                result['comparison_entities'] = entity_names[:2]
                col, level = _detect_hierarchy_column(' '.join(entity_names[:2]))
                result['comparison_column'] = col
                result['comparison_hierarchy_level'] = level
            elif len(entity_names) == 1:
                result['base_entity'] = entity_names[0]
                second_entity_patterns = [
                    rf'بیشتر\s+(?:بوده|است|هست)\s+یا\s+(.+?)(?:\s*$|\s+در|\s+سال|\s*؟|\s*\?)',
                    rf'کمتر\s+(?:بوده|است|هست)\s+یا\s+(.+?)(?:\s*$|\s+در|\s+سال|\s*؟|\s*\?)',
                    rf'یا\s+(.+?)(?:\s+بیشتر|\s+کمتر|\s*$|\s*؟|\s*\?)',
                ]
                for pat in second_entity_patterns:
                    m = re.search(pat, query_lower, re.IGNORECASE)
                    if m:
                        second_entity = m.group(1).strip()
                        second_entity = re.sub(r'\s*(در|سال|چقدر|است|هست|بوده|می‌?باشد)\s*', '', second_entity).strip()
                        if second_entity and len(second_entity) > 2:
                            result['compare_entity'] = second_entity
                            result['comparison_entities'] = [entity_names[0], second_entity]
                            col, level = _detect_hierarchy_column(f"{entity_names[0]} {second_entity}")
                            result['comparison_column'] = col
                            result['comparison_hierarchy_level'] = level
                            break
        
        # ========== 3. مقایسه سال به سال ==========
        year_comparison_patterns = [
            r'نسبت\s+به\s+(?:سال\s+)?(?:قبل|گذشته|پیش)',
            r'نسبت\s+به\s+(\d+)\s*سال\s+قبل',
            r'در\s+مقایسه\s+با\s+سال',
            r'افزایش|کاهش|رشد|تغییر',
            r'قبلی|قبل',
        ]
        
        if not result['comparison_type'] and any(re.search(p, query_lower) for p in year_comparison_patterns):
            result['comparison_type'] = 'year_over_year'
            if years:
                prev_years_match = re.search(r'نسبت\s+به\s+(\d+)\s*سال\s+قبل', query_lower)
                if prev_years_match:
                    num_prev_years = int(prev_years_match.group(1))
                    result['base_year'] = years[0]
                    base_year_int = int(years[0])
                    result['compare_years'] = [str(base_year_int - i) for i in range(1, num_prev_years + 1)]
                elif len(years) >= 2:
                    sorted_years = sorted(years, key=int, reverse=True)
                    result['base_year'] = sorted_years[0]
                    result['compare_years'] = sorted_years[1:]
                elif len(years) == 1:
                    result['base_year'] = years[0]
                    base_year_int = int(years[0])
                    if 'قبل' in query_lower or 'قبلی' in query_lower:
                        result['compare_years'] = [str(base_year_int - 1)]
        
        # اگر هیچکدام نبود، trend در نظر بگیر
        if not result['comparison_type'] and len(years) > 1:
            result['comparison_type'] = 'trend'
            sorted_years = sorted(years, key=int)
            result['compare_years'] = sorted_years
        
        # تشخیص metric و direction
        if 'افزایش' in query_lower or 'رشد' in query_lower:
            result['direction'] = 'increase'
        elif 'کاهش' in query_lower:
            result['direction'] = 'decrease'
        
        if 'درصد' in query_lower or '%' in query_lower:
            result['metric'] = 'percentage'
        elif 'تفاوت' in query_lower or 'فرق' in query_lower:
            result['metric'] = 'difference'
        
        logger.info(f"📊 Comparison Info: {result}")
        return result
    
    # ================== Budget Financial Methods ==================
    
    def detect_budget_table_type(self, query: str) -> Dict[str, Any]:
        """
        تشخیص نوع جدول بودجه (MANABE یا MASAREF)
        
        Args:
            query: سوال کاربر
            
        Returns:
            {
                'table_type': 'manabe' | 'masaref' | 'both' | 'unknown',
                'confidence': float,
                'matched_keywords': List[str],
                'reason': str
            }
        """
        query_lower = self.normalize_text(query).lower()
        
        # کلمات کلیدی MANABE (منابع/درآمد)
        manabe_keywords = {
            'primary': ['واگذاری', 'درآمد', 'درامد', 'منابع', 'وصول', 'حاصل از'],
            'secondary': ['ملی', 'استانی', 'عمومی', 'اختصاصی'],
            'compound': {
                'درآمد عمرانی': 'واگذاری دارایی‌های سرمایه‌ای',
                'درآمد عمومی': 'درآمد عمومی',
                'درآمد اختصاصی': 'درآمد اختصاصی'
            }
        }
        
        # کلمات کلیدی MASAREF (مصارف/هزینه)
        masaref_keywords = {
            'primary': ['برآورد', 'براورد', 'هزینه', 'هزينه', 'مخارج', 'مصارف', 'تملک', 'تملك', 'اعتبار', 'بودجه'],
            'secondary': ['عمومی', 'متفرقه', 'اختصاصی', 'یارانه'],
            'compound': {
                'هزینه جاری': 'اعتبارات هزینه‌ای',
                'اعتبارات جاری': 'اعتبارات هزینه‌ای',
                'هزینه عمرانی': 'تملک دارایی‌های سرمایه‌ای',
                'اعتبارات عمرانی': 'تملک دارایی‌های سرمایه‌ای'
            }
        }
        
        manabe_score = 0
        masaref_score = 0
        matched = {'manabe': [], 'masaref': []}
        
        # بررسی کلمات کلیدی اصلی
        for kw in manabe_keywords['primary']:
            if kw in query_lower:
                manabe_score += 2
                matched['manabe'].append(kw)
        
        for kw in masaref_keywords['primary']:
            if kw in query_lower:
                masaref_score += 2
                matched['masaref'].append(kw)
        
        # بررسی عبارات ترکیبی
        for compound in manabe_keywords['compound']:
            if compound in query_lower:
                manabe_score += 3
                matched['manabe'].append(compound)
        
        for compound in masaref_keywords['compound']:
            if compound in query_lower:
                masaref_score += 3
                matched['masaref'].append(compound)
        
        # تعیین نوع جدول
        if manabe_score > 0 and masaref_score > 0:
            if manabe_score > masaref_score:
                table_type = 'manabe'
                confidence = min(0.9, manabe_score / (manabe_score + masaref_score))
            elif masaref_score > manabe_score:
                table_type = 'masaref'
                confidence = min(0.9, masaref_score / (manabe_score + masaref_score))
            else:
                table_type = 'both'
                confidence = 0.5
        elif manabe_score > 0:
            table_type = 'manabe'
            confidence = min(0.95, 0.6 + manabe_score * 0.1)
        elif masaref_score > 0:
            table_type = 'masaref'
            confidence = min(0.95, 0.6 + masaref_score * 0.1)
        else:
            # پیش‌فرض: MASAREF
            table_type = 'masaref'
            confidence = 0.4
        
        reason = f"MANABE: {matched['manabe']}, MASAREF: {matched['masaref']}"
        
        logger.info(f"📊 [BUDGET_TABLE] {table_type} (confidence: {confidence:.2f})")
        
        return {
            'table_type': table_type,
            'confidence': confidence,
            'matched_keywords': matched,
            'reason': reason
        }
    
    def detect_hierarchy_level(self, query: str) -> Dict[str, Any]:
        """
        تشخیص سطح سلسله‌مراتبی از سوال
        
        سطوح MASAREF (از بالا به پایین):
        1. قسمت (بالاترین)
        2. بخش
        3. بند
        4. دستگاه اصلی
        5. دستگاه اجرایی
        6. جزء (پایین‌ترین)
        
        Returns:
            {
                'level': str or None,
                'level_priority': int (1-6),
                'column_name': str,
                'matched_keyword': str
            }
        """
        query_lower = self.normalize_text(query).lower()
        
        # ترتیب اولویت سطوح (از بالا به پایین)
        hierarchy_levels = [
            {'level': 'قسمت', 'priority': 1, 'column': 'عنوان_قسمت', 'keywords': ['قسمت']},
            {'level': 'بخش', 'priority': 2, 'column': 'عنوان_بخش', 'keywords': ['بخش']},
            {'level': 'بند', 'priority': 3, 'column': 'عنوان_بند', 'keywords': ['بند']},
            {'level': 'دستگاه اصلی', 'priority': 4, 'column': 'عنوان_دستگاه_اصلی', 'keywords': ['دستگاه اصلی', 'دستگاه اصلي']},
            {'level': 'دستگاه اجرایی', 'priority': 5, 'column': 'عنوان_دستگاه_اجرایی', 'keywords': ['دستگاه اجرایی', 'دستگاه اجرايي', 'دستگاه']},
            {'level': 'جزء', 'priority': 6, 'column': 'عنوان_جزء', 'keywords': ['جزء', 'جزو']},
        ]
        
        for level_info in hierarchy_levels:
            for keyword in level_info['keywords']:
                # جستجوی دقیق با word boundary
                pattern = rf'\b{re.escape(keyword)}\b'
                if re.search(pattern, query_lower):
                    logger.info(f"📊 [HIERARCHY] Detected: {level_info['level']} (priority: {level_info['priority']})")
                    return {
                        'level': level_info['level'],
                        'level_priority': level_info['priority'],
                        'column_name': level_info['column'],
                        'matched_keyword': keyword
                    }
        
        # پیش‌فرض: دستگاه اجرایی
        return {
            'level': None,
            'level_priority': 5,
            'column_name': 'عنوان_دستگاه_اجرایی',
            'matched_keyword': None
        }
    
    def detect_cost_type(self, query: str) -> Dict[str, Any]:
        """
        تشخیص نوع هزینه (جاری/سرمایه‌ای/کل)
        
        Returns:
            {
                'cost_type': 'هزینه‌ای' | 'سرمایه‌ای' | 'کل',
                'columns': List[str],
                'matched_keywords': List[str]
            }
        """
        query_lower = self.normalize_text(query).lower()
        
        cost_patterns = {
            'هزینه‌ای': {
                'keywords': ['جاری', 'هزینه ای', 'هزینه‌ای', 'اعتبارات هزینه'],
                'columns': ['براورد_اعتبارات_هزینه_ای_عمومی', 'براورد_اعتبارات_هزینه_ای_متفرقه', 
                           'براورد_اعتبارات_هزینه_ای_اختصاصی', 'جمع_براورد_اعتبارات_هزینه_ای']
            },
            'سرمایه‌ای': {
                'keywords': ['عمرانی', 'سرمایه ای', 'سرمایه‌ای', 'تملک', 'تملك', 'دارایی'],
                'columns': ['براورد_تملك_دارايي_هاي_سرمايه_اي_عمومي', 'براورد_تملك_دارايي_هاي_سرمايه_اي_متفرقه',
                           'براورد_تملك_دارايي_هاي_سرمايه_اي_اختصاصي', 'جمع_براورد_تملك_دارايي_هاي_سرمايه_اي']
            }
        }
        
        matched = []
        
        for cost_type, info in cost_patterns.items():
            for kw in info['keywords']:
                if kw in query_lower:
                    matched.append(kw)
                    logger.info(f"📊 [COST_TYPE] Detected: {cost_type}")
                    return {
                        'cost_type': cost_type,
                        'columns': info['columns'],
                        'matched_keywords': [kw]
                    }
        
        # پیش‌فرض: کل
        return {
            'cost_type': 'کل',
            'columns': ['جمع_کل'],
            'matched_keywords': []
        }
    
    def detect_subsidy_rule(self, years: List[str]) -> Dict[str, Any]:
        """
        تشخیص قانون یارانه بر اساس سال
        
        قوانین:
        - 1401: یارانه‌ها در جمع کل محاسبه می‌شوند
        - 1399, 1400: یارانه‌ها جدا نمایش داده می‌شوند
        - سایر سال‌ها: قانون خاصی ندارند
        
        Returns:
            {
                'rule': 'include' | 'separate' | 'none',
                'description': str,
                'affected_years': List[str]
            }
        """
        subsidy_rules = {
            '1399': 'separate',
            '1400': 'separate',
            '1401': 'include'
        }
        
        affected = []
        rules_found = set()
        
        for year in years:
            if year in subsidy_rules:
                rules_found.add(subsidy_rules[year])
                affected.append(year)
        
        if 'include' in rules_found:
            return {
                'rule': 'include',
                'description': 'یارانه‌ها در جمع کل محاسبه می‌شوند (سال 1401)',
                'affected_years': affected
            }
        elif 'separate' in rules_found:
            return {
                'rule': 'separate',
                'description': 'یارانه‌ها جدا نمایش داده می‌شوند (سال‌های 1399-1400)',
                'affected_years': affected
            }
        
        return {
            'rule': 'none',
            'description': 'قانون خاصی برای یارانه وجود ندارد',
            'affected_years': []
        }
    
    def analyze_budget_query(self, query: str) -> Dict[str, Any]:
        """
        تحلیل کامل سوال بودجه‌ای
        
        این متد همه تحلیل‌های مربوط به budget_financial را یکجا انجام می‌دهد.
        
        Returns:
            {
                'table_detection': {...},
                'hierarchy': {...},
                'cost_type': {...},
                'subsidy_rule': {...},
                'years': List[str],
                'entity_names': List[str],
                'income_type': str,
                'filters': {...},
                'is_budget_query': bool
            }
        """
        # تحلیل پایه
        base_analysis = self.analyze_query(query)
        
        # تشخیص نوع جدول
        table_detection = self.detect_budget_table_type(query)
        
        # تشخیص سطح سلسله‌مراتبی
        hierarchy = self.detect_hierarchy_level(query)
        
        # تشخیص نوع هزینه
        cost_type = self.detect_cost_type(query)
        
        # تشخیص قانون یارانه
        years = base_analysis.get('years', [])
        if not years:
            years = ['1403']  # سال پیش‌فرض
        subsidy_rule = self.detect_subsidy_rule(years)
        
        return {
            'table_detection': table_detection,
            'hierarchy': hierarchy,
            'cost_type': cost_type,
            'subsidy_rule': subsidy_rule,
            'years': years,
            'entity_names': base_analysis.get('entity_names', []),
            'income_type': base_analysis.get('income_type', 'کل'),
            'filters': base_analysis.get('filters', {}),
            'aggregation': base_analysis.get('aggregation', {}),
            'dimensions': base_analysis.get('dimensions', {}),
            'is_budget_query': True,
            'confidence': min(
                table_detection.get('confidence', 0.5),
                base_analysis.get('confidence', 0.5)
            ),
            'original_analysis': base_analysis
        }

