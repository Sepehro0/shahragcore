# -*- coding: utf-8 -*-
"""
تست جامع بودجه - گزارش دقیق
"""

import sys
import asyncio
import time
sys.path.insert(0, '.')

from core.refactored_rag_system import RefactoredRAGSystem


# سوالات تست
TEST_QUERIES = {
    "Cell Reference - Masaref": [
        "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403",
        "اعتبارات هزینه ای عمومی بنیاد ایران شناسی در سال 1403",
        "تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403",
        "تملک دارایی سرمایه ای متفرقه سازمان سنجش بند ج در سال 1403"
    ],
    "Aggregation - Sum": [
        "بودجه فرهنگستان هنر در سال 1403",
        "اعتبارات هزینه ای نهاد ریاست جمهوری در سال 1403",
        "درآمدهای وزارت نفت در سال 1401 چقدر است",
        "بودجه دانشگاه تهران"
    ],
    "Income - Manabe": [
        "درامد استانی اختصاصی دانشگاه تبریز در سال 1403"
    ]
}


async def test_query_detailed(rag, query: str, category: str, index: int):
    """تست یک query با جزئیات کامل"""
    
    print(f"\n{'='*90}")
    print(f"[{category}] Test #{index}: {query}")
    print(f"{'='*90}")
    
    start_time = time.time()
    
    try:
        result = await rag.retrieve_and_answer(
            query=query,
            collection_name='budget_financial',
            top_k=5
        )
        
        elapsed = time.time() - start_time
        
        # نتیجه
        success = result.get('success', False)
        answer = result.get('answer', '')
        answer_len = len(answer)
        
        # وضعیت
        print(f"\n📊 نتیجه:")
        print(f"  ✓ Success: {success}")
        print(f"  ✓ Time: {elapsed:.2f}s")
        print(f"  ✓ Answer Length: {answer_len} chars")
        
        if success and answer_len > 50:
            # نمایش پاسخ کامل
            print(f"\n💬 پاسخ کامل:")
            print(f"{'─'*90}")
            # Remove any prefix like "GenerationResponse(text='"
            clean_answer = answer
            if 'GenerationResponse(text=' in answer:
                # Extract the actual answer
                parts = answer.split("GenerationResponse(text='")
                if len(parts) > 1:
                    clean_answer = parts[1].split("',")[0] if "','" in parts[1] else parts[1].split("'")[0]
            
            print(clean_answer[:1000])  # اول 1000 کاراکتر
            if len(clean_answer) > 1000:
                print(f"... (+{len(clean_answer)-1000} chars more)")
            print(f"{'─'*90}")
            
            # Results preview
            top_results = result.get('top_results', [])
            if top_results:
                print(f"\n📄 Top Results ({len(top_results)}):")
                for i, res in enumerate(top_results[:2], 1):
                    score = res.get('score', res.get('hybrid_score', 0))
                    content_preview = res.get('text', res.get('content', ''))[:150]
                    print(f"  {i}. Score: {score:.3f}")
                    print(f"     Preview: {content_preview}...")
            
            # Confidence
            confidence = result.get('confidence', 0)
            print(f"\n📈 Confidence: {confidence:.2f}")
            
            # Metadata
            metadata = result.get('metadata', {})
            if metadata:
                print(f"\n🏷️  Metadata:")
                for key, val in list(metadata.items())[:3]:
                    print(f"  - {key}: {val}")
            
            return {
                'success': True,
                'time': elapsed,
                'answer_length': answer_len,
                'confidence': confidence,
                'num_results': len(top_results)
            }
        
        elif not success:
            print(f"\n❌ Error: {result.get('error', 'Unknown')}")
            return {'success': False, 'time': elapsed, 'error': result.get('error')}
        
        else:
            print(f"\n⚠️  Answer too short (expected >50 chars)")
            print(f"💬 Answer: {answer}")
            return {'success': False, 'time': elapsed, 'reason': 'answer_too_short'}
    
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'time': elapsed, 'exception': str(e)}


async def run_comprehensive_test():
    """اجرای تست جامع"""
    
    print("\n" + "🎯"*45)
    print("COMPREHENSIVE BUDGET TEST - Detailed Report")
    print("🎯"*45)
    
    # Initialize
    print("\n1️⃣ Initializing RefactoredRAGSystem...")
    rag = RefactoredRAGSystem()
    print("✅ Initialized")
    
    # Check orchestrators
    has_orch = getattr(rag, '_orchestrators_enabled', False)
    print(f"✅ Orchestrators: {'Enabled' if has_orch else 'Disabled'}")
    
    # Test all queries
    all_results = []
    
    for category, queries in TEST_QUERIES.items():
        print(f"\n\n{'#'*90}")
        print(f"# Category: {category}")
        print(f"{'#'*90}")
        
        for idx, query in enumerate(queries, 1):
            result = await test_query_detailed(rag, query, category, idx)
            all_results.append({
                'category': category,
                'query': query,
                **result
            })
            
            # Small delay
            await asyncio.sleep(1)
    
    # Summary
    print(f"\n\n{'='*90}")
    print("📊 FINAL SUMMARY")
    print(f"{'='*90}\n")
    
    passed = sum(1 for r in all_results if r.get('success'))
    total = len(all_results)
    avg_time = sum(r.get('time', 0) for r in all_results) / len(all_results)
    
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {total - passed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    print(f"Average Time: {avg_time:.2f}s")
    
    # Category breakdown
    print(f"\n📊 By Category:")
    for category in TEST_QUERIES.keys():
        cat_results = [r for r in all_results if r['category'] == category]
        cat_passed = sum(1 for r in cat_results if r.get('success'))
        cat_total = len(cat_results)
        print(f"  {category}: {cat_passed}/{cat_total} ({cat_passed/cat_total*100:.0f}%)")
    
    # Detailed results
    print(f"\n📋 Detailed Results:")
    for i, r in enumerate(all_results, 1):
        status = "✅" if r.get('success') else "❌"
        query_short = r['query'][:60] + "..." if len(r['query']) > 60 else r['query']
        print(f"  {status} {i}. [{r['category']}] {query_short} ({r.get('time', 0):.1f}s)")
    
    print(f"\n{'='*90}\n")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_comprehensive_test())
    sys.exit(0 if success else 1)



