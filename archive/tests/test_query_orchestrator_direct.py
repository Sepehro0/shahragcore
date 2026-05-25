#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست مستقیم query_orchestrator
"""

import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test():
    from core.refactored_rag_system import RefactoredRAGSystem
    
    print("="*80)
    print("🧪 Testing QueryOrchestrator with query_analyzer")
    print("="*80)
    
    rag_system = RefactoredRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=True,
        enable_advanced_retrieval=True,
        enable_multimodal=False,
        enable_self_rag=False,
        enable_corrective_rag=False,
        retrieval_strategy="hybrid"
    )
    
    print(f"\n✅ RAG System initialized")
    print(f"   orchestrators_enabled: {rag_system._orchestrators_enabled}")
    print(f"   has query_analyzer: {hasattr(rag_system, 'query_analyzer')}")
    print(f"   query_analyzer type: {type(rag_system.query_analyzer).__name__ if hasattr(rag_system, 'query_analyzer') else 'N/A'}")
    print(f"   query_orchestrator.query_analyzer: {rag_system.query_orchestrator.query_analyzer is not None if hasattr(rag_system, 'query_orchestrator') else 'N/A'}")
    
    query = "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403"
    collection_name = "budget_financial"
    
    print(f"\n🔍 Testing query: {query}")
    print(f"   collection: {collection_name}")
    
    try:
        # Test query processing
        result = await rag_system.query_orchestrator.process_query(
            query=query,
            collection_name=collection_name,
            domain_info=None
        )
        
        print(f"\n✅ Query processing result:")
        print(f"   normalized_query: {result.get('normalized_query', 'N/A')[:50]}...")
        print(f"   is_greeting: {result.get('is_greeting', False)}")
        print(f"   is_multi_part: {result.get('is_multi_part', False)}")
        
        if 'query_analysis' in result:
            print(f"\n📊 Query Analysis:")
            qa = result['query_analysis']
            print(f"   query_category: {qa.get('query_category', 'N/A')}")
            print(f"   entity_names: {qa.get('entity_names', [])}")
            print(f"   years: {qa.get('years', [])}")
            print(f"   confidence: {qa.get('confidence', 'N/A')}")
        else:
            print(f"\n⚠️ No query_analysis in result!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())

