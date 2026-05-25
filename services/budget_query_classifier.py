# -*- coding: utf-8 -*-
"""
Budget Query Classifier
دسته‌بندی هوشمند سوالات مالی برای تولید داده‌های chart

این ماژول سوالات را به دسته‌های زیر تقسیم می‌کند:

📊 دسته‌بندی‌های اصلی:

1. درآمد (Income/Revenue):
   - درآمد دستگاه در یک سال
   - درآمد دستگاه در چند سال
   - درآمد تقسیم‌بندی درآمدی (قسمت/بخش/بند) در یک سال
   - درآمد تقسیم‌بندی درآمدی در چند سال

2. مصارف (Expenses/Costs):
   - مصارف دستگاه در یک سال
   - مصارف دستگاه در چند سال

3. مقایسه‌ها (Comparisons):
   - مقایسه درآمد تقسیم‌بندی‌ها در یک سال
   - مقایسه درآمد تقسیم‌بندی‌ها در چند سال
   - مقایسه درآمد دستگاه‌ها در یک سال
   - مقایسه درآمد دستگاه‌ها در چند سال
   - مقایسه مصارف دستگاه‌ها در یک سال
   - مقایسه مصارف دستگاه‌ها در چند سال
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class DataType(Enum):
    """نوع داده: درآمد یا مصارف"""
    INCOME = "income"       # درآمد / منابع
    EXPENSE = "expense"     # مصارف / هزینه
    UNKNOWN = "unknown"


class EntityType(Enum):
    """نوع entity: دستگاه یا تقسیم‌بندی درآمدی"""
    DEVICE = "device"                    # دستگاه اجرایی / دستگاه اصلی
    INCOME_DIVISION = "income_division"  # قسمت / بخش / بند / جزء
    UNKNOWN = "unknown"


class TimeScope(Enum):
    """محدوده زمانی: تک سال یا چند سال"""
    SINGLE_YEAR = "single_year"
    MULTI_YEAR = "multi_year"


class QueryIntent(Enum):
    """نیت سوال: دریافت مقدار یا مقایسه"""
    FETCH = "fetch"           # دریافت مقدار (درآمد X چقدر است)
    COMPARE = "compare"       # مقایسه (درآمد X بیشتر است یا Y)


@dataclass
class BudgetQueryCategory:
    """ساختار دسته‌بندی سوال بودجه"""
    # دسته‌بندی اصلی
    data_type: DataType           # درآمد یا مصارف
    entity_type: EntityType       # دستگاه یا تقسیم‌بندی درآمدی
    time_scope: TimeScope         # تک سال یا چند سال
    query_intent: QueryIntent     # دریافت یا مقایسه
    
    # جزئیات
    years: List[str]              # سال‌های استخراج شده
    entities: List[str]           # entity های استخراج شده
    entity_count: int             # تعداد entity ها
    
    # نام دسته‌بندی انسان‌خوان
    category_name: str            # نام فارسی دسته
    category_code: str            # کد یکتا دسته
    
    # اطلاعات تکمیلی
    hierarchy_level: Optional[str] = None  # سطح سلسله‌مراتبی (قسمت/بخش/بند/جزء)
    income_type: Optional[str] = None      # نوع درآمد (عمومی/اختصاصی/ملی/استانی)
    expense_type: Optional[str] = None     # نوع مصارف (هزینه‌ای/سرمایه‌ای/عمومی)
    
    # امتیاز اطمینان
    confidence: float = 0.0
    
    # اطلاعات chart
    chart_type: str = "bar"       # نوع پیشنهادی chart
    chart_config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.chart_config is None:
            self.chart_config = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """تبدیل به dictionary"""
        result = asdict(self)
        result['data_type'] = self.data_type.value
        result['entity_type'] = self.entity_type.value
        result['time_scope'] = self.time_scope.value
        result['query_intent'] = self.query_intent.value
        return result


class BudgetQueryClassifier:
    """
    دسته‌بندی کننده هوشمند سوالات بودجه
    """
    
    def __init__(self):
        """Initialize classifier"""
        # کلمات کلیدی درآمد/منابع
        self.income_keywords = [
            'درآمد', 'درامد', 'منابع', 'عواید', 'عوايد', 
            'در آمد', 'در امد', 'وصول', 'وصولی'
        ]
        
        # کلمات کلیدی مصارف/هزینه
        self.expense_keywords = [
            'هزینه', 'هزينه', 'مصارف', 'بودجه', 'اعتبار', 'اعتبارات',
            'تملک دارایی', 'تملك دارايي', 'سرمایه‌ای', 'سرمایه ای',
            'هزینه‌ای', 'هزینه ای'
        ]
        
        # کلمات تقسیم‌بندی درآمدی (قسمت/بخش/بند/جزء)
        self.income_division_keywords = [
            'قسمت', 'بخش', 'بند', 'جزء', 'جزو', 'فصل', 'ماده',
            # نام‌های خاص تقسیم‌بندی‌ها
            'مالیات', 'مالیاتی', 'گمرک', 'گمرکی', 'نفت', 'نفتی',
            'عوارض', 'جرائم', 'جرایم', 'واگذاری', 'فروش'
        ]
        
        # کلمات کلیدی مقایسه
        self.comparison_keywords = [
            'مقایسه', 'مقایسه‌ای', 'بیشتر', 'کمتر', 'بالاتر', 'پایین‌تر',
            'افزایش', 'کاهش', 'رشد', 'نسبت به', 'در مقایسه با',
            'تفاوت', 'تغییر', 'بوده یا', 'است یا', 'بیشتری داشته',
            'کدام', 'چه کسی', 'کدام یک'
        ]
        
        # الگوهای regex برای تشخیص
        self.year_pattern = re.compile(
            r'(?:سال(?:های)?(?:\s*)?)?'
            r'(?:13|14)?(\d{2})'
            r'(?:\s*(?:تا|-|الی|و)\s*(?:13|14)?(\d{2}))?'
        )
        
        # الگوهای entity
        # Note: الگوها طوری طراحی شده‌اند که entity های کامل را بگیرند
        self.entity_patterns = [
            # نام دستگاه‌های رایج - با boundary های مناسب
            r'(وزارت\s+\S+)',  # وزارت + یک کلمه
            r'(سازمان\s+\S+(?:\s+\S+)?(?:\s+\S+)?)',  # سازمان + 1-3 کلمه
            r'(شرکت\s+(?:دولتی\s+)?[^،.]+?)(?=\s+(?:در|از|$))',
            r'(بنیاد\s+\S+(?:\s+\S+)?)',
            r'(دانشگاه\s+\S+)',
            r'(نهاد\s+\S+(?:\s+\S+)?)',  # نهاد + 1-2 کلمه
            r'(معاونت\s+\S+(?:\s+\S+)?(?:\s+\S+)?)',
            r'(مرکز\s+\S+(?:\s+\S+)?)',
            r'(ستاد\s+\S+(?:\s+\S+)?(?:\s+\S+)?)',
            r'(صندوق\s+\S+(?:\s+\S+)?)',
            r'(شورای\s+\S+(?:\s+\S+)?(?:\s+\S+)?)',  # شورای + 1-3 کلمه
            r'(هیات\s+\S+(?:\s+\S+)?)',
            r'(پست\s+بانک)',
            r'(فرهنگستان\s+\S+)',
            r'(مجمع\s+\S+(?:\s+\S+)?(?:\s+\S+)?)',
        ]
    
    def normalize_text(self, text: str) -> str:
        """نرمال‌سازی متن"""
        if not text:
            return ''
        # حذف zero-width
        text = text.replace('\u200c', ' ').replace('\u200f', ' ')
        # نرمال‌سازی کاراکترها
        text = text.replace('ي', 'ی').replace('ك', 'ک')
        text = text.replace('ة', 'ه').replace('ۀ', 'ه')
        # اصلاح "در آمد" به "درآمد"
        text = re.sub(r'در\s+ا?مد', 'درآمد', text, flags=re.IGNORECASE)
        # حذف فاصله‌های اضافی
        text = ' '.join(text.split())
        return text
    
    def extract_years(self, query: str) -> List[str]:
        """استخراج سال‌ها از query"""
        years = []
        query_normalized = self.normalize_text(query)
        
        # الگوی range سال
        range_match = re.search(
            r'(?:از\s+)?(?:سال\s+)?(?:های\s+)?(\d{2,4})\s*(?:تا|الی|-|و)\s*(\d{2,4})',
            query_normalized
        )
        if range_match:
            start = range_match.group(1)
            end = range_match.group(2)
            # تبدیل به 4 رقمی
            start = f"13{start}" if len(start) == 2 and int(start) < 50 else (f"14{start}" if len(start) == 2 else start)
            end = f"13{end}" if len(end) == 2 and int(end) < 50 else (f"14{end}" if len(end) == 2 else end)
            # ایجاد range
            try:
                for y in range(int(start), int(end) + 1):
                    years.append(str(y))
            except:
                pass
            return years
        
        # استخراج سال‌های منفرد
        year_matches = re.findall(r'(?:13|14)?\d{2}', query_normalized)
        for match in year_matches:
            if len(match) == 2:
                year = f"13{match}" if int(match) < 50 else f"14{match}"
            else:
                year = match
            if 1390 <= int(year) <= 1410:
                if year not in years:
                    years.append(year)
        
        return sorted(years)
    
    def detect_data_type(self, query: str) -> Tuple[DataType, float]:
        """تشخیص نوع داده: درآمد یا مصارف"""
        query_lower = self.normalize_text(query).lower()
        
        income_score = sum(1 for kw in self.income_keywords if kw in query_lower)
        expense_score = sum(1 for kw in self.expense_keywords if kw in query_lower)
        
        total = income_score + expense_score
        if total == 0:
            return DataType.UNKNOWN, 0.5
        
        if income_score > expense_score:
            confidence = income_score / (total + 1)
            return DataType.INCOME, min(0.95, 0.6 + confidence * 0.4)
        elif expense_score > income_score:
            confidence = expense_score / (total + 1)
            return DataType.EXPENSE, min(0.95, 0.6 + confidence * 0.4)
        else:
            return DataType.UNKNOWN, 0.5
    
    def detect_entity_type(self, query: str, entities: List[str]) -> Tuple[EntityType, Optional[str]]:
        """
        تشخیص نوع entity: دستگاه یا تقسیم‌بندی درآمدی
        
        منطق:
        1. اول بررسی می‌کنیم آیا entity های شناخته شده دستگاه هستند
        2. اگر entity دستگاهی پیدا نشد، بررسی می‌کنیم آیا سوال درباره تقسیم‌بندی درآمدی است
        
        Returns:
            (EntityType, hierarchy_level)
        """
        query_lower = self.normalize_text(query).lower()
        
        # بررسی entity ها برای تعیین نوع - اولویت اول
        device_keywords = [
            'وزارت', 'سازمان', 'شرکت', 'بنیاد', 'دانشگاه', 'نهاد', 'معاونت', 
            'مرکز', 'ستاد', 'صندوق', 'شورای', 'هیات', 'پست بانک', 'فرهنگستان', 'مجمع'
        ]
        
        for entity in entities:
            for kw in device_keywords:
                if kw in entity:
                    return EntityType.DEVICE, None
        
        # اگر entity داریم ولی keyword خاصی نداشت، احتمالاً دستگاه است
        if entities:
            return EntityType.DEVICE, None
        
        # بررسی کلمات کلیدی دستگاه در query
        for kw in device_keywords:
            if kw in query_lower:
                return EntityType.DEVICE, None
        
        # تشخیص تقسیم‌بندی درآمدی - اولویت دوم
        hierarchy_level = None
        division_found = False
        
        # بررسی کلمات کلیدی سلسله‌مراتبی
        if 'قسمت' in query_lower:
            hierarchy_level = 'قسمت'
            division_found = True
        elif 'بخش' in query_lower:
            # "بخش" ممکن است به معنای "تقسیم‌بندی" باشد (بخش مالیاتی) یا "بخشی از"
            # اگر کلمه بعد از "بخش" مربوط به درآمد باشد، تقسیم‌بندی است
            if re.search(r'بخش\s+(مالیات|گمرک|نفت|عواید|جرائم|واگذاری|فروش)', query_lower):
                hierarchy_level = 'بخش'
                division_found = True
        elif 'بند' in query_lower:
            hierarchy_level = 'بند'
            division_found = True
        elif 'جزء' in query_lower or 'جزو' in query_lower:
            hierarchy_level = 'جزء'
            division_found = True
        
        # بررسی کلمات کلیدی مربوط به نوع درآمد (بدون entity خاص)
        income_category_keywords = ['مالیات', 'گمرک', 'نفتی', 'عوارض', 'جرائم', 'واگذاری']
        for kw in income_category_keywords:
            if kw in query_lower and not entities:
                division_found = True
                break
        
        if division_found:
            return EntityType.INCOME_DIVISION, hierarchy_level
        
        return EntityType.UNKNOWN, None
    
    def detect_query_intent(self, query: str, entity_count: int) -> QueryIntent:
        """تشخیص نیت سوال: دریافت یا مقایسه"""
        query_lower = self.normalize_text(query).lower()
        
        # بررسی کلمات کلیدی مقایسه
        for kw in self.comparison_keywords:
            if kw in query_lower:
                return QueryIntent.COMPARE
        
        # اگر بیش از یک entity داریم، احتمالاً مقایسه است
        if entity_count > 1:
            # بررسی الگوهای مقایسه‌ای
            if re.search(r'\bیا\b|\bو\b.*\bو\b', query_lower):
                return QueryIntent.COMPARE
        
        return QueryIntent.FETCH
    
    def extract_entities(self, query: str) -> List[str]:
        """استخراج entity ها از query"""
        entities = []
        query_normalized = self.normalize_text(query)
        
        # استخراج با regex
        for pattern in self.entity_patterns:
            matches = re.findall(pattern, query_normalized)
            entities.extend(matches)
        
        # کلمات اضافی که باید از انتهای entity حذف شوند
        trailing_words = [
            'در سال', 'از سال', 'طی سال', 'سال های', 'سالهای',
            'در', 'از', 'تا', 'و', 'یا', 'با', 'به', 'که',
            'بیشتر', 'کمتر', 'است', 'بوده', 'باشد', 'می باشد'
        ]
        
        # حذف تکرار و تمیز کردن
        seen = set()
        unique_entities = []
        for e in entities:
            e_clean = e.strip()
            
            # حذف کلمات اضافی از انتها
            for word in trailing_words:
                if e_clean.endswith(' ' + word):
                    e_clean = e_clean[:-len(word)-1].strip()
            
            # حذف کلمات اضافی از ابتدا
            for word in ['و ', 'یا ']:
                if e_clean.startswith(word):
                    e_clean = e_clean[len(word):].strip()
            
            if e_clean and e_clean not in seen and len(e_clean) > 2:
                seen.add(e_clean)
                unique_entities.append(e_clean)
        
        return unique_entities
    
    def detect_income_type(self, query: str) -> Optional[str]:
        """تشخیص نوع درآمد"""
        query_lower = self.normalize_text(query).lower()
        
        # نوع درآمد
        if 'اختصاصی' in query_lower:
            if 'ملی' in query_lower:
                return 'ملی_اختصاصی'
            elif 'استانی' in query_lower:
                return 'استانی_اختصاصی'
            return 'اختصاصی'
        elif 'عمومی' in query_lower:
            if 'ملی' in query_lower:
                return 'ملی_عمومی'
            elif 'استانی' in query_lower:
                return 'استانی_عمومی'
            return 'عمومی'
        elif 'ملی' in query_lower:
            return 'ملی'
        elif 'استانی' in query_lower:
            return 'استانی'
        
        return 'کل'
    
    def detect_expense_type(self, query: str) -> Optional[str]:
        """تشخیص نوع مصارف/هزینه"""
        query_lower = self.normalize_text(query).lower()
        
        if 'هزینه ای' in query_lower or 'هزینه‌ای' in query_lower:
            if 'عمومی' in query_lower:
                return 'هزینه_ای_عمومی'
            elif 'اختصاصی' in query_lower:
                return 'هزینه_ای_اختصاصی'
            elif 'متفرقه' in query_lower:
                return 'هزینه_ای_متفرقه'
            return 'هزینه_ای'
        elif 'سرمایه ای' in query_lower or 'سرمایه‌ای' in query_lower or 'تملک دارایی' in query_lower:
            if 'عمومی' in query_lower:
                return 'سرمایه_ای_عمومی'
            elif 'اختصاصی' in query_lower:
                return 'سرمایه_ای_اختصاصی'
            elif 'متفرقه' in query_lower:
                return 'سرمایه_ای_متفرقه'
            return 'سرمایه_ای'
        
        return 'کل'
    
    def generate_category_name(
        self,
        data_type: DataType,
        entity_type: EntityType,
        time_scope: TimeScope,
        query_intent: QueryIntent,
        entity_count: int
    ) -> Tuple[str, str]:
        """
        تولید نام و کد دسته‌بندی
        
        Returns:
            (category_name_fa, category_code)
        """
        # نام فارسی
        parts = []
        
        # نیت
        if query_intent == QueryIntent.COMPARE:
            parts.append("مقایسه")
        
        # نوع داده
        if data_type == DataType.INCOME:
            parts.append("منابع" if query_intent == QueryIntent.COMPARE else "درآمد")
        elif data_type == DataType.EXPENSE:
            parts.append("مصارف")
        else:
            parts.append("بودجه")
        
        # تعداد entity (فقط برای مقایسه)
        if query_intent == QueryIntent.COMPARE and entity_count > 0:
            parts.append(f"{entity_count}" if entity_count > 1 else "چند")
        
        # نوع entity
        if entity_type == EntityType.DEVICE:
            parts.append("دستگاه")
        elif entity_type == EntityType.INCOME_DIVISION:
            parts.append("تقسیم‌بندی درآمدی")
        
        # زمان
        if time_scope == TimeScope.SINGLE_YEAR:
            parts.append("در یک سال")
        else:
            parts.append("در چند سال")
        
        category_name = " ".join(parts)
        
        # کد یکتا
        code_parts = []
        code_parts.append("CMP" if query_intent == QueryIntent.COMPARE else "FET")
        code_parts.append("INC" if data_type == DataType.INCOME else "EXP")
        code_parts.append("DEV" if entity_type == EntityType.DEVICE else "DIV")
        code_parts.append("1Y" if time_scope == TimeScope.SINGLE_YEAR else "MY")
        if entity_count > 1:
            code_parts.append(f"E{entity_count}")
        
        category_code = "_".join(code_parts)
        
        return category_name, category_code
    
    def suggest_chart_config(
        self,
        query_intent: QueryIntent,
        time_scope: TimeScope,
        entity_count: int,
        years: List[str]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        پیشنهاد نوع و تنظیمات chart
        
        Returns:
            (chart_type, chart_config)
        """
        # تعیین نوع chart
        if query_intent == QueryIntent.COMPARE:
            if entity_count > 1:
                if time_scope == TimeScope.MULTI_YEAR:
                    # مقایسه چند entity در چند سال -> grouped bar یا line
                    chart_type = "grouped_bar"
                    config = {
                        "x_axis": "سال",
                        "y_axis": "مبلغ",
                        "group_by": "entity",
                        "show_legend": True,
                        "show_values": True
                    }
                else:
                    # مقایسه چند entity در یک سال -> bar یا pie
                    chart_type = "bar"
                    config = {
                        "x_axis": "entity",
                        "y_axis": "مبلغ",
                        "show_values": True,
                        "show_percentage": entity_count <= 5
                    }
            else:
                # مقایسه یک entity در چند سال -> line
                chart_type = "line"
                config = {
                    "x_axis": "سال",
                    "y_axis": "مبلغ",
                    "show_trend": True,
                    "show_growth_rate": True
                }
        else:
            # FETCH
            if time_scope == TimeScope.MULTI_YEAR:
                # درآمد/مصارف یک entity در چند سال -> line یا bar
                chart_type = "line"
                config = {
                    "x_axis": "سال",
                    "y_axis": "مبلغ",
                    "show_trend": True,
                    "show_growth_rate": len(years) > 1
                }
            else:
                # درآمد/مصارف یک entity در یک سال -> single value یا breakdown
                chart_type = "single_value"
                config = {
                    "show_unit": True,
                    "show_comparison_to_prev_year": True
                }
        
        return chart_type, config
    
    def classify(self, query: str) -> BudgetQueryCategory:
        """
        دسته‌بندی سوال بودجه
        
        Args:
            query: سوال کاربر
            
        Returns:
            BudgetQueryCategory با تمام اطلاعات دسته‌بندی
        """
        logger.info(f"🔍 [CLASSIFIER] Classifying query: {query[:80]}...")
        
        # استخراج اطلاعات پایه
        years = self.extract_years(query)
        entities = self.extract_entities(query)
        
        # تشخیص نوع داده
        data_type, data_confidence = self.detect_data_type(query)
        
        # تشخیص نوع entity
        entity_type, hierarchy_level = self.detect_entity_type(query, entities)
        
        # تشخیص محدوده زمانی
        time_scope = TimeScope.MULTI_YEAR if len(years) > 1 else TimeScope.SINGLE_YEAR
        
        # تشخیص نیت
        query_intent = self.detect_query_intent(query, len(entities))
        
        # تشخیص نوع درآمد/مصارف
        income_type = self.detect_income_type(query) if data_type == DataType.INCOME else None
        expense_type = self.detect_expense_type(query) if data_type == DataType.EXPENSE else None
        
        # تولید نام و کد دسته
        category_name, category_code = self.generate_category_name(
            data_type, entity_type, time_scope, query_intent, len(entities)
        )
        
        # پیشنهاد chart
        chart_type, chart_config = self.suggest_chart_config(
            query_intent, time_scope, len(entities), years
        )
        
        # محاسبه confidence
        confidence = data_confidence
        if entities:
            confidence = min(confidence + 0.1, 0.95)
        if years:
            confidence = min(confidence + 0.1, 0.95)
        
        # ایجاد نتیجه
        result = BudgetQueryCategory(
            data_type=data_type,
            entity_type=entity_type,
            time_scope=time_scope,
            query_intent=query_intent,
            years=years,
            entities=entities,
            entity_count=len(entities),
            category_name=category_name,
            category_code=category_code,
            hierarchy_level=hierarchy_level,
            income_type=income_type,
            expense_type=expense_type,
            confidence=confidence,
            chart_type=chart_type,
            chart_config=chart_config
        )
        
        logger.info(f"✅ [CLASSIFIER] Category: {category_name} ({category_code})")
        logger.info(f"   Data: {data_type.value}, Entity: {entity_type.value}, Time: {time_scope.value}")
        logger.info(f"   Years: {years}, Entities: {entities}")
        logger.info(f"   Chart: {chart_type}, Confidence: {confidence:.2f}")
        
        return result
    
    def get_sql_template(self, category: BudgetQueryCategory, table_name: str) -> Dict[str, Any]:
        """
        دریافت template SQL بر اساس دسته‌بندی
        
        Returns:
            {
                'select': List[str],
                'from': str,
                'where': List[str],
                'group_by': List[str],
                'order_by': List[str],
                'chart_columns': List[str]  # ستون‌های مورد نیاز برای chart
            }
        """
        template = {
            'select': [],
            'from': table_name,
            'where': [],
            'group_by': [],
            'order_by': [],
            'chart_columns': []
        }
        
        # تعیین ستون‌های SELECT بر اساس دسته
        if category.data_type == DataType.INCOME:
            amount_col = self._get_income_column(category.income_type, table_name)
            template['select'].append(f'SUM(CAST({amount_col} AS DOUBLE PRECISION)) AS total_amount')
            template['chart_columns'].append('total_amount')
            
            if category.entity_type == EntityType.DEVICE:
                template['select'].extend(['"عنوان_دستگاه_اجرایی"', '"عنوان_دستگاه_اصلی"'])
                template['group_by'].extend(['"عنوان_دستگاه_اجرایی"', '"عنوان_دستگاه_اصلی"'])
                template['chart_columns'].append('عنوان_دستگاه_اجرایی')
            else:
                template['select'].extend(['"عنوان_بخش"', '"عنوان_بند"'])
                template['group_by'].extend(['"عنوان_بخش"', '"عنوان_بند"'])
                template['chart_columns'].append('عنوان_بخش')
        
        elif category.data_type == DataType.EXPENSE:
            amount_col = self._get_expense_column(category.expense_type, table_name)
            template['select'].append(f'SUM(CAST({amount_col} AS DOUBLE PRECISION)) AS total_amount')
            template['chart_columns'].append('total_amount')
            
            template['select'].extend(['"عنوان_دستگاه_اجرايي"', '"عنوان_دستگاه_اصلي"'])
            template['group_by'].extend(['"عنوان_دستگاه_اجرايي"', '"عنوان_دستگاه_اصلي"'])
            template['chart_columns'].append('عنوان_دستگاه_اجرايي')
        
        # افزودن سال به SELECT و GROUP BY اگر چند سال داریم
        if category.time_scope == TimeScope.MULTI_YEAR:
            template['select'].append('"سال"')
            template['group_by'].append('"سال"')
            template['order_by'].append('"سال" ASC')
            template['chart_columns'].append('سال')
        
        # فیلتر سال
        if category.years:
            year_list = ', '.join([f"'{y}'" for y in category.years])
            template['where'].append(f'"سال" IN ({year_list})')
        
        # ORDER BY
        template['order_by'].append('total_amount DESC')
        
        return template
    
    def _get_income_column(self, income_type: Optional[str], table_name: str) -> str:
        """تعیین ستون درآمد بر اساس نوع"""
        is_manabe3 = 'manabe3' in table_name
        
        mapping = {
            'ملی_عمومی': '"ملي_در_آمد_عمومي"' if is_manabe3 else '"در_آمد_عمومي_ملي"',
            'استانی_عمومی': '"استاني_در_آمد_عمومي"' if is_manabe3 else '"در_آمد_عمومي_استاني"',
            'عمومی': '"جمع_در_آمد_عمومي"',
            'ملی_اختصاصی': '"ملي_در_آمد_اختصاصي"' if is_manabe3 else '"در_آمد_اختصاصي_ملي"',
            'استانی_اختصاصی': '"استاني_در_آمد_اختصاصي"' if is_manabe3 else '"در_آمد_اختصاصي_استاني"',
            'اختصاصی': '"جمع_در_آمد_اختصاصي"',
            'ملی': '"ملي_جمع_کل"' if is_manabe3 else '"جمع_کل_ملي"',
            'استانی': '"استاني_جمع_کل"' if is_manabe3 else '"جمع_کل_استاني"',
            'کل': '"جمع_کل"'
        }
        return mapping.get(income_type, '"جمع_کل"')
    
    def _get_expense_column(self, expense_type: Optional[str], table_name: str) -> str:
        """تعیین ستون مصارف بر اساس نوع"""
        mapping = {
            'هزینه_ای_عمومی': '"براورد_اعتبارات_هزینه_ای_عمومی"',
            'هزینه_ای_اختصاصی': '"براورد_اعتبارات_هزینه_ای_اختصاصی"',
            'هزینه_ای_متفرقه': '"برآورد_اعتبارات_هزینه_ای_متفرقه"',
            'هزینه_ای': '"جمع_براورد_اعتبارات_هزینه_ای"',
            'سرمایه_ای_عمومی': '"براورد_تملك_دارايي_هاي_سرمايه_اي_ع"',
            'سرمایه_ای_اختصاصی': '"براورد_تملك_دارايي_هاي_سرمايه_اي_ا"',
            'سرمایه_ای_متفرقه': '"براورد_تملك_دارايي_هاي_سرمايه_اي_م"',
            'سرمایه_ای': '"جمع_برآورد_تملك_دارايي_هاي_سرمايه_"',
            'کل': '"جمع_كل"'
        }
        return mapping.get(expense_type, '"جمع_كل"')


# ========== Global Instance ==========
_classifier_instance = None

def get_budget_query_classifier() -> BudgetQueryClassifier:
    """دریافت instance سینگلتون"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = BudgetQueryClassifier()
    return _classifier_instance


def classify_budget_query(query: str) -> Dict[str, Any]:
    """
    تابع کمکی برای دسته‌بندی سریع سوال
    
    Args:
        query: سوال کاربر
        
    Returns:
        dict با اطلاعات دسته‌بندی
    """
    classifier = get_budget_query_classifier()
    category = classifier.classify(query)
    return category.to_dict()
