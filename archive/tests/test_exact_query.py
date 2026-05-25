#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from ultimate_rag_system import UltimateRAGSystem

async def test_exact_query():
    """Test exact query from user"""
    
    rag = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    # سوال دقیق کاربر
    query = "کد 110105 راجع به چیه؟"
    
    print("\n" + "="*80)
    print(f"Query: {query}")
    print("="*80)
    
    response = await rag.retrieve_and_answer(query, collection_name="jadval5-bodje")
    
    if response.get('success'):
        answer = response.get('answer', '')
        print(f"\nAnswer:\n{answer}\n")
        
        # Check correctness
        if "110105" in answer:
            if "وجود ندارد" in answer or "ندارد" in answer or "[عنوان دقیق از 📄]" in answer:
                print("❌ WRONG: Model says code doesn't exist!")
            elif "مالیات" in answer and ("غیر دولتی" in answer or "یتلود ریغ" in answer):
                print("✅ CORRECT: Model found the code and gave correct answer!")
            else:
                print("⚠️ PARTIAL: Code found but answer unclear")
        else:
            print("❌ WRONG: Code 110105 not mentioned in answer")
    else:
        print(f"❌ ERROR: {response.get('error', '')}")

if __name__ == "__main__":
    asyncio.run(test_exact_query())


