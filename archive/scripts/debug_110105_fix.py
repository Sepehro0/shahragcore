#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script for fixing 110105 code issue and RTL problems
"""

import asyncio
import sys
import os
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system")

from ultimate_rag_system import UltimateRAGSystem
import arabic_reshaper
from bidi.algorithm import get_display

async def test_110105_search():
    """Test specific search for code 110105"""
    print("🔍 Testing search for code 110105...")
    
    rag = UltimateRAGSystem()
    
    # Test the search directly
    collection_name = "jadval5-bodjee_176338230"
    
    try:
        # Test hybrid search
        results = await rag.hybrid_search("110105", collection_name, top_k=5)
        
        print(f"✅ Found {len(results)} results")
        
        for i, result in enumerate(results):
            print(f"\n--- Result {i+1} ---")
            print(f"ID: {result['id']}")
            print(f"Score: {result['hybrid_score']}")
            print(f"Text: {result['text'][:200]}...")
            print(f"Metadata: {result['metadata']}")
            
            # Test RTL fix
            if result['metadata'].get('hierarchy_title'):
                original = result['metadata']['hierarchy_title']
                fixed = rag._fix_persian_text_for_display(original)
                print(f"Original title: {original}")
                print(f"Fixed title: {fixed}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_full_query():
    """Test full query processing"""
    print("\n💬 Testing full query processing...")
    
    rag = UltimateRAGSystem()
    collection_name = "jadval5-bodjee_176338230"
    
    try:
        result = await rag.retrieve_and_answer(
            query="کد 110105 مربوط به چیه",
            collection_name=collection_name,
            top_k=5,
            use_reranking=True,
            use_multi_hop=True
        )
        
        print(f"Success: {result.get('success')}")
        if result.get('success'):
            print(f"Answer: {result.get('answer')}")
            print(f"Sources: {len(result.get('top_results', []))}")
            
            # Test RTL fix on answer
            if result.get('answer'):
                original_answer = result['answer']
                # Apply RTL fix to the answer
                fixed_answer = rag._fix_persian_text_for_display(original_answer)
                print(f"\nOriginal answer: {original_answer[:300]}...")
                print(f"Fixed answer: {fixed_answer[:300]}...")
        else:
            print(f"Error: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_rtl_fix():
    """Test RTL fix function"""
    print("\n🔧 Testing RTL fix function...")
    
    rag = UltimateRAGSystem()
    
    # Test text from the PDF
    test_text = "ﻣﺎﻟﻴﺎﺕ ﺍﺷﺨﺎﺹ ﺣﻘﻮﻗﻲ ﻏﻴﺮ ﺩﻭﻟﺘﻲ"
    
    print(f"Original: {test_text}")
    fixed = rag._fix_persian_text_for_display(test_text)
    print(f"Fixed: {fixed}")
    
    # Test with arabic_reshaper directly
    try:
        reshaped = arabic_reshaper.reshape(test_text)
        bidi_fixed = get_display(reshaped)
        print(f"Manual fix: {bidi_fixed}")
    except Exception as e:
        print(f"Manual fix error: {e}")

if __name__ == "__main__":
    print("🧪 Debugging 110105 and RTL issues...")
    print("="*60)
    
    # Test RTL fix
    test_rtl_fix()
    
    # Test search
    asyncio.run(test_110105_search())
    
    # Test full query
    asyncio.run(test_full_query())
