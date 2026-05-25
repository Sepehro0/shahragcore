# -*- coding: utf-8 -*-
"""
Test Database Query Only
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_count():
    """تست query شمارش"""
    logger.info("🧪 Testing Database Count Query...")
    
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    collection_name = "test_boodje_final"
    
    if not rag_system.enable_database:
        logger.error("❌ Database not enabled")
        return False
    
    # Check if collection exists
    tables = rag_system.database_service.list_tables(collection_name)
    if not tables:
        logger.warning(f"⚠️ No tables in {collection_name}, uploading Excel first...")
        excel_path = "/home/user01/qwen-api/enhanced_rag_system/boodje.xlsx"
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
    
    query = "چند ردیف در جدول وجود دارد؟"
    logger.info(f"📝 Query: {query}")
    
    try:
        result = await rag_system.retrieve_and_answer(
            query=query,
            collection_name=collection_name,
            top_k=5,
            use_reranking=False,
            use_multi_hop=False
        )
        
        if result.get("success"):
            logger.info("✅ Query successful!")
            answer = result.get("answer", "")
            logger.info(f"📋 Answer:\n{answer}")
            
            db_results = result.get("database_results")
            if db_results:
                logger.info(f"   - DB results count: {db_results.get('count', 0)}")
                logger.info(f"   - SQL: {db_results.get('sql', 'N/A')[:100]}")
            
            return True
        else:
            logger.error(f"❌ Query failed: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_database_count())
    sys.exit(0 if success else 1)

