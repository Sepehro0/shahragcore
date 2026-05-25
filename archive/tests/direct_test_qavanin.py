#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direct test of qavanin collection
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.vector_store import VectorStore, VectorStoreConfig
from services.persian_embedding_service import PersianEmbeddingService

def main():
    print("🔍 Testing qavanin collection directly...")
    
    # Initialize services
    print("\n1️⃣ Initializing embedding service...")
    embedding_service = PersianEmbeddingService()
    print(f"✅ Embedding service ready")
    
    print("\n2️⃣ Initializing vector store...")
    config = VectorStoreConfig(
        db_path="./chroma_db",
        embedding_service=embedding_service
    )
    vector_store = VectorStore(config)
    print(f"✅ Vector store ready")
    
    # Test query
    query = "تعریف «محیط کسب‌وکار» چیست؟"
    print(f"\n3️⃣ Testing query: {query}")
    
    # Generate query embedding
    print("   Generating query embedding...")
    query_embedding = embedding_service.generate_embedding(query)
    print(f"   Query embedding dimension: {len(query_embedding)}")
    
    # Search
    print(f"\n4️⃣ Searching in qavanin collection...")
    try:
        results = vector_store.query(
            collection_name='qavanin',
            query_embedding=query_embedding,
            top_k=3
        )
        
        print(f"✅ Found {len(results)} results\n")
        
        for idx, result in enumerate(results, 1):
            print(f"Result {idx}:")
            print(f"  Distance: {result.get('distance', 'N/A'):.4f}")
            print(f"  Text: {result.get('text', '')[:200]}...")
            print()
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
