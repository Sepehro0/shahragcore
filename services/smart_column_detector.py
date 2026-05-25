# -*- coding: utf-8 -*-
"""
Smart Column Detector - تشخیص هوشمند و داینامیک ستون‌ها

این ماژول مسئول تشخیص هوشمند این است که:
1. کاربر از کدام سطح سلسله مراتب صحبت می‌کند (قسمت/بخش/بند/جزء)
2. کدام ستون‌ها باید برای جستجو استفاده شوند
3. کدام ستون‌ها باید برای aggregation استفاده شوند
4. چگونه entity ها را در ستون‌های مختلف پیدا کنیم

ویژگی‌های کلیدی:
- کاملاً داینامیک: schema از metadata خوانده می‌شود
- هوشمند: از fuzzy matching و NLP استفاده می‌کند
- قابل توسعه: به راحتی می‌توان جداول جدید اضافه کرد

الگوریتم اصلی:
1. تحلیل query و استخراج کلمات کلیدی
2. تشخیص نوع جستجو (hierarchy vs entity)
3. تشخیص سطح سلسله مراتب (اگر hierarchy)
4. ساخت WHERE clause مناسب
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from .schema_metadata import (
    TableSchema, HierarchyLevel, get_schema, get_income_schema,
    MANABE_SCHEMA, MASAREF_SCHEMA
)

logger = logging.getLogger(__name__)


@dataclass
class SearchTarget:
    """هدف جستجو - کدام ستون‌ها با چه مقادیری"""
    columns: List[str]                    # ستون‌های مورد جستجو
    search_terms: List[str]               # عبارات جستجو
    hierarchy_level: Optional[str] = None # سطح سلسله مراتب (قسمت/بخش/بند/جزء)
    is_entity_search: bool = False        # آیا جستجوی entity است
    matched_value: Optional[str] = None   # مقدار یافت‌شده در database (برای exact match)
    confidence: float = 1.0               # میزان اطمینان


@dataclass
class ColumnDetectionResult:
    """نتیجه تشخیص ستون"""
    primary_column: Optional[str] = None      # ستون اصلی برای جستجو
    secondary_columns: List[str] = field(default_factory=list)  # ستون‌های ثانویه
    search_terms: List[str] = field(default_factory=list)       # عبارات جستجو
    exclude_terms: List[str] = field(default_factory=list)      # عبارات که باید exclude شوند
    hierarchy_level: Optional[str] = None     # سطح سلسله مراتب
    is_entity_search: bool = False            # آیا جستجوی entity است
    where_clause: str = "1=1"                 # WHERE clause ساخته شده
    aggregation_column: str = "جمع_کل"        # ستون برای aggregation
    year_column: str = "سال"                  # ستون سال
    income_type: str = "کل"                   # نوع درآمد (کل/عمومی/اختصاصی/ملی/استانی)
    confidence: float = 1.0                   # میزان اطمینان
    entity_name: Optional[str] = None         # نام entity (برای entity search)
    search_in_all_levels: bool = False        # آیا باید در همه سطوح جستجو شود


class SmartColumnDetector:
    """
    تشخیص‌دهنده هوشمند ستون‌ها
    
    این کلاس مسئول تحلیل query و تشخیص:
    1. نوع جستجو (hierarchy vs entity)
    2. سطح سلسله مراتب
    3. ستون‌های مناسب برای جستجو
    
    ویژگی‌های کلیدی:
    - استفاده از schema metadata
    - fuzzy matching با مقادیر واقعی database
    - پشتیبانی از نرمال‌سازی فارسی/عربی
    """
    
    # نقشه نرمال‌سازی کاراکترها
    # ⚠️ CRITICAL: "آ" را به "ا" تبدیل نمی‌کنیم چون در فارسی متفاوت هستند
    CHAR_NORMALIZE_MAP = str.maketrans({
        'ي': 'ی', 'ك': 'ک', 'ة': 'ه', 'ۀ': 'ه',
        'أ': 'ا', 'إ': 'ا', 'ٱ': 'ا'
        # 'آ': 'ا'  # حذف شد - آ و ا در فارسی متفاوت هستند
    })
    
    # کلمات توقف
    STOP_WORDS = {
        'از', 'به', 'در', 'و', 'یا', 'که', 'این', 'آن', 'برای', 'با',
        'های', 'ها', 'ی', 'ه', 'اول', 'دوم', 'سوم', 'چهارم', 'پنجم',
        'ششم', 'هفتم', 'هشتم', 'نهم', 'دهم', 'حاصل', 'ناشی', 'مربوط',
        'سال', 'چقدر', 'چند', 'کل', 'مجموع', 'درآمد', 'درامد',
        'هزینه', 'منابع', 'مصارف', ':', '-', '–'
    }
    
    # کلمات کلیدی entity - لیست کامل‌تر برای تشخیص دستگاه‌ها
    ENTITY_KEYWORDS = [
        # وزارتخانه‌ها و سازمان‌ها
        'وزارت', 'سازمان', 'نهاد', 'مرکز', 'مؤسسه', 'موسسه',
        # شرکت‌ها و بانک‌ها
        'شرکت', 'بانک', 'صندوق', 
        # آموزشی و فرهنگی
        'دانشگاه', 'آموزشگاه', 'فرهنگستان', 'پژوهشگاه', 'پژوهشکده',
        # درمانی
        'بیمارستان', 'درمانگاه',
        # اداری
        'اداره', 'استانداری', 'فرمانداری', 'شهرداری',
        # سایر
        'ستاد', 'بنیاد', 'کمیته', 'شورا', 'هیئت', 'هیات',
        'معاونت', 'دبیرخانه', 'کتابخانه', 'آکادمی'
    ]
    
    def __init__(self, schema: Optional[TableSchema] = None):
        """
        Args:
            schema: اختیاری - schema جدول. اگر ارائه نشود، از MANABE_SCHEMA استفاده می‌شود
        """
        self.schema = schema or MANABE_SCHEMA
        
    def normalize_text(self, text: str) -> str:
        """نرمال‌سازی متن فارسی"""
        if not text:
            return ''
        text = text.replace('\u200c', ' ').replace('\u200f', ' ')
        text = text.translate(self.CHAR_NORMALIZE_MAP)
        # نرمال‌سازی اضافی برای کاراکترهای خاص
        text = text.replace('ئ', 'ی')  # دارائی -> دارایی
        text = ' '.join(text.split())
        return text
    
    def extract_core_keywords(self, entity_name: str) -> List[str]:
        """
        استخراج کلمات کلیدی اصلی از نام entity
        
        مثال:
        - "شرکت بازرگانی گاز ایران" → ["بازرگان", "گاز"]
        - "وزارت آموزش و پرورش" → ["آموزش", "پرورش"]
        - "فرهنگستان علوم ایران" → ["فرهنگستان علوم"] (استفاده از phrase)
        
        بهبود: برای entity های خاص، از phrase استفاده می‌کنیم
        """
        # کلمات توقف که باید حذف شوند
        stop_words = {
            'شرکت', 'وزارت', 'سازمان', 'نهاد', 'مرکز', 'موسسه', 'مؤسسه',
            'بانک', 'صندوق', 'دانشگاه', 'پژوهشگاه',
            'ایران', 'کشور', 'ملی', 'دولتی', 'و', 'های', 'ها'
        }
        
        # کلمات که باید با کلمه بعدی ترکیب شوند (برای دقت بیشتر)
        combine_words = {'فرهنگستان', 'پژوهشکده', 'آکادمی'}
        
        words = entity_name.split()
        keywords = []
        i = 0
        
        while i < len(words):
            word = words[i]
            word_lower = word.lower().strip()
            
            # اگر کلمه در combine_words هست، با کلمه بعدی ترکیب کن
            if word_lower in combine_words and i + 1 < len(words):
                next_word = words[i + 1].lower().strip()
                if next_word not in stop_words:
                    # ترکیب دو کلمه به عنوان یک phrase
                    keywords.append(f"{word_lower} {next_word}")
                    i += 2
                    continue
                else:
                    keywords.append(word_lower)
                    i += 1
                    continue
            
            if word_lower in stop_words:
                i += 1
                continue
            if len(word_lower) < 2:
                i += 1
                continue
            # حذف پسوندها
            if word_lower.endswith('ی') and len(word_lower) > 3:
                word_lower = word_lower[:-1]
            keywords.append(word_lower)
            i += 1
        
        return keywords
    
    def detect(self, query: str, table_name: str = "manabe_sheet1") -> ColumnDetectionResult:
        """
        تشخیص هوشمند ستون‌ها از query
        
        این متد اصلی است که همه چیز رو تحلیل می‌کنه و نتیجه برمی‌گردونه.
        
        Args:
            query: سوال کاربر
            table_name: نام جدول
            
        Returns:
            ColumnDetectionResult با همه اطلاعات لازم
        """
        # دریافت schema
        schema = get_schema(table_name) or self.schema
        
        # نرمال‌سازی query
        query_normalized = self.normalize_text(query)
        query_lower = query_normalized.lower()
        
        result = ColumnDetectionResult()
        result.year_column = schema.year_column
        
        # 1. تشخیص سطح سلسله مراتب
        hierarchy_result = self._detect_hierarchy_level(query_lower, schema)
        if hierarchy_result:
            result.hierarchy_level = hierarchy_result['level']
            result.primary_column = hierarchy_result['column']
            result.search_terms = hierarchy_result['keywords']
            result.confidence = 0.9
            
            logger.info(f"🎯 Detected hierarchy level: {result.hierarchy_level}")
            logger.info(f"   Primary column: {result.primary_column}")
            logger.info(f"   Search terms: {result.search_terms}")
        
        # 2. تشخیص entity
        entity_result = self._detect_entity(query_normalized, schema)
        if entity_result:
            result.is_entity_search = True
            result.entity_name = entity_result['entity_name']
            if not result.primary_column:
                result.primary_column = entity_result['columns'][0]
            result.secondary_columns = entity_result['columns']
            if entity_result['entity_name']:
                result.search_terms.append(entity_result['entity_name'])
            # اضافه کردن exclude terms
            if entity_result.get('exclude_terms'):
                result.exclude_terms = entity_result['exclude_terms']
            # برای entity search بدون hierarchy level، باید در همه سطوح جستجو شود
            if not result.hierarchy_level:
                result.search_in_all_levels = True
            
            logger.info(f"🏢 Detected entity: {entity_result['entity_name']}")
        
        # 3. اگر هیچ چیز تشخیص داده نشد، جستجوی عمومی
        if not result.primary_column and not result.is_entity_search:
            general_result = self._create_general_search(query_normalized, schema)
            result.primary_column = general_result['column']
            result.search_terms = general_result['keywords']
            result.confidence = 0.5
            
            logger.info(f"🔍 Using general search")
        
        # 4. ساخت WHERE clause
        result.where_clause = self._build_where_clause(result, schema)
        
        # 5. تشخیص نوع درآمد
        result.income_type = self._detect_income_type(query_lower)
        
        # 6. تشخیص ستون aggregation بر اساس نوع درآمد
        result.aggregation_column = self._detect_aggregation_column(query_lower, schema)
        
        return result
    
    def _detect_income_type(self, query_lower: str) -> str:
        """
        تشخیص نوع درآمد از query
        
        Returns:
            'کل' | 'عمومی' | 'اختصاصی' | 'ملی' | 'استانی' | 'عمومی_ملی' | 'عمومی_استانی' | 'اختصاصی_ملی' | 'اختصاصی_استانی'
        """
        has_عمومی = 'عمومی' in query_lower or 'عمومي' in query_lower
        has_اختصاصی = 'اختصاصی' in query_lower or 'اختصاصي' in query_lower
        has_ملی = 'ملی' in query_lower or 'ملي' in query_lower
        has_استانی = 'استانی' in query_lower or 'استاني' in query_lower
        
        if has_عمومی:
            if has_ملی:
                return 'عمومی_ملی'
            elif has_استانی:
                return 'عمومی_استانی'
            return 'عمومی'
        
        if has_اختصاصی:
            if has_ملی:
                return 'اختصاصی_ملی'
            elif has_استانی:
                return 'اختصاصی_استانی'
            return 'اختصاصی'
        
        if has_ملی:
            return 'ملی'
        if has_استانی:
            return 'استانی'
        
        return 'کل'
    
    def _detect_hierarchy_level(
        self,
        query_lower: str,
        schema: TableSchema
    ) -> Optional[Dict[str, Any]]:
        """
        تشخیص سطح سلسله مراتب از query
        
        الگوریتم:
        1. جستجوی کلمات کلیدی سلسله مراتب در query
        2. تعیین سطح و ستون مربوطه
        3. استخراج کلمات کلیدی برای جستجو
        """
        if not schema.hierarchy_columns:
            return None
        
        # پیدا کردن کلمه کلیدی سلسله مراتب
        detected_level = None
        detected_position = len(query_lower)  # شروع از انتها
        
        for level_name, col_info in schema.hierarchy_columns.items():
            for keyword in col_info.keywords:
                pos = query_lower.find(keyword)
                if pos != -1 and pos < detected_position:
                    detected_level = level_name
                    detected_position = pos
        
        if not detected_level:
            return None
        
        # استخراج کلمات کلیدی
        keywords = self._extract_keywords_after_position(query_lower, detected_position)
        
        # اضافه کردن level name به keywords
        keywords.insert(0, detected_level)
        
        # حذف تکراری‌ها
        keywords = list(dict.fromkeys(keywords))
        
        return {
            'level': detected_level,
            'column': schema.hierarchy_columns[detected_level].column_name,
            'keywords': keywords[:4],  # حداکثر 4 keyword
            'position': detected_position
        }
    
    def _extract_keywords_after_position(self, text: str, position: int) -> List[str]:
        """
        استخراج کلمات کلیدی از متن بعد از یک موقعیت خاص
        
        مثال:
        - text: "بند درآمدهای حاصل از خدمات در سال 1402"
        - position: 0 (موقعیت "بند")
        - output: ["درآمد", "خدمات"]  # کلمات کلیدی مهم
        
        🔧 بهبود: "درآمد" رو نگه می‌داریم چون برای تفکیک بندها مهمه
        مثال: "بند درآمدهای حاصل از خدمات" vs "بند مالیات بر کالاها و خدمات"
        """
        after_text = text[position:].strip()
        words = after_text.split()
        
        # کلمات توقف اضافی برای hierarchy
        # ⚠️ "درآمد" رو حذف نمی‌کنیم چون برای تفکیک بندها مهمه
        hierarchy_stop_words = self.STOP_WORDS - {'درآمد', 'درامد'}  # حذف از stop words
        hierarchy_stop_words = hierarchy_stop_words | {
            'واگذار', 'واگذاری', 'دارای', 'دارایی', 'دارائی',
            'منابع', 'حاصل', 'ناشی', 'مربوط'
        }
        
        keywords = []
        for word in words:
            word = word.strip(':-–،.')
            
            # skip کلمات توقف و کوتاه
            if word in hierarchy_stop_words or len(word) < 3:
                continue
            
            # skip اعداد (سال)
            if word.isdigit():
                continue
            
            # نرمال‌سازی پسوندها
            if word.endswith('های'):
                word = word[:-3]
            elif word.endswith('ها'):
                word = word[:-2]
            elif word.endswith('ی') and len(word) > 4:
                word = word[:-1]
            
            if word and len(word) >= 3:
                keywords.append(word)
        
        # 🔧 بهبود: حداکثر 3 keyword (برای دقت بیشتر در تفکیک بندها)
        # مثال: "بند درآمدهای حاصل از خدمات" → ["درامد", "خدمات"]
        return keywords[:3]
    
    def _detect_entity(
        self,
        query: str,
        schema: TableSchema
    ) -> Optional[Dict[str, Any]]:
        """
        تشخیص entity (دستگاه/سازمان) از query
        
        الگوریتم:
        1. جستجوی کلمات کلیدی entity
        2. استخراج نام کامل entity
        3. تعیین ستون‌های جستجو
        """
        if not schema.entity_columns:
            return None
        
        query_lower = query.lower()
        
        # پیدا کردن کلمه کلیدی entity
        entity_start = -1
        entity_keyword = None
        
        for keyword in self.ENTITY_KEYWORDS:
            pos = query_lower.find(keyword)
            if pos != -1:
                if entity_start == -1 or pos < entity_start:
                    entity_start = pos
                    entity_keyword = keyword
        
        if entity_start == -1:
            return None
        
        # استخراج نام کامل entity
        entity_name = self._extract_entity_name(query, entity_start)
        
        # ستون‌های جستجو
        columns = [info.column_name for info in schema.entity_columns.values()]
        
        # تشخیص کلمات exclude (برای دقت بیشتر)
        # مثال: "فرهنگستان علوم ایران" - اگر "پزشکی" در query نیست، باید exclude بشه
        exclude_terms = self._detect_exclude_terms(entity_name, query)
        
        return {
            'entity_name': entity_name,
            'columns': columns,
            'keyword': entity_keyword,
            'exclude_terms': exclude_terms
        }
    
    def _detect_exclude_terms(self, entity_name: str, query: str) -> List[str]:
        """
        تشخیص کلمات که باید exclude شوند
        
        مثال:
        - entity: "فرهنگستان علوم ایران", query بدون "پزشکی" → exclude: ["پزشک"]
        """
        exclude_terms = []
        query_lower = query.lower()
        
        # اگر "علوم" هست ولی "پزشکی" نیست
        if 'علوم' in entity_name.lower() and 'پزشک' not in query_lower:
            exclude_terms.append('پزشک')
        
        # اگر "اطلاعات" هست ولی "فناوری" نیست
        if 'اطلاعات' in entity_name.lower() and 'فناور' not in query_lower:
            # برای "وزارت اطلاعات" vs "وزارت ارتباطات و فناوری اطلاعات"
            # این یک edge case هست که باید با دقت handle بشه
            pass
        
        return exclude_terms
    
    def _extract_entity_name(self, query: str, start_pos: int) -> str:
        """
        استخراج نام کامل entity
        
        مثال:
        - "درآمد وزارت نفت در سال 1403" → "وزارت نفت"
        """
        # کلمات توقف که پایان entity را مشخص می‌کنند
        stop_markers = {'در', 'از', 'به', 'با', 'که', 'سال', 'چقدر', 'چند', 'کل', 'مجموع'}
        
        remaining = query[start_pos:]
        words = remaining.split()
        
        entity_words = []
        for word in words:
            word_clean = word.strip('،.؟!')
            if word_clean.lower() in stop_markers:
                break
            if word_clean.isdigit():
                break
            entity_words.append(word_clean)
        
        return ' '.join(entity_words) if entity_words else ''
    
    def _create_general_search(
        self,
        query: str,
        schema: TableSchema
    ) -> Dict[str, Any]:
        """
        ایجاد جستجوی عمومی وقتی نوع خاصی تشخیص داده نشده
        """
        # استخراج کلمات کلیدی
        words = query.split()
        keywords = []
        
        for word in words:
            word = word.strip('،.؟!:-')
            if len(word) < 3 or word.lower() in self.STOP_WORDS:
                continue
            if word.isdigit():
                continue
            keywords.append(word)
        
        # ستون پیش‌فرض: جزء (پایین‌ترین سطح)
        default_column = "عنوان_جزء"
        if schema.hierarchy_columns:
            # انتخاب پایین‌ترین سطح
            lowest_level = max(schema.hierarchy_columns.items(), 
                             key=lambda x: x[1].level.level)
            default_column = lowest_level[1].column_name
        
        return {
            'column': default_column,
            'keywords': keywords[:3]
        }
    
    def _build_where_clause(
        self,
        result: ColumnDetectionResult,
        schema: TableSchema
    ) -> str:
        """
        ساخت WHERE clause از نتیجه تشخیص
        
        ویژگی‌های کلیدی:
        - استفاده از TRANSLATE برای نرمال‌سازی
        - AND بین keywords
        - OR بین ستون‌ها (فقط برای entity)
        """
        conditions = []
        
        def _normalize_column(col_name: str) -> str:
            """نرمال‌سازی ستون در SQL"""
            return (
                f"TRANSLATE(\"{col_name}\", 'يكيۀةأإٱ', 'یکیهههاا')"
            )
        
        # شرط اصلی
        if result.primary_column and result.search_terms:
            col_norm = _normalize_column(result.primary_column)
            
            # AND بین همه keywords
            term_conditions = []
            for term in result.search_terms:
                safe_term = term.replace("'", "''")
                term_conditions.append(f"{col_norm} ILIKE '%{safe_term}%'")
            
            if term_conditions:
                conditions.append(f"({' AND '.join(term_conditions)})")
        
        # شرط entity (OR بین ستون‌ها)
        if result.is_entity_search and result.secondary_columns:
            entity_conditions = []
            entity_term = result.entity_name or (result.search_terms[-1] if result.search_terms else '')
            
            if entity_term:
                # استخراج کلمات کلیدی اصلی از نام entity
                core_keywords = self.extract_core_keywords(entity_term)
                
                if core_keywords:
                    # استفاده از کلمات کلیدی اصلی (بدون شرکت/وزارت/...)
                    for col in result.secondary_columns:
                        col_norm = _normalize_column(col)
                        # AND بین کلمات کلیدی
                        kw_conditions = [f"{col_norm} ILIKE '%{kw}%'" for kw in core_keywords]
                        entity_conditions.append(f"({' AND '.join(kw_conditions)})")
                else:
                    # fallback به روش قبلی
                    safe_term = entity_term.replace("'", "''")
                    for col in result.secondary_columns:
                        col_norm = _normalize_column(col)
                        entity_conditions.append(f"{col_norm} ILIKE '%{safe_term}%'")
                
                if entity_conditions:
                    conditions.append(f"({' OR '.join(entity_conditions)})")
        
        # اضافه کردن شرط exclude
        if result.exclude_terms:
            for exclude_term in result.exclude_terms:
                safe_term = exclude_term.replace("'", "''")
                # NOT ILIKE برای همه ستون‌های entity
                exclude_conditions = []
                for col in result.secondary_columns:
                    col_norm = _normalize_column(col)
                    exclude_conditions.append(f"{col_norm} NOT ILIKE '%{safe_term}%'")
                if exclude_conditions:
                    conditions.append(f"({' AND '.join(exclude_conditions)})")
        
        if not conditions:
            return "1=1"
        
        return ' AND '.join(conditions)
    
    def _detect_aggregation_column(
        self,
        query_lower: str,
        schema: TableSchema
    ) -> str:
        """
        تشخیص ستون مناسب برای aggregation
        """
        # بررسی کلمات کلیدی
        if 'عمومی' in query_lower or 'عمومي' in query_lower:
            if 'ملی' in query_lower or 'ملي' in query_lower:
                return schema.value_columns.get("درآمد_عمومی_ملی", 
                       schema.value_columns.get("جمع_کل")).column_name
            elif 'استانی' in query_lower or 'استاني' in query_lower:
                return schema.value_columns.get("درآمد_عمومی_استانی",
                       schema.value_columns.get("جمع_کل")).column_name
        
        if 'اختصاصی' in query_lower or 'اختصاصي' in query_lower:
            if 'ملی' in query_lower or 'ملي' in query_lower:
                return schema.value_columns.get("درآمد_اختصاصی_ملی",
                       schema.value_columns.get("جمع_کل")).column_name
            elif 'استانی' in query_lower or 'استاني' in query_lower:
                return schema.value_columns.get("درآمد_اختصاصی_استانی",
                       schema.value_columns.get("جمع_کل")).column_name
        
        # Default: جمع کل
        if "جمع_کل" in schema.value_columns:
            return schema.value_columns["جمع_کل"].column_name
        return "جمع_کل"


# ============================================================================
# توابع کمکی برای استفاده سریع
# ============================================================================

def detect_columns(query: str, table_name: str = "manabe_sheet1") -> ColumnDetectionResult:
    """
    تابع کمکی برای تشخیص سریع ستون‌ها
    
    Args:
        query: سوال کاربر
        table_name: نام جدول
        
    Returns:
        ColumnDetectionResult
    """
    detector = SmartColumnDetector()
    return detector.detect(query, table_name)


def get_where_clause(query: str, table_name: str = "manabe_sheet1") -> str:
    """
    دریافت WHERE clause برای یک query
    """
    result = detect_columns(query, table_name)
    return result.where_clause


def get_hierarchy_level(query: str, table_name: str = "manabe_sheet1") -> Optional[str]:
    """
    دریافت سطح سلسله مراتب تشخیص داده شده
    """
    result = detect_columns(query, table_name)
    return result.hierarchy_level


# ============================================================================
# تست
# ============================================================================

if __name__ == "__main__":
    # تست‌های ساده
    test_queries = [
        "درآمد های حاصل از بخش درآمد های مالیاتی در سال 1401",
        "قسمت درآمدها در سال 1403",
        "بند مالیات بر واردات چقدر درآمد داشته",
        "درآمد وزارت نفت در سال 1402",
        "سازمان امور مالیاتی کشور چقدر درآمد داشته",
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        result = detect_columns(query)
        print(f"Hierarchy Level: {result.hierarchy_level}")
        print(f"Primary Column: {result.primary_column}")
        print(f"Search Terms: {result.search_terms}")
        print(f"WHERE: {result.where_clause}")
