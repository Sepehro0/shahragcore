#!/usr/bin/env python3
"""
Check available columns in incomes_sheet1 and search for Saadi Foundation
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from services.database_service import DatabaseService

async def main():
    print("🔍 Checking columns and searching for 'بنیاد سعدی'\n")
    
    db_service = DatabaseService()
    collection_name = "finance_combined_1762693261"
    
    # Step 1: Get all columns
    print("=" * 80)
    print("STEP 1: Available columns in incomes_sheet1")
    print("=" * 80)
    
    columns_map = db_service.get_collection_columns(collection_name)
    
    if 'incomes_sheet1' in columns_map:
        print("\nColumns in incomes_sheet1:")
        for col_name, col_info in columns_map['incomes_sheet1'].items():
            print(f"  - {col_name} ({col_info.get('data_type', 'unknown')})")
    
    # Step 2: Show sample data
    print("\n" + "=" * 80)
    print("STEP 2: Sample rows from incomes_sheet1")
    print("=" * 80)
    
    sql_sample = """
    SELECT *
    FROM incomes_sheet1
    LIMIT 5
    """
    
    result = db_service.execute_sql_query(sql_sample, timeout=30, collection_name=None)
    
    if result['success'] and result['rows']:
        print(f"\nSample data (first 5 rows):")
        print(f"Columns: {result['columns']}")
        for i, row in enumerate(result['rows'], 1):
            print(f"\nRow {i}:")
            for key, value in row.items():
                print(f"  {key}: {value}")
    
    # Step 3: Search for "بنیاد" in all text columns
    print("\n" + "=" * 80)
    print("STEP 3: Search for 'بنیاد' or 'بنياد' in all potential columns")
    print("=" * 80)
    
    if 'incomes_sheet1' in columns_map:
        # Try different column names that might contain organization names
        potential_columns = [
            'عنوان_دستگاه',
            'عنوان_دستگاه_اصلی',
            'عنوان_دستگاه_اصلي',
            'عنوان دستگاه',
            'نام_دستگاه',
            'دستگاه'
        ]
        
        for col in potential_columns:
            if any(col in k or k == col for k in columns_map['incomes_sheet1'].keys()):
                print(f"\n🔍 Searching in column: {col}")
                sql = f'''
                SELECT DISTINCT "{col}"
                FROM incomes_sheet1
                WHERE "{col}" ILIKE '%بنیاد%' OR "{col}" ILIKE '%بنياد%'
                LIMIT 20
                '''
                
                result = db_service.execute_sql_query(sql, timeout=30, collection_name=None)
                
                if result['success'] and result['rows'] and result['count'] > 0:
                    print(f"  ✅ Found {result['count']} results:")
                    for row in result['rows']:
                        print(f"    - {row.get(col)}")
                else:
                    print(f"  ❌ No results found")

if __name__ == "__main__":
    asyncio.run(main())


