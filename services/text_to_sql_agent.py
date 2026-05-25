# -*- coding: utf-8 -*-
"""
Text-to-SQL Agent
Agent تبدیل پرسش طبیعی به SQL Query
"""

import logging
from typing import Dict, Any, Optional, List
import re

from services.qwen_client import QwenClient
from services.database_service import DatabaseService
from services.query_analyzer import QueryAnalyzer
from processors.schema_analyzer import SchemaAnalyzer

logger = logging.getLogger(__name__)


class TextToSQLAgent:
    """Agent تبدیل پرسش به SQL"""
    
    def __init__(
        self,
        qwen_client: QwenClient,
        database_service: DatabaseService,
        enable_sql_validation: bool = True
    ):
        self.qwen_client = qwen_client
        self.database_service = database_service
        self.query_analyzer = QueryAnalyzer()
        self.schema_analyzer = SchemaAnalyzer(database_service)
        self.enable_sql_validation = enable_sql_validation
        self.entity_mapper = None  # 🆕 Entity mapper for collection-specific entity resolution
    
    def set_entity_mapper(self, entity_mapper):
        """تنظیم entity mapper برای collection مورد نظر"""
        self.entity_mapper = entity_mapper
    
    def _detect_table_type(self, query: str) -> str:
        """تشخیص اینکه سوال درباره هزینه است یا درآمد"""
        # Normalize query - حذف فاصله‌های اضافی و normalize کردن
        query_normalized = query.replace('‌', ' ').replace('\u200c', ' ')
        query_normalized = re.sub(r'در\s+ا\s*مد', 'درآمد', query_normalized, flags=re.IGNORECASE)
        query_normalized = re.sub(r'در\s+امد', 'درآمد', query_normalized, flags=re.IGNORECASE)
        query_lower = query_normalized.lower()
        
        # کلمات کلیدی مربوط به هزینه (مصارف = هزینه‌ها)
        cost_keywords = ['هزینه', 'هزينه', 'اعتبار', 'خرج', 'بودجه', 'مصارف', 'تملک دارایی', 'تملك دارايي']
        # کلمات کلیدی مربوط به درآمد (منابع = درآمد)
        income_keywords = ['درآمد', 'درامد', 'عواید', 'عوايد', 'منابع', 'در امد']
        
        # شمارش تعداد کلمات کلیدی
        cost_count = sum(1 for kw in cost_keywords if kw in query_lower)
        income_count = sum(1 for kw in income_keywords if kw in query_lower)
        
        # اگر هزینه بیشتر بود
        if cost_count > income_count:
            return 'costs'
        # اگر درآمد بیشتر بود یا مساوی (default)
        return 'incomes'
    
    def _get_costs_table_name(self, collection_name: str) -> Optional[str]:
        """
        پیدا کردن نام جدول هزینه‌ها (مصارف)
        اولویت: masaref3_sheet1 (جدیدترین)، سپس masaref_sheet1، سپس costs_sheet1
        """
        columns_map = self.database_service.get_collection_columns(collection_name)
        
        # بررسی masaref3_sheet1 (جدول جدیدترین)
        if 'masaref3_sheet1' in columns_map:
            return 'masaref3_sheet1'
        
        # بررسی masaref_sheet1
        if 'masaref_sheet1' in columns_map:
            return 'masaref_sheet1'
        
        # بررسی costs_sheet1 (جدول قدیمی)
        if 'costs_sheet1' in columns_map:
            return 'costs_sheet1'
        
        return None
    
    def _get_income_table_name(self, collection_name: str) -> Optional[str]:
        """
        پیدا کردن نام جدول درآمد/منابع
        اولویت: manabe3_sheet1 (نسخه جدید)، سپس manabe_sheet1، سپس incomes_sheet1
        """
        columns_map = self.database_service.get_collection_columns(collection_name)
        
        if 'manabe3_sheet1' in columns_map:
            return 'manabe3_sheet1'
        if 'manabe_sheet1' in columns_map:
            return 'manabe_sheet1'
        if 'incomes_sheet1' in columns_map:
            return 'incomes_sheet1'
        
        return None
    
    def _get_income_device_column(self, income_table: str) -> str:
        """ستون نام دستگاه اجرایی در جدول درآمد"""
        # در manabe3/manabe ستون عنوان_دستگاه_اجرایی هست نه عنوان_دستگاه
        if income_table and 'manabe' in income_table:
            return '"عنوان_دستگاه_اجرایی"'
        return '"عنوان_دستگاه"'
    
    def _get_income_parent_column(self, income_table: str) -> str:
        """ستون نام دستگاه اصلی در جدول درآمد"""
        return '"عنوان_دستگاه_اصلی"'
    
    def _adapt_entity_filter_for_income(self, entity_filter: str, income_table: str) -> str:
        """تبدیل entity_filter به فرمت مناسب جدول درآمد"""
        if not entity_filter or not income_table:
            return entity_filter
        if 'manabe' in income_table:
            # عنوان_دستگاه → عنوان_دستگاه_اجرایی در manabe tables
            return entity_filter.replace('"عنوان_دستگاه"', '"عنوان_دستگاه_اجرایی"')
        return entity_filter
    
    def _detect_table_type_with_year_check(self, query: str, years: List[str], collection_name: str) -> str:
        """
        تشخیص نوع جدول با بررسی وجود سال در جدول
        اگر جدول اصلی سال مورد نظر را نداشته باشد، به جدول دیگر fallback می‌کند
        """
        preferred_type = self._detect_table_type(query)
        
        if not years:
            return preferred_type
        
        # بررسی وجود سال در جدول ترجیحی
        columns_map = self.database_service.get_collection_columns(collection_name)
        costs_table = self._get_costs_table_name(collection_name)
        
        income_table = self._get_income_table_name(collection_name)
        
        if preferred_type == 'costs' and costs_table:
            # بررسی وجود سال در جدول هزینه (masaref یا costs)
            if self._check_years_exist_in_table(costs_table, years):
                return 'costs'
            # fallback به incomes/manabe اگر سال در costs وجود نداشت
            if income_table and self._check_years_exist_in_table(income_table, years):
                logger.info(f"⚠️ Years {years} not found in {costs_table}, falling back to {income_table}")
                return 'incomes'
        
        elif preferred_type == 'incomes' and income_table:
            # بررسی وجود سال در جدول درآمد (manabe یا incomes)
            if self._check_years_exist_in_table(income_table, years):
                return 'incomes'
            # fallback به costs اگر سال در incomes وجود نداشت
            if costs_table and self._check_years_exist_in_table(costs_table, years):
                logger.info(f"⚠️ Years {years} not found in {income_table}, falling back to {costs_table}")
                return 'costs'
        
        return preferred_type
    
    def _check_years_exist_in_table(self, table_name: str, years: List[str]) -> bool:
        """بررسی وجود سال‌ها در جدول مشخص"""
        try:
            year_list = ', '.join([f"'{year}'" for year in years])
            sql = f'SELECT COUNT(*) FROM "{table_name}" WHERE "سال" IN ({year_list}) LIMIT 1'
            
            # استفاده مستقیم از connection به جای execute_sql_query
            import psycopg2
            from config.settings import Settings
            settings = Settings()
            conn = psycopg2.connect(
                host=settings.database.postgres_host,
                port=settings.database.postgres_port,
                user=settings.database.postgres_user,
                password=settings.database.postgres_password,
                database=settings.database.postgres_db
            )
            cur = conn.cursor()
            cur.execute(sql)
            result = cur.fetchone()
            cur.close()
            conn.close()
            
            if result:
                count = result[0]
                logger.debug(f"Years {years} in {table_name}: count={count}")
                return count > 0
            return False
        except Exception as e:
            logger.warning(f"Error checking years in {table_name}: {e}")
            return False
    
    async def generate_sql(
        self,
        user_query: str,
        collection_name: str,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """تولید SQL از پرسش کاربر"""
        try:
            logger.info(f"🤖 Generating SQL for query: {user_query[:100]}")

            specialized_sql = self._build_specialized_sql(user_query, collection_name)
            if specialized_sql:
                logger.info("✅ Using specialized SQL heuristic")
                validation_result = self.schema_analyzer.validate_sql_query(specialized_sql, collection_name)
                if validation_result["valid"]:
                    return {
                        "success": True,
                        "sql": specialized_sql,
                        "warnings": validation_result.get("warnings", [])
                    }
                logger.warning(f"Specialized SQL validation failed, falling back to LLM: {validation_result.get('errors')}" )
            
            # دریافت schema description
            schema_description = self.schema_analyzer.get_collection_schema_description(collection_name)
            
            if not schema_description:
                return {
                    "success": False,
                    "error": "No database schema found for this collection",
                    "sql": None
                }
            
            # بررسی سریع اینکه آیا vLLM در دسترس است
            # اگر در دسترس نباشد، به query_analyzer fallback می‌کنیم
            try:
                is_available = await self.qwen_client.is_available()
                if not is_available:
                    logger.warning("⚠️ vLLM service unavailable, falling back to query_analyzer for SQL generation")
                    # Fallback to query_analyzer-based SQL generation
                    # این کار در متدهای دیگر انجام می‌شود
                    return {
                        "success": False,
                        "error": "vLLM service unavailable, using fallback SQL generation",
                        "sql": None
                    }
            except Exception as health_check_error:
                logger.warning(f"⚠️ vLLM health check failed: {health_check_error}, falling back to query_analyzer")
                return {
                    "success": False,
                    "error": "vLLM health check failed, using fallback SQL generation",
                    "sql": None
                }
            
            # ساخت prompt برای Qwen
            prompt = self._build_sql_generation_prompt(user_query, schema_description, collection_name)
            
            # تولید SQL با Qwen
            response = await self.qwen_client.generate_text(
                prompt=prompt,
                system_prompt=self._get_system_prompt(),
                max_tokens=512,
                temperature=0.1  # کم برای دقت بیشتر
            )
            
            if not response.success:
                # اگر error مربوط به connection است، warning بده نه error
                if "connection" in str(response.error).lower() or "unavailable" in str(response.error).lower():
                    logger.warning(f"⚠️ SQL generation failed (service unavailable): {response.error}")
                else:
                    logger.error(f"❌ SQL generation failed: {response.error}")
                return {
                    "success": False,
                    "error": response.error or "SQL generation failed",
                    "sql": None
                }
            
            # استخراج SQL از پاسخ
            sql_query = self._extract_sql_from_response(response.text)
            
            if not sql_query:
                return {
                    "success": False,
                    "error": "Could not extract SQL query from response",
                    "sql": None,
                    "raw_response": response.text
                }
            
            # اعتبارسنجی SQL
            validation_result = self.schema_analyzer.validate_sql_query(sql_query, collection_name)
            
            if not validation_result["valid"]:
                # تلاش مجدد با اصلاح خطاها
                if max_retries > 0:
                    logger.warning(f"SQL validation failed, retrying... Errors: {validation_result['errors']}")
                    
                    # ساخت prompt اصلاح شده
                    correction_prompt = self._build_correction_prompt(
                        user_query,
                        schema_description,
                        sql_query,
                        validation_result["errors"]
                    )
                    
                    correction_response = await self.qwen_client.generate_text(
                        prompt=correction_prompt,
                        system_prompt=self._get_system_prompt(),
                        max_tokens=512,
                        temperature=0.1
                    )
                    
                    if correction_response.success:
                        corrected_sql = self._extract_sql_from_response(correction_response.text)
                        if corrected_sql:
                            # اعتبارسنجی مجدد
                            validation_result = self.schema_analyzer.validate_sql_query(corrected_sql, collection_name)
                            if validation_result["valid"]:
                                sql_query = corrected_sql
                            else:
                                return {
                                    "success": False,
                                    "error": "SQL validation failed after correction",
                                    "sql": sql_query,
                                    "errors": validation_result["errors"]
                                }
                    else:
                        return {
                            "success": False,
                            "error": "SQL validation failed",
                            "sql": sql_query,
                            "errors": validation_result["errors"]
                        }
                else:
                    return {
                        "success": False,
                        "error": "SQL validation failed",
                        "sql": sql_query,
                        "errors": validation_result["errors"]
                    }
            
            logger.info(f"✅ Generated SQL: {sql_query[:200]}")
            
            return {
                "success": True,
                "sql": sql_query,
                "warnings": validation_result.get("warnings", [])
            }
            
        except Exception as e:
            logger.error(f"❌ SQL generation failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "sql": None
            }
    
    def _build_sql_generation_prompt(self, user_query: str, schema_description: str, collection_name: str) -> str:
        """ساخت prompt برای تولید SQL"""
        
        # IMPORTANT: اگر component_filter وجود دارد، آن را به prompt اضافه می‌کنیم
        # تا LLM از exact phrase استفاده کند
        analysis = self.query_analyzer.analyze_query(user_query)
        component_hint = ""
        if analysis.get('income_component') and analysis['filters'].get('component_filter'):
            component = analysis['income_component']
            component_hint = f"""
⚠️ IMPORTANT - برای component '{component}':
- حتماً از EXACT PHRASE استفاده کنید: ILIKE '%{component}%'
- هرگز از AND conditions برای کلمات جداگانه استفاده نکنید (مثل ILIKE '%مراکز%' AND ILIKE '%اموزشی%')
- برای چند ستون، از OR استفاده کنید: (TRANSLATE("عنوان_جزء", ...) ILIKE '%{component}%' OR TRANSLATE("عنوان_بخش", ...) ILIKE '%{component}%')
"""
        
        # Add column usage hints based on collection type
        column_hints = ""
        if any(t in schema_description for t in ["incomes_sheet1", "costs_sheet1", "masaref_sheet1", "masaref3_sheet1", "manabe3_sheet1", "manabe_sheet1"]):
            column_hints = """
# راهنمای استفاده از ستون‌ها:
- برای جستجوی نام سازمان/دستگاه/نهاد/موسسه/بنیاد: از ستون "عنوان_دستگاه" استفاده کنید
- برای جستجوی دستگاه اصلی/وزارتخانه: از ستون "عنوان_دستگاه_اصلی" استفاده کنید
- "عنوان_بخش" شامل دسته‌بندی درآمدها/هزینه‌هاست (مثل "بخش اول: درآمدهاي مالياتي") نه نام سازمان
- "عنوان_بند" و "عنوان_جزء" شامل جزئیات تفصیلی دسته‌بندی هستند
- برای درآمد ملی: "ملی_جمع_کل" یا "ملی_در_آمد_عمومی" یا "ملی_در_آمد_اختصاصی"
- برای درآمد استانی: "استانی_جمع_کل" یا "استانی_در_آمد_عمومی" یا "استانی_در_آمد_اختصاصی"
- برای هزینه جاری: "جمع_براورد_اعتبارات_هزینه_ای"
- برای هزینه عمرانی/سرمایه‌ای: "جمع_تملك_دارايي_هاي_سرمايه_اي"
- برای سال: از ستون "سال" استفاده کنید (مقادیر مثل '1398', '1403')
"""
        
        prompt = f"""شما یک متخصص SQL هستید. بر اساس schema زیر، یک SQL query بنویسید که پاسخ سوال کاربر را بدهد.

# Schema پایگاه داده:
{schema_description}
{column_hints}
{component_hint}
# سوال کاربر:
{user_query}

# دستورالعمل‌ها:
1. فقط یک SQL query بنویسید (بدون توضیحات اضافی)
2. از SELECT استفاده کنید
3. برای جستجوی متنی فارسی از ILIKE استفاده کنید
4. ستون‌هایی که شامل فاصله یا کاراکتر غیرلاتین هستند را داخل "" قرار بدهید
5. اگر روی ستون عددی از ILIKE استفاده می‌کنید، حتماً CAST(column AS TEXT) بنویسید
6. نام جداول و ستون‌ها را دقیقاً همانطور که در schema آمده استفاده کنید
7. پاسخ را فقط در یک خط بنویسید (بدون خطوط اضافی)
8. اگر سوال شامل بیشترین/کمترین/پر هزینه‌ترین/کم هزینه‌ترین یا عباراتی مانند "بیشترین بودجه" بود، حتماً ستون‌های عددی مرتبط را با SUM یا مناسب‌ترین تابع تجمعی جمع بزنید، آن‌ها را در SELECT با یک نام مستعار (مانند total_amount) برگردانید، بر اساس همان مقدار مرتب کنید و با LIMIT 1 نتیجهٔ نهایی را به‌دست آورید.
9. ⚠️ برای عبارات چندکلمه‌ای (مثل "مراکز اموزشی رفاهی")، همیشه از exact phrase استفاده کنید: ILIKE '%عبارت کامل%' و هرگز از AND conditions برای کلمات جداگانه استفاده نکنید.

# SQL Query:"""
        return prompt
    
    def _build_correction_prompt(
        self,
        user_query: str,
        schema_description: str,
        incorrect_sql: str,
        errors: List[str]
    ) -> str:
        """ساخت prompt برای تصحیح SQL"""
        prompt = f"""SQL query قبلی شما خطا داشت. لطفاً آن را تصحیح کنید.

# Schema پایگاه داده:
{schema_description}

# سوال کاربر:
{user_query}

# SQL نادرست قبلی:
{incorrect_sql}

# خطاها:
{chr(10).join(f'- {error}' for error in errors)}

# نکات مهم:
- ستون‌های دارای فاصله یا کاراکتر فارسی را داخل "" بنویسید
- برای استفاده از ILIKE روی ستون‌های عددی از CAST(column AS TEXT) استفاده کنید

# SQL Query تصحیح شده:"""
        return prompt
    
    def _get_system_prompt(self) -> str:
        """System prompt برای LLM"""
        return """شما یک متخصص SQL هستید که می‌توانید پرسش‌های طبیعی را به SQL query تبدیل کنید.
باید فقط SQL query را برگردانید، بدون توضیحات اضافی.
از دستورات SELECT استفاده کنید، نام ستون‌های فارسی یا دارای فاصله را داخل "" قرار دهید و برای استفاده از ILIKE روی ستون‌های عددی حتماً از CAST(column AS TEXT) استفاده کنید.
اگر سوال به بیشترین/کمترین مقدار یا پر هزینه‌ترین/کم هزینه‌ترین اشاره داشت، ستون‌های عددی مرتبط را با SUM یا MAX/MIN جمع‌بندی کنید، نتیجه را مرتب کنید و فقط سطر(های) نهایی را با LIMIT محدود نمایید."""
    
    def _extract_sql_from_response(self, response_text: str) -> Optional[str]:
        """استخراج SQL از پاسخ LLM"""
        # حذف فضاهای اضافی
        response_text = response_text.strip()
        
        # پیدا کردن SQL در پاسخ
        # حالت 1: اگر کل پاسخ یک SQL است
        if response_text.upper().startswith('SELECT'):
            sql = response_text.strip()
            # حذف علامت‌های اضافی
            if sql.endswith(';'):
                sql = sql[:-1].strip()
            return sql
        
        # حالت 2: اگر SQL در کد بلاک است
        sql_pattern = r'```(?:sql)?\s*(SELECT.*?)(?:```|$)'
        match = re.search(sql_pattern, response_text, re.DOTALL | re.IGNORECASE)
        if match:
            sql = match.group(1).strip()
            sql = sql.rstrip(';')
            return sql
        
        # حالت 3: جستجوی SELECT در متن
        select_match = re.search(r'(SELECT.*?)(?:[;\n]|$)', response_text, re.DOTALL | re.IGNORECASE)
        if select_match:
            sql = select_match.group(1).strip()
            sql = sql.rstrip(';')
            return sql
        
        return None

    def _rewrite_entity_filter(self, entity_filter: str, target_column: str) -> str:
        """بازنویسی شرط مربوط به نام دستگاه برای یک ستون مشخص"""
        if not entity_filter:
            return entity_filter
        adapted = entity_filter
        for placeholder in ('"عنوان_دستگاه"', '"عنوان_دستگاه_اصلی"'):
            adapted = adapted.replace(placeholder, target_column)
        return adapted

    def _build_combined_entity_filter(self, entity_filter: str, target_columns: List[str]) -> str:
        """ساخت شرط ترکیبی که چند ستون مختلف را پوشش می‌دهد"""
        if not entity_filter:
            return entity_filter
        unique_columns: List[str] = []
        for column in target_columns:
            if column not in unique_columns:
                unique_columns.append(column)
        rewritten_filters = [
            f"({self._rewrite_entity_filter(entity_filter, column)})"
            for column in unique_columns
        ]
        return " OR ".join(rewritten_filters) if rewritten_filters else entity_filter

    def _tokenize_phrase(self, phrase: str) -> List[str]:
        tokens = re.findall(r'[آ-یA-Za-z0-9]+', phrase or '')
        normalized_tokens: List[str] = []
        for token in tokens:
            normalized = token.translate(self.query_analyzer.char_normalization_map).strip()
            if not normalized:
                continue
            lowered = normalized.lower()
            if len(lowered) <= 1:
                continue
            if lowered in self.query_analyzer.stop_words:
                continue
            if normalized not in normalized_tokens:
                normalized_tokens.append(normalized)
        return normalized_tokens

    def _build_hierarchy_phrase_clause(self, column_expr: str, phrase: str) -> str:
        """
        ساخت clause برای جستجوی عبارات چندکلمه‌ای
        
        نکته مهم: فقط از عبارت کامل استفاده می‌کنیم تا false positive نداشته باشیم.
        مثلاً برای 'وزارت کشور'، فقط '%وزارت کشور%' استفاده می‌شود،
        نه '%وزارت%' AND '%کشور%' که باعث match شدن 'وزارت بهداشت ... کشور' می‌شود.
        
        بهبود: حذف خط تیره و فاصله‌های اضافی برای جستجوی انعطاف‌پذیرتر
        مثلاً "آموزشی رفاهی" باید "آموزشي - رفاهي" را هم پیدا کند
        """
        translation_source = 'يكيۀةأإٱآئ'
        translation_target = 'یکیهههااای'
        # حذف خط تیره و فاصله‌های اضافی از column
        normalized_column = (
            f"REGEXP_REPLACE(REPLACE(REPLACE(REPLACE(TRANSLATE({column_expr}, '{translation_source}', '{translation_target}'), '\u200c', ' '), '\u200f', ' '), '-', ' '), '\\s+', ' ', 'g')"
        )
        # حذف خط تیره و فاصله‌های اضافی از phrase
        cleaned_phrase = phrase.replace('\u200c', ' ').replace('\u200f', ' ').replace('-', ' ')
        cleaned_phrase = ' '.join(cleaned_phrase.split())  # normalize multiple spaces
        safe_phrase = cleaned_phrase.replace("'", "''")
        # فقط از عبارت کامل استفاده می‌کنیم (exact phrase matching)
        # این باعث می‌شود که false positive نداشته باشیم
        return f"{normalized_column} ILIKE '%{safe_phrase}%'"

    def _detect_income_hierarchy_context(
        self,
        phrase: str,
        years: List[str],
        collection_name: str
    ) -> Optional[Dict[str, Any]]:
        if not phrase:
            return None

        hierarchy_levels = [
            ('"عنوان_قسمت"', 'عنوان_قسمت'),
            ('"عنوان_بخش"', 'عنوان_بخش'),
            ('"عنوان_بند"', 'عنوان_بند'),
            ('"عنوان_دستگاه_اصلی"', 'عنوان_دستگاه_اصلی'),
            ('"عنوان_دستگاه"', 'عنوان_دستگاه'),
            ('"عنوان_جزء"', 'عنوان_جزء')
        ]

        year_filter = ""
        if years:
            year_list = ', '.join([f"'{year}'" for year in years])
            year_filter = f"TRANSLATE(\"سال\", 'يكيۀة', 'یکیهه') IN ({year_list})"

        for idx, (column_expr, alias) in enumerate(hierarchy_levels):
            match_clause = self._build_hierarchy_phrase_clause(column_expr, phrase)
            where_parts = [f"({match_clause})"]
            if year_filter:
                where_parts.append(year_filter)
            where_sql = " AND ".join(where_parts)
            _income_tbl = self._get_income_table_name(collection_name) or 'manabe3_sheet1'
            count_sql = f"SELECT COUNT(*) AS match_count FROM {_income_tbl} WHERE {where_sql}"
            result = self.database_service.execute_sql_query(
                count_sql,
                collection_name=collection_name
            )
            if not result.get("success"):
                continue
            rows = result.get("rows") or result.get("results") or []
            if not rows:
                continue
            count_value = rows[0].get("match_count")
            if count_value is None:
                count_value = rows[0].get("count") or rows[0].get("COUNT")
            try:
                count_numeric = float(count_value)
            except (TypeError, ValueError):
                count_numeric = 0.0
            if count_numeric > 0:
                select_exprs = [
                    f'{expr} AS "{alias_name}"'
                    for expr, alias_name in hierarchy_levels[:idx + 1]
                ]
                group_columns = [expr for expr, _ in hierarchy_levels[:idx + 1]]
                return {
                    "match_clause": match_clause,
                    "select_exprs": select_exprs,
                    "group_columns": group_columns
                }

        return None

    def _build_hierarchy_entity_filter(
        self,
        entity_names: List[str],
        device_column: str,
        parent_column: str,
        table_name: str,
        collection_name: str,
        years: List[str]
    ) -> Optional[str]:
        """
        ساخت entity filter با رعایت hierarchy:
        1. ابتدا parent_column را چک کن
        2. اگر نتیجه داشت، فقط از parent_column استفاده کن
        3. اگر نتیجه نداشت، از device_column استفاده کن
        """
        logger.info(f"🔍 [HIERARCHY_FILTER] Called with entity_names={entity_names}")
        if not entity_names:
            return None
        
        def _normalize_entity_for_sql(entity: str) -> str:
            """
            نرمال‌سازی entity در سمت Python قبل از ارسال به SQL.
            مشکلاتی مثل هیئت→هيات که TRANSLATE نمی‌تواند حل کند را برطرف می‌کند.
            همچنین حالتی که ئ قبلاً به ی تبدیل شده (هییت → هیات) را هم پوشش می‌دهد.
            """
            import re as _re_ent
            text = entity.strip()
            # جایگزینی ئ (U+0626) که در برخی کلمات مثل هیئت به‌جای هيات به‌کار می‌رود
            # هیئت → هيات  (ی+ئ+ت → ی+ا+ت)
            text = text.replace('ئت', 'ات')   # هیئت → هیات
            text = text.replace('ئ', 'ا')     # سایر موارد ئ
            # حالتی که ئ قبلاً توسط normalize به ی تبدیل شده: هییت → هیات
            # الگوی خاص: ییت (هیئت که به هییت تبدیل شده) → یات
            text = text.replace('ییت', 'یات')
            # نرمال‌سازی فضاهای اضافی
            text = _re_ent.sub(r'\s+', ' ', text).strip()
            return text
        
        # نرمال‌سازی entity_names در Python قبل از ارسال به SQL
        normalized_entity_names = [_normalize_entity_for_sql(e) for e in entity_names]
        safe_entities = [entity.replace("'", "''") for entity in normalized_entity_names]
        
        # ساخت year filter
        year_filter = ""
        if years:
            year_list = ', '.join([f"'{year}'" for year in years])
            year_filter = f" AND TRANSLATE(\"سال\", 'يكiۀة', 'یکیهه') IN ({year_list})"
        
        # کلمات عمومی که نباید در keyword search باشند
        _skip_kw = {'و', 'در', 'از', 'به', 'با', 'که', 'این', 'آن', 'یا', 'امور',
                    'سال', 'جمع', 'کل', 'مجموع', 'جهت', 'برای', 'بین', 'کلیه'}
        
        def _translate_cond(col, phrase):
            """ساخت ILIKE با TRANSLATE برای یک phrase"""
            return f"TRANSLATE({col}, 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{phrase}%', 'يكيۀةأإٱآ', 'یکیهههااا')"
        
        def _kw_cond(col, entity):
            """ساخت condition با AND بین کلمات کلیدی برای fuzzy matching"""
            import re as _re2
            words = [w for w in _re2.split(r'\s+', entity) if w and w not in _skip_kw and len(w) >= 2]
            key_words = [w for w in words if len(w) > 2][:4] or words[:3]
            if not key_words:
                return f"TRANSLATE({col}, 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{entity}%', 'يكيۀةأإٱآ', 'یکیهههااا')"
            parts = [
                f"TRANSLATE({col}, 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{kw}%', 'يكيۀةأإٱآ', 'یکیهههااا')"
                for kw in key_words
            ]
            return '(' + ' AND '.join(parts) + ')'
        
        # ── مرحله 0: اگر چند entity_name داریم، ترکیب همه را به عنوان یک عبارت واحد چک کن ──
        # مثلاً entity_names=['هیئت','عالی','گزینش'] را به صورت AND condition چک کن
        # این از مشکل تطابق 'عالی' به‌تنهایی جلوگیری می‌کند
        if len(safe_entities) > 1:
            combined_and_cond = ' AND '.join(
                _translate_cond(parent_column, se) for se in safe_entities
            )
            combined_sql = f'''
                SELECT COUNT(*) as cnt FROM {table_name}
                WHERE ({combined_and_cond})
                {year_filter}
            '''
            try:
                result = self.database_service.execute_sql_query(combined_sql, collection_name=collection_name)
                rows_res = result.get("rows") or result.get("results") or []
                count = rows_res[0].get("cnt", 0) if rows_res else 0
                if result.get("success") and count > 0:
                    logger.info(f"✅ Found {count} rows in parent_column (combined AND) for {entity_names}")
                    return f"({combined_and_cond})"
            except Exception as e:
                logger.warning(f"⚠️ Error checking combined entity in parent: {e}")
            
            # ترکیب همه entity_names به یک عبارت و چک کردن keyword-AND
            all_words = []
            for se in safe_entities:
                import re as _re_comb
                words = [w for w in _re_comb.split(r'\s+', se) if w and w not in _skip_kw and len(w) > 2]
                all_words.extend(words)
            all_words = all_words[:5]  # حداکثر 5 کلمه
            if all_words:
                kw_combined_cond = ' AND '.join(_translate_cond(parent_column, w) for w in all_words)
                kw_combined_sql = f'''
                    SELECT COUNT(*) as cnt FROM {table_name}
                    WHERE ({kw_combined_cond})
                    {year_filter}
                '''
                try:
                    result = self.database_service.execute_sql_query(kw_combined_sql, collection_name=collection_name)
                    rows_res = result.get("rows") or result.get("results") or []
                    count = rows_res[0].get("cnt", 0) if rows_res else 0
                    if result.get("success") and count > 0:
                        logger.info(f"✅ Found {count} rows in parent_column (combined keywords AND) for {entity_names}")
                        return f"({kw_combined_cond})"
                except Exception as e:
                    logger.warning(f"⚠️ Error checking combined keywords in parent: {e}")
        
        # برای هر entity، ابتدا parent را چک کن (exact phrase)
        for safe_entity in safe_entities:
            parent_check_sql = f'''
                SELECT COUNT(*) as cnt FROM {table_name}
                WHERE TRANSLATE({parent_column}, 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_entity}%', 'يكيۀةأإٱآ', 'یکیهههااا')
                {year_filter}
            '''
            try:
                result = self.database_service.execute_sql_query(parent_check_sql, collection_name=collection_name)
                rows_res = result.get("rows") or result.get("results") or []
                count = rows_res[0].get("cnt", 0) if rows_res else 0
                if result.get("success") and count > 0:
                    logger.info(f"✅ Found {count} rows in parent_column (exact) for '{safe_entity}'")
                    entity_conditions = [
                        f"TRANSLATE({parent_column}, 'يكiۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{se}%', 'يكiۀةأإٱآ', 'یکیهههااا')"
                        for se in safe_entities
                    ]
                    return f"({' OR '.join(entity_conditions)})"
            except Exception as e:
                logger.warning(f"⚠️ Error checking parent column: {e}")
        
        # Fuzzy fallback: جستجو با کلمات کلیدی در parent
        for safe_entity in safe_entities:
            kw_sql = f'''
                SELECT COUNT(*) as cnt FROM {table_name}
                WHERE {_kw_cond(parent_column, safe_entity)}
                {year_filter}
            '''
            try:
                result = self.database_service.execute_sql_query(kw_sql, collection_name=collection_name)
                rows_res = result.get("rows") or result.get("results") or []
                count = rows_res[0].get("cnt", 0) if rows_res else 0
                if result.get("success") and count > 0:
                    logger.info(f"✅ Found {count} rows in parent_column (keyword) for '{safe_entity}'")
                    entity_conditions = [_kw_cond(parent_column, se) for se in safe_entities]
                    return f"({' OR '.join(entity_conditions)})"
            except Exception as e:
                logger.warning(f"⚠️ Error checking parent (keyword): {e}")
        
        # اگر در parent نتیجه نداشت، از هر دو استفاده کن (OR)
        logger.info(f"ℹ️ No results in parent_column for {entity_names}, using both parent and device")
        entity_conditions = []
        for safe_entity in safe_entities:
            entity_conditions.append(
                f"((TRANSLATE({device_column}, 'يكiۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_entity}%', 'يكiۀةأإٱآ', 'یکیهههااا')) "
                f"OR (TRANSLATE({parent_column}, 'يكiۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_entity}%', 'يكiۀةأإٱآ', 'یکیهههااا')))"
            )
        return f"({' OR '.join(entity_conditions)})"

    def _build_specialized_sql(self, user_query: str, collection_name: str) -> Optional[str]:
        """
        ساخت SQL تخصصی با استفاده از QueryAnalyzer
        این method بر اساس query_category تصمیم می‌گیرد
        """
        query_normalized = user_query.replace('‌', ' ').replace('\u200c', ' ')
        
        # تحلیل کامل query
        analysis = self.query_analyzer.analyze_query(query_normalized, collection_name)
        
        logger.info(f"🎯 [SPEC_SQL] Query Category: {analysis['query_category']}, entity_names={analysis.get('entity_names')}, entity_filter_len={len(analysis['filters'].get('entity_filter') or '')}")
        
        # بررسی جداول موجود - استفاده از helper ها
        income_table = self._get_income_table_name(collection_name)
        has_incomes = income_table is not None
        costs_table = self._get_costs_table_name(collection_name)
        has_costs = costs_table is not None
        
        logger.info(f"📊 Tables: costs={costs_table}, income={income_table}")
        
        # استخراج سال‌ها برای بررسی وجود در جداول
        years = analysis.get('years', [])
        
        # انتخاب strategy بر اساس category
        if analysis['query_category'] == 'cross_table':
            if has_incomes and has_costs:
                return self._build_cross_table_sql(analysis, collection_name)
        
        elif analysis['query_category'] == 'comparison':
            # سوالات مقایسه‌ای (جدید!) - با بررسی وجود سال در جدول
            table_type = self._detect_table_type_with_year_check(query_normalized, years, collection_name)
            comparison_sql = self._build_comparison_sql(analysis, collection_name, table_type)
            if comparison_sql:
                return comparison_sql
        
        elif analysis['query_category'] == 'breakdown':
            if has_incomes:
                return self._build_breakdown_sql(analysis, collection_name)
        
        elif analysis['query_category'] == 'top_n':
            # تشخیص جدول بر اساس محتوای query با بررسی وجود سال
            table_type = self._detect_table_type_with_year_check(query_normalized, years, collection_name)
            
            if table_type == 'costs' and has_costs:
                return self._build_top_n_sql(analysis, collection_name, 'costs')
            elif table_type == 'incomes' and has_incomes:
                return self._build_top_n_sql(analysis, collection_name, 'incomes')
            # fallback: اگر جدول مورد نظر نبود، جدول دیگر را امتحان کن
            elif has_incomes:
                return self._build_top_n_sql(analysis, collection_name, 'incomes')
            elif has_costs:
                return self._build_top_n_sql(analysis, collection_name, 'costs')
        
        elif analysis['query_category'] == 'simple_sum':
            # بررسی وجود سال در جدول قبل از انتخاب
            table_type = self._detect_table_type_with_year_check(query_normalized, years, collection_name)
            logger.info(f"🔄 simple_sum: detected table_type={table_type} for years={years}")
            
            if table_type == 'costs' and has_costs:
                costs_sql = self._build_costs_specialized_sql(analysis, collection_name, user_query)
                if costs_sql:
                    return costs_sql
            
            # اگر table_type = 'incomes' است، از جدول manabe استفاده کن
            if table_type == 'incomes' and has_incomes:
                logger.info(f"🔄 Using {income_table} for income query")
                incomes_sql = self._build_generic_incomes_sql(analysis, collection_name)
                if incomes_sql:
                    return incomes_sql
            
            # اگر هنوز SQL نداریم، سعی کن با کلمات کلیدی
            incomes_sql = self._build_incomes_specialized_sql(query_normalized, collection_name)
            if incomes_sql:
                return incomes_sql
            
            # آخرین fallback به costs
            if has_costs:
                costs_sql = self._build_costs_specialized_sql(analysis, collection_name, user_query)
                if costs_sql:
                    return costs_sql
        
        # fallback: legacy cost heuristic
        query_lower = query_normalized.lower()
        if 'پر هزینه' in query_lower or 'پر هزينه' in query_lower or 'بیشترین هزینه' in query_lower:
            if costs_table:
                import re as _re
                year_match = _re.search(r'13\d{2}|14\d{2}', query_lower)
                year_filter = ""
                if year_match:
                    year_value = year_match.group(0)
                    year_filter = f"WHERE \"سال\" = '{year_value}'"
                    parent_col = '"عنوان_دستگاه_اصلي"'
                select_clause = (
                    f'SELECT {parent_col} AS "عنوان_دستگاه_اصلی", '
                    '"عنوان_دستگاه_اجرايي" AS "عنوان_دستگاه", '
                    'SUM(CAST("جمع_كل" AS DOUBLE PRECISION)) AS "مجموع_هزینه", '
                    'SUM(CAST("جمع_براورد_اعتبارات_هزینه_ای" AS DOUBLE PRECISION)) AS "جمع_هزینه_های_جاری", '
                    'SUM(CAST("جمع_تملك_دارايي_هاي_سرمايه_اي" AS DOUBLE PRECISION)) AS "جمع_هزینه_های_سرمایه_ای"'
                )
                where_clause = year_filter if year_filter else ''
                group_clause = f'GROUP BY {parent_col}, "عنوان_دستگاه_اجرايي"'
                order_clause = 'ORDER BY "مجموع_هزینه" DESC'
                sql = f"{select_clause} FROM {costs_table} {where_clause} {group_clause} {order_clause} LIMIT 5"
                return sql
        
        return None

    def _build_generic_incomes_sql(
        self,
        analysis: Dict[str, Any],
        collection_name: str
    ) -> Optional[str]:
        """
        ساخت SQL برای جدول درآمد (manabe3_sheet1 یا manabe_sheet1) بدون بررسی کلمات کلیدی درآمد.
        این method زمانی استفاده می‌شود که سال مورد نظر در جدول هزینه وجود ندارد.
        """
        income_table = self._get_income_table_name(collection_name)
        if not income_table:
            return None
        
        table_name = income_table
        device_column = self._get_income_device_column(income_table)
        parent_column = self._get_income_parent_column(income_table)
        
        # استفاده از income_type برای تعیین ستون مبلغ
        income_type = analysis.get('income_type')
        if income_type:
            total_column = self._determine_income_column_from_type(income_type, income_table)
        else:
            total_column = '"جمع_کل"'
        
        where_conditions: List[str] = []
        
        # Entity filter - adapt column names for income table
        entity_filter = analysis['filters'].get('entity_filter')
        if entity_filter:
            entity_filter = self._adapt_entity_filter_for_income(entity_filter, income_table)
            where_conditions.append(f"({entity_filter})")
        else:
            entity_names = analysis.get('entity_names') or []
            if entity_names:
                # 🆕 Hierarchy-aware entity filter
                hierarchy_filter = self._build_hierarchy_entity_filter(
                    entity_names,
                    device_column,
                    parent_column,
                    table_name,
                    collection_name,
                    analysis['years']
                )
                if hierarchy_filter:
                    where_conditions.append(hierarchy_filter)
        
        # Year filter
        if analysis['years']:
            year_list = ', '.join([f"'{year}'" for year in analysis['years']])
            where_conditions.append(f"TRANSLATE(\"سال\", 'يكيۀة', 'یکیهه') IN ({year_list})")
        
        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
        
        # Select clause
        select_clause = (
            f'SELECT SUM(COALESCE(CAST({total_column} AS DOUBLE PRECISION), 0)) AS total_amount, '
            f'{device_column}, {parent_column}'
        )
        
        group_clause = f'GROUP BY {device_column}, {parent_column}' if entity_filter or analysis.get('entity_names') else ''
        
        if not group_clause:
            select_clause = f'SELECT SUM(COALESCE(CAST({total_column} AS DOUBLE PRECISION), 0)) AS total_amount'
        
        sql = f"{select_clause} FROM {table_name} {where_clause} {group_clause}"
        logger.info(f"📊 Generated Generic Incomes SQL:\n{sql}")
        
        return sql

    def _build_topic_search_sql_for_masaref(
        self,
        user_query: str,
        costs_table: str,
        analysis: Dict[str, Any]
    ) -> Optional[str]:
        """
        ساخت SQL جستجوی topic-based برای masaref بدون نیاز به keyword هزینه.
        
        این متد در ستون‌های دستگاه masaref جستجو می‌کند.
        """
        years = analysis.get('years', [])
        if not years:
            return None
        
        # استخراج topic از query
        topic = user_query
        # حذف علائم نگارشی و سؤالی
        topic = re.sub(r'[؟?!،,.]', '', topic).strip()
        for year in years:
            topic = topic.replace(year, '').strip()
        remove_words = ['سال', 'در', 'چقدر', 'چه', 'مقدار', 'میزان', 'کل', 'جمع',
                        'چیست', 'چند', 'بوده', 'بوده است', 'است', 'هستش', 'هست', 'بگو',
                        'بده', 'نشان', 'گزارش', 'اطلاعات', 'داده']
        for word in remove_words:
            topic = re.sub(r'(?<!\w)' + re.escape(word) + r'(?!\w)', '', topic).strip()
        topic = re.sub(r'\s+', ' ', topic).strip()
        
        if len(topic) < 2:
            return None
        
        # ستون‌های masaref برای جستجوی topic
        masaref_topic_cols = ['عنوان_دستگاه_اجرايي', 'عنوان_دستگاه_اصلي']
        
        year_list = ', '.join([f"'{y}'" for y in years])
        year_condition = f'"سال" IN ({year_list})'
        
        topic_words = topic.split()
        wildcard_topic = '%'.join(topic_words)
        
        topic_parts = []
        for col in masaref_topic_cols:
            topic_parts.append(
                f'TRANSLATE("{col}", \'يكيۀةأإٱآ\', \'یکیهههااا\') ILIKE TRANSLATE(\'%{topic}%\', \'يكيۀةأإٱآ\', \'یکیهههااا\')'
            )
            if len(topic_words) > 1:
                topic_parts.append(
                    f'TRANSLATE("{col}", \'يكيۀةأإٱآ\', \'یکیهههااا\') ILIKE TRANSLATE(\'%{wildcard_topic}%\', \'يكيۀةأإٱآ\', \'یکیهههااا\')'
                )
        topic_condition = '(' + ' OR '.join(topic_parts) + ')'
        
        sql = f'''SELECT 
    SUM(COALESCE(CAST("جمع_كل" AS DOUBLE PRECISION), 0)) AS total_amount
FROM "{costs_table}"
WHERE {year_condition}
  AND {topic_condition}'''
        
        logger.info(f"🔍 [TOPIC-SQL-MASAREF] Built topic SQL for: '{topic}', years={years}")
        return sql
    
    def _build_topic_search_sql_for_manabe(
        self,
        user_query: str,
        income_table: str,
        analysis: Dict[str, Any]
    ) -> Optional[str]:
        """
        ساخت SQL جستجوی topic-based برای manabe بدون نیاز به keyword درآمد.
        
        این متد برای query های ambiguous استفاده می‌شود که topic مشخصی دارند
        اما کلمات کلیدی درآمد/منابع ندارند. (مثل "مالیات بر ثروت سال 1401")
        
        SQL تولید شده در همه سطوح سلسله‌مراتبی جستجو می‌کند.
        """
        years = analysis.get('years', [])
        if not years:
            return None
        
        # استخراج topic از query - حذف سال‌ها و کلمات عمومی
        topic = user_query
        # حذف علائم نگارشی و سؤالی
        topic = re.sub(r'[؟?!،,.]', '', topic).strip()
        # حذف سال‌ها
        for year in years:
            topic = topic.replace(year, '').strip()
        # حذف کلمات غیر مهم (شامل کلمات سؤالی)
        remove_words = ['سال', 'در', 'چقدر', 'چه', 'چه مقدار', 'مقدار', 'میزان', 'کل', 'جمع',
                        'چیست', 'چند', 'بوده', 'بوده است', 'است', 'هستش', 'هست', 'بگو',
                        'بده', 'نشان', 'گزارش', 'اطلاعات', 'داده', 'مقدار']
        for word in remove_words:
            topic = re.sub(r'(?<!\w)' + re.escape(word) + r'(?!\w)', '', topic).strip()
        topic = re.sub(r'\s+', ' ', topic).strip()
        
        if len(topic) < 2:
            return None
        
        # ستون‌های سلسله‌مراتبی manabe برای جستجو
        hierarchy_cols = ['عنوان_قسمت', 'عنوان_بخش', 'عنوان_بند', 'عنوان_جزء']
        
        # ساخت year filter
        year_list = ', '.join([f"'{y}'" for y in years])
        year_condition = f'"سال" IN ({year_list})'
        
        # ساخت topic filter - هم با عبارت کامل، هم با wildcard بین کلمات
        topic_words = topic.split()
        wildcard_topic = '%'.join(topic_words)  # "مالیات%بر%ثروت"
        
        topic_parts = []
        for col in hierarchy_cols:
            # جستجوی عبارت کامل
            topic_parts.append(
                f'TRANSLATE("{col}", \'يكيۀةأإٱآ\', \'یکیهههااا\') ILIKE TRANSLATE(\'%{topic}%\', \'يكيۀةأإٱآ\', \'یکیهههااا\')'
            )
            # جستجوی wildcard بین کلمات
            if len(topic_words) > 1:
                topic_parts.append(
                    f'TRANSLATE("{col}", \'يكيۀةأإٱآ\', \'یکیهههااا\') ILIKE TRANSLATE(\'%{wildcard_topic}%\', \'يكيۀةأإٱآ\', \'یکیهههااا\')'
                )
        topic_condition = '(' + ' OR '.join(topic_parts) + ')'
        
        # تشخیص ستون sum بر اساس نام جدول (ی فارسی vs ي عربی)
        sum_col = "جمع_کل"  # پیش‌فرض برای هر دو نسخه
        
        # SQL نهایی
        sql = f'''SELECT 
    SUM(COALESCE(CAST("{sum_col}" AS DOUBLE PRECISION), 0)) AS total_amount
FROM "{income_table}"
WHERE {year_condition}
  AND {topic_condition}'''
        
        logger.info(f"🔍 [TOPIC-SQL-MANABE] Built topic SQL for: '{topic}', years={years}, table={income_table}")
        return sql
    
    def _build_incomes_specialized_sql(
        self,
        user_query: str,
        collection_name: str
    ) -> Optional[str]:
        """ساخت SQL تخصصی برای سوالات درآمدی با استفاده از QueryAnalyzer"""
        income_table = self._get_income_table_name(collection_name)
        if not income_table:
            return None
        
        # ستون‌های dynamic بر اساس نوع جدول
        income_device_col = self._get_income_device_column(income_table)
        income_parent_col = self._get_income_parent_column(income_table)
        
        # تحلیل جامع query
        analysis = self.query_analyzer.analyze_query(user_query, collection_name)

        hierarchy_context: Optional[Dict[str, Any]] = None
        if analysis['income_component']:
            hierarchy_context = self._detect_income_hierarchy_context(
                analysis['income_component'],
                analysis['years'],
                collection_name
            )

        # بررسی وجود کلمه درآمد یا منابع
        # IMPORTANT: Normalize query first to handle "در امد" -> "درآمد"
        # هوشمندسازی: "منابع" = درآمد
        query_normalized = user_query.replace('‌', ' ').replace('\u200c', ' ')
        query_normalized = re.sub(r'در\s+ا\s*مد', 'درآمد', query_normalized, flags=re.IGNORECASE)
        query_normalized = re.sub(r'در\s+امد', 'درآمد', query_normalized, flags=re.IGNORECASE)
        query_lower = query_normalized.lower()
        # بهبود: "منابع" هم به معنای درآمد است
        has_income_keyword = any(kw in query_lower for kw in ['درآمد', 'درامد', 'منابع', 'عواید', 'عوايد'])
        if not has_income_keyword:
            return None
        
        # بررسی وجود سال
        if not analysis['years']:
            return None
        
        # ساخت WHERE clause
        where_conditions = []
        component_added = False
 
        # فیلتر component (اولویت دارد)
        # IMPORTANT: اگر hierarchy_context پیدا شد اما match_clause فقط برای یک column است،
        # از component_filter استفاده می‌کنیم که برای چند column است
        if analysis['filters']['component_filter']:
            if not hierarchy_context:
                # اگر hierarchy_context پیدا نشد، از component_filter استفاده می‌کنیم
                where_conditions.append(f"({analysis['filters']['component_filter']})")
                component_added = True
            else:
                # اگر hierarchy_context پیدا شد، بررسی می‌کنیم که آیا match_clause از exact phrase استفاده می‌کند
                # اگر نه، از component_filter استفاده می‌کنیم
                match_clause = hierarchy_context.get('match_clause', '')
                component_phrase = analysis['income_component']
                if component_phrase and f'%{component_phrase}%' not in match_clause:
                    # اگر match_clause از exact phrase استفاده نمی‌کند، از component_filter استفاده می‌کنیم
                    where_conditions.append(f"({analysis['filters']['component_filter']})")
                    component_added = True
                else:
                    # اگر match_clause از exact phrase استفاده می‌کند، از hierarchy_context استفاده می‌کنیم
                    pass
 
        # فیلتر entity (اگر هم component و هم entity داریم، هر دو را اضافه می‌کنیم)
        entity_filter = analysis['filters'].get('entity_filter')
        if entity_filter:
            # Adapt entity_filter for income table column names
            entity_filter = self._adapt_entity_filter_for_income(entity_filter, income_table)
            # IMPORTANT: Special case for "وزارت کشور" - ALWAYS use exact phrase
            # Check if entity_names contains "وزارت کشور"
            entity_names = analysis.get('entity_names', [])
            has_ministry_country = any('وزارت کشور' == str(name).strip() for name in entity_names)
            
            # If we have "وزارت کشور", ALWAYS use exact phrase (regardless of entity_filter format)
            if has_ministry_country:
                has_exact_phrase = '%وزارت کشور%' in entity_filter
                if not has_exact_phrase:
                    logger.warning(f"⚠️  FIXING: Forcing exact phrase for 'وزارت کشور'")
                    logger.warning(f"   Entity Names: {entity_names}")
                    logger.warning(f"   Old Filter: {entity_filter[:200]}")
                    safe_name = 'وزارت کشور'.replace("'", "''")
                    entity_filter = (
                        f"(TRANSLATE({income_device_col}, 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%" + safe_name + "%', 'يكيۀةأإٱآ', 'یکیهههااا') "
                        f"OR TRANSLATE({income_parent_col}, 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%" + safe_name + "%', 'يكيۀةأإٱآ', 'یکیهههااا'))"
                    )
                    logger.info(f"✅ Fixed Entity Filter: {entity_filter}")
            
            # Helper: check if entity_filter is a REAL separate org or derived from component/hierarchy
            def _should_skip_entity_filter(comp_filter_text: str) -> bool:
                """Returns True if entity_filter should be skipped (entity is not a real separate org)"""
                import re as _re
                # Extract keywords from ILIKE patterns in component_filter
                _comp_kws = set()
                for _pat in _re.findall(r"ILIKE '%([^']+)%'", comp_filter_text or ''):
                    _comp_kws.update(_pat.strip().split())
                # Also extract from income_component phrase if available
                _income_comp = analysis.get('income_component') or ''
                if _income_comp:
                    _comp_kws.update(_income_comp.split())
                # Organization indicator words = entity is a real separate agency
                _org_inds = {'وزارت', 'سازمان', 'بنیاد', 'اداره', 'شرکت', 'مرکز',
                             'کمیته', 'بانک', 'صندوق', 'دانشگاه', 'موسسه', 'نیرو',
                             'شهرداری', 'قوه', 'نهاد'}
                # Ordinal numbers that refer to hierarchy level (not real entities)
                _ords = {'اول', 'دوم', 'سوم', 'چهارم', 'پنجم', 'ششم',
                         'هفتم', 'هشتم', 'نهم', 'دهم', 'یکم', 'يكم'}
                _ent_list = analysis.get('entity_names', []) or []
                _ent_words = set()
                for _en in _ent_list:
                    _ent_words.update(str(_en).split())
                _has_org = bool(_ent_words & _org_inds)
                _non_gen = {w for w in _ent_words if len(w) > 2 and w not in
                            {'بر', 'در', 'از', 'به', 'با', 'که', 'یا', 'تا'}}
                _all_ord = bool(_non_gen) and _non_gen.issubset(_ords)
                _overlap = _non_gen & _comp_kws
                _derived = (bool(_overlap) or _all_ord) and not _has_org
                if _derived:
                    logger.info(f"⚡ Skipping entity_filter (derived): ent={_non_gen}, kws={_comp_kws}, ordinals={_all_ord}")
                return _derived

            # Only add entity_filter if not component context AND entity is a real separate org
            if not component_added:
                # If hierarchy_context is set, entity might be derived from the hierarchy level
                _comp_ctx_text = (analysis['filters'].get('component_filter') or '') + (' ' + (analysis.get('income_component') or ''))
                if hierarchy_context and _should_skip_entity_filter(_comp_ctx_text):
                    pass  # Skip entity filter - it's derived from the hierarchy/component text
                else:
                    where_conditions.append(f"({entity_filter})")
            # If we have both component and entity, only add entity_filter if it represents
            # a REAL separate organization/agency (not derived from the same component text)
            elif analysis['filters'].get('component_filter'):
                comp_filter_text = analysis['filters']['component_filter']
                if not _should_skip_entity_filter(comp_filter_text):
                    where_conditions.append(f"({entity_filter})")

        # اگر component_added=True باشد، نباید hierarchy_context اضافه شود
        # چون component_filter از exact phrase استفاده می‌کند و بهتر است
        if hierarchy_context and not component_added:
            where_conditions.append(f"({hierarchy_context['match_clause']})")

        # اگر هیچ فیلتری نباشد، برنگردانیم (مگر اینکه top_n باشد)
        if not where_conditions and analysis['query_category'] != 'top_n':
            return None
        
        # فیلتر سال
        year_list = ', '.join([f"'{year}'" for year in analysis['years']])
        year_filter = f"TRANSLATE(\"سال\", 'يكيۀة', 'یکیهه') IN ({year_list})"
        where_conditions.append(year_filter)
        
        where_clause = f"WHERE {' AND '.join(where_conditions)}"
        
        # Debug: Log final SQL to check if exact phrase is used
        if entity_filter and 'وزارت کشور' in (analysis.get('entity_names', []) or []):
            if '%وزارت کشور%' in where_clause:
                logger.info(f"✅ Final SQL uses exact phrase '%وزارت کشور%'")
            elif ' AND ' in where_clause and '%وزارت%' in where_clause and '%کشور%' in where_clause:
                logger.error(f"❌ Final SQL STILL uses AND pattern despite fix!")
                logger.error(f"   WHERE clause: {where_clause[:300]}")
        
        # تعیین ستون مبلغ
        amount_column = self._determine_income_column_from_type(analysis['income_type'], income_table)

        # اگر درخت سلسله‌مراتبی پیدا شد و فقط مبلغ خواسته شده است، بر اساس آن جمع بزنیم
        if hierarchy_context and analysis['query_type'] == 'amount':
            select_parts = hierarchy_context['select_exprs'] + [
                f"SUM(COALESCE(CAST({amount_column} AS DOUBLE PRECISION), 0)) AS total_amount"
            ]
            select_clause = "SELECT " + ", ".join(select_parts) + f" FROM {income_table}"
            group_clause = ""
            if hierarchy_context['group_columns']:
                group_clause = "GROUP BY " + ", ".join(hierarchy_context['group_columns'])
            order_clause = "ORDER BY total_amount DESC" if hierarchy_context['group_columns'] else ""
            sql = f"{select_clause} {where_clause} {group_clause} {order_clause}".strip()
            logger.info(f"📊 Generated Incomes hierarchical SQL:\n{sql}")
            return sql

        # تعیین نوع SELECT براساس query_type
        if analysis['query_type'] == 'sources':
            # نیاز به لیست منابع درآمد
            # 🆕 FIX: اگر entity_filter داریم (مثل "منابع بنیاد ملی نخبگان")،
            # از ستون‌های دستگاه استفاده کن نه hierarchy
            # این جلوگیری می‌کند از اینکه entity query با عنوان_جزء پاسخ داده شود
            if entity_filter and not component_added:
                # Entity-focused sources query: از ستون‌های دستگاه استفاده کن
                select_clause = (
                    f'SELECT {income_parent_col}, {income_device_col}, '
                    f'SUM(COALESCE(CAST({amount_column} AS DOUBLE PRECISION), 0)) AS total_amount '
                    f'FROM {income_table}'
                )
                group_clause = f'GROUP BY {income_parent_col}, {income_device_col}'
                order_clause = 'ORDER BY total_amount DESC'
                logger.info(f"📊 Entity-focused sources query: using device columns {income_parent_col}, {income_device_col}")
                return f"{select_clause} {where_clause} {group_clause} {order_clause}"
            else:
                # Hierarchy-based sources query: از سلسله‌مراتب استفاده کن
                # تشخیص بالاترین سطح سلسله‌مراتب از component_filter برای GROUP BY مناسب
                comp_filter_text = analysis['filters'].get('component_filter', '')
                if '"عنوان_قسمت"' in comp_filter_text:
                    # فیلتر روی قسمت → GROUP BY فقط قسمت
                    group_cols = ['"عنوان_قسمت"']
                elif '"عنوان_بخش"' in comp_filter_text:
                    # فیلتر روی بخش → GROUP BY قسمت + بخش
                    group_cols = ['"عنوان_قسمت"', '"عنوان_بخش"']
                elif '"عنوان_بند"' in comp_filter_text:
                    # فیلتر روی بند → GROUP BY قسمت + بخش + بند
                    group_cols = ['"عنوان_قسمت"', '"عنوان_بخش"', '"عنوان_بند"']
                else:
                    # fallback: همه سطوح
                    group_cols = ['"عنوان_قسمت"', '"عنوان_بخش"', '"عنوان_بند"', '"عنوان_جزء"']
                select_cols_str = ', '.join(group_cols)
                select_clause = (
                    f'SELECT {select_cols_str}, '
                    f'SUM(COALESCE(CAST({amount_column} AS DOUBLE PRECISION), 0)) AS total_amount '
                    f'FROM {income_table}'
                )
                group_clause = f'GROUP BY {select_cols_str}'
                order_clause = 'ORDER BY total_amount DESC'
                logger.info(f"📊 Hierarchy-based sources query: GROUP BY {group_cols}")
                return f"{select_clause} {where_clause} {group_clause} {order_clause}"
        
        elif analysis['query_type'] == 'amount_and_device':
            # نیاز به مبلغ + نام دستگاه
            select_clause = (
                f'SELECT {income_device_col}, {income_parent_col}, '
                f'SUM(COALESCE(CAST({amount_column} AS DOUBLE PRECISION), 0)) AS total_amount '
                f'FROM {income_table}'
            )
            group_clause = f'GROUP BY {income_device_col}, {income_parent_col}'
            order_clause = 'ORDER BY total_amount DESC'
            return f"{select_clause} {where_clause} {group_clause} {order_clause}"
        
        elif analysis['query_type'] == 'device':
            # فقط نیاز به نام دستگاه
            select_clause = (
                f'SELECT DISTINCT {income_device_col}, {income_parent_col} '
                f'FROM {income_table}'
            )
            return f"{select_clause} {where_clause}"
        
        else:
            # پیش‌فرض: فقط مبلغ
            # اما اگر component filter داریم و "چه دستگاهی" یا "توسط چه" داریم، 
            # باید GROUP BY دستگاه بکنیم
            query_lower_check = user_query.lower()
            if (analysis['filters']['component_filter'] and 
                ('چه دستگاه' in query_lower_check or 'توسط چه' in query_lower_check or 'وصول' in query_lower_check)):
                select_clause = (
                    f'SELECT {income_device_col}, {income_parent_col}, '
                    f'SUM(COALESCE(CAST({amount_column} AS DOUBLE PRECISION), 0)) AS total_amount '
                    f'FROM {income_table}'
                )
                group_clause = f'GROUP BY {income_device_col}, {income_parent_col}'
                order_clause = 'ORDER BY total_amount DESC'
                return f"{select_clause} {where_clause} {group_clause} {order_clause}"
            elif len(analysis['years']) > 1:
                # 🔧 FIX: سوال چند سالی → GROUP BY سال تا نتایج per-year برگردانده شود
                select_clause = (
                    f'SELECT "سال", SUM(COALESCE(CAST({amount_column} AS DOUBLE PRECISION), 0)) AS total_amount '
                    f'FROM {income_table}'
                )
                group_clause = 'GROUP BY "سال"'
                order_clause = 'ORDER BY "سال"'
                return f"{select_clause} {where_clause} {group_clause} {order_clause}"
            else:
                select_clause = (
                    f'SELECT SUM(COALESCE(CAST({amount_column} AS DOUBLE PRECISION), 0)) AS total_amount '
                    f'FROM {income_table}'
                )
                return f"{select_clause} {where_clause}"

    def _extract_year_values(self, query: str) -> List[str]:
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
        unique_years = sorted(set(years))
        return unique_years

    def _normalize_year_token(self, token: str) -> Optional[str]:
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

    def _extract_entity_filter(self, query: str) -> Optional[str]:
        # IMPORTANT: Special case for "وزارت کشور" - must use exact phrase
        # This OLD function is still being used somewhere (probably LLM fallback)
        # So we add the fix here too
        normalized_query_check = query.replace('\u200c', ' ').replace('\u200f', ' ')
        normalized_query_check = ' '.join(normalized_query_check.split())
        
        if 'وزارت کشور' in normalized_query_check or 'وزارت  کشور' in normalized_query_check:
            # برای "وزارت کشور"، همیشه exact phrase برگردان
            safe_name = 'وزارت کشور'.replace("'", "''")
            translation_source = 'يكيۀةأإٱآ'
            translation_target = 'یکیهههااا'
            return (
                "((TRANSLATE(\"عنوان_دستگاه\", '" + translation_source + "', '" + translation_target + "') ILIKE '%" + safe_name + "%') "
                "OR (TRANSLATE(\"عنوان_دستگاه_اصلی\", '" + translation_source + "', '" + translation_target + "') ILIKE '%" + safe_name + "%'))"
            )
        
        # Normal logic for other entities
        normalized_query = query.replace('\u200c', ' ').replace('\u200f', ' ')
        normalized_query = ' '.join(normalized_query.split())
        normalized_query = re.sub(
            r'در\s+سال(?:های|هاي)?\s+\d{2,4}(?:\s*(?:تا|-)\s*\d{2,4})?',
            ' ',
            normalized_query,
            flags=re.IGNORECASE
        )
        normalized_query = re.sub(
            r'سال(?:های|هاي)?\s+\d{2,4}(?:\s*(?:تا|-)\s*\d{2,4})?',
            ' ',
            normalized_query,
            flags=re.IGNORECASE
        )
        if not normalized_query.strip():
            normalized_query = query
        tokens = re.findall(r'[آ-یA-Za-z0-9]+', normalized_query)
        translation_map = str.maketrans({
            'ي': 'ی',
            'ك': 'ک',
            'ة': 'ه',
            'ۀ': 'ه',
            'أ': 'ا',
            'إ': 'ا',
            'ٱ': 'ا',
            'آ': 'ا'
        })
        stop_words = {
            'در', 'سال', 'های', 'سالهای', 'سالها', 'چقدر', 'مجموعا', 'چگونه',
            'چه', 'است', 'هست', 'کل', 'مجموع', 'درآمد', 'درامد', 'اختصاصی',
            'خصوصی', 'عمومی', 'ملی', 'ملي', 'استانی', 'استاني', 'چند', 'ميليارد',
            'از', 'راه', 'راهی', 'راههایی', 'راه‌های', 'طریق', 'روش', 'هایی', 'کسب', 'کرده', 'داشته', 'تا', 'الی', 'می', 'می‌شود', 'می شود', 'مي', 'شده', 'گردد'
        }
        entity_tokens: List[str] = []
        for token in tokens:
            if token and token not in stop_words and not token.isdigit():
                normalized_token = token.translate(translation_map)
                entity_tokens.append(normalized_token)
        if not entity_tokens:
            return None
        conditions: List[str] = []
        for token in entity_tokens:
            safe_token = token.replace("'", "''")
            conditions.append(
                "("
                "TRANSLATE(\"عنوان_دستگاه\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%" + safe_token + "%' "
                "OR TRANSLATE(\"عنوان_دستگاه_اصلی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%" + safe_token + "%'"
                ")"
            )
        return " AND ".join(conditions)

    def _determine_income_column_from_type(self, income_type: str, income_table: str = '') -> str:
        """تعیین ستون مبلغ براساس income_type از QueryAnalyzer
        
        برخی جداول مثل manabe3_sheet1 از ي عربی استفاده می‌کنند (مثل ملي_جمع_کل)
        و برخی مثل manabe_sheet1 از ی فارسی (مثل ملی_جمع_کل).
        این متد نام ستون درست را بر اساس جدول برمی‌گرداند.
        """
        # تشخیص اینکه آیا جدول از ي عربی استفاده می‌کند
        use_arabic_yi = income_table == 'manabe3_sheet1'
        
        if use_arabic_yi:
            # manabe3_sheet1 از ي عربی استفاده می‌کند
            type_to_column = {
                'ملی_اختصاصی': '"ملي_در_آمد_اختصاصي"',
                'استانی_اختصاصی': '"استاني_در_آمد_اختصاصي"',
                'اختصاصی': '"جمع_در_آمد_اختصاصي"',
                'ملی_عمومی': '"ملي_در_آمد_عمومي"',
                'استانی_عمومی': '"استاني_در_آمد_عمومي"',
                'عمومی': '"جمع_در_آمد_عمومي"',
                'ملی': '"ملي_جمع_کل"',
                'استانی': '"استاني_جمع_کل"',
                'کل': '"جمع_کل"'
            }
        else:
            # manabe_sheet1 از ی فارسی استفاده می‌کند
            type_to_column = {
                'ملی_اختصاصی': '"ملی_در_آمد_اختصاصی"',
                'استانی_اختصاصی': '"استانی_در_آمد_اختصاصی"',
                'اختصاصی': '"جمع_در_آمد_اختصاصی"',
                'ملی_عمومی': '"ملی_در_آمد_عمومی"',
                'استانی_عمومی': '"استانی_در_آمد_عمومی"',
                'عمومی': '"جمع_در_آمد_عمومی"',
                'ملی': '"ملی_جمع_کل"',
                'استانی': '"استانی_جمع_کل"',
                'کل': '"جمع_کل"'
            }
        return type_to_column.get(income_type, '"جمع_کل"')

    async def execute_and_get_results(
        self,
        user_query: str,
        collection_name: str
    ) -> Dict[str, Any]:
        """تولید SQL و اجرا و دریافت نتایج"""
        # تولید SQL
        sql_result = await self.generate_sql(user_query, collection_name)
        
        if not sql_result["success"]:
            return {
                "success": False,
                "error": sql_result.get("error"),
                "sql": None,
                "results": None
            }
        
        sql_query = sql_result["sql"]
        
        # اجرای SQL
        query_result = self.database_service.execute_sql_query(
            sql_query,
            collection_name=collection_name
        )
        
        if not query_result["success"]:
            return {
                "success": False,
                "error": query_result.get("error"),
                "sql": sql_query,
                "results": None
            }
        
        executed_sql = query_result.get("prepared_sql", sql_query)
        
        response: Dict[str, Any] = {
            "success": True,
            "sql": executed_sql,
            "results": query_result["rows"],
            "count": query_result["count"],
            "columns": query_result["columns"],
            "warnings": sql_result.get("warnings", [])
        }
        if query_result.get("detail_rows"):
            response["detail_rows"] = query_result.get("detail_rows")
            response["detail_columns"] = query_result.get("detail_columns", [])
            response["detail_sql"] = query_result.get("detail_sql")
        
        return response
    
    async def execute_with_analysis(
        self,
        user_query: str,
        collection_name: str,
        query_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        تولید SQL با استفاده از query_analysis و اجرا و دریافت نتایج
        
        این متد از analysis موجود استفاده می‌کند و نیاز به تحلیل مجدد ندارد.
        """
        logger.info(f"🔧 Executing with pre-analyzed query: category={query_analysis.get('query_category')}")
        
        # استفاده از original_analysis اگر موجود است
        analysis = query_analysis.get('original_analysis', query_analysis)
        
        # تولید SQL با analysis موجود
        sql = await self._build_specialized_sql_with_analysis(user_query, collection_name, analysis)
        
        if not sql:
            # fallback به generate_sql معمولی
            return await self.execute_and_get_results(user_query, collection_name)
        
        logger.info(f"📝 Generated SQL from analysis:\n{sql[:300]}...")
        
        # اجرای SQL
        query_result = self.database_service.execute_sql_query(
            sql,
            collection_name=collection_name
        )
        
        if not query_result["success"]:
            return {
                "success": False,
                "error": query_result.get("error"),
                "sql": sql,
                "results": None
            }
        
        executed_sql = query_result.get("prepared_sql", sql)
        rows_count = query_result.get("count", 0) or len(query_result.get("rows") or [])
        
        # 🆕 FUZZY FALLBACK: اگر نتیجه‌ای نداشتیم و component_filter داریم،
        # ممکن است typo در کلمات کلیدی باشد → سعی کن با fuzzy matching جواب پیدا کنی
        if rows_count == 0 and analysis.get('income_component') and analysis.get('filters', {}).get('component_filter'):
            fuzzy_result = await self._try_fuzzy_component_fallback(
                user_query, collection_name, analysis, query_result
            )
            if fuzzy_result:
                logger.info(f"✅ Fuzzy fallback found results for component: {analysis.get('income_component')}")
                return fuzzy_result
        
        response = {
            "success": True,
            "sql": executed_sql,
            "results": query_result["rows"],
            "count": query_result["count"],
            "columns": query_result["columns"],
            "analysis_used": query_analysis.get('query_category')
        }
        # اضافه کردن detail_rows اگر موجود باشد
        if query_result.get("detail_rows"):
            response["detail_rows"] = query_result.get("detail_rows")
            response["detail_columns"] = query_result.get("detail_columns", [])
            response["detail_sql"] = query_result.get("detail_sql")
        return response

    async def _try_fuzzy_component_fallback(
        self,
        user_query: str,
        collection_name: str,
        analysis: Dict[str, Any],
        original_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Fuzzy fallback برای component_filter که نتیجه‌ای نداشته.
        
        وقتی کاربر typo دارد (مثل ثرورت به جای ثروت)، این متد:
        1. کلمات کلیدی را از income_component استخراج می‌کند
        2. در ستون مربوطه (عنوان_بند/عنوان_بخش/عنوان_قسمت) نزدیک‌ترین match را پیدا می‌کند
        3. SQL را با match صحیح اجرا می‌کند
        """
        try:
            from difflib import SequenceMatcher
            
            income_component = analysis.get('income_component', '')
            component_filter = analysis.get('filters', {}).get('component_filter', '')
            if not income_component or not component_filter:
                return None
            
            # تشخیص ستون هدف از component_filter
            target_col = None
            for col in ['"عنوان_بند"', '"عنوان_بخش"', '"عنوان_قسمت"', '"عنوان_جزء"']:
                if col in component_filter:
                    target_col = col.strip('"')
                    break
            
            if not target_col:
                return None
            
            # دریافت تمام مقادیر یکتا از ستون هدف
            income_table = self._get_income_table_name(collection_name)
            if not income_table:
                return None
            
            distinct_sql = f'SELECT DISTINCT "{target_col}" FROM {income_table} WHERE "{target_col}" IS NOT NULL LIMIT 500'
            distinct_result = self.database_service.execute_sql_query(distinct_sql, collection_name=collection_name)
            
            if not distinct_result.get('success') or not distinct_result.get('rows'):
                return None
            
            # نرمال‌سازی component برای مقایسه
            def _norm(s):
                if not s:
                    return ''
                return str(s).replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه').lower().strip()
            
            component_norm = _norm(income_component)
            
            # پیدا کردن بهترین match با SequenceMatcher
            best_match = None
            best_score = 0.0
            
            for row in distinct_result['rows']:
                val = row.get(target_col, '') if isinstance(row, dict) else (row[0] if row else '')
                if not val:
                    continue
                val_norm = _norm(str(val))
                
                # محاسبه شباهت
                score = SequenceMatcher(None, component_norm, val_norm).ratio()
                
                # بونوس برای کلمات مشترک
                comp_words = set(w for w in component_norm.split() if len(w) > 2)
                val_words = set(w for w in val_norm.split() if len(w) > 2)
                common = comp_words & val_words
                if common:
                    word_bonus = len(common) / max(len(comp_words), len(val_words), 1) * 0.4
                    score = min(1.0, score + word_bonus)
                
                if score > best_score:
                    best_score = score
                    best_match = val
            
            # threshold: حداقل 0.6 شباهت
            if best_score < 0.6 or not best_match:
                logger.info(f"🔍 Fuzzy fallback: no good match for '{income_component}' (best={best_score:.2f})")
                return None
            
            logger.info(f"🔍 Fuzzy fallback: '{income_component}' → '{best_match}' (score={best_score:.2f})")
            
            # ساخت SQL جدید با match صحیح
            safe_match = best_match.replace("'", "''")
            new_filter = f"TRANSLATE(\"{target_col}\", 'يكيۀةأإٱآئ', 'یکیهههااای') ILIKE TRANSLATE('%{safe_match}%', 'يكيۀةأإٱآئ', 'یکیهههااای')"
            
            # جایگزینی component_filter در SQL اصلی
            original_sql = original_result.get('prepared_sql', '') or original_result.get('sql', '')
            if not original_sql:
                return None
            
            # ساخت SQL جدید با filter اصلاح شده
            # استفاده از analysis با component_filter جدید
            new_analysis = dict(analysis)
            new_filters = dict(analysis.get('filters', {}))
            new_filters['component_filter'] = new_filter
            new_analysis['filters'] = new_filters
            
            new_sql = await self._build_specialized_sql_with_analysis(user_query, collection_name, new_analysis)
            if not new_sql:
                return None
            
            new_result = self.database_service.execute_sql_query(new_sql, collection_name=collection_name)
            if not new_result.get('success') or not new_result.get('rows'):
                return None
            
            response = {
                "success": True,
                "sql": new_result.get("prepared_sql", new_sql),
                "results": new_result["rows"],
                "count": new_result["count"],
                "columns": new_result["columns"],
                "analysis_used": analysis.get('query_category'),
                "_fuzzy_corrected": True,
                "_fuzzy_original": income_component,
                "_fuzzy_matched": best_match,
                "_fuzzy_score": best_score
            }
            if new_result.get("detail_rows"):
                response["detail_rows"] = new_result.get("detail_rows")
                response["detail_columns"] = new_result.get("detail_columns", [])
                response["detail_sql"] = new_result.get("detail_sql")
            return response
        
        except Exception as e:
            logger.warning(f"⚠️ Fuzzy component fallback failed: {e}")
            return None

    async def execute_dual_table_search(
        self,
        user_query: str,
        collection_name: str,
        query_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        جستجو در هر دو جدول manabe و masaref به صورت موازی
        
        این متد برای query های ambiguous استفاده می‌شود که مشخص نیست
        درباره درآمد هستند یا هزینه.
        
        Returns:
            {
                'success': bool,
                'manabe_result': dict or None,   # نتایج از جدول منابع (درآمد)
                'masaref_result': dict or None,  # نتایج از جدول مصارف (هزینه)
                'has_manabe': bool,
                'has_masaref': bool,
                'combined': bool  # آیا هر دو نتیجه دارند
            }
        """
        analysis = query_analysis.get('original_analysis', query_analysis)
        
        income_table = self._get_income_table_name(collection_name)
        costs_table = self._get_costs_table_name(collection_name)
        
        logger.info(f"🔍 [DUAL-DEBUG] query='{user_query}' income_table={income_table} costs_table={costs_table}")
        
        manabe_result = None
        masaref_result = None
        
        # 1. جستجو در manabe (درآمد)
        if income_table:
            try:
                query_norm = self.query_analyzer.normalize_text(user_query)
                income_sql = self._build_incomes_specialized_sql(query_norm, collection_name)
                
                # 🆕 اگر _build_incomes_specialized_sql جواب نداد (چون keyword درآمد نداشت)،
                # یک SQL topic-based مستقیم بساز
                if not income_sql:
                    income_sql = self._build_topic_search_sql_for_manabe(
                        query_norm, income_table, analysis
                    )
                
                if income_sql:
                    income_qr = self.database_service.execute_sql_query(income_sql, collection_name=collection_name)
                    if income_qr.get('success') and income_qr.get('rows'):
                        total = None
                        if income_qr['rows'] and 'total_amount' in income_qr['rows'][0]:
                            total = income_qr['rows'][0]['total_amount']
                        if total is not None and float(str(total).replace(',', '') or 0) > 0:
                            manabe_result = {
                                'success': True,
                                'sql': income_qr.get('prepared_sql', income_sql),
                                'results': income_qr['rows'],
                                'count': income_qr.get('count', 0),
                                'columns': income_qr.get('columns', []),
                                'table_type': 'manabe'
                            }
                            if income_qr.get('detail_rows'):
                                manabe_result['detail_rows'] = income_qr['detail_rows']
                                manabe_result['detail_columns'] = income_qr.get('detail_columns', [])
                            logger.info(f"✅ [DUAL] manabe found: total={total}")
                        else:
                            logger.info(f"⚠️ [DUAL] manabe returned null/zero total")
            except Exception as e:
                logger.warning(f"⚠️ [DUAL] manabe search failed: {e}")
        
        # 2. جستجو در masaref (مصارف/هزینه)
        if costs_table:
            try:
                costs_sql = self._build_costs_specialized_sql(analysis, collection_name, user_query)
                if not costs_sql:
                    # fallback: topic-based search for masaref
                    costs_sql = self._build_topic_search_sql_for_masaref(
                        self.query_analyzer.normalize_text(user_query), costs_table, analysis
                    )
                if costs_sql:
                    costs_qr = self.database_service.execute_sql_query(costs_sql, collection_name=collection_name)
                    if costs_qr.get('success') and costs_qr.get('rows'):
                        total = None
                        if costs_qr['rows'] and 'total_amount' in costs_qr['rows'][0]:
                            total = costs_qr['rows'][0]['total_amount']
                        if total is not None and float(str(total).replace(',', '') or 0) > 0:
                            masaref_result = {
                                'success': True,
                                'sql': costs_qr.get('prepared_sql', costs_sql),
                                'results': costs_qr['rows'],
                                'count': costs_qr.get('count', 0),
                                'columns': costs_qr.get('columns', []),
                                'table_type': 'masaref'
                            }
                            if costs_qr.get('detail_rows'):
                                masaref_result['detail_rows'] = costs_qr['detail_rows']
                                masaref_result['detail_columns'] = costs_qr.get('detail_columns', [])
                            logger.info(f"✅ [DUAL] masaref found: total={total}")
                        else:
                            logger.info(f"⚠️ [DUAL] masaref returned null/zero total")
            except Exception as e:
                logger.warning(f"⚠️ [DUAL] masaref search failed: {e}")
        
        has_manabe = manabe_result is not None
        has_masaref = masaref_result is not None
        
        return {
            'success': has_manabe or has_masaref,
            'manabe_result': manabe_result,
            'masaref_result': masaref_result,
            'has_manabe': has_manabe,
            'has_masaref': has_masaref,
            'combined': has_manabe and has_masaref
        }

    async def _build_specialized_sql_with_analysis(
        self,
        query: str,
        collection_name: str,
        analysis: Dict[str, Any]
    ) -> Optional[str]:
        """ساخت SQL با استفاده از analysis موجود"""
        if not analysis:
            return None
        
        query_category = analysis.get('query_category', 'simple_sum')
        years = analysis.get('years', [])
        logger.info(f"🔄 Building SQL with analysis: category={query_category}, years={years}")
        
        # تشخیص نوع جدول با بررسی وجود سال در جدول
        query_normalized = self.query_analyzer.normalize_text(query)
        table_type = self._detect_table_type_with_year_check(query_normalized, years, collection_name)
        
        income_table = self._get_income_table_name(collection_name)
        has_incomes = income_table is not None
        costs_table = self._get_costs_table_name(collection_name)
        has_costs = costs_table is not None
        
        logger.info(f"📊 Table type: {table_type}, has_incomes={has_incomes}, has_costs={has_costs}, costs_table={costs_table}, income_table={income_table}")
        
        # انتخاب strategy بر اساس category
        if query_category == 'comparison':
            sql = self._build_comparison_sql(analysis, collection_name, table_type)
            if sql:
                return sql
        
        elif query_category == 'cross_table':
            if has_incomes and has_costs:
                return self._build_cross_table_sql(analysis, collection_name)
        
        elif query_category == 'breakdown':
            if has_incomes:
                return self._build_breakdown_sql(analysis, collection_name)
        
        elif query_category == 'top_n':
            if table_type == 'costs' and has_costs:
                return self._build_top_n_sql(analysis, collection_name, 'costs')
            elif table_type == 'incomes' and has_incomes:
                return self._build_top_n_sql(analysis, collection_name, 'incomes')
            elif has_incomes:
                return self._build_top_n_sql(analysis, collection_name, 'incomes')
            elif has_costs:
                return self._build_top_n_sql(analysis, collection_name, 'costs')
        
        elif query_category == 'simple_sum':
            if table_type == 'costs' and has_costs:
                costs_sql = self._build_costs_specialized_sql(analysis, collection_name, query)
                if costs_sql:
                    return costs_sql
            # fallback به incomes/manabe
            incomes_sql = self._build_incomes_specialized_sql(query_normalized, collection_name)
            if incomes_sql:
                return incomes_sql
            # آخرین fallback
            if has_costs:
                return self._build_costs_specialized_sql(analysis, collection_name, query)
        
        return None
    
    def _build_top_n_sql(
        self,
        analysis: Dict[str, Any],
        collection_name: str,
        table_type: str
    ) -> Optional[str]:
        """
        ساخت SQL برای سوالات Top N (بیشترین/کمترین)
        
        مثال: "کدام سازمان ها در سال 1398 بیشترین درآمد را کسب کردند؟"
        مثال: "پر هزینه ترین دستگاه های اجرایی منتصب به نهاد ریاست جمهوری کدام دستگاه ها هستند ؟"
        """
        if table_type == 'incomes':
            income_table = self._get_income_table_name(collection_name)
            if not income_table:
                return None
            table_name = income_table
            amount_column = self._determine_income_column_from_type(analysis['income_type'], income_table)
            device_column = self._get_income_device_column(income_table)
            parent_column = self._get_income_parent_column(income_table)
        elif table_type == 'costs':
            costs_table = self._get_costs_table_name(collection_name)
            if not costs_table:
                return None
            table_name = costs_table
            amount_column = '"جمع_كل"'
            device_column = '"عنوان_دستگاه_اجرايي"'
            parent_column = '"عنوان_دستگاه_اصلي"'
        else:
            return None
        
        # ساخت WHERE clause
        where_conditions = []
        
        # فیلتر سال (اختیاری - اگر سال نداشته باشد، همه سال‌ها را می‌گیرد)
        if analysis['years']:
            year_list = ', '.join([f"'{year}'" for year in analysis['years']])
            year_filter = f"TRANSLATE(\"سال\", 'يكيۀة', 'یکیهه') IN ({year_list})"
            where_conditions.append(year_filter)
        
        # فیلتر parent entity (برای سوالات "منتصب به" یا "وابسته به")
        # این فیلتر روی parent_column اعمال می‌شود
        if analysis['filters'].get('entity_filter'):
            entity_filter = analysis['filters']['entity_filter']
            if table_type == 'costs':
                combined_filter = self._build_combined_entity_filter(entity_filter, [device_column, parent_column])
                where_conditions.append(f"({combined_filter})")
            else:
                where_conditions.append(f"({entity_filter})")
        
        # فیلتر component (فقط برای incomes)
        if table_type == 'incomes' and analysis['filters'].get('component_filter'):
            where_conditions.append(f"({analysis['filters']['component_filter']})")
        
        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
        
        # تعیین LIMIT
        limit = analysis['aggregation'].get('limit', 10)
        sort_dir = analysis['aggregation'].get('sort_direction', 'DESC')
        
        sql = (
            f"SELECT {device_column}, {parent_column}, "
            f"SUM(COALESCE(CAST({amount_column} AS DOUBLE PRECISION), 0)) AS total_amount "
            f"FROM {table_name} "
            f"{where_clause} "
            f"GROUP BY {device_column}, {parent_column} "
            f"ORDER BY total_amount {sort_dir} "
            f"LIMIT {limit}"
        )
        
        logger.info(f"📊 Generated Top-N SQL:\n{sql}")
        return sql
    
    def _build_breakdown_sql(
        self,
        analysis: Dict[str, Any],
        collection_name: str
    ) -> Optional[str]:
        """
        ساخت SQL برای سوالات breakdown (تفکیک چند بعدی)
        
        مثال: "وزارت کشور در سال 1398 چقدر درآمد؟ ملی و استانی؟ از چه راه‌ها؟"
        
        این query باید:
        1. مجموع کل را بدهد
        2. تفکیک ملی/استانی بدهد
        3. breakdown منابع بدهد
        """
        if not analysis['years']:
            return None
        
        # بررسی اینکه آیا entity filter داریم
        entity_filter = analysis['filters'].get('entity_filter')
        if not entity_filter:
            # اگر entity نداریم، نمی‌توانیم breakdown بدهیم
            return None
        
        # IMPORTANT: Special case for "وزارت کشور" - ALWAYS use exact phrase
        # Check if entity_names contains "وزارت کشور"
        entity_names = analysis.get('entity_names', [])
        has_ministry_country = any('وزارت کشور' == str(name).strip() for name in entity_names)
        
        # If we have "وزارت کشور", ALWAYS use exact phrase (regardless of entity_filter format)
        if has_ministry_country:
            has_exact_phrase = '%وزارت کشور%' in entity_filter
            if not has_exact_phrase:
                logger.warning(f"⚠️  FIXING: Forcing exact phrase for 'وزارت کشور'")
                logger.warning(f"   Entity Names: {entity_names}")
                logger.warning(f"   Old Filter: {entity_filter[:200]}")
                safe_name = 'وزارت کشور'.replace("'", "''")
                entity_filter = (
                    "(TRANSLATE(\"عنوان_دستگاه\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%" + safe_name + "%' "
                    "OR TRANSLATE(\"عنوان_دستگاه_اصلی\", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%" + safe_name + "%')"
                )
                logger.info(f"✅ Fixed Entity Filter: {entity_filter}")
        
        # ساخت WHERE clause
        where_conditions = [f"({entity_filter})"]
        year_list = ', '.join([f"'{year}'" for year in analysis['years']])
        year_filter = f"TRANSLATE(\"سال\", 'يكيۀة', 'یکیهه') IN ({year_list})"
        where_conditions.append(year_filter)
        
        where_clause = f"WHERE {' AND '.join(where_conditions)}"
        
        # Debug: Log final SQL to check if exact phrase is used
        if entity_filter and 'وزارت کشور' in (analysis.get('entity_names', []) or []):
            if '%وزارت کشور%' in where_clause:
                logger.info(f"✅ Final Breakdown SQL uses exact phrase '%وزارت کشور%'")
            elif ' AND ' in where_clause and '%وزارت%' in where_clause and '%کشور%' in where_clause:
                logger.error(f"❌ Final Breakdown SQL STILL uses AND pattern despite fix!")
                logger.error(f"   WHERE clause: {where_clause[:300]}")
        
        # SELECT clause بر اساس dimensions
        dims = analysis['dimensions']
        
        select_parts = []
        if dims['asks_sources']:
            select_parts.extend(['"عنوان_بخش"', '"عنوان_بند"', '"عنوان_جزء"'])
        
        # همیشه aggregations
        select_parts.append('SUM(COALESCE(CAST("جمع_کل" AS DOUBLE PRECISION), 0)) AS total_amount')
        
        if dims['asks_national_provincial']:
            select_parts.append('SUM(COALESCE(CAST("ملی_جمع_کل" AS DOUBLE PRECISION), 0)) AS total_national')
            select_parts.append('SUM(COALESCE(CAST("استانی_جمع_کل" AS DOUBLE PRECISION), 0)) AS total_provincial')
        
        select_clause = f"SELECT {', '.join(select_parts)}"
        
        # GROUP BY
        group_fields = []
        if dims['asks_sources']:
            group_fields = ['"عنوان_بخش"', '"عنوان_بند"', '"عنوان_جزء"']
        
        group_clause = f"GROUP BY {', '.join(group_fields)}" if group_fields else ""
        order_clause = "ORDER BY total_amount DESC" if group_fields else ""
        
        _income_tbl = self._get_income_table_name(collection_name) or 'manabe3_sheet1'
        sql = f"{select_clause} FROM {_income_tbl} {where_clause} {group_clause} {order_clause}"
        
        logger.info(f"📊 Generated Breakdown SQL:\n{sql}")
        return sql
    
    def _build_cross_table_sql(
        self,
        analysis: Dict[str, Any],
        collection_name: str
    ) -> Optional[str]:
        """
        ساخت SQL برای محاسبات cross-table (درآمد - هزینه)
        
        مثال: "زیان‌ده‌ترین دستگاه سال 1403 چه دستگاهی است؟"
        
        این query باید:
        1. JOIN بین incomes و costs بزند
        2. تراز (income - cost) را محاسبه کند
        3. بر اساس تراز مرتب کند
        """
        if not analysis['years']:
            return None
        
        calculation_type = analysis['cross_table'].get('calculation_type')
        if not calculation_type:
            return None
        
        year_list = ', '.join([f"'{year}'" for year in analysis['years']])
        year_filter = f"TRANSLATE(\"سال\", 'يكيۀة', 'یکیهه') IN ({year_list})"
        
        # تعیین جدول هزینه
        costs_table = self._get_costs_table_name(collection_name)
        if not costs_table:
            costs_table = 'costs_sheet1'  # fallback
        parent_col = '"عنوان_دستگاه_اصلي"'
        
        # تعیین جدول درآمد
        income_table = self._get_income_table_name(collection_name) or 'manabe3_sheet1'
        income_device_col = self._get_income_device_column(income_table)
        income_parent_col = self._get_income_parent_column(income_table)
        # ستون کد دستگاه اجرایی در manabe
        income_code_col = '"کد_دستگاه_اجرایی"' if 'manabe' in income_table else '"کد_دستگاه"'
        
        # CTE برای income
        income_cte = f"""
WITH income_agg AS (
    SELECT {income_code_col}, {income_device_col}, {income_parent_col},
           SUM(COALESCE(CAST("جمع_کل" AS DOUBLE PRECISION), 0)) as total_income
    FROM {income_table}
    WHERE {year_filter}
    GROUP BY {income_code_col}, {income_device_col}, {income_parent_col}
),
cost_agg AS (
    SELECT "کد_دستگاه_اجرايي" as کد_دستگاه, 
           "عنوان_دستگاه_اجرايي" as عنوان_دستگاه,
           {parent_col} as عنوان_دستگاه_اصلی,
           SUM(COALESCE(CAST("جمع_كل" AS DOUBLE PRECISION), 0)) as total_cost
    FROM {costs_table}
    WHERE {year_filter}
    GROUP BY "کد_دستگاه_اجرايي", "عنوان_دستگاه_اجرايي", {parent_col}
)
SELECT 
    COALESCE(i."عنوان_دستگاه", c.عنوان_دستگاه) as "عنوان_دستگاه",
    COALESCE(i."عنوان_دستگاه_اصلی", c.عنوان_دستگاه_اصلی) as "عنوان_دستگاه_اصلی",
    COALESCE(i.total_income, 0) as total_income,
    COALESCE(c.total_cost, 0) as total_cost,
    (COALESCE(i.total_income, 0) - COALESCE(c.total_cost, 0)) as balance
FROM income_agg i
FULL OUTER JOIN cost_agg c ON i."کد_دستگاه" = c.کد_دستگاه
"""
        
        # ORDER BY بر اساس نوع سوال
        query_lower = analysis.get('query_type', '').lower()
        if 'زیان' in str(analysis):
            # زیان‌ده‌ترین = کمترین تراز (منفی‌ترین)
            order_clause = "ORDER BY balance ASC"
        elif 'سود' in str(analysis):
            # سودآورترین = بیشترین تراز (مثبت‌ترین)
            order_clause = "ORDER BY balance DESC"
        else:
            # پیش‌فرض
            order_clause = "ORDER BY balance ASC"
        
        sql = f"{income_cte}\n{order_clause}\nLIMIT 10"
        
        logger.info(f"📊 Generated Cross-Table SQL:\n{sql}")
        return sql
    
    def _build_comparison_sql(
        self,
        analysis: Dict[str, Any],
        collection_name: str,
        table_type: str = 'incomes'
    ) -> Optional[str]:
        """
        ساخت SQL برای سوالات مقایسه‌ای
        
        پشتیبانی از:
        - year_over_year: مقایسه سال به سال
        - entity_vs_entity: مقایسه دو entity
        - trend: روند چند ساله
        """
        columns_map = self.database_service.get_collection_columns(collection_name)
        
        comparison_info = analysis.get('comparison_info', {})
        if not comparison_info:
            return None
        
        comparison_type = comparison_info.get('comparison_type')
        if not comparison_type:
            return None
        
        # تنظیمات جدول بر اساس نوع
        if table_type == 'costs':
            costs_table = self._get_costs_table_name(collection_name)
            if not costs_table:
                return None
            table_name = costs_table
            device_column = '"عنوان_دستگاه_اجرايي"'
            parent_column = '"عنوان_دستگاه_اصلي"'
            total_column = '"جمع_كل"'
        else:
            income_table = self._get_income_table_name(collection_name)
            if not income_table:
                return None
            table_name = income_table
            device_column = self._get_income_device_column(income_table)
            parent_column = self._get_income_parent_column(income_table)
            total_column = '"جمع_کل"'
        
        entity_filter = analysis['filters'].get('entity_filter')
        years = analysis.get('years', [])
        comparison_entities = comparison_info.get('comparison_entities', [])
        comparison_column = comparison_info.get('comparison_column')
        comparison_hierarchy_level = comparison_info.get('comparison_hierarchy_level', 'دستگاه')
        
        logger.info(f"🔄 Building Comparison SQL: type={comparison_type}, entities={comparison_entities}, level={comparison_hierarchy_level}")
        
        # ========== ENTITY_COMPARISON: مقایسه X با Y (پشتیبانی از سلسله‌مراتب) ==========
        if comparison_type in ('entity_comparison', 'entity_vs_entity') and comparison_entities:
            return self._build_aggregated_entity_comparison_sql(
                comparison_entities=comparison_entities,
                comparison_column=comparison_column,
                comparison_hierarchy_level=comparison_hierarchy_level,
                years=years,
                table_name=table_name,
                device_column=device_column,
                parent_column=parent_column,
                total_column=total_column,
                collection_name=collection_name,
                table_type=table_type,
            )
        
        # ========== BALANCE: تراز (درآمد - مصارف) ==========
        if comparison_type == 'balance':
            return self._build_balance_sql(
                entity=comparison_info.get('base_entity'),
                years=years,
                collection_name=collection_name,
            )
        
        # ===== YEAR_OVER_YEAR: مقایسه سال به سال =====
        if comparison_type == 'year_over_year':
            base_year = comparison_info.get('base_year')
            compare_years = comparison_info.get('compare_years', [])
            
            if not base_year:
                if years:
                    base_year = max(years, key=int)
                else:
                    return None
            
            if not compare_years and base_year:
                # اگر سال‌های مقایسه نبود، سال قبلی را در نظر بگیر
                compare_years = [str(int(base_year) - 1)]
            
            all_years = [base_year] + compare_years
            year_list = ', '.join([f"'{y}'" for y in all_years])
            
            # ساخت SQL با GROUP BY سال برای مقایسه
            where_conditions = []
            
            if entity_filter:
                # تبدیل entity_filter برای جدول costs
                if table_type == 'costs':
                    costs_filter = entity_filter.replace('"عنوان_دستگاه"', device_column)
                    costs_filter = costs_filter.replace('"عنوان_دستگاه_اصلی"', parent_column)
                    where_conditions.append(f"({costs_filter})")
                else:
                    where_conditions.append(f"({entity_filter})")
            
            where_conditions.append(f"TRANSLATE(\"سال\", 'يكيۀة', 'یکیهه') IN ({year_list})")
            where_clause = f"WHERE {' AND '.join(where_conditions)}"
            
            sql = f"""
WITH yearly_data AS (
    SELECT 
        "سال"::text AS year,
        SUM(COALESCE(CAST({total_column} AS DOUBLE PRECISION), 0)) AS total_amount
    FROM {table_name}
    {where_clause}
    GROUP BY "سال"
    ORDER BY "سال"
)
SELECT 
    year,
    total_amount,
    LAG(total_amount) OVER (ORDER BY year) AS prev_amount,
    total_amount - LAG(total_amount) OVER (ORDER BY year) AS change_amount,
    CASE 
        WHEN LAG(total_amount) OVER (ORDER BY year) > 0 
        THEN ROUND(((total_amount - LAG(total_amount) OVER (ORDER BY year)) / LAG(total_amount) OVER (ORDER BY year) * 100)::numeric, 2)
        ELSE 0 
    END AS change_percent
FROM yearly_data
ORDER BY year"""
            
            logger.info(f"📊 Generated Year-over-Year SQL:\n{sql}")
            return sql
        
        # ===== ENTITY_VS_ENTITY: مقایسه دو entity =====
        elif comparison_type == 'entity_vs_entity':
            base_entity = comparison_info.get('base_entity')
            compare_entity = comparison_info.get('compare_entity')
            
            # اگر دو entity نداریم، از entity_names استفاده کن
            entity_names = analysis.get('entity_names', [])
            if not base_entity and entity_names:
                base_entity = entity_names[0] if len(entity_names) > 0 else None
            if not compare_entity and len(entity_names) > 1:
                compare_entity = entity_names[1]
            
            if not base_entity or not compare_entity:
                return None
            
            # ساخت فیلتر برای هر دو entity
            safe_base = base_entity.replace("'", "''")
            safe_compare = compare_entity.replace("'", "''")
            
            year_filter = ""
            if years:
                year_list = ', '.join([f"'{y}'" for y in years])
                year_filter = f"AND TRANSLATE(\"سال\", 'يكيۀة', 'یکیهه') IN ({year_list})"
            
            sql = f"""
WITH entity_data AS (
    SELECT 
        CASE 
            WHEN TRANSLATE({device_column}, 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%{safe_base}%' 
                 OR TRANSLATE({parent_column}, 'يكiۀةأإٱآ', 'یکیهههااا') ILIKE '%{safe_base}%'
            THEN '{base_entity}'
            WHEN TRANSLATE({device_column}, 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%{safe_compare}%'
                 OR TRANSLATE({parent_column}, 'يكiۀةأإٱآ', 'یکیهههااا') ILIKE '%{safe_compare}%'
            THEN '{compare_entity}'
        END AS entity_name,
        SUM(COALESCE(CAST({total_column} AS DOUBLE PRECISION), 0)) AS total_amount
    FROM {table_name}
    WHERE (
        TRANSLATE({device_column}, 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%{safe_base}%'
        OR TRANSLATE({parent_column}, 'يكiۀةأإٱآ', 'یکیهههااا') ILIKE '%{safe_base}%'
        OR TRANSLATE({device_column}, 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE '%{safe_compare}%'
        OR TRANSLATE({parent_column}, 'يكiۀةأإٱآ', 'یکیهههااا') ILIKE '%{safe_compare}%'
    )
    {year_filter}
    GROUP BY entity_name
)
SELECT 
    entity_name,
    total_amount,
    total_amount - FIRST_VALUE(total_amount) OVER () AS difference_from_first
FROM entity_data
WHERE entity_name IS NOT NULL
ORDER BY total_amount DESC"""
            
            logger.info(f"📊 Generated Entity-vs-Entity SQL:\n{sql}")
            return sql
        
        # ===== TREND: روند چند ساله =====
        elif comparison_type == 'trend':
            compare_years = comparison_info.get('compare_years', years)
            if not compare_years:
                return None
            
            year_list = ', '.join([f"'{y}'" for y in compare_years])
            
            where_conditions = []
            if entity_filter:
                if table_type == 'costs':
                    costs_filter = entity_filter.replace('"عنوان_دستگاه"', device_column)
                    costs_filter = costs_filter.replace('"عنوان_دستگاه_اصلی"', parent_column)
                    where_conditions.append(f"({costs_filter})")
                else:
                    where_conditions.append(f"({entity_filter})")
            
            where_conditions.append(f"TRANSLATE(\"سال\", 'يكيۀة', 'یکیهه') IN ({year_list})")
            where_clause = f"WHERE {' AND '.join(where_conditions)}"
            
            sql = f"""
SELECT 
    "سال"::text AS year,
    SUM(COALESCE(CAST({total_column} AS DOUBLE PRECISION), 0)) AS total_amount
FROM {table_name}
{where_clause}
GROUP BY "سال"
ORDER BY "سال" """
            
            logger.info(f"📊 Generated Trend SQL:\n{sql}")
            return sql
        
        return None

    def _build_aggregated_entity_comparison_sql(
        self,
        comparison_entities: List[str],
        comparison_column: Optional[str],
        comparison_hierarchy_level: str,
        years: List[str],
        table_name: str,
        device_column: str,
        parent_column: str,
        total_column: str,
        collection_name: str,
        table_type: str = 'incomes',
    ) -> Optional[str]:
        """
        ساخت SQL مقایسه‌ای با SUM/GROUP BY برای مقایسه دو یا چند entity.
        
        این متد برای همه انواع مقایسه استفاده می‌شود:
        - مقایسه بخش اول با بخش دوم (hierarchy-level)
        - مقایسه دستگاه X با دستگاه Y (entity-level)
        
        خروجی: aggregate با SUM per entity (نه raw rows)
        """
        if not comparison_entities:
            return None
        
        year_filter = ""
        if years:
            year_list = ', '.join([f"'{y}'" for y in years])
            year_filter = f"AND TRANSLATE(\"سال\", 'يكيۀة', 'یکیهه') IN ({year_list})"
        
        # تعیین ستون جستجو و ستون نمایش
        if comparison_column:
            # مقایسه بر اساس ستون سلسله‌مراتبی (بخش/قسمت/بند/جزء)
            search_col = comparison_column  # e.g. "عنوان_بخش"
            display_col = comparison_column
            is_hierarchy = True
        else:
            # مقایسه بر اساس ستون دستگاه
            search_col = None
            display_col = device_column  # e.g. "عنوان_دستگاه_اجرایی"
            is_hierarchy = False
        
        # تعیین ستون‌های مبلغ
        if table_type == 'incomes':
            income_table = self._get_income_table_name(collection_name)
            if income_table and 'manabe3' in income_table:
                # manabe3: ملي_جمع_کل و استاني_جمع_کل
                amount_expr = 'SUM(COALESCE(CAST("ملي_جمع_کل" AS DOUBLE PRECISION), 0)) + SUM(COALESCE(CAST("استاني_جمع_کل" AS DOUBLE PRECISION), 0))'
                amount_cols = [
                    'SUM(COALESCE(CAST("ملي_جمع_کل" AS DOUBLE PRECISION), 0)) AS total_national',
                    'SUM(COALESCE(CAST("استاني_جمع_کل" AS DOUBLE PRECISION), 0)) AS total_regional',
                    f'SUM(COALESCE(CAST("ملي_جمع_کل" AS DOUBLE PRECISION), 0)) + SUM(COALESCE(CAST("استاني_جمع_کل" AS DOUBLE PRECISION), 0)) AS total_amount',
                ]
            else:
                # manabe: ملی_جمع_کل و استانی_جمع_کل
                amount_expr = 'SUM(COALESCE(CAST("ملی_جمع_کل" AS DOUBLE PRECISION), 0)) + SUM(COALESCE(CAST("استانی_جمع_کل" AS DOUBLE PRECISION), 0))'
                amount_cols = [
                    'SUM(COALESCE(CAST("ملی_جمع_کل" AS DOUBLE PRECISION), 0)) AS total_national',
                    'SUM(COALESCE(CAST("استانی_جمع_کل" AS DOUBLE PRECISION), 0)) AS total_regional',
                    f'SUM(COALESCE(CAST("ملی_جمع_کل" AS DOUBLE PRECISION), 0)) + SUM(COALESCE(CAST("استانی_جمع_کل" AS DOUBLE PRECISION), 0)) AS total_amount',
                ]
        else:
            # masaref
            amount_cols = [
                f'SUM(COALESCE(CAST({total_column} AS DOUBLE PRECISION), 0)) AS total_amount',
            ]
        
        # ساخت CASE WHEN برای نرمالایز کردن entity names
        case_parts = []
        where_parts = []
        
        for entity in comparison_entities:
            safe_entity = entity.replace("'", "''")
            
            if is_hierarchy and comparison_column:
                # برای hierarchy: جستجو در ستون hierarchy
                col_clean = comparison_column.strip('"')
                case_parts.append(
                    f"WHEN TRANSLATE({comparison_column}, 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_entity}%', 'يكيۀةأإٱآ', 'یکیهههااا') THEN '{entity}'"
                )
                where_parts.append(
                    f"TRANSLATE({comparison_column}, 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_entity}%', 'يكيۀةأإٱآ', 'یکیهههااا')"
                )
            else:
                # برای دستگاه: جستجو در هر دو ستون دستگاه
                case_parts.append(
                    f"WHEN TRANSLATE({device_column}, 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_entity}%', 'يكيۀةأإٱآ', 'یکیهههااا') "
                    f"OR TRANSLATE({parent_column}, 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_entity}%', 'يكيۀةأإٱآ', 'یکیهههااا') "
                    f"THEN '{entity}'"
                )
                where_parts.append(
                    f"(TRANSLATE({device_column}, 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_entity}%', 'يكيۀةأإٱآ', 'یکیهههااا') "
                    f"OR TRANSLATE({parent_column}, 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_entity}%', 'يكيۀةأإٱآ', 'یکیهههااا'))"
                )
        
        case_expr = "CASE\n        " + "\n        ".join(case_parts) + "\n    END AS entity_name"
        where_clause = f"WHERE ({' OR '.join(where_parts)}) {year_filter}"
        
        # ستون‌های مبلغ برای subquery (بدون AS)
        if table_type == 'incomes':
            income_table = self._get_income_table_name(collection_name)
            if income_table and 'manabe3' in income_table:
                raw_cols = ['"ملي_جمع_کل"', '"استاني_جمع_کل"']
            else:
                raw_cols = ['"ملی_جمع_کل"', '"استانی_جمع_کل"']
            inner_select = ', '.join(raw_cols)
        else:
            total_col_clean = total_column.strip('"')
            raw_cols = [total_column]
            inner_select = total_column
        
        # outer aggregate
        outer_select_parts = ['entity_name'] + amount_cols
        outer_select = ',\n    '.join(outer_select_parts)
        
        sql = f"""SELECT
    {outer_select}
FROM (
    SELECT
        {case_expr},
        {inner_select}
    FROM {table_name}
    {where_clause}
) sub
WHERE entity_name IS NOT NULL
GROUP BY entity_name
ORDER BY total_amount DESC"""
        
        logger.info(f"📊 Generated Aggregated Entity Comparison SQL (level={comparison_hierarchy_level}):\n{sql[:400]}")
        return sql

    def _build_balance_sql(
        self,
        entity: Optional[str],
        years: List[str],
        collection_name: str,
    ) -> Optional[str]:
        """
        ساخت SQL تراز = درآمد - مصارف برای یک entity.
        
        این متد دو SQL جداگانه می‌سازد (یکی برای manabe، یکی برای masaref)
        و نتایج را در Python ترکیب می‌کنیم.
        
        توجه: این متد یک marker SQL برمی‌گرداند که در execute_with_analysis پردازش می‌شود.
        """
        if not entity:
            return None
        
        income_table = self._get_income_table_name(collection_name)
        costs_table = self._get_costs_table_name(collection_name)
        
        if not income_table or not costs_table:
            return None
        
        year_filter = ""
        if years:
            year_list = ', '.join([f"'{y}'" for y in years])
            year_filter = f"AND TRANSLATE(\"سال\", 'يكيۀة', 'یکیهه') IN ({year_list})"
        
        safe_entity = entity.replace("'", "''")
        
        # ستون‌های درآمد بر اساس جدول
        if 'manabe3' in income_table:
            income_amount = '"ملي_جمع_کل"'
        else:
            income_amount = '"ملی_جمع_کل"'
        
        # SQL ترکیبی: جمع درآمد و جمع مصارف در یک query با CTE
        sql = f"""WITH income_total AS (
    SELECT 
        '{entity}' AS entity_name,
        'درآمد' AS type,
        SUM(COALESCE(CAST({income_amount} AS DOUBLE PRECISION), 0)) AS total_amount
    FROM {income_table}
    WHERE (
        TRANSLATE("عنوان_دستگاه_اجرایی", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_entity}%', 'يكيۀةأإٱآ', 'یکیهههااا')
        OR TRANSLATE("عنوان_دستگاه_اصلی", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_entity}%', 'يكيۀةأإٱآ', 'یکیهههااا')
    ) {year_filter}
),
expense_total AS (
    SELECT
        '{entity}' AS entity_name,
        'مصارف' AS type,
        SUM(COALESCE(CAST("جمع_كل" AS DOUBLE PRECISION), 0)) AS total_amount
    FROM {costs_table}
    WHERE (
        TRANSLATE("عنوان_دستگاه_اجرايي", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_entity}%', 'يكيۀةأإٱآ', 'یکیهههااا')
        OR TRANSLATE("عنوان_دستگاه_اصلي", 'يكيۀةأإٱآ', 'یکیهههااا') ILIKE TRANSLATE('%{safe_entity}%', 'يكيۀةأإٱآ', 'یکیهههااا')
    ) {year_filter}
),
balance AS (
    SELECT
        i.entity_name,
        i.total_amount AS income_amount,
        e.total_amount AS expense_amount,
        (i.total_amount - e.total_amount) AS balance_amount,
        CASE WHEN (i.total_amount - e.total_amount) >= 0 THEN 'مثبت' ELSE 'منفی' END AS balance_status
    FROM income_total i
    JOIN expense_total e ON i.entity_name = e.entity_name
)
SELECT * FROM balance"""
        
        logger.info(f"📊 Generated Balance SQL for entity='{entity}':\n{sql[:400]}")
        return sql

    def _build_costs_specialized_sql(
        self,
        analysis: Dict[str, Any],
        collection_name: str,
        original_query: str = ""
    ) -> Optional[str]:
        """ساخت SQL تخصصی برای سوالات هزینه‌ای"""
        from config.collection_instructions import CollectionInstructions, normalize_persian
        
        costs_table = self._get_costs_table_name(collection_name)
        if not costs_table:
            return None

        table_name = costs_table
        device_column = '"عنوان_دستگاه_اجرايي"'
        parent_column = '"عنوان_دستگاه_اصلي"'
        
        # تشخیص ستون هدف بر اساس دستورالعمل‌های collection
        target_column = CollectionInstructions.detect_target_column(original_query, collection_name)
        if target_column:
            total_column = f'"{target_column}"'
            logger.info(f"📌 Detected target column from instructions: {target_column}")
        else:
            total_column = '"جمع_كل"'
        
        current_column = '"جمع_براورد_اعتبارات_هزینه_ای"'
        capital_column = '"جمع_برآورد_تملك_دارايي_هاي_سرمايه_"'

        where_conditions: List[str] = []
        
        # کلمات عمومی که نباید به عنوان entity filter استفاده شوند
        generic_words = {
            'جمع', 'کل', 'همه', 'تمام', 'مجموع', 'میانگین', 'بیشترین', 'کمترین',
            'هزینه', 'هزينه', 'درآمد', 'درامد', 'بودجه', 'اعتبار', 'مبلغ',
            'چقدر', 'چند', 'است', 'باشد', 'شود', 'بده', 'نشان', 'عمومی', 'اختصاصی',
            'متفرقه', 'سرمایه', 'دارایی', 'تملک', 'براورد', 'برآورد'
        }
        
        # اولویت: استفاده از entity_filter از QueryAnalyzer (که عبارات کامل را حفظ می‌کند)
        entity_filter = analysis['filters'].get('entity_filter')
        has_valid_entity_filter = False
        logger.info(f"🔍 [COSTS_SQL] entity_filter={entity_filter!r}, entity_names={analysis.get('entity_names')}")
        
        if entity_filter:
            # بررسی که entity_filter فقط شامل کلمات عمومی نباشد
            filter_text = entity_filter.lower()
            filter_words = set(re.findall(r'[\u0600-\u06FF]+', filter_text))
            is_only_generic = filter_words and filter_words.issubset(generic_words)
            
            if not is_only_generic:
                # 🔧 FIX: استفاده از جستجوی سلسله‌مراتبی (parent-first) به جای OR ساده
                # اگر entity در parent_column پیدا شود، فقط از parent استفاده کن
                # (همه ردیف‌های زیرمجموعه آن دستگاه اصلی نمایش داده می‌شوند)
                entity_names_for_hier = [
                    e for e in (analysis.get('entity_names') or [])
                    if normalize_persian(e.lower()) not in generic_words
                ]
                if entity_names_for_hier:
                    _h_years = []
                    for _yr in (analysis.get('years') or []):
                        _h_years.append(CollectionInstructions.normalize_year(str(_yr)))
                    hier_filter = self._build_hierarchy_entity_filter(
                        entity_names_for_hier,
                        device_column,
                        parent_column,
                        table_name,
                        collection_name,
                        _h_years
                    )
                    if hier_filter:
                        where_conditions.append(hier_filter)
                        has_valid_entity_filter = True
                        logger.info(f"📊 [HIERARCHY_FILTER] Used hierarchy filter for: {entity_names_for_hier}")
                
                if not has_valid_entity_filter:
                    # fallback: از entity_filter مستقیم (OR ساده) استفاده کن
                    costs_filter = entity_filter
                    costs_filter = costs_filter.replace('"عنوان_دستگاه_اجرایی"', device_column)
                    costs_filter = costs_filter.replace('"عنوان_دستگاه_اجرايي"', device_column)
                    costs_filter = costs_filter.replace('"عنوان_دستگاه"', device_column)
                    costs_filter = costs_filter.replace('"عنوان_دستگاه_اصلی"', parent_column)
                    costs_filter = costs_filter.replace('"عنوان_دستگاه_اصلي"', parent_column)
                    where_conditions.append(f"({costs_filter})")
                    has_valid_entity_filter = True
        
        # اگر entity_filter کافی نبود، از entity_names استفاده کنیم
        if not has_valid_entity_filter:
            entity_names = analysis.get('entity_names') or []
            if entity_names:
                valid_entities = [
                    entity for entity in entity_names
                    if normalize_persian(entity.lower()) not in generic_words
                ]
                if valid_entities:
                    # 🔧 FIX: استفاده از جستجوی سلسله‌مراتبی (parent-first)
                    # ابتدا در parent_column (عنوان_دستگاه_اصلي) جستجو می‌کنیم
                    # اگر نتیجه داشت، فقط از parent استفاده می‌کنیم (همه ردیف‌های آن دستگاه اصلی)
                    # اگر نتیجه نداشت، از هر دو (parent OR exec) استفاده می‌کنیم
                    _norm_years = []
                    for _yr in (analysis.get('years') or []):
                        _norm_years.append(CollectionInstructions.normalize_year(str(_yr)))
                    hierarchy_filter = self._build_hierarchy_entity_filter(
                        valid_entities,
                        device_column,
                        parent_column,
                        table_name,
                        collection_name,
                        _norm_years
                    )
                    if hierarchy_filter:
                        where_conditions.append(hierarchy_filter)

        if analysis['years']:
            # نرمال‌سازی سال‌ها
            normalized_years = []
            for year in analysis['years']:
                normalized_years.append(CollectionInstructions.normalize_year(str(year)))
            year_list = ', '.join([f"'{year}'" for year in normalized_years])
            where_conditions.append(f"TRANSLATE(\"سال\", 'يكيۀة', 'یکیهه') IN ({year_list})")

        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""

        # انتخاب ستون‌های مناسب برای SELECT
        # 🆕 تشخیص اینکه آیا سوال نیاز به تفکیک دارد
        query_lower_normalized = normalize_persian(original_query.lower())
        needs_breakdown = any(kw in query_lower_normalized for kw in [
            'جاری', 'جاري', 'سرمایه', 'سرمايه', 'عمرانی', 'عمراني',
            'تفکیک', 'تفكيك', 'تفصیلی', 'تفصيلي', 'جزییات', 'جزييات',
            'هزینه ای', 'هزينه اي', 'تملک', 'تملك', 'دارایی', 'دارايي'
        ])
        
        if target_column and target_column != "جمع_كل":
            # اگر ستون خاصی درخواست شده، فقط آن را نمایش دهیم
            amount_expressions = [
                f"SUM(COALESCE(CAST({total_column} AS DOUBLE PRECISION), 0)) AS total_amount"
            ]
        elif needs_breakdown:
            # نمایش جمع کل به همراه تفکیک (فقط اگر سوال درباره تفکیک باشد)
            amount_expressions = [
                f"SUM(COALESCE(CAST({total_column} AS DOUBLE PRECISION), 0)) AS total_amount",
                f"SUM(COALESCE(CAST({current_column} AS DOUBLE PRECISION), 0)) AS total_current_cost",
                f"SUM(COALESCE(CAST({capital_column} AS DOUBLE PRECISION), 0)) AS total_capital_cost"
            ]
        else:
            # 🆕 فقط جمع کل را نمایش بده (بدون تفکیک)
            amount_expressions = [
                f"SUM(COALESCE(CAST({total_column} AS DOUBLE PRECISION), 0)) AS total_amount"
            ]

        aggregation = analysis.get('aggregation', {})
        query_type = analysis.get('query_type')
        needs_groupby = (
            query_type in ('device', 'amount_and_device')
            or aggregation.get('needs_groupby')
        )

        # 🔧 FIX: اگر entity در parent_column پیدا شده (توسط _build_hierarchy_entity_filter)
        # باید GROUP BY بر اساس exec و parent باشد تا همه ردیف‌های فرزند نمایش داده شوند
        # تشخیص: اگر where شامل فقط parent_column است (نه device_column)
        # این یعنی entity در parent پیدا شده و باید breakdown نمایش داده شود
        hierarchy_where = where_conditions[0] if where_conditions else ""
        _parent_col_name = parent_column.strip('"')
        _device_col_name = device_column.strip('"')
        _only_parent_filter = (
            hierarchy_where
            and _parent_col_name in hierarchy_where
            and _device_col_name not in hierarchy_where
        )
        if _only_parent_filter:
            needs_groupby = True
            logger.info(f"📊 [HIERARCHY_FIX] Entity found in parent column → forcing GROUP BY for breakdown")

        if needs_groupby:
            # اگر چندین سال درخواست شده، باید سال را هم در GROUP BY اضافه کنیم
            # تا per-year breakdown نمایش داده شود
            multi_year = len(analysis.get('years') or []) > 1
            if multi_year:
                year_col = f"TRANSLATE(\"سال\", 'يكيۀة', 'یکیهه')"
                select_clause = (
                    f"SELECT {device_column} AS \"عنوان_دستگاه\", "
                    f"{parent_column} AS \"عنوان_دستگاه_اصلی\", "
                    f"{year_col} AS \"سال\", "
                    + ', '.join(amount_expressions)
                )
                group_clause = f"GROUP BY {device_column}, {parent_column}, {year_col}"
                order_clause = f"ORDER BY {year_col}, total_amount DESC"
            else:
                select_clause = (
                    f"SELECT {device_column} AS \"عنوان_دستگاه\", "
                    f"{parent_column} AS \"عنوان_دستگاه_اصلی\", "
                    + ', '.join(amount_expressions)
                )
                group_clause = f"GROUP BY {device_column}, {parent_column}"
                order_clause = "ORDER BY total_amount DESC"
        else:
            select_clause = "SELECT " + ', '.join(amount_expressions)
            group_clause = ""
            order_clause = ""

        sql = (
            f"{select_clause} "
            f"FROM {table_name} "
            f"{where_clause} "
            f"{group_clause} "
            f"{order_clause}"
        ).strip()

        logger.info(f"📊 Generated Costs SQL:\n{sql}")
        return sql

