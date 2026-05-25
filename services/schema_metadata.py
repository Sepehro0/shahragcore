# -*- coding: utf-8 -*-
"""
Schema Metadata - متادیتای ساختار جداول

این ماژول شامل اطلاعات کامل درباره ساختار جداول است:
- ستون‌های سلسله مراتبی
- ستون‌های entity
- ستون‌های مقادیر
- مقادیر یکتا برای هر ستون (برای fuzzy matching)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TableType(Enum):
    """نوع جدول"""
    INCOME = "income"       # درآمدها/منابع
    EXPENSE = "expense"     # هزینه‌ها/مصارف


class HierarchyLevel(Enum):
    """سطوح سلسله مراتب"""
    QESMAT = ("قسمت", 1)     # Level 1 - بالاترین
    BAKHSH = ("بخش", 2)      # Level 2
    BAND = ("بند", 3)        # Level 3
    JOZV = ("جزء", 4)        # Level 4 - پایین‌ترین
    
    def __init__(self, persian_name: str, level: int):
        self.persian_name = persian_name
        self.level = level


@dataclass
class HierarchyColumnInfo:
    """اطلاعات ستون سلسله مراتبی"""
    column_name: str           # نام ستون در database
    level: HierarchyLevel      # سطح سلسله مراتب
    keywords: List[str]        # کلمات کلیدی برای تشخیص
    unique_values: List[str] = field(default_factory=list)  # مقادیر یکتا
    
    def matches_keyword(self, text: str) -> bool:
        """بررسی اینکه آیا متن شامل کلمه کلیدی این سطح است"""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.keywords)


@dataclass
class EntityColumnInfo:
    """اطلاعات ستون entity"""
    column_name: str           # نام ستون در database
    entity_type: str           # نوع entity (دستگاه_اصلی، دستگاه_اجرایی)
    keywords: List[str]        # کلمات کلیدی برای تشخیص
    unique_values: List[str] = field(default_factory=list)


@dataclass
class ValueColumnInfo:
    """اطلاعات ستون مقدار"""
    column_name: str           # نام ستون در database
    value_type: str            # نوع مقدار (جمع_کل، عمومی، اختصاصی، ...)
    keywords: List[str]        # کلمات کلیدی برای تشخیص


@dataclass
class TableSchema:
    """ساختار کامل یک جدول"""
    table_name: str
    table_type: TableType
    description: str
    
    # ستون‌های سلسله مراتبی
    hierarchy_columns: Dict[str, HierarchyColumnInfo] = field(default_factory=dict)
    
    # ستون‌های entity
    entity_columns: Dict[str, EntityColumnInfo] = field(default_factory=dict)
    
    # ستون‌های مقدار
    value_columns: Dict[str, ValueColumnInfo] = field(default_factory=dict)
    
    # ستون سال
    year_column: str = "سال"
    
    def get_hierarchy_column(self, level_name: str) -> Optional[str]:
        """دریافت نام ستون برای یک سطح سلسله مراتب"""
        if level_name in self.hierarchy_columns:
            return self.hierarchy_columns[level_name].column_name
        return None
    
    def get_all_hierarchy_columns(self) -> List[str]:
        """دریافت همه ستون‌های سلسله مراتبی"""
        return [info.column_name for info in self.hierarchy_columns.values()]
    
    def get_all_entity_columns(self) -> List[str]:
        """دریافت همه ستون‌های entity"""
        return [info.column_name for info in self.entity_columns.values()]


# Schema برای جدول manabe
MANABE_SCHEMA = TableSchema(
    table_name="manabe_sheet1",
    table_type=TableType.INCOME,
    description="جدول درآمدها و منابع",
    
    hierarchy_columns={
        "قسمت": HierarchyColumnInfo(
            column_name="عنوان_قسمت",
            level=HierarchyLevel.QESMAT,
            keywords=["قسمت", "قسمتها", "قسمت‌ها", "قسمتهای"],
            unique_values=[
                "قسمت اول: درآمدها",
                "قسمت دوم: منابع حاصل از واگذاري دارائي هاي سرمايه اي",
                "قسمت سوم: منابع حاصل از واگذاري دارائي هاي مالي"
            ]
        ),
        "بخش": HierarchyColumnInfo(
            column_name="عنوان_بخش",
            level=HierarchyLevel.BAKHSH,
            keywords=["بخش", "بخشها", "بخش‌ها", "بخشهای"],
            unique_values=[
                "بخش اول: درآمدهاي مالياتي",
                "بخش دوم: درآمدهاي ناشي از كمكهاي اجتماعي",
                "بخش سوم: درآمدهاي حاصل از مالكيت دولت",
                "بخش چهارم: درآمدهاي حاصل از فروش كالاها و خدمات",
                "بخش پنجم: درآمدهاي حاصل از جرايم و خسارات",
                "بخش ششم: درآمدهاي متفرقه",
                "بخش اول: واگذاري دارائي هاي سرمايه اي",
                "بخش اول: واگذاري دارائي هاي مالي"
            ]
        ),
        "بند": HierarchyColumnInfo(
            column_name="عنوان_بند",
            level=HierarchyLevel.BAND,
            keywords=["بند", "بندها", "بند‌ها", "بندهای"],
            unique_values=[]  # Too many to list
        ),
        "جزء": HierarchyColumnInfo(
            column_name="عنوان_جزء",
            level=HierarchyLevel.JOZV,
            keywords=["جزء", "جزو", "اجزاء", "اجزای", "جزءها", "جزوها"],
            unique_values=[]  # Too many to list
        )
    },
    
    entity_columns={
        "دستگاه_اصلی": EntityColumnInfo(
            column_name="عنوان_دستگاه_اصلی",
            entity_type="main_device",
            keywords=["وزارت", "سازمان", "نهاد", "مرکز", "مؤسسه", "موسسه",
                     "شرکت", "بانک", "صندوق", "دانشگاه", "بیمارستان",
                     "اداره", "استانداری", "فرمانداری", "ستاد", "بنیاد"]
        ),
        "دستگاه_اجرایی": EntityColumnInfo(
            column_name="عنوان_دستگاه_اجرایی",
            entity_type="exec_device",
            keywords=[]  # Same as main device
        )
    },
    
    value_columns={
        "جمع_کل": ValueColumnInfo(
            column_name="جمع_کل",
            value_type="total",
            keywords=["کل", "مجموع", "جمع"]
        ),
        "درآمد_عمومی_ملی": ValueColumnInfo(
            column_name="در_آمد_عمومی_ملی",
            value_type="public_national",
            keywords=["عمومی", "ملی"]
        ),
        "درآمد_عمومی_استانی": ValueColumnInfo(
            column_name="در_آمد_عمومی_استانی",
            value_type="public_provincial",
            keywords=["عمومی", "استانی"]
        ),
        "درآمد_اختصاصی_ملی": ValueColumnInfo(
            column_name="در_آمد_اختصاصی_ملی",
            value_type="private_national",
            keywords=["اختصاصی", "ملی"]
        ),
        "درآمد_اختصاصی_استانی": ValueColumnInfo(
            column_name="در_آمد_اختصاصی_استانی",
            value_type="private_provincial",
            keywords=["اختصاصی", "استانی"]
        )
    },
    
    year_column="سال"
)

# Schema برای جدول masaref
MASAREF_SCHEMA = TableSchema(
    table_name="masaref2_sheet1",
    table_type=TableType.EXPENSE,
    description="جدول هزینه‌ها و مصارف",
    
    hierarchy_columns={},  # masaref ساختار سلسله مراتبی ندارد
    
    entity_columns={
        "دستگاه_اصلی": EntityColumnInfo(
            column_name="عنوان_دستگاه_اصلی",
            entity_type="main_device",
            keywords=["وزارت", "سازمان", "نهاد", "مرکز", "مؤسسه", "موسسه",
                     "شرکت", "بانک", "صندوق", "دانشگاه", "بیمارستان",
                     "اداره", "استانداری", "فرمانداری", "ستاد", "بنیاد"]
        ),
        "دستگاه_اجرایی": EntityColumnInfo(
            column_name="عنوان_دستگاه_اجرایی",
            entity_type="exec_device",
            keywords=[]
        )
    },
    
    value_columns={
        "جمع_کل": ValueColumnInfo(
            column_name="جمع_كل",
            value_type="total",
            keywords=["کل", "مجموع", "جمع"]
        ),
        "اعتبارات_هزینه_ای": ValueColumnInfo(
            column_name="جمع_براورد_اعتبارات_هزینه_ای",
            value_type="expense_credits",
            keywords=["هزینه", "اعتبار"]
        ),
        "تملک_دارایی": ValueColumnInfo(
            column_name="جمع_برآورد_تملك_دارايي_هاي_سرمايه_اي",
            value_type="asset_acquisition",
            keywords=["تملک", "دارایی", "سرمایه"]
        )
    },
    
    year_column="سال"
)

# دیکشنری همه schema ها
ALL_SCHEMAS: Dict[str, TableSchema] = {
    "manabe_sheet1": MANABE_SCHEMA,
    "masaref2_sheet1": MASAREF_SCHEMA
}


def get_schema(table_name: str) -> Optional[TableSchema]:
    """دریافت schema برای یک جدول"""
    return ALL_SCHEMAS.get(table_name)


def get_income_schema() -> TableSchema:
    """دریافت schema جدول درآمدها"""
    return MANABE_SCHEMA


def get_expense_schema() -> TableSchema:
    """دریافت schema جدول هزینه‌ها"""
    return MASAREF_SCHEMA


