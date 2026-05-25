# -*- coding: utf-8 -*-
"""
Test Complex Queries - برای تست query های پیچیده‌تر
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_complex_queries():
    """تست query های پیچیده"""
    logger.info("🧪 Testing Complex Queries...")
    
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    collection_name = "test_boodje_final"
    
    # بررسی وجود collection
    tables = rag_system.database_service.list_tables(collection_name) if rag_system.enable_database else []
    if not tables:
        logger.warning("⚠️ No tables found, uploading Excel first...")
        excel_path = "/home/user01/qwen-api/enhanced_rag_system/boodje.xlsx"
        if os.path.exists(excel_path):
            with open(excel_path, 'rb') as f:
                file_bytes = f.read()
            
            result = await rag_system.process_excel(
                file_bytes=file_bytes,
                filename="boodje.xlsx",
                collection_name=collection_name
            )
            
            if not result.get("success"):
                logger.error(f"❌ Upload failed: {result.get('error')}")
                return False
    
    # Query های پیچیده برای تست
    test_queries = [
        {
            "query": "درآمد عمومی کل ردیف‌های چقدر میشه؟",
            "type": "aggregation",
            "description": "جمع کل یک ستون (درآمد عمومی)"
        },
        {
            "query": "کد جز 110104 راجع به چه چیزیه؟",
            "type": "lookup",
            "description": "جستجوی یک کد خاص"
        },
        {
            "query": "چند ردیف در جدول وجود دارد؟",
            "type": "count",
            "description": "شمارش ردیف‌ها"
        },
        {
            "query": "نمایش ردیف‌هایی که درآمد عمومی بیشتر از 1000 دارند",
            "type": "filter",
            "description": "فیلتر بر اساس شرط"
        }
    ]
    
    results = []
    
    for test_case in test_queries:
        query = test_case["query"]
        query_type = test_case["type"]
        description = test_case["description"]
        
        logger.info(f"\n{'='*80}")
        logger.info(f"📝 Query ({query_type}): {query}")
        logger.info(f"📋 Description: {description}")
        logger.info(f"{'='*80}")
        
        try:
            result = await rag_system.retrieve_and_answer(
                query=query,
                collection_name=collection_name,
                top_k=5,
                use_reranking=False,
                use_multi_hop=False
            )
            
            if result.get("success"):
                answer = result.get("answer", "")
                logger.info(f"✅ Query successful!")
                logger.info(f"\n📋 Answer:\n{answer}\n")
                
                # نمایش اطلاعات تکمیلی
                if result.get("used_hybrid_retrieval"):
                    logger.info(f"   - Used hybrid retrieval: ✅")
                    logger.info(f"   - Route: {result.get('route', {}).get('primary_path', 'N/A')}")
                    logger.info(f"   - Used fallback: {result.get('used_fallback', False)}")
                
                if result.get("database_results"):
                    db_info = result.get("database_results", {})
                    logger.info(f"   - DB SQL: {db_info.get('sql', 'N/A')[:100]}")
                    logger.info(f"   - DB Results count: {db_info.get('count', 0)}")
                
                results.append({
                    "query": query,
                    "type": query_type,
                    "success": True,
                    "answer": answer[:200] if answer else ""
                })
            else:
                logger.error(f"❌ Query failed: {result.get('error')}")
                results.append({
                    "query": query,
                    "type": query_type,
                    "success": False,
                    "error": result.get('error', 'Unknown error')
                })
                
        except Exception as e:
            logger.error(f"❌ Query error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "query": query,
                "type": query_type,
                "success": False,
                "error": str(e)
            })
    
    # خلاصه نتایج
    logger.info(f"\n{'='*80}")
    logger.info("📊 SUMMARY")
    logger.info(f"{'='*80}")
    
    successful = sum(1 for r in results if r.get("success"))
    logger.info(f"✅ Successful: {successful}/{len(results)}")
    
    for result in results:
        status = "✅" if result.get("success") else "❌"
        logger.info(f"{status} {result.get('type')}: {result.get('query')[:50]}")
    
    return successful == len(results)


if __name__ == "__main__":
    success = asyncio.run(test_complex_queries())
    sys.exit(0 if success else 1)

