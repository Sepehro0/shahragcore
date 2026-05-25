# -*- coding: utf-8 -*-
"""
تست کامل فایل فرمت هزینه‌ها
"""

import asyncio
import logging
import sys
import os
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_format_hazineh():
    """تست پردازش فایل فرمت هزینه‌ها"""
    logger.info("=" * 80)
    logger.info("🧪 TEST: فرمت هزینه ها.xlsx Processing")
    logger.info("=" * 80)
    
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=True,
        enable_query_understanding=True,
        enable_advanced_retrieval=True
    )
    
    try:
        excel_path = "/home/user01/qwen-api/enhanced_rag_system/فرمت هزینه ها.xlsx"
        if not os.path.exists(excel_path):
            logger.error(f"❌ Excel file not found: {excel_path}")
            return False
        
        with open(excel_path, 'rb') as f:
            file_bytes = f.read()
        
        file_size_mb = len(file_bytes) / (1024 * 1024)
        logger.info(f"📄 File size: {file_size_mb:.2f} MB")
        
        collection_name = f"format_hazineh_{int(time.time())}"
        logger.info(f"📤 Processing to collection: {collection_name}")
        
        # Process Excel
        start_time = time.time()
        result = await rag_system.process_excel(
            file_bytes=file_bytes,
            filename="فرمت هزینه ها.xlsx",
            collection_name=collection_name
        )
        processing_time = time.time() - start_time
        
        if result.get("success"):
            logger.info(f"✅ Excel processing successful in {processing_time:.2f}s!")
            logger.info(f"   - Chunks: {result.get('chunks_count', 0)}")
            logger.info(f"   - RAG storage: {result.get('rag_storage', {}).get('success')}")
            logger.info(f"   - DB storage: {result.get('database_storage', {}).get('success')}")
            
            if result.get('database_storage', {}).get('success'):
                db_info = result.get('database_storage', {})
                logger.info(f"   - Tables: {db_info.get('total_tables', 0)}")
                for table in db_info.get('tables', []):
                    logger.info(f"     * {table.get('table_name')}: {table.get('row_count')} rows")
            
            # Test queries
            await test_queries(rag_system, collection_name)
            
            return collection_name
        else:
            logger.error(f"❌ Processing failed: {result.get('error')}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        await rag_system.close()


async def test_queries(rag_system, collection_name: str):
    """تست query های مختلف روی فایل"""
    logger.info("\n" + "=" * 80)
    logger.info("🔍 Testing Queries")
    logger.info("=" * 80)
    
    queries = [
        "این فایل درباره چیست؟",
        "چه هزینه‌هایی در این فایل ثبت شده؟",
        "جمع کل هزینه‌ها چقدر است؟",
        "آیا ردیف‌هایی با کد خاص وجود دارد؟",
        "چند ردیف در این فایل است؟"
    ]
    
    for i, query in enumerate(queries, 1):
        logger.info(f"\n📝 Query {i}: {query}")
        
        try:
            start_time = time.time()
            result = await rag_system.retrieve_and_answer(
                query=query,
                collection_name=collection_name,
                top_k=5,
                use_reranking=True,
                use_multi_hop=False
            )
            query_time = time.time() - start_time
            
            if result.get("success"):
                answer = result.get("answer", "")
                if answer:
                    preview = answer[:300] + "..." if len(answer) > 300 else answer
                    logger.info(f"   ✅ Answer ({query_time:.2f}s):\n   {preview}")
                    
                top_results = result.get("top_results") or []
                logger.info(f"   - Retrieved results: {len(top_results)}")
                
                db_result = result.get("database_results") or {}
                if db_result:
                    logger.info(f"   - DB rows: {db_result.get('count', 0)}")
                if not answer and not top_results and not db_result:
                    logger.warning("   ⚠️ Empty answer")
            else:
                logger.error(f"   ❌ Query failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"   ❌ Query error: {e}")


async def main():
    """تابع اصلی"""
    logger.info("🚀 شروع تست فایل فرمت هزینه‌ها\n")
    
    collection_name = await test_format_hazineh()
    
    logger.info("\n" + "=" * 80)
    if collection_name:
        logger.info(f"✅ تست کامل با موفقیت انجام شد!")
        logger.info(f"Collection: {collection_name}")
    else:
        logger.error("❌ تست ناموفق بود")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        import gc
        gc.collect()

