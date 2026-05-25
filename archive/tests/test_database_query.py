#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست مستقیم database query برای بررسی عملکرد
"""

import sys
import asyncio
sys.path.insert(0, '.')

from core.refactored_rag_system import RefactoredRAGSystem
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_query():
    """تست مستقیم database query"""
    
    queries = [
        "درآمدهای وزارت نفت چقدر است",
        "درامد استانی اختصاصی دانشگاه تبریز در سال 1403"
    ]
    
    print("\n" + "="*90)
    print("تست مستقیم Database Query")
    print("="*90 + "\n")
    
    rag = RefactoredRAGSystem()
    
    # بررسی database_handler
    print("🔍 بررسی Database Handler:")
    print(f"  - database_handler موجود است: {hasattr(rag, 'database_handler')}")
    if hasattr(rag, 'database_handler') and rag.database_handler:
        print(f"  - database_handler مقدار دارد: {rag.database_handler is not None}")
        print(f"  - database_service: {rag.database_handler.database_service is not None}")
        print(f"  - text_to_sql_agent: {rag.database_handler.text_to_sql_agent is not None}")
        print(f"  - query_classifier: {rag.database_handler.query_classifier is not None}")
    print()
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*90}")
        print(f"سوال {i}: {query}")
        print(f"{'='*90}\n")
        
        # تست مستقیم database query
        if rag.database_handler and rag.database_handler.text_to_sql_agent:
            try:
                print("🔍 تست مستقیم Text-to-SQL Agent...")
                db_results = await rag.database_handler.text_to_sql_agent.execute_and_get_results(
                    user_query=query,
                    collection_name='budget_financial'
                )
                
                if db_results:
                    print(f"✅ Database query returned: success={db_results.get('success')}")
                    print(f"  - Error: {db_results.get('error', 'None')}")
                    print(f"  - SQL: {db_results.get('sql', 'None')[:200] if db_results.get('sql') else 'None'}")
                    
                    results = db_results.get('results')
                    rows = db_results.get('rows')
                    detail_rows = db_results.get('detail_rows')
                    
                    print(f"  - Results: {len(results) if results else 0} rows")
                    print(f"  - Rows: {len(rows) if rows else 0} rows")
                    print(f"  - Detail rows: {len(detail_rows) if detail_rows else 0} rows")
                    
                    if results and len(results) > 0:
                        print(f"\n📊 نمونه نتایج:")
                        for idx, row in enumerate(results[:3]):
                            print(f"  [{idx+1}] {row}")
                    elif rows and len(rows) > 0:
                        print(f"\n📊 نمونه rows:")
                        for idx, row in enumerate(rows[:3]):
                            print(f"  [{idx+1}] {row}")
                else:
                    print("❌ Database query returned None")
            except Exception as e:
                print(f"❌ خطا در database query: {e}")
                import traceback
                traceback.print_exc()
        
        print()


if __name__ == "__main__":
    asyncio.run(test_database_query())

