#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Retrieval - بررسی دقیق اینکه چه چیزی به مدل ارسال می‌شود
"""

import asyncio
from loguru import logger
from ultimate_rag_system import UltimateRAGSystem

async def debug_retrieval():
    """Debug retrieval for 110103"""
    logger.info("🔍 Debugging Retrieval for 110103...")
    
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    query = "110103 راجع به چیه؟"
    collection_name = "jadval5-bodje"
    
    # 1. بررسی نتایج hybrid_search
    logger.info("\n" + "="*80)
    logger.info("📊 Step 1: Hybrid Search Results")
    logger.info("="*80)
    
    results = await rag_system.hybrid_search(query, collection_name, top_k=5)
    
    for i, result in enumerate(results, 1):
        logger.info(f"\n🔍 Result {i}:")
        logger.info(f"   Score: {result.get('hybrid_score', 0):.4f}")
        logger.info(f"   Metadata:")
        metadata = result.get('metadata', {})
        logger.info(f"      - hierarchy_level: {metadata.get('hierarchy_level', 'N/A')}")
        logger.info(f"      - hierarchy_code: {metadata.get('hierarchy_code', 'N/A')}")
        logger.info(f"      - hierarchy_title: {metadata.get('hierarchy_title', 'N/A')}")
        logger.info(f"      - parent_clause: {metadata.get('parent_clause', 'N/A')}")
        logger.info(f"      - parent_clause_code: {metadata.get('parent_clause_code', 'N/A')}")
        logger.info(f"      - parent_section: {metadata.get('parent_section', 'N/A')}")
        logger.info(f"   Text (first 200 chars):")
        logger.info(f"      {result.get('text', '')[:200]}")
    
    # 2. بررسی context که به مدل ارسال می‌شود
    logger.info("\n" + "="*80)
    logger.info("📝 Step 2: Context Sent to LLM")
    logger.info("="*80)
    
    # ساخت context
    context_parts = []
    for i, result in enumerate(results, 1):
        metadata = result.get('metadata', {})
        text = result.get('text', '')
        
        context_part = f"Document {i}:\n"
        if metadata.get('hierarchy_code'):
            context_part += f"Code: {metadata.get('hierarchy_code')}\n"
        if metadata.get('hierarchy_title'):
            context_part += f"Title: {metadata.get('hierarchy_title')}\n"
        if metadata.get('parent_clause'):
            context_part += f"Parent Clause: {metadata.get('parent_clause')}\n"
        context_part += f"Content: {text}\n"
        
        context_parts.append(context_part)
    
    full_context = "\n---\n".join(context_parts)
    
    logger.info(f"\n📄 Full Context:\n{full_context}\n")
    
    # 3. تست با retrieve_and_answer
    logger.info("\n" + "="*80)
    logger.info("🤖 Step 3: Full Retrieve and Answer")
    logger.info("="*80)
    
    response = await rag_system.retrieve_and_answer(query, collection_name=collection_name)
    
    if response.get('success'):
        logger.info(f"\n✅ Answer:\n{response.get('answer', '')}\n")
    else:
        logger.error(f"\n❌ Error: {response.get('error', '')}\n")
    
    # 4. بررسی مستقیم در database
    logger.info("\n" + "="*80)
    logger.info("🔎 Step 4: Direct Database Query for 110103")
    logger.info("="*80)
    
    collection = rag_system.chroma_client.get_collection(collection_name)
    all_docs = collection.get()
    
    found_110103 = False
    for doc_id, doc_text, metadata in zip(all_docs['ids'], all_docs['documents'], all_docs['metadatas']):
        if metadata.get('hierarchy_code') == '110103':
            found_110103 = True
            logger.info(f"\n✅ Found 110103 in database!")
            logger.info(f"   Document ID: {doc_id}")
            logger.info(f"   Metadata:")
            logger.info(f"      - hierarchy_level: {metadata.get('hierarchy_level', 'N/A')}")
            logger.info(f"      - hierarchy_code: {metadata.get('hierarchy_code', 'N/A')}")
            logger.info(f"      - hierarchy_title: {metadata.get('hierarchy_title', 'N/A')}")
            logger.info(f"      - parent_clause: {metadata.get('parent_clause', 'N/A')}")
            logger.info(f"      - parent_clause_code: {metadata.get('parent_clause_code', 'N/A')}")
            logger.info(f"      - parent_section: {metadata.get('parent_section', 'N/A')}")
            logger.info(f"      - search_keywords: {metadata.get('search_keywords', 'N/A')}")
            logger.info(f"   Text:")
            logger.info(f"      {doc_text}")
            break
    
    if not found_110103:
        logger.error("❌ 110103 NOT found in database!")
    
    logger.info("\n" + "="*80)
    logger.info("✅ Debug Complete")
    logger.info("="*80)

if __name__ == "__main__":
    asyncio.run(debug_retrieval())

