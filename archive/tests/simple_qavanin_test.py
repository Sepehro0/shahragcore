#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple direct test using chromadb
"""

import sys
import chromadb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.persian_embedding_service import PersianEmbeddingService

def main():
    print("🔍 Simple qavanin test...")
    
    # 1. Initialize embedding
    print("\n1️⃣ Loading embedding model...")
    embedding_service = PersianEmbeddingService()
    print("✅ Ready")
    
    # 2. Connect to database
    print("\n2️⃣ Connecting to database...")
    client = chromadb.PersistentClient(path='./chroma_db')
    col = client.get_collection('qavanin')
    print(f"✅ Connected. Documents: {col.count()}")
    
    # 3. Test query
    query = "تعریف «محیط کسب‌وکار» چیست؟"
    print(f"\n3️⃣ Query: {query}")
    
    # Generate embedding
    print("   Generating embedding...")
    query_emb = embedding_service.generate_embedding(query)
    print(f"   Dimension: {len(query_emb)}")
    
    # Search
    print("\n4️⃣ Searching...")
    try:
        results = col.query(
            query_embeddings=[query_emb],
            n_results=3,
            include=['documents', 'distances', 'metadatas']
        )
        
        print(f"✅ Found {len(results['documents'][0])} results\n")
        
        for idx, (doc, dist) in enumerate(zip(results['documents'][0], results['distances'][0]), 1):
            print(f"Result {idx}:")
            print(f"  Distance: {dist:.4f}")
            print(f"  Text: {doc[:200]}...")
            print()
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
