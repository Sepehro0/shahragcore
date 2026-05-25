#!/usr/bin/env python3
"""
Test direct query for Saadi Foundation with correct column
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from services.database_service import DatabaseService

async def main():
    print("🔍 Testing direct query for 'بنیاد سعدی' (Saadi Foundation)\n")
    
    db_service = DatabaseService()
    collection_name = "finance_combined_1762693261"
    
    # Test 1: Query WITHOUT normalization
    print("=" * 80)
    print("Test 1: Query WITHOUT TRANSLATE normalization")
    print("=" * 80)
    
    sql1 = """
    SELECT "عنوان_دستگاه", "سال", SUM(CAST("ملي_جمع_کل" AS DOUBLE PRECISION)) as total_income
    FROM incomes_sheet1
    WHERE "عنوان_دستگاه" ILIKE '%بنیاد سعدی%'
    AND "سال" IN ('1398', '1399', '1400', '1401', '1402', '1403')
    GROUP BY "عنوان_دستگاه", "سال"
    ORDER BY "سال"
    """
    
    print(f"SQL:\n{sql1}\n")
    result1 = db_service.execute_sql_query(sql1, timeout=30, collection_name=None)
    print(f"Success: {result1['success']}, Count: {result1['count']}")
    
    if result1['success'] and result1['rows']:
        print("\n📊 Results:")
        for row in result1['rows']:
            print(f"  {row}")
    else:
        print("❌ No results")
    
    # Test 2: Query WITH TRANSLATE normalization
    print("\n" + "=" * 80)
    print("Test 2: Query WITH TRANSLATE normalization")
    print("=" * 80)
    
    sql2 = """
    SELECT "عنوان_دستگاه", "سال", SUM(CAST("ملي_جمع_کل" AS DOUBLE PRECISION)) as total_income
    FROM incomes_sheet1
    WHERE TRANSLATE("عنوان_دستگاه", 'يكيۀة', 'یکیهه') ILIKE '%بنیاد سعدی%'
    AND "سال" IN ('1398', '1399', '1400', '1401', '1402', '1403')
    GROUP BY "عنوان_دستگاه", "سال"
    ORDER BY "سال"
    """
    
    print(f"SQL:\n{sql2}\n")
    result2 = db_service.execute_sql_query(sql2, timeout=30, collection_name=None)
    print(f"Success: {result2['success']}, Count: {result2['count']}")
    
    if result2['success'] and result2['rows']:
        print("\n📊 Results:")
        for row in result2['rows']:
            print(f"  {row}")
    else:
        print("❌ No results")
    
    # Test 3: Query with database hardening
    print("\n" + "=" * 80)
    print("Test 3: Query WITH database hardening (_prepare_sql_query)")
    print("=" * 80)
    
    sql3 = """
    SELECT "عنوان_دستگاه", "سال", SUM(CAST("ملي_جمع_کل" AS DOUBLE PRECISION)) as total_income
    FROM incomes_sheet1
    WHERE "عنوان_دستگاه" ILIKE '%بنیاد سعدی%'
    AND "سال" IN ('1398', '1399', '1400', '1401', '1402', '1403')
    GROUP BY "عنوان_دستگاه", "سال"
    ORDER BY "سال"
    """
    
    print(f"Original SQL:\n{sql3}\n")
    result3 = db_service.execute_sql_query(sql3, timeout=30, collection_name=collection_name)
    print(f"Success: {result3['success']}, Count: {result3['count']}")
    
    if result3.get('prepared_sql'):
        print(f"\n📝 Prepared SQL (after hardening):\n{result3['prepared_sql']}\n")
    
    if result3['success'] and result3['rows']:
        print("\n📊 Results:")
        for row in result3['rows']:
            print(f"  {row}")
    else:
        print("❌ No results")
    
    # Test 4: Query using just one token
    print("\n" + "=" * 80)
    print("Test 4: Query with single token '%سعدي%'")
    print("=" * 80)
    
    sql4 = """
    SELECT "عنوان_دستگاه", "سال", SUM(CAST("ملي_جمع_کل" AS DOUBLE PRECISION)) as total_income
    FROM incomes_sheet1
    WHERE "عنوان_دستگاه" ILIKE '%سعدي%'
    AND "سال" IN ('1398', '1399', '1400', '1401', '1402', '1403')
    GROUP BY "عنوان_دستگاه", "سال"
    ORDER BY "سال"
    """
    
    print(f"SQL:\n{sql4}\n")
    result4 = db_service.execute_sql_query(sql4, timeout=30, collection_name=None)
    print(f"Success: {result4['success']}, Count: {result4['count']}")
    
    if result4['success'] and result4['rows']:
        print("\n📊 Results:")
        for row in result4['rows']:
            print(f"  {row}")
    else:
        print("❌ No results")

if __name__ == "__main__":
    asyncio.run(main())


