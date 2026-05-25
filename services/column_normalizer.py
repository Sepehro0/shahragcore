"""
🔧 Column Normalizer - تبدیل دقیق نام ستون‌ها بر اساس جدول

این ماژول وظیفه normalize کردن نام ستون‌ها را بر اساس schema واقعی هر جدول انجام می‌دهد.

الگوهای حروف در جداول:
- manabe_sheet1: ✅ کاملاً فارسی (ی، ک)
- manabe3_sheet1: ⚠️ مخلوط (ستون‌های دستگاه: ی فارسی، بقیه: ي عربی، ک همه فارسی)
- masaref_sheet1: ✅ کاملاً فارسی (ی، ک)
- masaref2_sheet1: ⚠️ مخلوط (ستون‌های هزینه: ی فارسی، تملک: ي/ك عربی، دستگاه: ي عربی، جمع_كل: ك عربی)
- masaref3_sheet1: ⚠️ مخلوط (همان masaref2)
"""

from typing import Dict, Optional
import re


class ColumnNormalizer:
    """
    تبدیل هوشمند نام ستون‌ها بر اساس جدول
    """
    
    # 🎯 الگوی دقیق ستون‌های هر جدول
    # این mapping بر اساس schema واقعی database ساخته شده است
    
    MANABE_SHEET1_COLUMNS = {
        # دستگاه (ی فارسی)
        'عنوان_دستگاه_اجرایی': 'عنوان_دستگاه_اجرایی',
        'عنوان_دستگاه_اصلی': 'عنوان_دستگاه_اصلی',
        'کد_دستگاه_اجرایی': 'کد_دستگاه_اجرایی',
        # درآمد (ی فارسی)
        'ملی_جمع_کل': 'ملی_جمع_کل',
        'ملی_در_آمد_عمومی': 'ملی_در_آمد_عمومی',
        'ملی_در_آمد_اختصاصی': 'ملی_در_آمد_اختصاصی',
        'استانی_جمع_کل': 'استانی_جمع_کل',
        'استانی_در_آمد_عمومی': 'استانی_در_آمد_عمومی',
        'استانی_در_آمد_اختصاصی': 'استانی_در_آمد_اختصاصی',
        'جمع_در_آمد_عمومی': 'جمع_در_آمد_عمومی',
        'جمع_در_آمد_اختصاصی': 'جمع_در_آمد_اختصاصی',
        'جمع_کل': 'جمع_کل',
    }
    
    MANABE3_SHEET1_COLUMNS = {
        # دستگاه (ی فارسی)
        'عنوان_دستگاه_اجرایی': 'عنوان_دستگاه_اجرایی',
        'عنوان_دستگاه_اصلی': 'عنوان_دستگاه_اصلی',
        'کد_دستگاه_اجرایی': 'کد_دستگاه_اجرایی',
        # درآمد (ي عربی، ک فارسی)
        'ملي_جمع_کل': 'ملي_جمع_کل',
        'ملي_در_آمد_عمومي': 'ملي_در_آمد_عمومي',
        'ملي_در_آمد_اختصاصي': 'ملي_در_آمد_اختصاصي',
        'استاني_جمع_کل': 'استاني_جمع_کل',
        'استاني_در_آمد_عمومي': 'استاني_در_آمد_عمومي',
        'استاني_در_آمد_اختصاصي': 'استاني_در_آمد_اختصاصي',
        'جمع_در_آمد_عمومي': 'جمع_در_آمد_عمومي',
        'جمع_در_آمد_اختصاصي': 'جمع_در_آمد_اختصاصي',
        'جمع_کل': 'جمع_کل',
    }
    
    MASAREF_SHEET1_COLUMNS = {
        # دستگاه (ی فارسی)
        'عنوان_دستگاه_اجرایی': 'عنوان_دستگاه_اجرایی',
        'عنوان_دستگاه_اصلی': 'عنوان_دستگاه_اصلی',
        'کد_دستگاه_اجرایی': 'کد_دستگاه_اجرایی',
        # هزینه (ی فارسی)
        'براورد_اعتبارات_هزینه_ای_عمومی': 'براورد_اعتبارات_هزینه_ای_-_عمومی',
        'براورد_اعتبارات_هزینه_ای_اختصاصی': 'براورد_اعتبارات_هزینه_ای_-_اختصاصی',
        'براورد_اعتبارات_هزینه_ای_متفرقه': 'برآورد_اعتبارات_هزینه_ای_-_متفرقه',
        'براورد_اعتبارات_هزینه_ای_یارانه_ها': 'براورد_اعتبارات_هزینه_ای_-_یارانه_ها',
        'جمع_براورد_اعتبارات_هزینه_ای': 'جمع_براورد_اعتبارات_هزینه_ای',
        # تملک (ی فارسی، ک فارسی)
        'براورد_تملک_دارایی_های_سرمایه_ای_عمومی': 'براورد_تملک_دارایی_های_سرمایه_ای_-_عمومی',
        'براورد_تملک_دارایی_های_سرمایه_ای_اختصاصی': 'براورد_تملک_دارایی_های_سرمایه_ای_-_اختصاصی',
        'براورد_تملک_دارایی_های_سرمایه_ای_متفرقه': 'براورد_تملک_دارایی_های_سرمایه_ای_-_متفرقه',
        'براورد_تملک_دارایی_های_سرمایه_ای_یارانه_ها': 'براورد_تملک_دارایی_های_سرمایه_ای_-_یارانه_ها',
        'جمع_برآورد_تملک_دارایی_های_سرمایه_ای': 'جمع_برآورد_تملک_دارایی_های_سرمایه_ای',
        'جمع_کل': 'جمع_کل',
    }
    
    MASAREF2_SHEET1_COLUMNS = {
        # دستگاه (ي عربی)
        'عنوان_دستگاه_اجرايي': 'عنوان_دستگاه_اجرايي',
        'عنوان_دستگاه_اصلي': 'عنوان_دستگاه_اصلي',
        'کد_دستگاه_اجرايي': 'کد_دستگاه_اجرايي',
        # هزینه (ی فارسی)
        'براورد_اعتبارات_هزینه_ای_عمومی': 'براورد_اعتبارات_هزینه_ای_عمومی',
        'براورد_اعتبارات_هزینه_ای_اختصاصی': 'براورد_اعتبارات_هزینه_ای_اختصاصی',
        'برآورد_اعتبارات_هزینه_ای_متفرقه': 'برآورد_اعتبارات_هزینه_ای_متفرقه',
        'براورد_اعتبارات_هزینه_ای_یارانه_ها': 'براورد_اعتبارات_هزینه_ای_یارانه_ها',
        'جمع_براورد_اعتبارات_هزینه_ای': 'جمع_براورد_اعتبارات_هزینه_ای',
        # تملک (ي عربی، ك عربی)
        'براورد_تملك_دارايي_هاي_سرمايه_اي_عمومی': 'براورد_تملك_دارايي_هاي_سرمايه_اي_عمومی',
        'براورد_تملك_دارايي_هاي_سرمايه_اي_اختصاصی': 'براورد_تملك_دارايي_هاي_سرمايه_اي_اختصاصی',
        'براورد_تملك_دارايي_هاي_سرمايه_اي_متفرقه': 'براورد_تملك_دارايي_هاي_سرمايه_اي_متفرقه',
        'براورد_تملک_دارایی_های_سرمایه_ای_یارانه_ها': 'براورد_تملک_دارایی_های_سرمایه_ای_یارانه_ها',
        'جمع_برآورد_تملك_دارايي_هاي_سرمايه_اي': 'جمع_برآورد_تملك_دارايي_هاي_سرمايه_اي',
        'جمع_كل': 'جمع_كل',
    }
    
    MASAREF3_SHEET1_COLUMNS = MASAREF2_SHEET1_COLUMNS.copy()
    
    TABLE_COLUMNS = {
        'manabe_sheet1': MANABE_SHEET1_COLUMNS,
        'manabe3_sheet1': MANABE3_SHEET1_COLUMNS,
        'masaref_sheet1': MASAREF_SHEET1_COLUMNS,
        'masaref2_sheet1': MASAREF2_SHEET1_COLUMNS,
        'masaref3_sheet1': MASAREF3_SHEET1_COLUMNS,
    }
    
    @classmethod
    def normalize_column_name(cls, column_name: str, table_name: str) -> str:
        """
        تبدیل نام ستون به schema دقیق جدول
        
        Args:
            column_name: نام ستون (ممکن است با حروف فارسی یا عربی باشد)
            table_name: نام جدول (مثلاً masaref3_sheet1)
        
        Returns:
            نام ستون normalized شده بر اساس schema واقعی
        """
        if not table_name or not column_name:
            return column_name
        
        table_name = table_name.lower()
        
        # اگر جدول را نمی‌شناسیم، بدون تغییر برگردان
        if table_name not in cls.TABLE_COLUMNS:
            return column_name
        
        table_cols = cls.TABLE_COLUMNS[table_name]
        
        # اگر دقیقاً پیدا شد
        if column_name in table_cols:
            return table_cols[column_name]
        
        # اگر دقیقاً نبود، fuzzy matching
        # تبدیل تمام حالت‌های ممکن و جستجو
        normalized = cls._normalize_all_variants(column_name)
        
        for variant in normalized:
            if variant in table_cols:
                return table_cols[variant]
        
        # اگر هیچکدام پیدا نشد، خود ستون را برگردان
        return column_name
    
    @classmethod
    def _normalize_all_variants(cls, column_name: str) -> list:
        """تولید تمام variant های ممکن یک نام ستون"""
        variants = [column_name]
        
        # Variant 1: تبدیل ی→ي
        v1 = column_name.replace('ی', 'ي').replace('های', 'هاي')
        if v1 not in variants:
            variants.append(v1)
        
        # Variant 2: تبدیل ک→ك
        v2 = column_name.replace('ک', 'ك')
        if v2 not in variants:
            variants.append(v2)
        
        # Variant 3: ترکیب هر دو
        v3 = column_name.replace('ی', 'ي').replace('های', 'هاي').replace('ک', 'ك')
        if v3 not in variants:
            variants.append(v3)
        
        # Variant 4: تبدیل ي→ی
        v4 = column_name.replace('ي', 'ی').replace('هاي', 'های')
        if v4 not in variants:
            variants.append(v4)
        
        # Variant 5: تبدیل ك→ک
        v5 = column_name.replace('ك', 'ک')
        if v5 not in variants:
            variants.append(v5)
        
        # Variant 6: ترکیب هر دو (عکس)
        v6 = column_name.replace('ي', 'ی').replace('هاي', 'های').replace('ك', 'ک')
        if v6 not in variants:
            variants.append(v6)
        
        # Variant 7: حذف/اضافه دش (-)
        if '_-_' in column_name:
            v7 = column_name.replace('_-_', '_')
            if v7 not in variants:
                variants.append(v7)
        else:
            # جایگزینی _ با _-_ در موقعیت‌های خاص
            pass
        
        return variants
    
    @classmethod
    def normalize_sql_column_names(cls, sql_query: str) -> str:
        """
        تبدیل تمام نام ستون‌های داخل SQL به schema صحیح
        
        این تابع نام جدول را از SQL تشخیص می‌دهد و ستون‌ها را normalize می‌کند
        """
        # تشخیص نام جدول از SQL
        table_pattern = r'\bFROM\s+(\w+)|JOIN\s+(\w+)'
        table_matches = re.findall(table_pattern, sql_query, re.IGNORECASE)
        
        detected_table = None
        for match in table_matches:
            for table in match:
                if table and 'sheet' in table.lower():
                    detected_table = table.lower()
                    break
            if detected_table:
                break
        
        if not detected_table or detected_table not in cls.TABLE_COLUMNS:
            return sql_query
        
        # پیدا کردن تمام نام ستون‌های داخل double quotes
        column_pattern = r'"([^"]+)"'
        
        def replace_column(match):
            col_name = match.group(1)
            normalized = cls.normalize_column_name(col_name, detected_table)
            return f'"{normalized}"'
        
        normalized_sql = re.sub(column_pattern, replace_column, sql_query)
        
        return normalized_sql


# تابع helper برای استفاده آسان
def normalize_column_for_table(column_name: str, table_name: str) -> str:
    """Helper function برای normalize کردن یک ستون"""
    return ColumnNormalizer.normalize_column_name(column_name, table_name)


def normalize_sql_columns(sql_query: str) -> str:
    """Helper function برای normalize کردن تمام ستون‌های SQL"""
    return ColumnNormalizer.normalize_sql_column_names(sql_query)
