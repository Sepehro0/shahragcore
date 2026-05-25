# -*- coding: utf-8 -*-
"""تست سریع بودجه"""
import sys, asyncio
sys.path.insert(0, '.')

QUERIES = [
    ("Q1", "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403"),
    ("Q2", "بودجه فرهنگستان هنر در سال 1403"),
    ("Q3", "درآمدهای وزارت نفت در سال 1401 چقدر است"),
    ("Q4", "بودجه دانشگاه تهران"),
    ("Q5", "درامد استانی اختصاصی دانشگاه تبریز در سال 1403")
]

async def main():
    from core.refactored_rag_system import RefactoredRAGSystem
    
    print("\n" + "="*80)
    print("تست بودجه - سوالات کاربر")
    print("="*80 + "\n")
    
    rag = RefactoredRAGSystem()
    print(f"✓ Initialized, Collections: {len(rag.get_collections())}\n")
    
    results = []
    for qid, query in QUERIES:
        print(f"\n{qid}: {query}")
        print("-"*80)
        
        r = await rag.retrieve_and_answer(query, 'budget_financial', top_k=5)
        success = r.get('success', False)
        ans = r.get('answer', '')
        ans_len = len(ans)
        
        if success and ans_len > 50:
            print(f"✅ SUCCESS ({ans_len} chars)")
            print(f"Answer: {ans[:300]}...")
            results.append(True)
        else:
            print(f"❌ FAILED")
            if not success:
                print(f"Error: {r.get('error', 'Unknown')}")
            else:
                print(f"Answer too short: {ans}")
            results.append(False)
    
    print("\n" + "="*80)
    passed = sum(results)
    print(f"📊 نتیجه: {passed}/{len(results)} موفق ({passed/len(results)*100:.0f}%)")
    print("="*80 + "\n")

asyncio.run(main())
