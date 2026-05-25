#!/usr/bin/env python3
"""
Simple test script for debugging the Saadi query issue
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from services.database_service import DatabaseService

async def main():
    print("🔍 Testing Saadi query with direct SQL\n")
    
    # Initialize database service
    db_service = DatabaseService()
    
    collection_name = "finance_combined_1762693261"
    
    print(f"Collection: {collection_name}\n")
    
    # Step 1: Check available tables
    print("=" * 80)
    print("STEP 1: Available Tables")
    print("=" * 80)
    
    columns_map = db_service.get_collection_columns(collection_name)
    print(f"\nTables in collection:")
    for table_name in columns_map.keys():
        print(f"  - {table_name}")
        
    # Step 2: Test simple query without hardening
    print("\n" + "=" * 80)
    print("STEP 2: Simple Query WITHOUT Hardening")
    print("=" * 80)
    
    if 'incomes_sheet1' in columns_map:
        print("\n🔍 Testing query on incomes_sheet1:")
        simple_sql = """
        SELECT "عنوان_بخش", "سال", CAST("ملي_جمع_کل" AS DOUBLE PRECISION) as total_income
        FROM incomes_sheet1
        WHERE "عنوان_بخش" ILIKE '%بنیاد سعدی%'
        AND "سال" IN ('1398', '1399', '1400', '1401', '1402', '1403')
        ORDER BY "سال"
        LIMIT 10
        """
        
        print(f"SQL:\n{simple_sql}\n")
        
        # Execute without hardening by not passing collection_name
        result = db_service.execute_sql_query(simple_sql, timeout=30, collection_name=None)
        print(f"Success: {result['success']}")
        print(f"Count: {result['count']}")
        
        if result['success'] and result['rows']:
            print(f"\n📊 Results:")
            for row in result['rows']:
                print(f"  {row}")
        else:
            print(f"❌ Error or no results: {result.get('error')}")
    
    # Step 3: Test with hardening enabled
    print("\n" + "=" * 80)
    print("STEP 3: Query WITH Hardening (_expand_phrase_ilike)")
    print("=" * 80)
    
    if 'incomes_sheet1' in columns_map:
        print("\n🔍 Testing query with hardening:")
        sql_to_harden = """
        SELECT "عنوان_بخش", "سال", SUM(CAST("ملي_جمع_کل" AS DOUBLE PRECISION)) as total_income
        FROM incomes_sheet1
        WHERE "عنوان_بخش" ILIKE '%بنیاد سعدی%'
        AND "سال" IN ('1398', '1399', '1400', '1401', '1402', '1403')
        GROUP BY "عنوان_بخش", "سال"
        ORDER BY "سال"
        """
        
        print(f"Original SQL:\n{sql_to_harden}\n")
        
        # Execute WITH hardening
        result = db_service.execute_sql_query(sql_to_harden, timeout=30, collection_name=collection_name)
        print(f"Success: {result['success']}")
        print(f"Count: {result['count']}")
        
        if result.get('prepared_sql'):
            print(f"\n📝 Prepared SQL (after hardening):\n{result['prepared_sql']}\n")
        
        if result['success'] and result['rows']:
            print(f"\n📊 Results:")
            for row in result['rows']:
                print(f"  {row}")
        else:
            print(f"❌ Error or no results: {result.get('error')}")
    
    # Step 4: Test the _expand_phrase_ilike function directly
    print("\n" + "=" * 80)
    print("STEP 4: Test _expand_phrase_ilike Function")
    print("=" * 80)
    
    test_sql = '"عنوان_بخش" ILIKE \'%بنیاد سعدی%\''
    print(f"\nInput: {test_sql}")
    
    expanded = db_service._expand_phrase_ilike(test_sql)
    print(f"Output: {expanded}")
    
    # Step 5: Test with broader ILIKE
    print("\n" + "=" * 80)
    print("STEP 5: Query with Broader ILIKE Pattern")
    print("=" * 80)
    
    if 'incomes_sheet1' in columns_map:
        print("\n🔍 Testing with just '%بنیاد%':")
        broad_sql = """
        SELECT "عنوان_بخش", "سال", SUM(CAST("ملي_جمع_کل" AS DOUBLE PRECISION)) as total_income
        FROM incomes_sheet1
        WHERE "عنوان_بخش" ILIKE '%بنیاد%'
        AND "سال" IN ('1398', '1399', '1400', '1401', '1402', '1403')
        GROUP BY "عنوان_بخش", "سال"
        ORDER BY "سال"
        """
        
        print(f"SQL:\n{broad_sql}\n")
        
        result = db_service.execute_sql_query(broad_sql, timeout=30, collection_name=collection_name)
        print(f"Success: {result['success']}")
        print(f"Count: {result['count']}")
        
        if result.get('prepared_sql'):
            print(f"\n📝 Prepared SQL:\n{result['prepared_sql']}\n")
        
        if result['success'] and result['rows']:
            print(f"\n📊 Results:")
            for row in result['rows']:
                print(f"  {row}")
        else:
            print(f"❌ Error or no results: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())


