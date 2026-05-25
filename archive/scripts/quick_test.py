#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from ultimate_rag_system import UltimateRAGSystem

async def quick_test():
    rag = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    tests = [
        ("110103", "مالیات عملکرد شرکتهای دولتی"),
        ("110104", "مالیات بنگاه"),  # کافیه یک بخشش رو داشته باشه
        ("110105", "مالیات اشخاص حقوقی غیر دولتی")
    ]
    
    for code, expected in tests:
        print(f"\n{'='*80}")
        print(f"Code: {code}")
        print(f"Expected (contains): {expected}")
        print("-"*80)
        
        response = await rag.retrieve_and_answer(
            f"کد {code} راجع به چیه؟",
            collection_name="jadval5-bodje"
        )
        
        if response.get('success'):
            answer = response.get('answer', '')
            found = expected in answer
            print(f"Status: {'✅ PASS' if found else '❌ FAIL'}")
            print(f"Answer (first 200 chars):\n{answer[:200]}...")
        else:
            print(f"❌ ERROR: {response.get('error', '')}")

if __name__ == "__main__":
    asyncio.run(quick_test())


