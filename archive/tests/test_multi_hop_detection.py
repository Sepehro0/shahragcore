# -*- coding: utf-8 -*-
"""
تست تشخیص Multi-Hop
"""

import asyncio
import logging
from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_multi_hop_detection():
    """تست تشخیص Multi-Hop"""
    rag = UltimateRAGSystem()
    collection_name = "karbaran_omomi"
    
    test_queries = [
        "چه حوزه‌هایی رو پوشش می‌دید و چه مزایایی دارید؟",
        "فرآیند سرمایه‌گذاری چطوریه و چه مدت طول می‌کشه؟",
        "معیارهای پذیرش طرح‌ها چیه و چه نوع طرح‌هایی رو قبول می‌کنید؟",
        "اگر من یک استارتاپ در حوزه فناوری داشته باشم، چطور می‌تونم از شما سرمایه بگیرم و چه مراحلی باید طی کنم و چه مدت طول می‌کشه؟",
        "مزیت‌های سرمایه‌گذاری در این صندوق چیه و چه حوزه‌هایی رو پوشش می‌دید و فرآیند چطوریه؟",
    ]
    
    for query in test_queries:
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 سوال: {query}")
        logger.info(f"{'='*80}")
        
        # بررسی تشخیص
        query_lower = query.lower()
        multi_part_keywords = [" و ", " و", "و ", " چطور", " چه", " کجا", " کی", " چرا", " چگونه", " چه مدت", " چه نوع"]
        multi_part_count = sum(1 for kw in multi_part_keywords if kw in query_lower)
        has_multiple_questions = multi_part_count >= 2 or query_lower.count("؟") >= 2
        
        question_markers = ["چیه", "چیست", "چطور", "چگونه", "چه", "کجا", "کی", "چرا"]
        question_count = sum(1 for marker in question_markers if marker in query_lower)
        is_multi_part_query = question_count >= 2 or (multi_part_count >= 1 and len(query.split()) >= 10)
        
        logger.info(f"   multi_part_count: {multi_part_count}")
        logger.info(f"   question_count: {question_count}")
        logger.info(f"   is_multi_part_query: {is_multi_part_query}")
        logger.info(f"   has_multiple_questions: {has_multiple_questions}")
        
        # تقسیم
        parts = []
        if " و " in query:
            parts = [p.strip() for p in query.split(" و ") if len(p.strip()) > 5]
        elif "؟" in query:
            parts = [p.strip() for p in query.split("؟") if len(p.strip()) > 5]
        
        logger.info(f"   parts: {parts}")
        logger.info(f"   len(parts): {len(parts)}")
        
        if len(parts) >= 2:
            logger.info(f"   ✅ باید Multi-Hop فعال شود!")
        else:
            logger.info(f"   ❌ Multi-Hop فعال نمی‌شود")
        
        await asyncio.sleep(0.5)
    
    await rag.close()


if __name__ == "__main__":
    asyncio.run(test_multi_hop_detection())

