#!/usr/bin/env python3
"""
Find what values exist for "بنیاد" in the database
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from services.database_service import DatabaseService

async def main():
    print("🔍 Searching for 'بنیاد' variations in database\n")
    
    db_service = DatabaseService()
    collection_name = "finance_combined_1762693261"
    
    # Query 1: Find all rows containing "بنیاد" (any variation)
    print("=" * 80)
    print("Query 1: All rows with 'بنیاد' or 'بنياد' in عنوان_بخش")
    print("=" * 80)
    
    sql1 = """
    SELECT DISTINCT "عنوان_بخش"
    FROM incomes_sheet1
    WHERE "عنوان_بخش" ILIKE '%بنیاد%' OR "عنوان_بخش" ILIKE '%بنياد%'
    LIMIT 50
    """
    
    result1 = db_service.execute_sql_query(sql1, timeout=30, collection_name=None)
    print(f"Success: {result1['success']}, Count: {result1['count']}")
    
    if result1['success'] and result1['rows']:
        print(f"\nFound {result1['count']} distinct values:")
        for i, row in enumerate(result1['rows'], 1):
            print(f"{i}. {row.get('عنوان_بخش')}")
    else:
        print("No results found")
    
    # Query 2: Find all rows containing "سعدی" or "سعدي"
    print("\n" + "=" * 80)
    print("Query 2: All rows with 'سعدی' or 'سعدي' in عنوان_بخش")
    print("=" * 80)
    
    sql2 = """
    SELECT DISTINCT "عنوان_بخش"
    FROM incomes_sheet1
    WHERE "عنوان_بخش" ILIKE '%سعدی%' OR "عنوان_بخش" ILIKE '%سعدي%'
    LIMIT 50
    """
    
    result2 = db_service.execute_sql_query(sql2, timeout=30, collection_name=None)
    print(f"Success: {result2['success']}, Count: {result2['count']}")
    
    if result2['success'] and result2['rows']:
        print(f"\nFound {result2['count']} distinct values:")
        for i, row in enumerate(result2['rows'], 1):
            print(f"{i}. {row.get('عنوان_بخش')}")
    else:
        print("No results found")
    
    # Query 3: Show sample of all distinct عنوان_بخش values (first 100)
    print("\n" + "=" * 80)
    print("Query 3: Sample of all distinct عنوان_بخش values")
    print("=" * 80)
    
    sql3 = """
    SELECT DISTINCT "عنوان_بخش"
    FROM incomes_sheet1
    ORDER BY "عنوان_بخش"
    LIMIT 100
    """
    
    result3 = db_service.execute_sql_query(sql3, timeout=30, collection_name=None)
    print(f"Success: {result3['success']}, Count: {result3['count']}")
    
    if result3['success'] and result3['rows']:
        print(f"\nFirst {result3['count']} values (alphabetically):")
        for i, row in enumerate(result3['rows'], 1):
            value = row.get('عنوان_بخش')
            # Check if it contains بنیاد or سعدی
            marker = ""
            if value and ('بنیاد' in value or 'بنياد' in value):
                marker = " ⭐ [contains بنیاد]"
            if value and ('سعدی' in value or 'سعدي' in value):
                marker += " ⭐⭐ [contains سعدی]"
            print(f"{i}. {value}{marker}")
    else:
        print("No results found")

if __name__ == "__main__":
    asyncio.run(main())


