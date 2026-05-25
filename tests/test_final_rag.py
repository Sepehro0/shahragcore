# -*- coding: utf-8 -*-
"""
Test Final RAG System with all advanced features
"""

import asyncio
import sys
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system")

from ultimate_rag_system import UltimateRAGSystem


async def test_semantic_chunking():
    """Test semantic chunking feature"""
    print("\n" + "="*80)
    print("🧠 Testing Semantic Chunking")
    print("="*80)
    
    rag = UltimateRAGSystem(enable_semantic_chunking=True)
    
    sample_text = """
    بودجه سال 1404 با رشد 25 درصدی نسبت به سال قبل تصویب شد.
    
    بررسی بودجه نشان می‌دهد که بخش عمرانی با اختصاص 120 هزار میلیارد تومان
    بیشترین سهم را به خود اختصاص داده است. این رقم در سال 1403 برابر با
    95 هزار میلیارد تومان بود.
    
    برای مثال، در بخش حمل و نقل، اعتبارات از 15 به 20 هزار میلیارد تومان
    افزایش یافته است. این افزایش برای تکمیل پروژه‌های نیمه‌تمام ضروری است.
    
    بنابراین می‌توان نتیجه گرفت که دولت به توسعه زیرساخت‌ها اولویت داده است.
    """
    
    if rag.semantic_chunker:
        chunks = rag.semantic_chunker.chunk_document(
            text=sample_text,
            metadata={"test": "semantic_chunking"}
        )
        
        print(f"✅ Created {len(chunks)} semantic chunks")
        for i, chunk in enumerate(chunks, 1):
            print(f"\nChunk {i}:")
            print(f"  - Text length: {chunk['metadata']['chunk_size']}")
            print(f"  - Sentences: {chunk['metadata']['sentence_count']}")
            print(f"  - Coherence: {chunk['metadata']['semantic_coherence']:.3f}")
            print(f"  - Text preview: {chunk['text'][:100]}...")
    else:
        print("❌ Semantic chunker not available")


async def test_query_understanding():
    """Test query understanding feature"""
    print("\n" + "="*80)
    print("🎯 Testing Query Understanding")
    print("="*80)
    
    rag = UltimateRAGSystem(enable_query_understanding=True)
    
    test_queries = [
        "بودجه سال 1404 چقدر است؟",  # Factoid
        "تفاوت بودجه 1403 و 1404 چیست؟",  # Comparison
        "چرا بودجه افزایش یافته؟",  # Analytical
    ]
    
    if rag.query_understander:
        for query in test_queries:
            print(f"\n📝 Query: {query}")
            understanding = await rag.query_understander.understand_and_expand_query(query)
            
            print(f"  - Intent: {understanding['intent'].intent_type}")
            print(f"  - Confidence: {understanding['intent'].confidence:.2f}")
            print(f"  - Complexity: {understanding['complexity_score']:.2f}")
            print(f"  - Expanded queries: {len(understanding['expanded_queries'])}")
            print(f"  - Sub-questions: {len(understanding['sub_questions'])}")
            
            if understanding['expanded_queries']:
                print(f"  - First expansion: {understanding['expanded_queries'][0]}")
    else:
        print("❌ Query understander not available")


async def test_advanced_retrieval():
    """Test advanced retrieval strategies"""
    print("\n" + "="*80)
    print("🚀 Testing Advanced Retrieval")
    print("="*80)
    
    strategies = ["simple", "hybrid", "iterative", "graph", "advanced"]
    
    for strategy in strategies:
        print(f"\n📊 Testing strategy: {strategy}")
        try:
            rag = UltimateRAGSystem(
                enable_advanced_retrieval=True,
                retrieval_strategy=strategy
            )
            
            if rag.advanced_retrieval:
                print(f"  ✅ Advanced retrieval initialized with {strategy} strategy")
            else:
                print(f"  ❌ Advanced retrieval not available")
        except Exception as e:
            print(f"  ❌ Error: {e}")


async def test_all_features_together():
    """Test all features enabled together"""
    print("\n" + "="*80)
    print("🌟 Testing All Features Together")
    print("="*80)
    
    try:
        rag = UltimateRAGSystem(
            enable_semantic_chunking=True,
            enable_query_understanding=True,
            enable_advanced_retrieval=True,
            retrieval_strategy="hybrid"
        )
        
        print("✅ System initialized with all features:")
        print(f"  - Semantic Chunking: {rag.enable_semantic_chunking}")
        print(f"  - Query Understanding: {rag.enable_query_understanding}")
        print(f"  - Advanced Retrieval: {rag.enable_advanced_retrieval}")
        print(f"  - Strategy: {rag.retrieval_strategy}")
        
    except Exception as e:
        print(f"❌ Error initializing with all features: {e}")


async def test_backward_compatibility():
    """Test that system works with all features disabled"""
    print("\n" + "="*80)
    print("🔄 Testing Backward Compatibility")
    print("="*80)
    
    try:
        rag = UltimateRAGSystem(
            enable_semantic_chunking=False,
            enable_query_understanding=False,
            enable_advanced_retrieval=False
        )
        
        print("✅ System initialized with no advanced features (backward compatible)")
        print(f"  - Semantic Chunking: {rag.enable_semantic_chunking}")
        print(f"  - Query Understanding: {rag.enable_query_understanding}")
        print(f"  - Advanced Retrieval: {rag.enable_advanced_retrieval}")
        
        # Test that basic functionality still works
        collections = await rag.get_collections()
        print(f"  - Can list collections: ✅ ({len(collections)} collections)")
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🧪 FINAL RAG SYSTEM - COMPREHENSIVE TEST SUITE")
    print("="*80)
    
    try:
        await test_semantic_chunking()
        await test_query_understanding()
        await test_advanced_retrieval()
        await test_all_features_together()
        await test_backward_compatibility()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())



