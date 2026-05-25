# -*- coding: utf-8 -*-
"""
Budget Query Processor - پردازشگر اختصاصی سوالات بودجه
این ماژول مسئول پردازش هوشمند سوالات مربوط به collection budget_financial است.

قابلیت‌ها:
- تشخیص نوع جدول (MANABE vs MASAREF)
- جستجوی سلسله‌مراتبی
- مدیریت سال و قوانین یارانه
- فرمت‌دهی پاسخ استاندارد
"""

import re
import logging
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class TableType(Enum):
    """نوع جدول بودجه"""
    MANABE = "manabe"      # منابع/درآمد
    MASAREF = "masaref"    # مصارف/هزینه
    BOTH = "both"          # هر دو جدول
    UNKNOWN = "unknown"    # نامشخص


class HierarchyLevel(Enum):
    """سطوح سلسله‌مراتبی جداول"""
    # MANABE levels
    GHESMAT = "قسمت"
    BAKHSH = "بخش"
    BAND = "بند"
    JOZ = "جزء"
    DASTGAH = "دستگاه"
    DASTGAH_EJRAEI = "دستگاه اجرایی"
    
    # MASAREF levels
    DASTGAH_ASLI = "دستگاه اصلی"


@dataclass
class BudgetQueryAnalysis:
    """نتیجه تحلیل سوال بودجه"""
    table_type: TableType
    hierarchy_level: Optional[str]
    entity_names: List[str]
    years: List[str]
    income_type: Optional[str]  # عمومی/اختصاصی/کل
    cost_type: Optional[str]    # هزینه‌ای/سرمایه‌ای/کل
    needs_subsidy_calculation: bool
    subsidy_rule: Optional[str]  # "include" or "separate"
    confidence: float


