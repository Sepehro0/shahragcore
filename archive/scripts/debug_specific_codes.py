#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Specific Codes - بررسی دقیق کدهای خاص
"""

import asyncio
from loguru import logger
from ultimate_rag_system import UltimateRAGSystem

async def debug_specific_codes():
    """Debug specific codes that are giving wrong answers"""
    logger.info("🔍 Debugging Specific Codes...")
    
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    # کدهای مشکل‌دار
    problem_codes = ["110103", "110104", "110105"]
    
    collection_name = "jadval5-bodje"
    collection = rag_system.chroma_client.get_collection(collection_name)
    all_docs = collection.get()
    
    logger.info("\n" + "="*80)
    logger.info("📊 Checking Database for Problem Codes")
    logger.info("="*80)
    
    for code in problem_codes:
        logger.info(f"\n🔍 Searching for code: {code}")
        logger.info("-" * 80)
        
        found = False
        for doc_id, doc_text, metadata in zip(all_docs['ids'], all_docs['documents'], all_docs['metadatas']):
            if metadata.get('hierarchy_code') == code:
                found = True
                logger.info(f"✅ Found in database!")
                logger.info(f"   Document ID: {doc_id}")
                logger.info(f"   Hierarchy Code: {metadata.get('hierarchy_code')}")
                logger.info(f"   Hierarchy Title: {metadata.get('hierarchy_title')}")
                logger.info(f"   Parent Clause: {metadata.get('parent_clause')}")
                logger.info(f"   Parent Clause Code: {metadata.get('parent_clause_code')}")
                logger.info(f"   Text (first 300 chars):")
                logger.info(f"      {doc_text[:300]}")
                break
        
        if not found:
            logger.error(f"❌ Code {code} NOT found in database!")
    
    # تست query برای هر کد
    logger.info("\n" + "="*80)
    logger.info("🧪 Testing Queries")
    logger.info("="*80)
    
    for code in problem_codes:
        query = f"کد {code} راجع به چیه؟"
        logger.info(f"\n❓ Query: {query}")
        logger.info("-" * 80)
        
        # گرفتن نتایج hybrid_search
        results = await rag_system.hybrid_search(query, collection_name, top_k=3)
        
        logger.info(f"📊 Hybrid Search Results (top 3):")
        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            logger.info(f"\n   Result {i}:")
            logger.info(f"      Score: {result.get('hybrid_score', 0):.4f}")
            logger.info(f"      Hierarchy Code: {metadata.get('hierarchy_code', 'N/A')}")
            logger.info(f"      Hierarchy Title: {metadata.get('hierarchy_title', 'N/A')}")
            logger.info(f"      Text (first 150 chars): {result.get('text', '')[:150]}")
        
        # گرفتن پاسخ کامل
        logger.info(f"\n🤖 Full Answer:")
        response = await rag_system.retrieve_and_answer(query, collection_name=collection_name)
        
        if response.get('success'):
            answer = response.get('answer', '')
            logger.info(f"{answer[:500]}...\n")
        else:
            logger.error(f"❌ Error: {response.get('error', '')}\n")

if __name__ == "__main__":
    asyncio.run(debug_specific_codes())


