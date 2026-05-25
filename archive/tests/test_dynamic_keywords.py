#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست برای dynamic keyword extraction
"""

import sys
import asyncio
import chromadb
from core.gates.dynamic_keyword_extractor import DynamicKeywordExtractor

async def test_dynamic_extraction():
    """تست dynamic keyword extraction"""
    
    print("🧪 Testing Dynamic Keyword Extraction...")
    print("-" * 80)
    
    try:
        # Initialize ChromaDB client
        chroma_client = chromadb.PersistentClient(path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db")
        
        # Initialize extractor
        extractor = DynamicKeywordExtractor()
        
        # Test extraction for karbaran_omomi
        collection_name = "karbaran_omomi"
        print(f"📚 Extracting keywords for collection: {collection_name}")
        
        extracted = extractor.extract_keywords(
            collection_name=collection_name,
            chroma_client=chroma_client,
            force_refresh=True
        )
        
        print(f"\n✅ Extraction successful!")
        print(f"   Method: {extracted.extraction_method}")
        print(f"   Confidence: {extracted.confidence:.2f}")
        print(f"   Keywords count: {len(extracted.keywords)}")
        print(f"\n📝 Top 20 keywords:")
        for i, keyword in enumerate(extracted.keywords[:20], 1):
            print(f"   {i}. {keyword}")
        
        print(f"\n📄 Domain description:")
        print(f"   {extracted.domain_description[:200]}...")
        
        print("-" * 80)
        print("✅ TEST PASSED")
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_dynamic_extraction())
    sys.exit(0 if success else 1)



