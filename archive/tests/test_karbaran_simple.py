# -*- coding: utf-8 -*-
"""
تست ساده برای collection karbaran_omomi
"""

import asyncio
import logging
from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_simple():
    """تست ساده"""
    rag = UltimateRAGSystem(
        enable_query_understanding=True,
        enable_advanced_retrieval=False,  # غیرفعال برای تست ساده‌تر
        retrieval_strategy="hybrid"
    )
    collection_name = "karbaran_omomi"
    
    # تست چند سوال ساده
    test_queries = [
        "من چطوری می تونم از موسسه دانشمند سرمایه بگیرم؟",
        "تمرکزتون روی چیه؟",
        "مزیت این صندوق چیه؟"
    ]
    
    for query in test_queries:
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 سوال: {query}")
        logger.info(f"{'='*80}")
        
        try:
            result = await rag.retrieve_and_answer(
                query=query,
                collection_name=collection_name,
                top_k=5,
                use_reranking=False,  # غیرفعال برای تست سریع‌تر
                use_multi_hop=False   # غیرفعال برای تست ساده‌تر
            )
            
            if result.get('success'):
                answer = result.get('answer', '')
                logger.info(f"\n✅ پاسخ ({len(answer)} کاراکتر):")
                logger.info(f"{answer[:500]}...")
            else:
                logger.error(f"\n❌ خطا: {result.get('error')}")
        
        except Exception as e:
            logger.error(f"\n❌ استثنا: {e}")
            import traceback
            traceback.print_exc()
        
        await asyncio.sleep(1)
    
    await rag.close()


if __name__ == "__main__":
    asyncio.run(test_simple())

