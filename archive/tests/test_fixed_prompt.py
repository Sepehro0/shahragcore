#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Fixed Prompt - تست prompt بهبود یافته
"""

import asyncio
from loguru import logger
from ultimate_rag_system import UltimateRAGSystem

async def test_fixed_prompt():
    """Test the fixed prompt with metadata"""
    logger.info("🧪 Testing Fixed Prompt with Metadata...")
    
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    test_queries = [
        "110103 راجع به چیه؟",
        "110309 چیست؟",
        "110205 مربوط به چه موضوعی است؟",
        "140101 در مورد چیست؟"
    ]
    
    logger.info("\n" + "="*80)
    logger.info("📊 Testing Queries with Fixed Prompt")
    logger.info("="*80)
    
    for query in test_queries:
        logger.info(f"\n❓ Query: {query}")
        logger.info("-" * 80)
        
        response = await rag_system.retrieve_and_answer(query, collection_name="jadval5-bodje")
        
        if response.get('success'):
            answer = response.get('answer', '')
            logger.info(f"✅ Answer:\n{answer}\n")
        else:
            logger.error(f"❌ Error: {response.get('error', '')}\n")
    
    logger.info("="*80)
    logger.info("✅ Test Complete")
    logger.info("="*80)

if __name__ == "__main__":
    asyncio.run(test_fixed_prompt())

