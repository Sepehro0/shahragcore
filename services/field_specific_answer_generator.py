# -*- coding: utf-8 -*-
"""
Field-Specific Answer Generator
تولید پاسخ هوشمند بر اساس فیلد خاصی که کاربر پرسیده است
"""

import logging
import re
from typing import Dict, Any, Optional, List
from config.collection_instructions import CollectionInstructions, normalize_persian

logger = logging.getLogger(__name__)


class FieldSpecificAnswerGenerator:
    """
    تولید پاسخ هوشمند که به جای همیشه جمع_کل را نشان دادن،
    دقیقاً فیلدی که کاربر پرسیده را برمی‌گرداند
    """
    
    def __init__(self):
        """Initialize field-specific answer generator"""
        pass
    
    def detect_requested_field(
        self,
        user_query: str,
        collection_name: str = 'budget_financial'
    ) -> Optional[str]:
        """
        تشخیص فیلد مورد نظر کاربر از query
        
        Args:
            user_query: سوال کاربر
            collection_name: نام کالکشن
            
        Returns:
            نام فیلد در دیتابیس (مثل 'براورد_اعتبارات_هزینه_ای_عمومی')
        """
        # استفاده از detect_target_column موجود
        target_column = CollectionInstructions.detect_target_column(user_query, collection_name)
        
        if target_column:
            logger.info(f"🎯 Detected requested field: {target_column}")
            return target_column
        
        # اگر تشخیص نداد، default به جمع_کل
        logger.warning(f"⚠️ Could not detect specific field, defaulting to جمع_کل")
        return "جمع_كل"
    
    def get_field_display_name(self, field_name: str) -> str:
        """
        تبدیل نام فیلد دیتابیس به نام قابل نمایش فارسی
        
        Args:
            field_name: نام فیلد در دیتابیس
            
        Returns:
            نام فارسی برای نمایش
        """
        # نقشه نام فیلدها به نام‌های فارسی
        display_names = {
            # اعتبارات هزینه‌ای
            'براورد_اعتبارات_هزینه_ای_عمومی': 'اعتبارات هزینه‌ای عمومی',
            'برآورد_اعتبارات_هزینه_ای_متفرقه': 'اعتبارات هزینه‌ای متفرقه',
            'براورد_اعتبارات_هزینه_ای_اختصاصی': 'اعتبارات هزینه‌ای اختصاصی',
            'جمع_براورد_اعتبارات_هزینه_ای': 'جمع اعتبارات هزینه‌ای',
            'براورد_اعتبارات_هزینه_ای_یارانه_ها': 'اعتبارات هزینه‌ای یارانه‌ها',
            
            # تملک دارایی
            'براورد_تملك_دارايي_هاي_سرمايه_اي_ع': 'تملک دارایی سرمایه‌ای عمومی',
            'براورد_تملك_دارايي_هاي_سرمايه_اي_م': 'تملک دارایی سرمایه‌ای متفرقه',
            'براورد_تملك_دارايي_هاي_سرمايه_اي_ا': 'تملک دارایی سرمایه‌ای اختصاصی',
            'جمع_برآورد_تملك_دارايي_هاي_سرمايه_': 'جمع تملک دارایی سرمایه‌ای',
            'براورد_تملک_دارایی_های_سرمایه_ای_ی': 'تملک دارایی سرمایه‌ای یارانه',
            
            # درآمد
            'ملی_در_آمد_عمومی': 'درآمد عمومی ملی',
            'استانی_در_آمد_عمومی': 'درآمد عمومی استانی',
            'جمع_در_آمد_عمومی': 'جمع درآمد عمومی',
            'ملی_در_آمد_اختصاصی': 'درآمد اختصاصی ملی',
            'استانی_در_آمد_اختصاصی': 'درآمد اختصاصی استانی',
            'جمع_در_آمد_اختصاصی': 'جمع درآمد اختصاصی',
            # manabe_sheet1 uses Persian ی
            'ملی_جمع_کل': 'جمع منابع ملی',
            'استانی_جمع_کل': 'جمع منابع استانی',
            # manabe3_sheet1 uses Arabic ي
            'ملي_جمع_کل': 'جمع منابع ملی',
            'استاني_جمع_کل': 'جمع منابع استانی',
            
            # جمع کل
            'جمع_كل': 'جمع کل',
            'جمع_کل': 'جمع کل',
        }
        
        return display_names.get(field_name, field_name.replace('_', ' '))
    
    def extract_field_value_from_row(
        self,
        row: Dict[str, Any],
        requested_field: str
    ) -> Optional[Any]:
        """
        استخراج مقدار فیلد خاص از یک row
        
        Args:
            row: یک ردیف از نتایج دیتابیس
            requested_field: نام فیلد مورد نظر
            
        Returns:
            مقدار فیلد یا None
        """
        # جستجوی مستقیم
        if requested_field in row:
            return row[requested_field]
        
        # جستجوی با normalize کردن کلیدها
        normalized_field = normalize_persian(requested_field.lower())
        for key, value in row.items():
            normalized_key = normalize_persian(key.lower())
            if normalized_key == normalized_field:
                return value
        
        # ⚠️ CRITICAL: اگر total_amount موجود است، آن را برنگردان!
        # چون total_amount ممکن است جمع_کل باشد نه فیلد خاص
        # به جای آن، از detail_rows استفاده کن
        
        logger.warning(f"⚠️ Field '{requested_field}' not found in row. Available keys: {list(row.keys())}")
        return None
    
    def format_answer_with_specific_field(
        self,
        user_query: str,
        database_results: Dict[str, Any],
        collection_name: str = 'budget_financial'
    ) -> str:
        """
        فرمت کردن پاسخ با استفاده از فیلد خاص
        
        Args:
            user_query: سوال کاربر
            database_results: نتایج دیتابیس
            collection_name: نام کالکشن
            
        Returns:
            پاسخ فرمت شده
        """
        # تشخیص فیلد مورد نظر
        requested_field = self.detect_requested_field(user_query, collection_name)
        field_display_name = self.get_field_display_name(requested_field)
        
        # استخراج rows
        rows = database_results.get('rows', []) or database_results.get('results', [])
        
        if not rows:
            return f"متأسفانه اطلاعاتی درباره {field_display_name} پیدا نشد."
        
        # اگر فقط یک row داریم (aggregation)
        if len(rows) == 1:
            row = rows[0]
            value = self.extract_field_value_from_row(row, requested_field)
            
            if value is not None:
                # فرمت کردن عدد
                try:
                    numeric_value = float(str(value).replace(',', ''))
                    formatted_value = f"{numeric_value:,.0f}"
                except (ValueError, TypeError):
                    formatted_value = str(value)
                
                # ساخت پاسخ
                answer = f"{field_display_name} مطابق بودجه مصوب، **{formatted_value}** میلیون ریال است."
                
                # اضافه کردن اطلاعات دستگاه اگر موجود باشد
                device_name = row.get('عنوان_دستگاه') or row.get('عنوان_دستگاه_اجرایی') or row.get('عنوان_دستگاه_اجرايي')
                if device_name:
                    answer = f"{field_display_name} **{device_name}** مطابق بودجه مصوب، **{formatted_value}** میلیون ریال است."
                
                # اضافه کردن سال اگر موجود باشد
                year = row.get('سال')
                if year:
                    answer = answer.replace('مطابق بودجه مصوب', f'در سال {year}')
                
                return answer
            else:
                # fallback: استفاده از total_amount
                total_amount = row.get('total_amount')
                if total_amount is not None:
                    try:
                        numeric_value = float(str(total_amount).replace(',', ''))
                        formatted_value = f"{numeric_value:,.0f}"
                        return f"{field_display_name} مطابق بودجه مصوب، **{formatted_value}** میلیون ریال است."
                    except (ValueError, TypeError):
                        pass
        
        # اگر چند row داریم (list)
        elif len(rows) > 1:
            total = 0.0
            valid_rows = 0
            
            for row in rows:
                value = self.extract_field_value_from_row(row, requested_field)
                if value is not None:
                    try:
                        numeric_value = float(str(value).replace(',', ''))
                        total += numeric_value
                        valid_rows += 1
                    except (ValueError, TypeError):
                        pass
            
            if valid_rows > 0:
                formatted_total = f"{total:,.0f}"
                return f"جمع {field_display_name} برای {valid_rows} دستگاه، **{formatted_total}** میلیون ریال است."
        
        # fallback: پاسخ عمومی
        return f"اطلاعات {field_display_name} در نتایج موجود است."
    
    def enhance_database_results(
        self,
        user_query: str,
        database_results: Dict[str, Any],
        collection_name: str = 'budget_financial'
    ) -> Dict[str, Any]:
        """
        بهبود نتایج دیتابیس با اضافه کردن اطلاعات فیلد خاص
        
        Args:
            user_query: سوال کاربر
            database_results: نتایج دیتابیس
            collection_name: نام کالکشن
            
        Returns:
            نتایج بهبود یافته
        """
        if not database_results or not database_results.get('success'):
            return database_results
        
        # تشخیص فیلد مورد نظر
        requested_field = self.detect_requested_field(user_query, collection_name)
        field_display_name = self.get_field_display_name(requested_field)
        
        # اضافه کردن metadata
        database_results['requested_field'] = requested_field
        database_results['requested_field_display'] = field_display_name
        
        # اگر rows موجود است، مقدار فیلد را استخراج کن
        rows = database_results.get('rows', []) or database_results.get('results', [])
        if rows:
            field_values = []
            for row in rows:
                value = self.extract_field_value_from_row(row, requested_field)
                if value is not None:
                    field_values.append(value)
            
            if field_values:
                database_results['field_values'] = field_values
                # محاسبه جمع
                try:
                    numeric_values = [float(str(v).replace(',', '')) for v in field_values]
                    database_results['field_total'] = sum(numeric_values)
                except (ValueError, TypeError):
                    pass
        
        logger.info(f"✅ Enhanced database results with field: {requested_field}")
        return database_results


# Global instance
_field_answer_generator = None

def get_field_answer_generator() -> FieldSpecificAnswerGenerator:
    """دریافت instance سینگلتون"""
    global _field_answer_generator
    if _field_answer_generator is None:
        _field_answer_generator = FieldSpecificAnswerGenerator()
    return _field_answer_generator

