#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from loguru import logger
from ultimate_rag_system import UltimateRAGSystem

async def debug_110105():
    """Debug 110105 specifically"""
    logger.info("🔍 Debugging 110105...")
    
    rag = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    collection_name = "jadval5-bodje"
    
    # 1. Check database
    logger.info("\n" + "="*80)
    logger.info("📊 Step 1: Checking Database")
    logger.info("="*80)
    
    try:
        collection = rag.chroma_client.get_collection(collection_name)
        all_docs = collection.get()
        
        found_110105 = False
        for doc_id, doc_text, metadata in zip(all_docs['ids'], all_docs['documents'], all_docs['metadatas']):
            if metadata.get('hierarchy_code') == '110105':
                found_110105 = True
                logger.info(f"\n✅ Found 110105 in database!")
                logger.info(f"   Doc ID: {doc_id}")
                logger.info(f"   Hierarchy Code: {metadata.get('hierarchy_code')}")
                logger.info(f"   Hierarchy Title: {metadata.get('hierarchy_title')}")
                logger.info(f"   Parent Clause: {metadata.get('parent_clause')}")
                logger.info(f"   Parent Clause Code: {metadata.get('parent_clause_code')}")
                logger.info(f"   Search Keywords: {metadata.get('search_keywords')}")
                logger.info(f"   Text (first 200): {doc_text[:200]}")
                break
        
        if not found_110105:
            logger.error("❌ 110105 NOT found in database!")
            logger.info(f"\nTotal documents: {len(all_docs['ids'])}")
            logger.info("Sample codes in database:")
            codes = set()
            for metadata in all_docs['metadatas']:
                code = metadata.get('hierarchy_code')
                if code and code.startswith('1101'):
                    codes.add(code)
            for code in sorted(codes):
                logger.info(f"   - {code}")
    
    except Exception as e:
        logger.error(f"❌ Error accessing database: {e}")
        return
    
    # 2. Test hybrid_search
    logger.info("\n" + "="*80)
    logger.info("📊 Step 2: Testing Hybrid Search")
    logger.info("="*80)
    
    query = "کد 110105 راجع به چیه؟"
    results = await rag.hybrid_search(query, collection_name, top_k=5)
    
    logger.info(f"\nQuery: {query}")
    logger.info(f"Results found: {len(results)}")
    
    for i, result in enumerate(results, 1):
        metadata = result.get('metadata', {})
        logger.info(f"\n   Result {i}:")
        logger.info(f"      Score: {result.get('hybrid_score', 0):.4f}")
        logger.info(f"      Code: {metadata.get('hierarchy_code', 'N/A')}")
        logger.info(f"      Title: {metadata.get('hierarchy_title', 'N/A')[:50]}")
        logger.info(f"      Text: {result.get('text', '')[:100]}")
    
    # 3. Test full query
    logger.info("\n" + "="*80)
    logger.info("📊 Step 3: Testing Full Query")
    logger.info("="*80)
    
    response = await rag.retrieve_and_answer(query, collection_name=collection_name)
    
    if response.get('success'):
        answer = response.get('answer', '')
        logger.info(f"\n✅ Answer received:")
        logger.info(f"{answer}")
        
        # Check if answer is correct
        if "110105" in answer and ("مالیات" in answer or "غیر دولتی" in answer):
            logger.info("\n✅ Answer seems correct!")
        else:
            logger.error("\n❌ Answer is WRONG!")
    else:
        logger.error(f"\n❌ Query failed: {response.get('error', '')}")

if __name__ == "__main__":
    asyncio.run(debug_110105())


