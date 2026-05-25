#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست مستقیم database_handler بدون نیاز به LLM
"""

import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test():
    print("="*80)
    print("🧪 Testing Database Handler Directly")
    print("="*80)
    
    from core.refactored_rag_system import RefactoredRAGSystem
    
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
    print(f"   has database_handler: {hasattr(rag_system, 'database_handler') and rag_system.database_handler is not None}")
    
    if not rag_system.database_handler:
        print("❌ database_handler not available!")
        return
    
    # تست query analysis
    # query = "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403"
    # query = "بودجه فرهنگستان هنر در سال 1403"
    # query = "درآمد عمومی ملی شرکت دولتی پست بانک در سال 1402"
    # query = "درآمدهای وزارت نفت در سال 1401 چقدر است"
    # query = "درامد ملی سازمان تامین اجتماعی در سال 1403"
    query = "هزینه عمومی نهاد ریاست جمهوری در سال 1403 بیشتر بوده یا شورای عالی امنیت ملی"
    collection_name = "budget_financial"
    
    print(f"\n🔍 Testing query: {query}")
    print(f"   collection: {collection_name}")
    
    # تست query_orchestrator
    print("\n📊 Step 1: Query Orchestrator")
    domain_info = None
    try:
        domain_info = rag_system.collection_manager.get_collection_domain(collection_name) if hasattr(rag_system, 'collection_manager') else None
    except:
        pass
    
    query_result = await rag_system.query_orchestrator.process_query(
        query=query,
        collection_name=collection_name,
        domain_info=domain_info
    )
    
    print(f"   normalized_query: {query_result.get('normalized_query', 'N/A')[:50]}...")
    
    query_analysis = query_result.get('query_analysis')
    if query_analysis:
        print(f"   query_analysis:")
        print(f"      - query_category: {query_analysis.get('query_category', 'N/A')}")
        print(f"      - entity_names: {query_analysis.get('entity_names', [])}")
        print(f"      - years: {query_analysis.get('years', [])}")
        print(f"      - confidence: {query_analysis.get('confidence', 'N/A')}")
    else:
        print(f"   ⚠️ No query_analysis!")
    
    # تست database_handler
    print("\n📊 Step 2: Database Handler")
    
    def build_metadata(extra_meta):
        return {"query_type": query_result.get('query_type', 'unknown'), **extra_meta}
    
    try:
        db_result = await rag_system.database_handler.try_database_before_rag(
            query=query,
            collection_name=collection_name,
            top_k=5,
            conversation_id=None,
            build_metadata=build_metadata,
            used_query_understanding=True,
            query_analysis=query_analysis,
            streaming=False,
            collection_metadata=domain_info
        )
        
        if db_result:
            print(f"   ✅ database_handler returned result!")
            print(f"      - has_answer: {db_result.get('answer') is not None}")
            print(f"      - has_database_results: {db_result.get('database_results') is not None}")
            if db_result.get('answer'):
                print(f"      - answer preview: {db_result['answer'][:100]}...")
            if db_result.get('database_results'):
                dr = db_result['database_results']
                print(f"      - database_results.success: {dr.get('success')}")
                print(f"      - database_results.results count: {len(dr.get('results', []))}")
                print(f"      - database_results.rows: {dr.get('rows', [])}")
                print(f"      - database_results.results: {dr.get('results', [])}")
        else:
            print(f"   ⚠️ database_handler returned None (will use RAG)")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test())