class BudgetTableDetector:
    """تشخیص نوع جدول بر اساس کلمات کلیدی"""
    
    # کلمات کلیدی برای جدول MANABE (منابع/درآمد)
    MANABE_KEYWORDS = {
        'primary': ['واگذاری', 'درآمد', 'منابع', 'وصول', 'حاصل از', 'درامد'],
        'secondary': ['ملی', 'استانی', 'عمومی', 'اختصاصی'],
        'compound': {
            'درآمد عمرانی': 'واگذاری دارایی‌های سرمایه‌ای',
            'درآمد عمومی': 'درآمد عمومی',
            'درآمد اختصاصی': 'درآمد اختصاصی'
        }
    }
    
    # کلمات کلیدی برای جدول MASAREF (مصارف/هزینه)
    MASAREF_KEYWORDS = {
        'primary': ['برآورد', 'هزینه', 'مخارج', 'مصارف', 'تملک', 'اعتبار', 'بودجه', 'تملك'],
        'secondary': ['عمومی', 'متفرقه', 'اختصاصی', 'یارانه'],
        'compound': {
            'هزینه جاری': 'اعتبارات هزینه‌ای',
            'اعتبارات جاری': 'اعتبارات هزینه‌ای',
            'هزینه عمرانی': 'تملک دارایی‌های سرمایه‌ای',
            'اعتبارات عمرانی': 'تملک دارایی‌های سرمایه‌ای'
        }
    }
    
    # کلمات کلیدی سطوح سلسله‌مراتبی
    HIERARCHY_KEYWORDS = {
        'قسمت': ['قسمت'],
        'بخش': ['بخش'],
        'بند': ['بند'],
        'جزء': ['جزء', 'جزو'],
        'دستگاه اصلی': ['دستگاه اصلی', 'دستگاه اصلي'],
        'دستگاه اجرایی': ['دستگاه اجرایی', 'دستگاه اجرايي', 'دستگاه']
    }
    
    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: کلاینت LLM برای موارد مبهم (اختیاری)
        """
        self.llm_client = llm_client
    
    def detect_table(self, query: str) -> Tuple[TableType, float, str]:
        """
        تشخیص نوع جدول از روی سوال
        
        Args:
            query: سوال کاربر
            
        Returns:
            Tuple of (TableType, confidence, reason)
        """
        query_lower = self._normalize_query(query)
        
        manabe_score = 0
        masaref_score = 0
        matched_keywords = {'manabe': [], 'masaref': []}
        
        # بررسی کلمات کلیدی اصلی MANABE
        for keyword in self.MANABE_KEYWORDS['primary']:
            if keyword in query_lower:
                manabe_score += 2
                matched_keywords['manabe'].append(keyword)
        
        # بررسی کلمات کلیدی اصلی MASAREF
        for keyword in self.MASAREF_KEYWORDS['primary']:
            if keyword in query_lower:
                masaref_score += 2
                matched_keywords['masaref'].append(keyword)
        
        # بررسی عبارات ترکیبی MANABE
        for compound, target in self.MANABE_KEYWORDS['compound'].items():
            if compound in query_lower:
                manabe_score += 3
                matched_keywords['manabe'].append(compound)
        
        # بررسی عبارات ترکیبی MASAREF
        for compound, target in self.MASAREF_KEYWORDS['compound'].items():
            if compound in query_lower:
                masaref_score += 3
                matched_keywords['masaref'].append(compound)
        
        # تعیین نوع جدول
        if manabe_score > 0 and masaref_score > 0:
            # هر دو جدول مرتبط هستند
            if manabe_score > masaref_score:
                table_type = TableType.MANABE
                confidence = min(0.9, manabe_score / (manabe_score + masaref_score))
            elif masaref_score > manabe_score:
                table_type = TableType.MASAREF
                confidence = min(0.9, masaref_score / (manabe_score + masaref_score))
            else:
                table_type = TableType.BOTH
                confidence = 0.5
        elif manabe_score > 0:
            table_type = TableType.MANABE
            confidence = min(0.95, 0.6 + manabe_score * 0.1)
        elif masaref_score > 0:
            table_type = TableType.MASAREF
            confidence = min(0.95, 0.6 + masaref_score * 0.1)
        else:
            # پیش‌فرض: MASAREF (بودجه = هزینه)
            table_type = TableType.MASAREF
            confidence = 0.4
        
        reason = f"MANABE keywords: {matched_keywords['manabe']}, MASAREF keywords: {matched_keywords['masaref']}"
        
        logger.info(f"📊 [TABLE_DETECT] Query: '{query[:50]}...' -> {table_type.value} (confidence: {confidence:.2f})")
        
        return table_type, confidence, reason
    
    async def detect_table_with_llm(self, query: str) -> Tuple[TableType, float, str]:
        """
        تشخیص نوع جدول با کمک LLM برای موارد مبهم
        
        Args:
            query: سوال کاربر
            
        Returns:
            Tuple of (TableType, confidence, reason)
        """
        # ابتدا از روش rule-based استفاده کن
        table_type, confidence, reason = self.detect_table(query)
        
        # اگر confidence کافی است یا LLM موجود نیست، همان را برگردان
        if confidence >= 0.7 or not self.llm_client:
            return table_type, confidence, reason
        
        # استفاده از LLM برای موارد مبهم
        try:
            prompt = f"""سوال زیر درباره بودجه کشور است. تشخیص بده این سوال مربوط به کدام جدول است:

1. MANABE (منابع/درآمد): شامل واگذاری، درآمد، منابع، وصول، حاصل از
2. MASAREF (مصارف/هزینه): شامل برآورد، هزینه، مخارج، مصارف، تملک، اعتبار

سوال: {query}

