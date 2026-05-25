#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reprocess PDF and Test - پردازش مجدد PDF و تست
"""

import asyncio
from loguru import logger
from ultimate_rag_system import UltimateRAGSystem

async def reprocess_and_test():
    """Reprocess PDF and test specific codes"""
    logger.info("🚀 Reprocessing PDF and Testing...")
    
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    pdf_path = '/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf'
    collection_name = "jadval5-bodje"
    
    # 1. Process PDF
    logger.info("\n📄 Processing PDF...")
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    result = await rag_system.process_pdf_advanced(pdf_bytes, "jadval5-bodje.pdf", collection_name)
    
    if not result['success']:
        logger.error(f"❌ PDF processing failed: {result.get('error', 'Unknown')}")
        return False
    
    logger.info(f"✅ PDF processed successfully. Chunks: {result.get('chunks_created', 0)}")
    
    # 2. Check database for specific codes
    logger.info("\n" + "="*80)
    logger.info("📊 Checking Database for Specific Codes")
    logger.info("="*80)
    
    codes_to_check = {
        "110103": "مالیات عملکرد شرکتهای دولتی",
        "110104": "مالیات بنگاه های اقتصادی نهادها و بنیادهای انقالب اسلامی",
        "110105": "مالیات اشخاص حقوقی غیر دولتی"
    }
    
    collection = rag_system.chroma_client.get_collection(collection_name)
    all_docs = collection.get()
    
    for code, expected_title in codes_to_check.items():
        logger.info(f"\n🔍 Code: {code}")
        logger.info(f"   Expected Title: {expected_title}")
        
        found = False
        for doc_id, doc_text, metadata in zip(all_docs['ids'], all_docs['documents'], all_docs['metadatas']):
            if metadata.get('hierarchy_code') == code:
                found = True
                actual_title = metadata.get('hierarchy_title', '')
                
                if expected_title in actual_title or actual_title in expected_title:
                    logger.info(f"   ✅ Correct Title: {actual_title}")
                else:
                    logger.error(f"   ❌ Wrong Title: {actual_title}")
                
                logger.info(f"   Parent Clause Code: {metadata.get('parent_clause_code')}")
                logger.info(f"   Text: {doc_text[:200]}...")
                break
        
        if not found:
            logger.error(f"   ❌ Code {code} NOT found in database!")
    
    # 3. Test queries
    logger.info("\n" + "="*80)
    logger.info("🧪 Testing Queries")
    logger.info("="*80)
    
    test_queries = [
        ("110103", "مالیات عملکرد شرکتهای دولتی"),
        ("110104", "مالیات بنگاه های اقتصادی"),
        ("110105", "مالیات اشخاص حقوقی غیر دولتی")
    ]
    
    for code, expected_keyword in test_queries:
        query = f"کد {code} راجع به چیه؟"
        logger.info(f"\n❓ Query: {query}")
        logger.info(f"   Expected keyword: {expected_keyword}")
        logger.info("-" * 80)
        
        response = await rag_system.retrieve_and_answer(query, collection_name=collection_name)
        
        if response.get('success'):
            answer = response.get('answer', '')
            
            if expected_keyword in answer:
                logger.info(f"   ✅ CORRECT - Found expected keyword")
            else:
                logger.error(f"   ❌ WRONG - Expected keyword NOT found")
            
            logger.info(f"\n   Answer: {answer[:300]}...\n")
        else:
            logger.error(f"   ❌ Query failed: {response.get('error', '')}")
    
    logger.info("="*80)
    logger.info("✅ Test Complete")
    logger.info("="*80)

if __name__ == "__main__":
    asyncio.run(reprocess_and_test())


