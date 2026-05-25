# -*- coding: utf-8 -*-
"""
Final Test with Fallback Mechanism
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_all():
    """تست کامل با fallback"""
    logger.info("🧪 Final Test with Fallback...")
    
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    collection_name = "test_boodje_final"
    
    queries = [
        ("چند ردیف در جدول وجود دارد؟", "database"),
        ("این فایل درباره چیست؟", "rag"),
    ]
    
    results = []
    
    for query, expected_type in queries:
        logger.info(f"\n{'='*60}")
        logger.info(f"Query: {query}")
        logger.info(f"{'='*60}")
        
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
                logger.info(f"✅ Success!")
                logger.info(f"Answer: {answer[:300]}")
                logger.info(f"Used hybrid: {result.get('used_hybrid_retrieval', False)}")
                logger.info(f"Used fallback: {result.get('used_fallback', False)}")
                results.append(True)
            else:
                logger.error(f"❌ Failed: {result.get('error')}")
                results.append(False)
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Results: {sum(results)}/{len(results)} successful")
    logger.info(f"{'='*60}")
    
    return all(results)


if __name__ == "__main__":
    success = asyncio.run(test_all())
    sys.exit(0 if success else 1)