فقط یکی از این دو کلمه را پاسخ بده: MANABE یا MASAREF"""

            response = await self.llm_client.generate_text(
                prompt=prompt,
                max_tokens=10,
                temperature=0.1
            )
            
            if response and response.success:
                answer = response.text.strip().upper()
                if 'MANABE' in answer:
                    return TableType.MANABE, 0.85, "LLM detected MANABE"
                elif 'MASAREF' in answer:
                    return TableType.MASAREF, 0.85, "LLM detected MASAREF"
        
        except Exception as e:
            logger.warning(f"⚠️ [TABLE_DETECT] LLM fallback failed: {e}")
        
        return table_type, confidence, reason
    
    def _normalize_query(self, query: str) -> str:
        """نرمال‌سازی سوال"""
        # حذف zero-width characters
        query = query.replace('\u200c', ' ').replace('\u200f', '')
        # نرمال‌سازی کاراکترهای عربی/فارسی
        query = query.replace('ي', 'ی').replace('ك', 'ک')
        query = query.replace('ة', 'ه').replace('ۀ', 'ه')
        return query.lower()


class BudgetYearHandler:
    """مدیریت سال و قوانین یارانه"""
    
    # الگوهای معتبر سال
    YEAR_PATTERNS = {
        '1398': ['1398', '98', '398', 'نود و هشت', 'سال نود و هشت'],
        '1399': ['1399', '99', '399', 'نود و نه', 'سال نود و نه'],
        '1400': ['1400', '00', '400', 'چهارصد', 'یکهزار و چهارصد'],
        '1401': ['1401', '01', '401', 'چهارصد و یک', 'یکهزار و چهارصد و یک'],
        '1402': ['1402', '02', '402', 'چهارصد و دو'],
        '1403': ['1403', '03', '403', 'چهارصد و سه']
    }
    
    # قوانین یارانه برای هر سال
    SUBSIDY_RULES = {
        '1399': 'separate',  # یارانه‌ها جدا نمایش داده می‌شوند
        '1400': 'separate',  # یارانه‌ها جدا نمایش داده می‌شوند
        '1401': 'include',   # یارانه‌ها در جمع کل محاسبه می‌شوند
        '1402': 'none',      # قانون خاصی ندارند
        '1403': 'none'       # قانون خاصی ندارند
    }
    
    DEFAULT_YEAR = '1403'
    
    def extract_years(self, query: str) -> List[str]:
        """
        استخراج سال‌ها از سوال
        
        Args:
            query: سوال کاربر
            
        Returns:
            لیست سال‌های شناسایی شده
        """
        years = []
        query_lower = query.lower()
        
        # پیدا کردن range سال
        range_match = re.search(r'(\d{2,4})\s*(?:تا|-)\s*(\d{2,4})', query)
        if range_match:
            start = self._normalize_year(range_match.group(1))
            end = self._normalize_year(range_match.group(2))
            if start and end:
                start_int = int(start)
                end_int = int(end)
                years = [str(y) for y in range(start_int, end_int + 1)]
                return years
        
        # پیدا کردن سال‌های منفرد
        for year, patterns in self.YEAR_PATTERNS.items():
            for pattern in patterns:
                if pattern in query_lower or pattern in query:
                    if year not in years:
                        years.append(year)
        
        # اگر سالی پیدا نشد، سال پیش‌فرض
        if not years:
            years = [self.DEFAULT_YEAR]
            logger.info(f"📅 [YEAR] No year found, using default: {self.DEFAULT_YEAR}")
        
        return years
    
    def _normalize_year(self, year_str: str) -> Optional[str]:
        """نرمال‌سازی سال به فرمت 4 رقمی"""
        year_str = year_str.strip()
        
        # اگر 2 رقمی است
        if len(year_str) == 2:
            year_int = int(year_str)
            if year_int >= 98:
                return f'13{year_str}'
            elif year_int <= 3:
                return f'140{year_str}'
        
        # اگر 3 رقمی است (مثل 400, 401)
        if len(year_str) == 3:
            return f'1{year_str}'
        
        # اگر 4 رقمی است
        if len(year_str) == 4 and year_str.startswith('1'):
            return year_str
        
        return None
    
    def get_subsidy_rule(self, year: str) -> str:
        """
        دریافت قانون یارانه برای سال مشخص
        
        Args:
            year: سال (4 رقمی)
            
        Returns:
            'include' | 'separate' | 'none'
        """
        return self.SUBSIDY_RULES.get(year, 'none')
    
    def needs_subsidy_calculation(self, year: str) -> bool:
        """آیا سال نیاز به محاسبه خاص یارانه دارد؟"""
        return self.get_subsidy_rule(year) in ['include', 'separate']


class BudgetHierarchySearcher:
    """جستجوی سلسله‌مراتبی در جداول بودجه"""
    
    # سطوح سلسله‌مراتبی MANABE
    MANABE_HIERARCHY = [
        ('عنوان دستگاه اصلی', 'عنوان_دستگاه_اصلی'),
        ('عنوان دستگاه اجرایی', 'عنوان_دستگاه_اجرایی')
    ]
    
    # سطوح سلسله‌مراتبی MASAREF (از بالا به پایین)
    MASAREF_HIERARCHY = [
        ('قسمت', 'عنوان_قسمت'),
        ('بخش', 'عنوان_بخش'),
        ('بند', 'عنوان_بند'),
        ('دستگاه اصلی', 'عنوان_دستگاه_اصلی'),
        ('دستگاه اجرایی', 'عنوان_دستگاه_اجرایی'),
        ('جزء', 'عنوان_جزء')
    ]
    
    # کلمات کلیدی برای تشخیص سطح
    LEVEL_KEYWORDS = {
        'قسمت': ['قسمت'],
        'بخش': ['بخش'],
        'بند': ['بند'],
        'جزء': ['جزء', 'جزو'],
        'دستگاه اصلی': ['دستگاه اصلی', 'دستگاه اصلي'],
        'دستگاه اجرایی': ['دستگاه اجرایی', 'دستگاه اجرايي'],
        'دستگاه': ['دستگاه', 'سازمان', 'وزارت', 'نهاد', 'معاونت']
    }
    
    def detect_hierarchy_level(self, query: str) -> Optional[str]:
        """
        تشخیص سطح سلسله‌مراتبی از سوال
        
        Args:
            query: سوال کاربر
            
        Returns:
            نام سطح یا None
        """
        query_lower = query.lower().replace('\u200c', ' ')
        
        # بررسی کلمات کلیدی صریح
        for level, keywords in self.LEVEL_KEYWORDS.items():
            for keyword in keywords:
                # جستجوی دقیق‌تر برای جلوگیری از تطابق اشتباه
                pattern = rf'\b{re.escape(keyword)}\b'
                if re.search(pattern, query_lower):
                    logger.info(f"📊 [HIERARCHY] Detected level: {level} (keyword: {keyword})")
                    return level
        
        return None
    
    def get_search_columns(self, table_type: TableType, level: Optional[str] = None) -> List[str]:
        """
        دریافت ستون‌های جستجو بر اساس نوع جدول و سطح
        
        Args:
            table_type: نوع جدول
            level: سطح سلسله‌مراتبی (اختیاری)
            
        Returns:
            لیست نام ستون‌ها برای جستجو
        """
        if table_type == TableType.MANABE:
            # برای MANABE، همیشه هر دو سطح را جستجو کن
            return ['عنوان_دستگاه_اصلی', 'عنوان_دستگاه_اجرایی']
        
        elif table_type == TableType.MASAREF:
            if level:
                # اگر سطح مشخص شده، فقط آن سطح
                for name, column in self.MASAREF_HIERARCHY:
                    if level in name or name in level:
                        return [column]
            
            # پیش‌فرض: جستجو در دستگاه اصلی و اجرایی
            return ['عنوان_دستگاه_اصلی', 'عنوان_دستگاه_اجرایی']
        
        return []


class BudgetResponseFormatter:
    """فرمت‌دهی پاسخ بودجه"""
    
    def format_masaref_response(
        self,
        entity_name: str,
        year: str,
        data: Dict[str, Any],
        subsidy_rule: str = 'none'
    ) -> str:
        """
        فرمت پاسخ برای جدول MASAREF
        
        Args:
            entity_name: نام دستگاه
            year: سال
            data: داده‌های بودجه
            subsidy_rule: قانون یارانه ('include', 'separate', 'none')
            
        Returns:
            پاسخ فرمت شده
        """
        parts = []
        
        # عنوان
        parts.append(f"📊 گزارش {entity_name} - سال {year}")
        parts.append("")
        
        # سطح سازمانی
        level = data.get('level', 'دستگاه')
        parts.append(f"🏛️ سطح سازمانی: {level}")
        parts.append("")
        
        # اعتبارات هزینه‌ای
        parts.append("💰 اعتبارات هزینه‌ای:")
        parts.append(f"├─ عمومی: {self._format_number(data.get('cost_public', 0))} ریال")
        parts.append(f"├─ متفرقه: {self._format_number(data.get('cost_misc', 0))} ریال")
        parts.append(f"├─ اختصاصی: {self._format_number(data.get('cost_special', 0))} ریال")
        
        if subsidy_rule == 'include':
            parts.append(f"├─ یارانه‌ها: {self._format_number(data.get('cost_subsidy', 0))} ریال")
        
        parts.append(f"└─ جمع کل: {self._format_number(data.get('cost_total', 0))} ریال")
        parts.append("")
        
        # تملک دارایی‌های سرمایه‌ای
        parts.append("🏗️ تملک دارایی‌های سرمایه‌ای:")
        parts.append(f"├─ عمومی: {self._format_number(data.get('capital_public', 0))} ریال")
        parts.append(f"├─ متفرقه: {self._format_number(data.get('capital_misc', 0))} ریال")
        parts.append(f"├─ اختصاصی: {self._format_number(data.get('capital_special', 0))} ریال")
        
        if subsidy_rule == 'include':
            parts.append(f"├─ یارانه‌ها: {self._format_number(data.get('capital_subsidy', 0))} ریال")
        
        parts.append(f"└─ جمع کل: {self._format_number(data.get('capital_total', 0))} ریال")
        parts.append("")
        
        # جمع کل نهایی
        parts.append(f"📈 جمع کل نهایی: {self._format_number(data.get('grand_total', 0))} ریال")
        
        # یارانه‌های جداگانه برای سال‌های 1399-1400
        if subsidy_rule == 'separate':
            parts.append("")
            parts.append(f"⚠️ یارانه‌ها (مستقل): {self._format_number(data.get('total_subsidy', 0))} ریال")
            parts.append("توضیح: یارانه‌ها در این سال در جمع‌کل محاسبه نشده‌اند")
        
        return "\n".join(parts)
    
    def format_manabe_response(
        self,
        entity_name: str,
        year: str,
        data: Dict[str, Any],
        show_breakdown: bool = True
    ) -> str:
        """
        فرمت پاسخ برای جدول MANABE
        
        Args:
            entity_name: نام دستگاه
            year: سال
            data: داده‌های درآمد
            show_breakdown: نمایش تفکیک سازمانی
            
        Returns:
            پاسخ فرمت شده
        """
        parts = []
        
        # عنوان
        parts.append(f"📊 گزارش درآمد {entity_name} - سال {year}")
        parts.append("")
        
        # درآمد عمومی
        parts.append("💵 درآمد عمومی:")
        parts.append(f"├─ ملی: {self._format_number(data.get('public_national', 0))} ریال")
        parts.append(f"├─ استانی: {self._format_number(data.get('public_provincial', 0))} ریال")
        parts.append(f"└─ جمع: {self._format_number(data.get('public_total', 0))} ریال")
        parts.append("")
        
        # درآمد اختصاصی
        parts.append("💼 درآمد اختصاصی:")
        parts.append(f"├─ ملی: {self._format_number(data.get('special_national', 0))} ریال")
        parts.append(f"├─ استانی: {self._format_number(data.get('special_provincial', 0))} ریال")
        parts.append(f"└─ جمع: {self._format_number(data.get('special_total', 0))} ریال")
        parts.append("")
        
        # جمع کل درآمد
        parts.append(f"📈 جمع کل درآمد: {self._format_number(data.get('grand_total', 0))} ریال")
        
        # تفکیک سازمانی
        if show_breakdown and data.get('breakdown'):
            parts.append("")
            parts.append("🔍 تفکیک سازمانی:")
            for item in data['breakdown']:
                parts.append(f"├─ {item['name']}: {self._format_number(item['amount'])} ریال")
        
        return "\n".join(parts)
    
    def format_not_found_response(
        self,
        query: str,
        table_type: TableType,
        searched_keywords: List[str],
        year: str,
        searched_levels: List[str]
    ) -> str:
        """
        فرمت پاسخ برای حالت عدم یافتن نتیجه
        """
        parts = []
        parts.append("❌ نتیجه‌ای یافت نشد")
        parts.append("")
        parts.append("🔍 بررسی‌های انجام شده:")
        parts.append(f"- جدول: {table_type.value.upper()}")
        parts.append(f"- کلمات کلیدی جستجو شده: {', '.join(searched_keywords)}")
        parts.append(f"- سال مورد نظر: {year}")
        parts.append(f"- سطوح بررسی شده: {', '.join(searched_levels)}")
        parts.append("")
        parts.append("💡 پیشنهادات:")
        parts.append("1. املای صحیح نام دستگاه را بررسی کنید")
        parts.append("2. سال دیگری را امتحان کنید")
        parts.append("3. از نام کامل‌تر دستگاه استفاده کنید")
        
        return "\n".join(parts)
    
    def format_multiple_results_response(
        self,
        results: List[Dict[str, Any]]
    ) -> str:
        """
        فرمت پاسخ برای حالت نتایج متعدد
        """
        parts = []
        parts.append("⚠️ چند نتیجه یافت شد - لطفاً دقیق‌تر مشخص کنید:")
        parts.append("")
        
        for i, result in enumerate(results[:10], 1):
            name = result.get('name', 'نامشخص')
            level = result.get('level', 'نامشخص')
            parts.append(f"{i}️⃣ {name} - {level}")
        
        if len(results) > 10:
            parts.append(f"... و {len(results) - 10} نتیجه دیگر")
        
        parts.append("")
        parts.append("💬 لطفاً شماره یا نام کامل را مشخص کنید.")
        
        return "\n".join(parts)
    
    def _format_number(self, value: Any) -> str:
        """فرمت عدد با کاما"""
        if value is None:
            return "0"
        try:
            num = float(value)
            if num >= 1_000_000_000:
                return f"{num/1_000_000_000:,.2f} میلیارد"
            elif num >= 1_000_000:
                return f"{num/1_000_000:,.2f} میلیون"
            elif num >= 1000:
                return f"{num:,.0f}"
            else:
                return f"{num:,.2f}"
        except (ValueError, TypeError):
            return str(value)


class BudgetQueryProcessor:
    """پردازشگر اصلی سوالات بودجه"""
    
    def __init__(self, llm_client=None, database_service=None):
        """
        Args:
            llm_client: کلاینت LLM
            database_service: سرویس دیتابیس
        """
        self.table_detector = BudgetTableDetector(llm_client)
        self.year_handler = BudgetYearHandler()
        self.hierarchy_searcher = BudgetHierarchySearcher()
        self.response_formatter = BudgetResponseFormatter()
        self.llm_client = llm_client
        self.database_service = database_service
    
    def analyze_query(self, query: str) -> BudgetQueryAnalysis:
        """
        تحلیل کامل سوال بودجه
        
        Args:
            query: سوال کاربر
            
        Returns:
            BudgetQueryAnalysis
        """
        # تشخیص نوع جدول
        table_type, confidence, _ = self.table_detector.detect_table(query)
        
        # استخراج سال‌ها
        years = self.year_handler.extract_years(query)
        
        # تشخیص سطح سلسله‌مراتبی
        hierarchy_level = self.hierarchy_searcher.detect_hierarchy_level(query)
        
        # استخراج entity names (از query_analyzer موجود استفاده می‌شود)
        entity_names = self._extract_entity_names(query)
        
        # تشخیص نوع درآمد/هزینه
        income_type = self._detect_income_type(query)
        cost_type = self._detect_cost_type(query)
        
        # قوانین یارانه
        primary_year = years[0] if years else '1403'
        subsidy_rule = self.year_handler.get_subsidy_rule(primary_year)
        needs_subsidy = self.year_handler.needs_subsidy_calculation(primary_year)
        
        return BudgetQueryAnalysis(
            table_type=table_type,
            hierarchy_level=hierarchy_level,
            entity_names=entity_names,
            years=years,
            income_type=income_type,
            cost_type=cost_type,
            needs_subsidy_calculation=needs_subsidy,
            subsidy_rule=subsidy_rule if needs_subsidy else None,
            confidence=confidence
        )
    
    async def analyze_query_async(self, query: str) -> BudgetQueryAnalysis:
        """
        تحلیل کامل سوال بودجه (async با LLM fallback)
        """
        # تشخیص نوع جدول با LLM fallback
        table_type, confidence, _ = await self.table_detector.detect_table_with_llm(query)
        
        # بقیه مثل sync
        years = self.year_handler.extract_years(query)
        hierarchy_level = self.hierarchy_searcher.detect_hierarchy_level(query)
        entity_names = self._extract_entity_names(query)
        income_type = self._detect_income_type(query)
        cost_type = self._detect_cost_type(query)
        
        primary_year = years[0] if years else '1403'
        subsidy_rule = self.year_handler.get_subsidy_rule(primary_year)
        needs_subsidy = self.year_handler.needs_subsidy_calculation(primary_year)
        
        return BudgetQueryAnalysis(
            table_type=table_type,
            hierarchy_level=hierarchy_level,
            entity_names=entity_names,
            years=years,
            income_type=income_type,
            cost_type=cost_type,
            needs_subsidy_calculation=needs_subsidy,
            subsidy_rule=subsidy_rule if needs_subsidy else None,
            confidence=confidence
        )
    
    def get_target_table(self, analysis: BudgetQueryAnalysis) -> str:
        """
        دریافت نام جدول هدف
        
        Args:
            analysis: نتیجه تحلیل
            
        Returns:
            نام جدول در database
        """
        if analysis.table_type == TableType.MANABE:
            return "manabe_sheet1"
        elif analysis.table_type == TableType.MASAREF:
            return "masaref2_sheet1"
        else:
            # پیش‌فرض: MASAREF
            return "masaref2_sheet1"
    
    def get_search_columns(self, analysis: BudgetQueryAnalysis) -> List[str]:
        """
        دریافت ستون‌های جستجو
        
        Args:
            analysis: نتیجه تحلیل
            
        Returns:
            لیست ستون‌ها
        """
        return self.hierarchy_searcher.get_search_columns(
            analysis.table_type,
            analysis.hierarchy_level
        )
    
    def _extract_entity_names(self, query: str) -> List[str]:
        """استخراج نام entity ها از query"""
        # این متد بعداً با query_analyzer یکپارچه می‌شود
        # فعلاً یک پیاده‌سازی ساده
        entities = []
        
        # الگوهای رایج
        patterns = [
            r'(وزارت\s+[\w\s]+?)(?:\s+در|\s+سال|\s+چقدر|$)',
            r'(سازمان\s+[\w\s]+?)(?:\s+در|\s+سال|\s+چقدر|$)',
            r'(نهاد\s+[\w\s]+?)(?:\s+در|\s+سال|\s+چقدر|$)',
            r'(معاونت\s+[\w\s]+?)(?:\s+در|\s+سال|\s+چقدر|$)',
            r'(بانک\s+[\w\s]+?)(?:\s+در|\s+سال|\s+چقدر|$)',
            r'(شرکت\s+[\w\s]+?)(?:\s+در|\s+سال|\s+چقدر|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query)
            for match in matches:
                if match and len(match) > 3:
                    entities.append(match.strip())
        
        return entities
    
    def _detect_income_type(self, query: str) -> Optional[str]:
        """تشخیص نوع درآمد"""
        query_lower = query.lower()
        
        if 'عمومی' in query_lower:
            return 'عمومی'
        elif 'اختصاصی' in query_lower:
            return 'اختصاصی'
        elif 'ملی' in query_lower and 'استانی' not in query_lower:
            return 'ملی'
        elif 'استانی' in query_lower and 'ملی' not in query_lower:
            return 'استانی'
        
        return 'کل'
    
    def _detect_cost_type(self, query: str) -> Optional[str]:
        """تشخیص نوع هزینه"""
        query_lower = query.lower()
        
        if 'جاری' in query_lower or 'هزینه‌ای' in query_lower or 'هزینه ای' in query_lower:
            return 'هزینه‌ای'
        elif 'عمرانی' in query_lower or 'سرمایه‌ای' in query_lower or 'تملک' in query_lower:
            return 'سرمایه‌ای'
        
        return 'کل'


# Singleton instance برای استفاده در سایر ماژول‌ها
_budget_processor_instance: Optional[BudgetQueryProcessor] = None


def get_budget_processor(llm_client=None, database_service=None) -> BudgetQueryProcessor:
    """
    دریافت instance از BudgetQueryProcessor (singleton pattern)
    """
    global _budget_processor_instance
    
    if _budget_processor_instance is None:
        _budget_processor_instance = BudgetQueryProcessor(llm_client, database_service)
    elif llm_client and not _budget_processor_instance.llm_client:
        _budget_processor_instance.llm_client = llm_client
        _budget_processor_instance.table_detector.llm_client = llm_client
    
    return _budget_processor_instance

