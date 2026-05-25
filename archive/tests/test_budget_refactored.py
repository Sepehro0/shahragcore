# -*- coding: utf-8 -*-
"""
تست بودجه با RefactoredRAGSystem
"""
import sys, asyncio, time
sys.path.insert(0, '.')

from core.refactored_rag_system import RefactoredRAGSystem

QUERIES = {
    "Cell Reference": [
        "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403",
        "اعتبارات هزینه ای عمومی بنیاد ایران شناسی در سال 1403",
        "تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403",
        "تملک دارایی سرمایه ای متفرقه سازمان سنجش بند ج در سال 1403"
    ],
    "Aggregation": [
        "بودجه فرهنگستان هنر در سال 1403",
        "اعتبارات هزینه ای نهاد ریاست جمهوری در سال 1403",
        "درآمدهای وزارت نفت در سال 1401 چقدر است",
        "بودجه دانشگاه تهران"
    ],
    "Income": [
        "درامد استانی اختصاصی دانشگاه تبریز در سال 1403"
    ]
}

async def main():
    print("\n" + "="*90)
    print("تست بودجه - RefactoredRAGSystem")
    print("="*90 + "\n")
    
    rag = RefactoredRAGSystem()
    orch_enabled = getattr(rag, '_orchestrators_enabled', False)
    print(f"✓ RAG Initialized")
    print(f"✓ Orchestrators Enabled: {orch_enabled}\n")
    
    all_results = []
    
    for category, queries in QUERIES.items():
        print(f"\n{'#'*90}")
        print(f"# {category}")
        print(f"{'#'*90}\n")
        
        for i, q in enumerate(queries, 1):
            print(f"{i}. {q}")
            print("-"*90)
            
            start = time.time()
            r = await rag.retrieve_and_answer(q, 'budget_financial', top_k=5)
            elapsed = time.time() - start
            
            success = r.get('success', False)
            ans = r.get('answer', '')
            ans_len = len(ans)
            
            if success and ans_len > 50:
                print(f"✅ SUCCESS ({elapsed:.1f}s, {ans_len} chars)")
                
                # نمایش پاسخ
                clean_ans = str(ans)
                if 'GenerationResponse' in clean_ans:
                    try:
                        import re
                        match = re.search(r"text='([^']*)'", clean_ans)
                        if match:
                            clean_ans = match.group(1)
                    except:
                        pass
                
                print(f"\nپاسخ:")
                print(clean_ans[:600])
                if len(clean_ans) > 600:
                    print(f"... (+{len(clean_ans)-600} chars)")
                
                all_results.append({'category': category, 'query': q, 'success': True, 'time': elapsed, 'answer': clean_ans})
            else:
                print(f"❌ FAILED ({elapsed:.1f}s)")
                if not success:
                    print(f"Error: {r.get('error', 'Unknown')}")
                else:
                    print(f"Answer too short: {ans[:200]}")
                
                all_results.append({'category': category, 'query': q, 'success': False, 'time': elapsed})
            
            print()
    
    # خلاصه
    print("\n" + "="*90)
    print("📊 خلاصه نتایج")
    print("="*90)
    
    passed = sum(1 for r in all_results if r['success'])
    total = len(all_results)
    
    print(f"\nکل تست‌ها: {total}")
    print(f"✅ موفق: {passed}")
    print(f"❌ ناموفق: {total - passed}")
    print(f"نرخ موفقیت: {passed/total*100:.1f}%")
    
    # به تفکیک دسته
    print(f"\nبه تفکیک دسته:")
    for cat in QUERIES.keys():
        cat_results = [r for r in all_results if r['category'] == cat]
        cat_passed = sum(1 for r in cat_results if r['success'])
        cat_total = len(cat_results)
        print(f"  {cat}: {cat_passed}/{cat_total} ({cat_passed/cat_total*100:.0f}%)")
    
    print("\n" + "="*90 + "\n")
    
    # ذخیره نتایج
    return all_results

if __name__ == "__main__":
    results = asyncio.run(main())
    sys.exit(0 if all(r['success'] for r in results) else 1)
