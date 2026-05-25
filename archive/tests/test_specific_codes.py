#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Specific Codes - تست کدهای خاص
"""

import asyncio
from loguru import logger
from ultimate_rag_system import UltimateRAGSystem

async def test_specific_codes():
    """تست کدهای خاص"""
    logger.info("🧪 Testing Specific Codes...")
    
    # کدهای خاص برای تست
    test_codes = [
        "110103",  # تست اولیه
        "110301",  # اولین کد بند سوم
        "110305",  # وسط
        "110309",  # آخرین کد بند سوم
        "110205",  # بند دوم
        "140101",  # بخش چهارم - اولین
        "140199",  # بخش چهارم - آخرین
        "150101",  # بخش پنجم
        "160169",  # بخش ششم - آخرین
    ]
    
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    logger.info("\n📊 Testing specific codes:")
    logger.info("=" * 80)
    
    for code in test_codes:
        query = f"{code} راجع به چیه؟"
        
        try:
            response = await rag_system.retrieve_and_answer(query, collection_name="jadval5-bodje")
            
            if response.get('success'):
                answer = response.get('answer', '')
                
                # بررسی وجود کد در پاسخ
                if code in answer:
                    logger.info(f"✅ {code}: Found in answer")
                    # نمایش اولین 100 کاراکتر از پاسخ
                    logger.info(f"   Answer: {answer[:100]}...")
                else:
                    logger.warning(f"⚠️ {code}: Not found in answer")
                    logger.warning(f"   Answer: {answer[:200]}...")
            else:
                logger.error(f"❌ {code}: Query failed - {response.get('error', 'Unknown')}")
        
        except Exception as e:
            logger.error(f"❌ {code}: Exception - {str(e)}")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ Specific codes test completed!")

if __name__ == "__main__":
    asyncio.run(test_specific_codes())

