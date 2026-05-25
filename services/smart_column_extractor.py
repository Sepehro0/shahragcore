# -*- coding: utf-8 -*-
"""
Smart Column Extractor
استخراج هوشمند ستون مورد نظر از query کاربر

مثال:
- "هزینه های سرمایه ای عمومی" -> براورد_تملك_دارايي_هاي_سرمايه_اي_ع
- "اعتبارات هزینه ای متفرقه" -> برآورد_اعتبارات_هزینه_ای_متفرقه
- "جمع هزینه های سرمایه ای" -> جمع_برآورد_تملك_دارايي_هاي_سرمايه_
- "بودجه کل" -> جمع_كل
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ColumnMatch:
    """نتیجه تطبیق ستون"""
    column_name: str  # نام واقعی ستون در database
    confidence: float  # اطمینان (0-1)
    matched_text: str  # متن match شده در query
    column_type: str  # نوع: 'current' (هزینه‌ای), 'capital' (سرمایه‌ای), 'total' (کل)
    scope: str  # محدوده: 'public' (عمومی), 'specific' (اختصاصی), 'misc' (متفرقه), 'sum' (جمع), 'all' (همه)


class SmartColumnExtractor:
    """استخراج هوشمند ستون از query"""
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # الگوهای تشخیص برای جدول MASAREF (هزینه)
    # ═══════════════════════════════════════════════════════════════════════════════
    MASAREF_PATTERNS = [
        # ========== هزینه‌ای (اعتبارات) ==========
        
        # هزینه‌ای عمومی
        {
            'patterns': [
                r'هزینه\s*(های)?\s*عمومی',
                r'هزینه\s*(های)?\s*جاری\s*عمومی',
                r'اعتبارات?\s*هزینه\s*ای\s*عمومی',
                r'(برآورد|براورد)\s*اعتبارات?\s*هزینه\s*ای\s*عمومی',
            ],
            'column': 'براورد_اعتبارات_هزینه_ای_عمومی',
            'type': 'current',
            'scope': 'public',
            'priority': 10  # بالاترین اولویت
        },
        
        # هزینه‌ای متفرقه
        {
            'patterns': [
                r'هزینه\s*(های)?\s*متفرقه',
                r'هزینه\s*(های)?\s*جاری\s*متفرقه',
                r'اعتبارات?\s*هزینه\s*ای\s*متفرقه',
                r'(برآورد|براورد)\s*اعتبارات?\s*هزینه\s*ای\s*متفرقه',
            ],
            'column': 'برآورد_اعتبارات_هزینه_ای_متفرقه',
            'type': 'current',
            'scope': 'misc',
            'priority': 10
        },
        
        # هزینه‌ای اختصاصی
        {
            'patterns': [
                r'هزینه\s*(های)?\s*اختصاصی',
                r'هزینه\s*(های)?\s*جاری\s*اختصاصی',
                r'اعتبارات?\s*هزینه\s*ای\s*اختصاصی',
                r'(برآورد|براورد)\s*اعتبارات?\s*هزینه\s*ای\s*اختصاصی',
            ],
            'column': 'براورد_اعتبارات_هزینه_ای_اختصاصی',
            'type': 'current',
            'scope': 'specific',
            'priority': 10
        },
        
        # جمع هزینه‌ای یا اعتبارات هزینه‌ای عمومی (general)
        {
            'patterns': [
                r'اعتبارات?\s*هزینه\s*(های)?\s*ای(?!\s*(عمومی|متفرقه|اختصاصی))',  # اعتبارات هزینه‌ای (بدون scope)
                r'جمع\s*(کل)?\s*هزینه\s*(های)?\s*ای',
                r'جمع\s*اعتبارات?\s*هزینه\s*ای',
                r'جمع\s*(برآورد|براورد)\s*اعتبارات?\s*هزینه\s*ای',
            ],
            'column': 'جمع_براورد_اعتبارات_هزینه_ای',
            'type': 'current',
            'scope': 'sum',
            'priority': 8  # کاهش priority تا exact matches (عمومی/متفرقه/اختصاصی) بالاتر باشند
        },
        
        # ========== سرمایه‌ای (تملک دارایی) ==========
        
        # سرمایه‌ای عمومی
        {
            'patterns': [
                r'(هزینه\s*(های)?\s*)?سرمایه\s*ای\s*عمومی',
                r'تملک\s*دارایی\s*(های)?\s*سرمایه\s*ای\s*عمومی',
                r'(برآورد|براورد)\s*تملک\s*دارایی\s*(های)?\s*سرمایه\s*ای\s*عمومی',
                r'دارایی\s*(های)?\s*سرمایه\s*ای\s*عمومی',
            ],
            'column': 'براورد_تملك_دارايي_هاي_سرمايه_اي_ع',
            'type': 'capital',
            'scope': 'public',
            'priority': 10
        },
        
        # سرمایه‌ای متفرقه
        {
            'patterns': [
                r'(هزینه\s*(های)?\s*)?سرمایه\s*ای\s*متفرقه',
                r'تملک\s*دارایی\s*(های)?\s*سرمایه\s*ای\s*متفرقه',
                r'(برآورد|براورد)\s*تملک\s*دارایی\s*(های)?\s*سرمایه\s*ای\s*متفرقه',
                r'دارایی\s*(های)?\s*سرمایه\s*ای\s*متفرقه',
            ],
            'column': 'براورد_تملك_دارايي_هاي_سرمايه_اي_م',
            'type': 'capital',
            'scope': 'misc',
            'priority': 10
        },
        
        # سرمایه‌ای اختصاصی
        {
            'patterns': [
                r'(هزینه\s*(های)?\s*)?سرمایه\s*ای\s*اختصاصی',
                r'تملک\s*دارایی\s*(های)?\s*سرمایه\s*ای\s*اختصاصی',
                r'(برآورد|براورد)\s*تملک\s*دارایی\s*(های)?\s*سرمایه\s*ای\s*اختصاصی',
                r'دارایی\s*(های)?\s*سرمایه\s*ای\s*اختصاصی',
            ],
            'column': 'براورد_تملك_دارايي_هاي_سرمايه_اي_ا',
            'type': 'capital',
            'scope': 'specific',
            'priority': 10
        },
        
        # جمع سرمایه‌ای
        {
            'patterns': [
                r'جمع\s*(کل)?\s*(هزینه\s*(های)?\s*)?سرمایه\s*ای',
                r'جمع\s*تملک\s*دارایی\s*(های)?\s*سرمایه\s*ای',
                r'جمع\s*(برآورد|براورد)\s*تملک\s*دارایی\s*(های)?\s*سرمایه\s*ای',
                r'جمع\s*دارایی\s*(های)?\s*سرمایه\s*ای',
            ],
            'column': 'جمع_برآورد_تملك_دارايي_هاي_سرمايه_',
            'type': 'capital',
            'scope': 'sum',
            'priority': 9
        },
        
        # ========== کل ==========
        
        # جمع کل / بودجه کل
        {
            'patterns': [
                r'جمع\s*کل',
                r'بودجه\s*کل',
                r'کل\s*بودجه',
                r'مجموع\s*کل',
            ],
            'column': 'جمع_كل',
            'type': 'total',
            'scope': 'all',
            'priority': 7  # اولویت پایین‌تر
        },
        
        # ========== Fallback: فقط "هزینه‌ای" یا "سرمایه‌ای" ==========
        
        # فقط "هزینه‌ای" یا "هزینه جاری" -> جمع هزینه‌ای
        {
            'patterns': [
                r'هزینه\s*(های)?\s*ای(?!\s*(عمومی|متفرقه|اختصاصی))',
                r'هزینه\s*(های)?\s*جاری(?!\s*(عمومی|متفرقه|اختصاصی))',
                r'اعتبارات?\s*هزینه\s*ای(?!\s*(عمومی|متفرقه|اختصاصی))',
            ],
            'column': 'جمع_براورد_اعتبارات_هزینه_ای',
            'type': 'current',
            'scope': 'sum',
            'priority': 5
        },
        
        # فقط "سرمایه‌ای" -> جمع سرمایه‌ای
        {
            'patterns': [
                r'سرمایه\s*ای(?!\s*(عمومی|متفرقه|اختصاصی))',
            ],
            'column': 'جمع_برآورد_تملك_دارايي_هاي_سرمايه_',
            'type': 'capital',
            'scope': 'sum',
            'priority': 5
        },
    ]
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # الگوهای تشخیص برای جدول MANABE قدیم (manabe_sheet1)
    # ═══════════════════════════════════════════════════════════════════════════════
    MANABE_PATTERNS = [
        # ========== درآمد عمومی ==========
        
        # درآمد عمومی ملی
        {
            'patterns': [
                r'(در\s*آمد|درامد|در\s*امد)\s*عمومی\s*ملی',
            ],
            'column': 'در_آمد_عمومي_ملي',
            'type': 'public_income',
            'scope': 'national',
            'priority': 10
        },
        
        # درآمد عمومی استانی
        {
            'patterns': [
                r'(در\s*آمد|درامد|در\s*امد)\s*عمومی\s*استانی',
            ],
            'column': 'در_آمد_عمومي_استاني',
            'type': 'public_income',
            'scope': 'provincial',
            'priority': 10
        },
        
        # جمع درآمد عمومی
        {
            'patterns': [
                r'جمع\s*(در\s*آمد|درامد|در\s*امد)\s*عمومی',
            ],
            'column': 'جمع_در_آمد_عمومی',
            'type': 'public_income',
            'scope': 'sum',
            'priority': 9
        },
        
        # ========== درآمد اختصاصی ==========
        
        # درآمد اختصاصی ملی
        {
            'patterns': [
                r'(در\s*آمد|درامد|در\s*امد)\s*اختصاصی\s*ملی',
            ],
            'column': 'در_آمد_اختصاصي_ملي',
            'type': 'specific_income',
            'scope': 'national',
            'priority': 10
        },
        
        # درآمد اختصاصی استانی
        {
            'patterns': [
                r'(در\s*آمد|درامد|در\s*امد)\s*اختصاصی\s*استانی',
            ],
            'column': 'در_آمد_اختصاصي_استاني',
            'type': 'specific_income',
            'scope': 'provincial',
            'priority': 10
        },
        
        # جمع درآمد اختصاصی
        {
            'patterns': [
                r'جمع\s*(در\s*آمد|درامد|در\s*امد)\s*اختصاصی',
            ],
            'column': 'جمع_در_آمد_اختصاصی',
            'type': 'specific_income',
            'scope': 'sum',
            'priority': 9
        },
        
        # ========== کل ==========
        
        # جمع کل ملی
        {
            'patterns': [
                r'جمع\s*کل\s*ملی',
            ],
            'column': 'جمع_کل_ملي',
            'type': 'total',
            'scope': 'national',
            'priority': 9
        },
        
        # جمع کل استانی
        {
            'patterns': [
                r'جمع\s*کل\s*استانی',
            ],
            'column': 'جمع_کل_استاني',
            'type': 'total',
            'scope': 'provincial',
            'priority': 9
        },
        
        # جمع کل / بودجه کل
        {
            'patterns': [
                r'جمع\s*کل',
                r'بودجه\s*کل',
                r'کل\s*(در\s*آمد|درامد|در\s*امد)',
                r'مجموع\s*کل',
            ],
            'column': 'جمع_کل',
            'type': 'total',
            'scope': 'all',
            'priority': 7
        },
    ]
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # الگوهای تشخیص برای جدول MANABE3 جدید (manabe3_sheet1) - ترتیب ستون‌ها متفاوت
    # ═══════════════════════════════════════════════════════════════════════════════
    MANABE3_PATTERNS = [
        # ========== درآمد عمومی ==========
        
        # درآمد عمومی ملی -> ملی_در_آمد_عمومی
        {
            'patterns': [
                r'(در\s*آمد|درامد|در\s*امد)\s*(عمومی\s*ملی|ملی\s*عمومی)',
                r'ملی\s*(در\s*آمد|درامد|در\s*امد)?\s*عمومی',
            ],
            'column': 'ملی_در_آمد_عمومی',
            'type': 'public_income',
            'scope': 'national',
            'priority': 10
        },
        
        # درآمد عمومی استانی -> استانی_در_آمد_عمومی
        {
            'patterns': [
                r'(در\s*آمد|درامد|در\s*امد)\s*(عمومی\s*استانی|استانی\s*عمومی)',
                r'استانی\s*(در\s*آمد|درامد|در\s*امد)?\s*عمومی',
            ],
            'column': 'استانی_در_آمد_عمومی',
            'type': 'public_income',
            'scope': 'provincial',
            'priority': 10
        },
        
        # جمع درآمد عمومی
        {
            'patterns': [
                r'جمع\s*(در\s*آمد|درامد|در\s*امد)\s*عمومی',
            ],
            'column': 'جمع_در_آمد_عمومی',
            'type': 'public_income',
            'scope': 'sum',
            'priority': 9
        },
        
        # ========== درآمد اختصاصی ==========
        
        # درآمد اختصاصی ملی -> ملی_در_آمد_اختصاصی
        {
            'patterns': [
                r'(در\s*آمد|درامد|در\s*امد)\s*(اختصاصی\s*ملی|ملی\s*اختصاصی)',
                r'ملی\s*(در\s*آمد|درامد|در\s*امد)?\s*اختصاصی',
            ],
            'column': 'ملی_در_آمد_اختصاصی',
            'type': 'specific_income',
            'scope': 'national',
            'priority': 10
        },
        
        # درآمد اختصاصی استانی -> استانی_در_آمد_اختصاصی
        {
            'patterns': [
                r'(در\s*آمد|درامد|در\s*امد)\s*(اختصاصی\s*استانی|استانی\s*اختصاصی)',
                r'استانی\s*(در\s*آمد|درامد|در\s*امد)?\s*اختصاصی',
            ],
            'column': 'استانی_در_آمد_اختصاصی',
            'type': 'specific_income',
            'scope': 'provincial',
            'priority': 10
        },
        
        # جمع درآمد اختصاصی
        {
            'patterns': [
                r'جمع\s*(در\s*آمد|درامد|در\s*امد)\s*اختصاصی',
            ],
            'column': 'جمع_در_آمد_اختصاصی',
            'type': 'specific_income',
            'scope': 'sum',
            'priority': 9
        },
        
        # ========== کل ==========
        
        # جمع کل ملی / درآمد ملی -> ملی_جمع_کل
        {
            'patterns': [
                r'جمع\s*کل\s*ملی',
                r'ملی\s*جمع\s*کل',
                r'(در\s*آمد|درامد|در\s*امد)\s*ملی(?!\s*(عمومی|اختصاصی))',
            ],
            'column': 'ملی_جمع_کل',
            'type': 'total',
            'scope': 'national',
            'priority': 9
        },
        
        # جمع کل استانی / درآمد استانی -> استانی_جمع_کل
        {
            'patterns': [
                r'جمع\s*کل\s*استانی',
                r'استانی\s*جمع\s*کل',
                r'(در\s*آمد|درامد|در\s*امد)\s*استانی(?!\s*(عمومی|اختصاصی))',
            ],
            'column': 'استانی_جمع_کل',
            'type': 'total',
            'scope': 'provincial',
            'priority': 9
        },
        
        # جمع کل / بودجه کل
        {
            'patterns': [
                r'جمع\s*کل',
                r'بودجه\s*کل',
                r'کل\s*(در\s*آمد|درامد|در\s*امد)',
                r'مجموع\s*کل',
            ],
            'column': 'جمع_کل',
            'type': 'total',
            'scope': 'all',
            'priority': 7
        },
    ]
    
    def __init__(self):
        """Initialize extractor"""
        # کامپایل regex patterns برای بهبود عملکرد
        self._compile_patterns()
    
    def _compile_patterns(self):
        """کامپایل کردن regex patterns"""
        for pattern_group in self.MASAREF_PATTERNS:
            pattern_group['compiled'] = [
                re.compile(p, re.IGNORECASE) for p in pattern_group['patterns']
            ]
        
        for pattern_group in self.MANABE_PATTERNS:
            pattern_group['compiled'] = [
                re.compile(p, re.IGNORECASE) for p in pattern_group['patterns']
            ]
        
        for pattern_group in self.MANABE3_PATTERNS:
            pattern_group['compiled'] = [
                re.compile(p, re.IGNORECASE) for p in pattern_group['patterns']
            ]
    
    def _normalize_query(self, query: str) -> str:
        """نرمال‌سازی query"""
        # حذف فضاهای اضافی
        query = re.sub(r'\s+', ' ', query).strip()
        # یکسان‌سازی کاراکترها
        query = query.replace('ي', 'ی').replace('ى', 'ی')
        query = query.replace('ك', 'ک')
        # حذف نیم‌فاصله
        query = query.replace('\u200c', ' ')
        return query
    
    def extract_column(
        self,
        query: str,
        table_name: str,
        return_all_matches: bool = False
    ) -> Optional[ColumnMatch] | List[ColumnMatch]:
        """
        استخراج ستون از query
        
        Args:
            query: پرسش کاربر
            table_name: نام جدول (masaref2_sheet1, masaref_sheet1, manabe_sheet1)
            return_all_matches: اگر True باشد، تمام matches را برمی‌گرداند
            
        Returns:
            بهترین ColumnMatch یا None
        """
        query_normalized = self._normalize_query(query)
        
        # انتخاب الگوهای مناسب
        if 'masaref' in table_name.lower():
            patterns = self.MASAREF_PATTERNS
        elif 'manabe3' in table_name.lower():
            # برای جدول جدید با ترتیب ستون‌های متفاوت
            patterns = self.MANABE3_PATTERNS
        elif 'manabe' in table_name.lower():
            patterns = self.MANABE_PATTERNS
        else:
            logger.warning(f"⚠️ Unknown table type: {table_name}")
            return [] if return_all_matches else None
        
        # جستجو در همه patterns
        matches: List[ColumnMatch] = []
        
        for pattern_group in patterns:
            for compiled_pattern in pattern_group['compiled']:
                match = compiled_pattern.search(query_normalized)
                if match:
                    # محاسبه confidence بر اساس:
                    # 1. priority از pattern
                    # 2. طول متن match شده (بلندتر = بهتر)
                    # 3. موقعیت در query (زودتر = بهتر)
                    base_confidence = pattern_group['priority'] / 10.0
                    length_bonus = len(match.group(0)) / 100.0  # بونوس بر اساس طول
                    position_penalty = match.start() / len(query_normalized) * 0.1  # جریمه موقعیت
                    
                    confidence = min(1.0, base_confidence + length_bonus - position_penalty)
                    
                    col_match = ColumnMatch(
                        column_name=pattern_group['column'],
                        confidence=confidence,
                        matched_text=match.group(0),
                        column_type=pattern_group['type'],
                        scope=pattern_group['scope']
                    )
                    
                    matches.append(col_match)
                    
                    logger.debug(
                        f"✅ Column match: '{match.group(0)}' -> {pattern_group['column']} "
                        f"(confidence={confidence:.2f})"
                    )
        
        if not matches:
            logger.info(f"❌ No column match found in query: '{query[:100]}'")
            return [] if return_all_matches else None
        
        if return_all_matches:
            # مرتب‌سازی بر اساس confidence
            matches.sort(key=lambda m: m.confidence, reverse=True)
            return matches
        
        # بازگشت بهترین match
        best_match = max(matches, key=lambda m: m.confidence)
        logger.info(
            f"🎯 Best column match: '{best_match.matched_text}' -> {best_match.column_name} "
            f"(confidence={best_match.confidence:.2f}, type={best_match.column_type}, "
            f"scope={best_match.scope})"
        )
        
        return best_match
    
    def get_column_for_aggregation(
        self,
        query: str,
        table_name: str,
        default_column: str = None
    ) -> str:
        """
        دریافت نام ستون برای aggregation (SUM)
        
        Args:
            query: پرسش کاربر
            table_name: نام جدول
            default_column: ستون پیش‌فرض اگر هیچ match پیدا نشد
            
        Returns:
            نام ستون برای استفاده در SQL
        """
        match = self.extract_column(query, table_name)
        
        if match:
            return match.column_name
        
        # اگر match پیدا نشد، از default استفاده کن
        if default_column:
            logger.info(f"⚠️ Using default column: {default_column}")
            return default_column
        
        # آخرین fallback: جمع_کل یا جمع_كل
        if 'masaref' in table_name.lower():
            logger.warning(f"⚠️ No column match, using fallback: جمع_كل")
            return 'جمع_كل'
        elif 'manabe' in table_name.lower():
            logger.warning(f"⚠️ No column match, using fallback: جمع_کل")
            return 'جمع_کل'
        
        return default_column or 'جمع_كل'


# Global instance
_extractor_instance = None

def get_smart_column_extractor() -> SmartColumnExtractor:
    """دریافت instance سینگلتون"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = SmartColumnExtractor()
    return _extractor_instance

