#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from loguru import logger
from ultimate_rag_system import UltimateRAGSystem

async def test_normalization():
    """Test with normalized text"""
    logger.info("🧪 Testing with Normalized Persian Text...")
    
    rag = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    # Process PDF
    logger.info("\n📄 Processing PDF...")
    pdf_path = '/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf'
    
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    result = await rag.process_pdf_advanced(pdf_bytes, "jadval5-bodje.pdf", "jadval5-bodje")
    
    if not result['success']:
        logger.error(f"❌ Processing failed: {result.get('error', '')}")
        return False
    
    logger.info(f"✅ Processing complete. Chunks: {result.get('chunks_created', 0)}")
    
    # Test specific queries
    test_queries = [
        ("110103", "مالیات عملکرد شرکتهای دولتی"),
        ("110104", "مالیات بنگاه"),
        ("110105", "مالیات اشخاص حقوقی غیر دولتی")
    ]
    
    logger.info("\n" + "="*80)
    logger.info("🧪 Testing Queries")
    logger.info("="*80)
    
    all_passed = True
    for code, expected_keyword in test_queries:
        query = f"کد {code} راجع به چیه؟"
        
        response = await rag.retrieve_and_answer(query, collection_name="jadval5-bodje")
        
        if response.get('success'):
            answer = response.get('answer', '')
            
            # Check for expected keyword
            found = expected_keyword in answer
            
            # Check for presentation forms (bad)
            has_presentation_forms = any(char in answer for char in ['ﻲ', 'ﻱ', 'ﻝ', 'ﻭ', 'ﺍ', 'ﺪ', 'ﻨ', 'ﺑ'])
            
            status = "✅" if (found and not has_presentation_forms) else "❌"
            
            logger.info(f"\n{status} Code: {code}")
            logger.info(f"   Expected keyword found: {'✅' if found else '❌'}")
            logger.info(f"   Text is normalized (no presentation forms): {'✅' if not has_presentation_forms else '❌'}")
            logger.info(f"   Answer (first 200 chars): {answer[:200]}")
            
            if not (found and not has_presentation_forms):
                all_passed = False
        else:
            logger.error(f"❌ Code {code}: Query failed")
            all_passed = False
    
    logger.info("\n" + "="*80)
    if all_passed:
        logger.info("🎉 All tests PASSED! Text is normalized correctly.")
    else:
        logger.error("❌ Some tests FAILED!")
    logger.info("="*80)
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(test_normalization())
    exit(0 if success else 1)


