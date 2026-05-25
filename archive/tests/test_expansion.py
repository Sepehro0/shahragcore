# -*- coding: utf-8 -*-
"""
Test expansion for indirect questions
"""

import sys
import asyncio
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from services.smart_query_preprocessor import SmartQueryPreprocessor


async def test_expansion():
    """Test expansion"""
    
    preprocessor = SmartQueryPreprocessor()
    
    test_queries = [
        "ایا من برای اینکه بتونم نتایج نواورم و به یکی دیگه بفروشم باید از صندوق اجازه بگیرم ؟",
        "معیار اصلی طرحمون چیا باید باشه که بتونیم از حمایت های صندوق نوآور استفاده کنیم ؟",
        "بعد از اینکه پیشنهادمونو ارسال کردیم چقد طول میکشه تا جوابشو بگیریم ؟"
    ]
    
    for query in test_queries:
        expanded, is_indirect = preprocessor._expand_indirect_question(query)
        print(f"\nQuery: {query}")
        print(f"Expanded: {expanded}")
        print(f"Is Indirect: {is_indirect}")
        print(f"Changed: {expanded != query}")


if __name__ == "__main__":
    asyncio.run(test_expansion())

