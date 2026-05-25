# -*- coding: utf-8 -*-
"""
Filter Extractor
استخراج فیلترهای قابل اعمال بر اساس query و database structure
"""

import logging
from typing import List, Dict, Any, Optional, Set
import re

logger = logging.getLogger(__name__)


class FilterExtractor:
    """
    استخراج فیلترهای قابل اعمال برای کاربر
    مثال فیلترها:
    - سال‌های موجود
    - انواع درآمد/هزینه
    - دستگاه‌های والد
    - محدوده مبالغ
    """
    
    def __init__(self, database_service=None):
        """Initialize filter extractor"""
        self.database_service = database_service
        
        # تعریف فیلترهای استاندارد بر اساس domain
        self.filter_definitions = {
            "financial": {
                "year": {
                    "type": "multiselect",
                    "label": "سال",
                    "field": "سال",
                    "description": "انتخاب سال‌های مورد نظر"
                },
                "income_type": {
                    "type": "select",
                    "label": "نوع درآمد",
                    "field": "type",
                    "options": [
                        {"value": "national", "label": "درآمد ملی"},
                        {"value": "provincial", "label": "درآمد استانی"},
                        {"value": "exclusive", "label": "درآمد اختصاصی"},
                        {"value": "general", "label": "درآمد عمومی"},
                        {"value": "total", "label": "جمع کل"}
                    ],
                    "description": "نوع درآمد مورد نظر"
                },
                "parent_entity": {
                    "type": "multiselect",
                    "label": "دستگاه والد",
                    "field": "عنوان_دستگاه_اصلی",
                    "description": "دستگاه‌های اصلی"
                },
                "entity": {
                    "type": "autocomplete",
                    "label": "دستگاه اجرایی",
                    "field": "عنوان_دستگاه",
                    "description": "نام دستگاه اجرایی"
                },
                "amount_range": {
                    "type": "range",
                    "label": "محدوده مبلغ (ریال)",
                    "field": "amount",
                    "description": "فیلتر بر اساس مبلغ"
                },
                "income_source": {
                    "type": "multiselect",
                    "label": "منبع درآمد",
                    "field": "عنوان_جزء",
                    "description": "منابع کسب درآمد"
                }
            }
        }
    
    async def extract_filters(
        self,
        original_query: str,
        database_results: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None,
        query_analysis: Optional[Dict[str, Any]] = None,
        domain: str = "financial"
    ) -> List[Dict[str, Any]]:
        """
        استخراج فیلترهای قابل اعمال
        
        Args:
            original_query: سوال اصلی
            database_results: نتایج database
            collection_name: نام collection
            query_analysis: تحلیل query
            domain: دامنه (financial, ...)
            
        Returns:
            لیست فیلترها با مقادیر قابل انتخاب
        """
        try:
            filters = []
            
            # 1. فیلترهای مبتنی بر query analysis
            if query_analysis:
                query_filters = self._extract_from_query_analysis(
                    query_analysis, domain
                )
                filters.extend(query_filters)
            
            # 2. فیلترهای مبتنی بر database results
            if database_results and database_results.get('results'):
                result_filters = await self._extract_from_results(
                    database_results, collection_name, domain
                )
                filters.extend(result_filters)
            
            # 3. فیلترهای مبتنی بر database schema
            if collection_name and self.database_service:
                schema_filters = await self._extract_from_schema(
                    collection_name, query_analysis, domain
                )
                filters.extend(schema_filters)
            
            # حذف تکراری‌ها و مرتب‌سازی بر اساس اهمیت
            unique_filters = self._deduplicate_and_prioritize(filters)
            
            return unique_filters
            
        except Exception as e:
            logger.error(f"Failed to extract filters: {e}")
            return []
    
    def _extract_from_query_analysis(
        self,
        query_analysis: Dict[str, Any],
        domain: str
    ) -> List[Dict[str, Any]]:
        """استخراج فیلترها از تحلیل query"""
        filters = []
        
        if domain != "financial":
            return filters
        
        # 1. فیلتر سال
        years = query_analysis.get('years', [])
        if years:
            # اگر سال خاصی در query است، range پیشنهاد بده
            year_filter = {
                "id": "year",
                "type": "multiselect",
                "label": "سال",
                "field": "سال",
                "description": "انتخاب سال‌های مورد نظر",
                "current_value": years,
                "options": self._generate_year_options(years),
                "priority": 1
            }
            filters.append(year_filter)
        
        # 2. فیلتر نوع درآمد
        income_type = query_analysis.get('income_type', '')
        if income_type or 'درآمد' in query_analysis.get('original_query', ''):
            income_filter = {
                "id": "income_type",
                "type": "select",
                "label": "نوع درآمد",
                "field": "income_type",
                "description": "تغییر نوع درآمد",
                "current_value": self._map_income_type_to_value(income_type),
                "options": [
                    {"value": "national", "label": "درآمد ملی", "selected": False},
                    {"value": "provincial", "label": "درآمد استانی", "selected": False},
                    {"value": "exclusive", "label": "درآمد اختصاصی", "selected": False},
                    {"value": "general", "label": "درآمد عمومی", "selected": False},
                    {"value": "total", "label": "جمع کل", "selected": False}
                ],
                "priority": 2
            }
            # علامت‌گذاری current value
            for opt in income_filter['options']:
                if opt['value'] == income_filter['current_value']:
                    opt['selected'] = True
            filters.append(income_filter)
        
        # 3. فیلتر entity (اگر entity خاصی در query بود)
        entity_filter_text = query_analysis.get('entity_filter', '')
        if entity_filter_text:
            entity_filter = {
                "id": "entity",
                "type": "autocomplete",
                "label": "دستگاه اجرایی",
                "field": "عنوان_دستگاه",
                "description": "جستجو و انتخاب دستگاه دیگر",
                "current_value": entity_filter_text,
                "placeholder": "نام دستگاه را تایپ کنید...",
                "priority": 3
            }
            filters.append(entity_filter)
        
        # 4. فیلتر query category
        query_category = query_analysis.get('query_category', '')
        if query_category == 'top_n':
            # برای top-n، limit قابل تغییر است
            aggregation = query_analysis.get('aggregation', {})
            current_limit = aggregation.get('limit', 10)
            
            limit_filter = {
                "id": "limit",
                "type": "select",
                "label": "تعداد نتایج",
                "field": "limit",
                "description": "تعداد دستگاه‌های نمایش داده شده",
                "current_value": current_limit,
                "options": [
                    {"value": 5, "label": "5 مورد برتر"},
                    {"value": 10, "label": "10 مورد برتر"},
                    {"value": 20, "label": "20 مورد برتر"},
                    {"value": 50, "label": "50 مورد برتر"}
                ],
                "priority": 4
            }
            filters.append(limit_filter)
        
        return filters
    
    async def _extract_from_results(
        self,
        database_results: Dict[str, Any],
        collection_name: Optional[str],
        domain: str
    ) -> List[Dict[str, Any]]:
        """استخراج فیلترها از نتایج database"""
        filters = []
        
        try:
            results = database_results.get('results', [])
            columns = database_results.get('columns', [])
            
            if not results:
                return filters
            
            # 1. فیلتر parent entity (اگر ستون parent وجود دارد)
            if 'عنوان_دستگاه_اصلی' in columns or 'عنوان_دستگاه_اصلي_دستگاه_اجرايي' in columns:
                parent_col = 'عنوان_دستگاه_اصلی' if 'عنوان_دستگاه_اصلی' in columns else 'عنوان_دستگاه_اصلي_دستگاه_اجرايي'
                
                # استخراج unique parents
                parents = set()
                for row in results:
                    parent = row.get(parent_col)
                    if parent and isinstance(parent, str) and parent.strip():
                        parents.add(parent.strip())
                
                if parents and len(parents) > 1:  # فقط اگر بیش از 1 parent داشته باشیم
                    parent_filter = {
                        "id": "parent_entity",
                        "type": "multiselect",
                        "label": "دستگاه والد",
                        "field": parent_col,
                        "description": "فیلتر بر اساس دستگاه والد",
                        "options": [
                            {"value": p, "label": p, "selected": False}
                            for p in sorted(parents)
                        ],
                        "priority": 5
                    }
                    filters.append(parent_filter)
            
            # 2. فیلتر محدوده مبلغ
            amount_columns = ['total_amount', 'جمع_کل', 'جمع_كل', 'مبلغ']
            amount_col = None
            for col in amount_columns:
                if col in columns:
                    amount_col = col
                    break
            
            if amount_col:
                amounts = []
                for row in results:
                    amount = row.get(amount_col)
                    if amount and isinstance(amount, (int, float)) and amount > 0:
                        amounts.append(amount)
                
                if amounts:
                    min_amount = min(amounts)
                    max_amount = max(amounts)
                    
                    # فقط اگر range معنی‌داری داشته باشد
                    if max_amount > min_amount * 2:
                        amount_filter = {
                            "id": "amount_range",
                            "type": "range",
                            "label": "محدوده مبلغ (ریال)",
                            "field": amount_col,
                            "description": "فیلتر بر اساس مبلغ",
                            "min": int(min_amount),
                            "max": int(max_amount),
                            "current_min": int(min_amount),
                            "current_max": int(max_amount),
                            "step": self._calculate_step(min_amount, max_amount),
                            "format": "ریال",
                            "priority": 6
                        }
                        filters.append(amount_filter)
            
        except Exception as e:
            logger.warning(f"Failed to extract filters from results: {e}")
        
        return filters
    
    async def _extract_from_schema(
        self,
        collection_name: str,
        query_analysis: Optional[Dict[str, Any]],
        domain: str
    ) -> List[Dict[str, Any]]:
        """استخراج فیلترها از schema database"""
        filters = []
        
        try:
            if not self.database_service:
                return filters
            
            # دریافت available years از database
            years_filter = await self._get_available_years(collection_name)
            if years_filter:
                filters.append(years_filter)
            
            # دریافت income sources اگر query درباره sources است
            if query_analysis and query_analysis.get('query_type') == 'sources':
                sources_filter = await self._get_income_sources(collection_name)
                if sources_filter:
                    filters.append(sources_filter)
            
        except Exception as e:
            logger.warning(f"Failed to extract filters from schema: {e}")
        
        return filters
    
    async def _get_available_years(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """دریافت سال‌های موجود در database"""
        try:
            # Query برای دریافت unique years
            sql = """
                SELECT DISTINCT "سال"
                FROM incomes_sheet1
                WHERE "سال" IS NOT NULL
                ORDER BY "سال" DESC
                LIMIT 20
            """
            
            result = self.database_service.execute_sql_query(
                sql,
                collection_name=collection_name
            )
            
            if result.get('success') and result.get('rows'):
                years = [row.get('سال') for row in result['rows'] if row.get('سال')]
                years = [y for y in years if y and str(y).isdigit()]
                
                if years:
                    return {
                        "id": "available_years",
                        "type": "multiselect",
                        "label": "سال‌های موجود",
                        "field": "سال",
                        "description": "سال‌های موجود در سیستم",
                        "options": [
                            {"value": str(y), "label": str(y), "selected": False}
                            for y in sorted(years, reverse=True)
                        ],
                        "priority": 1
                    }
        except Exception as e:
            logger.warning(f"Failed to get available years: {e}")
        
        return None
    
    async def _get_income_sources(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """دریافت منابع درآمد موجود"""
        try:
            sql = """
                SELECT DISTINCT "عنوان_جزء"
                FROM incomes_sheet1
                WHERE "عنوان_جزء" IS NOT NULL
                  AND "عنوان_جزء" != ''
                LIMIT 50
            """
            
            result = self.database_service.execute_sql_query(
                sql,
                collection_name=collection_name
            )
            
            if result.get('success') and result.get('rows'):
                sources = [row.get('عنوان_جزء') for row in result['rows'] if row.get('عنوان_جزء')]
                sources = [s.strip() for s in sources if s and isinstance(s, str)]
                
                if sources:
                    return {
                        "id": "income_source",
                        "type": "multiselect",
                        "label": "منبع درآمد",
                        "field": "عنوان_جزء",
                        "description": "منابع کسب درآمد",
                        "options": [
                            {"value": s, "label": s, "selected": False}
                            for s in sorted(set(sources))[:20]
                        ],
                        "priority": 7
                    }
        except Exception as e:
            logger.warning(f"Failed to get income sources: {e}")
        
        return None
    
    def _generate_year_options(self, current_years: List[int]) -> List[Dict[str, Any]]:
        """تولید options برای فیلتر سال"""
        if not current_years:
            return []
        
        # محدوده: 3 سال قبل تا 2 سال بعد
        min_year = min(current_years)
        max_year = max(current_years)
        
        start_year = max(1395, min_year - 3)
        end_year = min(1405, max_year + 2)
        
        options = []
        for year in range(start_year, end_year + 1):
            options.append({
                "value": str(year),
                "label": str(year),
                "selected": year in current_years
            })
        
        return sorted(options, key=lambda x: x['value'], reverse=True)
    
    def _map_income_type_to_value(self, income_type: str) -> str:
        """تبدیل income_type به value مناسب"""
        mapping = {
            "ملی_اختصاصی": "exclusive",
            "ملی_عمومی": "general",
            "ملی": "national",
            "استانی": "provincial",
            "کل": "total"
        }
        return mapping.get(income_type, "total")
    
    def _calculate_step(self, min_val: float, max_val: float) -> int:
        """محاسبه step مناسب برای range slider"""
        range_size = max_val - min_val
        
        if range_size < 1000:
            return 10
        elif range_size < 10000:
            return 100
        elif range_size < 100000:
            return 1000
        elif range_size < 1000000:
            return 10000
        elif range_size < 10000000:
            return 100000
        elif range_size < 100000000:
            return 1000000
        else:
            # برای اعداد خیلی بزرگ
            return int(range_size / 100)  # 100 قدم
    
    def _deduplicate_and_prioritize(
        self,
        filters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """حذف تکراری‌ها و مرتب‌سازی بر اساس priority"""
        if not filters:
            return []
        
        # حذف تکراری بر اساس id
        unique_filters = {}
        for f in filters:
            filter_id = f.get('id')
            if filter_id:
                # اگر تکراری بود، اولویت بالاتر را نگه دار
                if filter_id not in unique_filters:
                    unique_filters[filter_id] = f
                else:
                    existing_priority = unique_filters[filter_id].get('priority', 999)
                    new_priority = f.get('priority', 999)
                    if new_priority < existing_priority:
                        unique_filters[filter_id] = f
        
        # مرتب‌سازی بر اساس priority
        sorted_filters = sorted(
            unique_filters.values(),
            key=lambda x: x.get('priority', 999)
        )
        
        return sorted_filters


