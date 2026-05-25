#!/usr/bin/env python3
"""
Test script for debugging the Saadi query issue
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from services.database_service import DatabaseService
from services.text_to_sql_agent import TextToSQLAgent
from processors.schema_analyzer import SchemaAnalyzer
from services.qwen_client import QwenClient
from config import QWEN_API_URL

async def main():
    print("🔍 Testing Saadi query SQL generation and execution\n")
    
    # Initialize services
    db_service = DatabaseService()
    qwen_client = QwenClient(api_url=QWEN_API_URL)
    schema_analyzer = SchemaAnalyzer(db_service)
    text_to_sql = TextToSQLAgent(qwen_client, schema_analyzer, db_service)
    
    query = "بنیاد سعدی در سال های 98 تا 1403 چقدر درامد ملی داشته است ؟"
    collection_name = "finance_combined_1762693261"
    
    print(f"Query: {query}")
    print(f"Collection: {collection_name}\n")
    
    # Step 1: Generate SQL
    print("=" * 80)
    print("STEP 1: SQL Generation")
    print("=" * 80)
    
    sql_result = await text_to_sql.generate_sql(query, collection_name)
    
    if not sql_result["success"]:
        print(f"❌ SQL generation failed: {sql_result.get('error')}")
        return
    
    generated_sql = sql_result["sql"]
    print(f"✅ Generated SQL:\n{generated_sql}\n")
    
    # Step 2: Execute SQL (with hardening)
    print("=" * 80)
    print("STEP 2: SQL Execution with Hardening")
    print("=" * 80)
    
    execution_result = db_service.execute_sql_query(
        generated_sql,
        timeout=30,
        collection_name=collection_name
    )
    
    print(f"Success: {execution_result['success']}")
    print(f"Count: {execution_result['count']}")
    print(f"Columns: {execution_result['columns']}")
    
    if execution_result.get('prepared_sql'):
        print(f"\n📝 Prepared SQL (after hardening):\n{execution_result['prepared_sql']}\n")
    
    if execution_result['success'] and execution_result['rows']:
        print(f"\n📊 Results:")
        for i, row in enumerate(execution_result['rows'][:5]):
            print(f"  Row {i+1}: {row}")
    else:
        print(f"\n❌ No results or error: {execution_result.get('error')}")
    
    # Step 3: Test direct SQL without hardening
    print("\n" + "=" * 80)
    print("STEP 3: Test Simple Direct SQL")
    print("=" * 80)
    
    # First, check what tables exist
    print("\n🔍 Available tables in collection:")
    columns_map = db_service.get_collection_columns(collection_name)
    for table_name in columns_map.keys():
        print(f"  - {table_name}")
        
    # Try a simple query on incomes_sheet1
    if 'incomes_sheet1' in columns_map:
        print("\n🔍 Testing simple query on incomes_sheet1:")
        simple_sql = """
        SELECT "عنوان_بخش", "سال", SUM(CAST("ملي_جمع_کل" AS DOUBLE PRECISION)) as total_income
        FROM incomes_sheet1
        WHERE TRANSLATE("عنوان_بخش", 'يكيۀة', 'یکیهه') ILIKE '%بنیاد%'
        AND "سال" IN ('1398', '1399', '1400', '1401', '1402', '1403')
        GROUP BY "عنوان_بخش", "سال"
        ORDER BY "سال"
        """
        
        print(f"SQL: {simple_sql}")
        result = db_service.execute_sql_query(simple_sql, timeout=30, collection_name=collection_name)
        print(f"\nSuccess: {result['success']}")
        print(f"Count: {result['count']}")
        
        if result['success'] and result['rows']:
            print(f"\n📊 Results:")
            for row in result['rows']:
                print(f"  {row}")
        else:
            print(f"❌ Error or no results: {result.get('error')}")
            
    # Test with expanded ILIKE
    print("\n" + "=" * 80)
    print("STEP 4: Test Expanded ILIKE Pattern")
    print("=" * 80)
    
    if 'incomes_sheet1' in columns_map:
        expanded_sql = """
        SELECT "عنوان_بخش", "سال", SUM(CAST("ملي_جمع_کل" AS DOUBLE PRECISION)) as total_income
        FROM incomes_sheet1
        WHERE (TRANSLATE("عنوان_بخش", 'يكيۀة', 'یکیهه') ILIKE '%بنیاد%' AND TRANSLATE("عنوان_بخش", 'يكيۀة', 'یکیهه') ILIKE '%سعدی%')
        AND "سال" IN ('1398', '1399', '1400', '1401', '1402', '1403')
        GROUP BY "عنوان_بخش", "سال"
        ORDER BY "سال"
        """
        
        print(f"SQL with expanded ILIKE: {expanded_sql}")
        result = db_service.execute_sql_query(expanded_sql, timeout=30, collection_name=collection_name)
        print(f"\nSuccess: {result['success']}")
        print(f"Count: {result['count']}")
        
        if result['success'] and result['rows']:
            print(f"\n📊 Results:")
            for row in result['rows']:
                print(f"  {row}")
        else:
            print(f"❌ Error or no results: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())

