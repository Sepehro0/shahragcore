# -*- coding: utf-8 -*-
"""
تست یکپارچگی Ultimate RAG System
"""

import asyncio
import logging
import sys
import os

# Add path for imports
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system")

from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_ultimate_integration():
    """تست یکپارچگی Ultimate RAG System"""
    print("="*80)
    print("🧪 Testing Ultimate RAG System Integration")
    print("="*80)
    
    try:
        # Initialize system
        print("\n🚀 Initializing Ultimate RAG System...")
        rag = UltimateRAGSystem()
        print("✅ System initialized successfully")
        
        # Test collections
        print("\n📋 Testing collections...")
        collections = await rag.get_collections()
        print(f"✅ Found {len(collections)} collections: {collections}")
        
        # Test with existing collection if available
        if collections:
            test_collection = collections[0]
            print(f"\n🔍 Testing with collection: {test_collection}")
            
            # Test query
            test_query = "بند چهارم توی این جدول چیه؟"
            print(f"\n💬 Testing query: {test_query}")
            
            result = await rag.retrieve_and_answer(
                query=test_query,
                collection_name=test_collection,
                top_k=3,
                use_reranking=True,
                use_multi_hop=True
            )
            
            if result["success"]:
                print(f"✅ Query successful!")
                print(f"   Score: {result.get('top_score', 0):.4f}")
                print(f"   Reranking: {'✅' if result.get('used_reranking', False) else '❌'}")
                print(f"   Multi-hop: {'✅' if result.get('used_multi_hop', False) else '❌'}")
                print(f"   Answer: {result['answer'][:200]}...")
            else:
                print(f"❌ Query failed: {result.get('error', 'Unknown error')}")
        
        else:
            print("⚠️ No collections found. Please upload a document first.")
        
        print("\n🎉 Integration test completed successfully!")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ultimate_integration())
