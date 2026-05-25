#!/usr/bin/env python3
"""
تست دقیق مسیر تصمیم‌گیری: Database یا RAG
"""

import asyncio
import sys
import os

# اضافه کردن مسیر پروژه به sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from services.hybrid_query_analyzer import HybridQueryAnalyzer
from integrations.database_handler import DatabaseHandler
from services.text_to_sql_agent import TextToSQLAgent
import mysql.connector
import logging

# تنظیم لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_route_decision():
    """
    تست دقیق مسیر تصمیم‌گیری برای query های مختلف
    """
    
    # تنظیم analyzer
    analyzer = HybridQueryAnalyzer(
        llm_api_url="http://localhost:11434/api/generate",
        model_name="qwen2.5:7b"
    )
    
    # تنظیم database handler
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': 'mysql',
        'database': 'booklet_database'
    }
    
    try:
        db_connection = mysql.connector.connect(**db_config)
        text_to_sql = TextToSQLAgent(db_connection)
        db_handler = DatabaseHandler(text_to_sql)
    except Exception as e:
        logger.error(f"خطا در اتصال به دیتابیس: {e}")
        return
    
    # سوالات تست
    test_queries = [
        {
            "query": "درآمد وزارت نفت",
            "description": "سوال ساده درآمد (بدون سال صریح)"
        },
        {
            "query": "درآمد وزارت نفت در سال 1403",
            "description": "سوال درآمد با سال صریح"
        },
        {
            "query": "هزینه های سرمایه ای وزارت اطلاعات در سال 1402",
            "description": "سوال هزینه با سال"
        },
        {
            "query": "تاریخچه وزارت نفت",
            "description": "سوال غیرمالی (باید RAG باشد)"
        }
    ]
    
    print("\n" + "="*80)
    print("🔍 تحلیل دقیق Route Path: Database vs RAG")
    print("="*80 + "\n")
    
    for idx, test_case in enumerate(test_queries, 1):
        query = test_case["query"]
        description = test_case["description"]
        
        print(f"\n{'='*80}")
        print(f"Test {idx}: {description}")
        print(f"Query: {query}")
        print(f"{'='*80}\n")
        
        # مرحله 1: Query Analysis
        print("📊 [STAGE 1] Query Analysis:")
        print("-" * 40)
        analysis = await analyzer.analyze(query)
        
        print(f"✓ Query Category: {analysis.get('query_category')}")
        print(f"✓ Entity Names: {analysis.get('entity_names')}")
        print(f"✓ Years: {analysis.get('years')}")
        print(f"✓ Income Component: {analysis.get('income_component')}")
        print(f"✓ Expense Type: {analysis.get('expense_type')}")
        print(f"✓ Query Type: {analysis.get('query_type')}")
        
        # مرحله 2: Route Decision
        print(f"\n🚦 [STAGE 2] Route Decision Logic:")
        print("-" * 40)
        
        # محاسبه expects_structured
        expects_structured = bool(
            analysis and analysis.get("query_category") in {
                "simple_sum", "top_n", "breakdown", "cross_table", "comparison"
            }
        )
        print(f"✓ expects_structured: {expects_structured}")
        print(f"  └─ Based on query_category: {analysis.get('query_category')}")
        
        # بررسی شرط budget_financial
        collection_name = "budget_financial"
        if collection_name == "budget_financial" and expects_structured:
            print(f"✓ Collection: {collection_name}")
            print(f"✓ Force Database Route: TRUE")
            print(f"  └─ Reason: budget_financial + expects_structured")
            final_route = "database"
        elif expects_structured:
            print(f"✓ expects_structured is True")
            print(f"✓ Route Decision: database")
            final_route = "database"
        else:
            print(f"✓ expects_structured is False")
            print(f"✓ Route Decision: RAG (fallback)")
            final_route = "rag"
        
        # مرحله 3: نتیجه نهایی
        print(f"\n✅ [STAGE 3] Final Decision:")
        print("-" * 40)
        if final_route == "database":
            print(f"🗄️  ROUTE: DATABASE")
            print(f"   └─ Query will be executed via Text-to-SQL")
            print(f"   └─ Direct SQL query on booklet_database")
        else:
            print(f"📚 ROUTE: RAG")
            print(f"   └─ Query will use semantic search on ChromaDB")
            print(f"   └─ Retrieval-Augmented Generation")
        
        print(f"\n{'='*80}\n")
        
        # فاصله بین تست‌ها
        await asyncio.sleep(0.5)
    
    print("\n" + "="*80)
    print("✅ تست تمام شد")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_route_decision())

