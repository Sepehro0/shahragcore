#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug qavanin API response
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ultimate_rag_system import UltimateRAGSystem


async def main():
    print("🔍 Debugging qavanin query...")
    
    rag = UltimateRAGSystem()
    
    query = "تعریف «محیط کسب‌وکار» چیست؟"
    collection = "qavanin"
    
    print(f"\n📝 Query: {query}")
    print(f"📦 Collection: {collection}")
    
    # Test hybrid_search directly
    print(f"\n🔍 Calling hybrid_search...")
    results = await rag.hybrid_search(query, collection, top_k=3)
    
    print(f"\n✅ Got {len(results)} results")
    
    for idx, res in enumerate(results, 1):
        print(f"\nResult {idx}:")
        print(f"  ID: {res.get('id', 'N/A')[:30]}")
        print(f"  Dense score: {res.get('dense_score', 'N/A')}")
        print(f"  BM25 score: {res.get('bm25_score', 'N/A')}")
        print(f"  Hybrid score: {res.get('hybrid_score', 'N/A')}")
        print(f"  Original score: {res.get('original_score', 'N/A')}")
        print(f"  Final score: {res.get('final_score', 'N/A')}")
        print(f"  Text: {res.get('text', '')[:100]}...")
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
