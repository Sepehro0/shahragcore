# -*- coding: utf-8 -*-
"""
تست مستقیم Database Route
"""

import asyncio
import sys
sys.path.insert(0, '/home/user01/qwen-api/enhanced_rag_system_dev')

from core.refactored_rag_system import RefactoredRAGSystem


async def test_database_route():
    """تست مستقیم database route"""
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🧪 تست مستقیم Database Route")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # Initialize RAG system
    print("\n1️⃣ Initializing RAG System...")
    rag_system = RefactoredRAGSystem()
    
    # Check components
    print(f"\n2️⃣ Checking components:")
    print(f"   - database_handler: {hasattr(rag_system, 'database_handler') and rag_system.database_handler is not None}")
    print(f"   - answer_orchestrator: {hasattr(rag_system, 'answer_orchestrator') and rag_system.answer_orchestrator is not None}")
    
    if hasattr(rag_system, 'answer_orchestrator') and rag_system.answer_orchestrator:
        print(f"   - answer_orchestrator.database_handler: {rag_system.answer_orchestrator.database_handler is not None}")
    
    # Test query
    query = "اعتبارات هزینه‌ای نهاد ریاست جمهوری در سال 1403"
    collection_name = "budget_financial"
    
    print(f"\n3️⃣ Testing query:")
    print(f"   Query: {query}")
    print(f"   Collection: {collection_name}")
    
    # Call answer_orchestrator directly
    if hasattr(rag_system, 'answer_orchestrator') and rag_system.answer_orchestrator:
        result = await rag_system.answer_orchestrator.retrieve_and_answer(
            query=query,
            collection_name=collection_name,
            top_k=5,
            use_reranking=True,
            use_multi_hop=False,
            conversation_id=None
        )
        
        print(f"\n4️⃣ Result:")
        print(f"   - answer: {result.get('answer', 'N/A')[:200]}...")
        print(f"   - database_results: {result.get('database_results') is not None}")
        print(f"   - database_rows_count: {result.get('database_rows_count', 0)}")
        
        if result.get('database_results'):
            print(f"\n   ✅ DATABASE QUERY انجام شد!")
        else:
            print(f"\n   ❌ Database query انجام نشد")
    else:
        print(f"\n❌ answer_orchestrator not available")
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    asyncio.run(test_database_route())

