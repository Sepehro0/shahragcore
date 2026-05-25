# -*- coding: utf-8 -*-
"""
تست Column Mapper
"""

import asyncio
from services.budget_column_mapper import get_budget_column_mapper


def test_column_mapper():
    """تست نگاشت نام ستون‌ها"""
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🧪 تست Budget Column Mapper")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    mapper = get_budget_column_mapper()
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # تست 1: نگاشت نام ستون‌های مصارف
    # ═══════════════════════════════════════════════════════════════════════════════
    
    print("\n📋 تست 1: نگاشت نام ستون‌های مصارف")
    print("="*80)
    
    masaref_tests = [
        "اعتبارات هزینه ای عمومی",
        "برآورد اعتبارات هزینه ای متفرقه",
        "تملک دارایی سرمایه ای عمومی",
        "جمع تملک دارایی سرمایه ای",
        "جمع کل بودجه",
    ]
    
    for col_name in masaref_tests:
        mapped = mapper.map_column_name(col_name, "masaref2_sheet1")
        print(f"   '{col_name}' → '{mapped}'")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # تست 2: نگاشت نام ستون‌های منابع
    # ═══════════════════════════════════════════════════════════════════════════════
    
    print("\n📋 تست 2: نگاشت نام ستون‌های منابع")
    print("="*80)
    
    manabe_tests = [
        "درآمد عمومی ملی",
        "درامد اختصاصی استانی",
        "جمع درآمد عمومی",
        "جمع کل",
    ]
    
    for col_name in manabe_tests:
        mapped = mapper.map_column_name(col_name, "manabe_sheet1")
        print(f"   '{col_name}' → '{mapped}'")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # تست 3: نگاشت SQL query
    # ═══════════════════════════════════════════════════════════════════════════════
    
    print("\n📋 تست 3: نگاشت SQL Query")
    print("="*80)
    
    sql_tests = [
        (
            'SELECT "اعتبارات هزینه ای عمومی", "تملک دارایی سرمایه ای عمومی" FROM masaref2_sheet1',
            "masaref2_sheet1"
        ),
        (
            'SELECT "درآمد عمومی ملی", "درامد اختصاصی استانی" FROM manabe_sheet1',
            "manabe_sheet1"
        ),
    ]
    
    for sql, table in sql_tests:
        print(f"\n   اصلی: {sql}")
        mapped_sql = mapper.map_sql_query(sql, table)
        print(f"   نگاشت شده: {mapped_sql}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # تست 4: لیست تمام ستون‌ها
    # ═══════════════════════════════════════════════════════════════════════════════
    
    print("\n📋 تست 4: لیست تمام ستون‌ها")
    print("="*80)
    
    masaref_columns = mapper.get_all_column_names("masaref2_sheet1")
    print(f"\n   تعداد ستون‌های مصارف: {len(masaref_columns)}")
    print(f"   نمونه: {masaref_columns[:5]}")
    
    manabe_columns = mapper.get_all_column_names("manabe_sheet1")
    print(f"\n   تعداد ستون‌های منابع: {len(manabe_columns)}")
    print(f"   نمونه: {manabe_columns[:5]}")
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ تست کامل شد!")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    test_column_mapper()



