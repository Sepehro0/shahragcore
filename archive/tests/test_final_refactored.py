# -*- coding: utf-8 -*-
"""
Final Comprehensive Test - RefactoredRAGSystem
تست نهایی جامع برای تأیید عملکرد کامل
"""

import sys
import asyncio
import time
sys.path.insert(0, '.')

from core.refactored_rag_system import RefactoredRAGSystem


async def test_comprehensive():
    """تست جامع نهایی"""
    
    print("\n" + "🎯"*40)
    print("FINAL COMPREHENSIVE TEST - RefactoredRAGSystem")
    print("🎯"*40 + "\n")
    
    # Initialize
    print("1️⃣ Initialization...")
    start_time = time.time()
    rag = RefactoredRAGSystem()
    init_time = time.time() - start_time
    
    # Check features
    has_orch = getattr(rag, '_orchestrators_enabled', False)
    collections = rag.get_collections()
    
    print(f"   ✓ Initialized in {init_time:.2f}s")
    print(f"   ✓ Orchestrators: {'✅ Enabled' if has_orch else '❌ Disabled'}")
    print(f"   ✓ Collections: {len(collections)} ({', '.join(collections)})")
    
    # Test queries
    print("\n2️⃣ Testing Queries...")
    
    test_cases = [
        {
            'name': 'QA - Exact Match',
            'query': 'صندوق باور چیست؟',
            'collection': 'karbaran_omomi',
            'expected_min_length': 100
        },
        {
            'name': 'Budget - Default Year',
            'query': 'درآمد وزارت بهداشت',
            'collection': 'budget_financial',
            'expected_min_length': 50
        },
        {
            'name': 'Contact Info - Direct',
            'query': 'ایمیل صندوق باور',
            'collection': 'karbaran_omomi',
            'expected_min_length': 20
        },
        {
            'name': 'Multi-part',
            'query': 'تفاوت صندوق نوآور و باور چیست؟',
            'collection': 'karbaran_omomi',
            'expected_min_length': 100
        }
    ]
    
    results = []
    for test in test_cases:
        print(f"\n   {test['name']}:")
        print(f"      Query: {test['query']}")
        
        start = time.time()
        result = await rag.retrieve_and_answer(
            query=test['query'],
            collection_name=test['collection'],
            top_k=5
        )
        elapsed = time.time() - start
        
        success = result.get('success', False)
        answer_len = len(result.get('answer', ''))
        meets_length = answer_len >= test['expected_min_length']
        
        status = "✅" if (success and meets_length) else "❌"
        print(f"      {status} Success: {success}, Length: {answer_len} chars, Time: {elapsed:.2f}s")
        
        if success and meets_length:
            # Show preview
            preview = result['answer'][:150].replace('\n', ' ')
            print(f"      Preview: {preview}...")
        elif not success:
            print(f"      Error: {result.get('error', 'Unknown')}")
        
        results.append({
            'test': test['name'],
            'success': success and meets_length,
            'time': elapsed
        })
    
    # Test streaming
    print("\n3️⃣ Testing Streaming...")
    print("   Streaming query...")
    
    full_resp = ""
    chunk_count = 0
    start = time.time()
    
    async for chunk in rag.retrieve_and_answer_stream(
        query='ماموریت موسسه دانشمند چیست؟',
        collection_name='karbaran_omomi',
        top_k=3
    ):
        if chunk.get('chunk'):
            full_resp += chunk['chunk']
            chunk_count += 1
    
    elapsed = time.time() - start
    stream_success = chunk_count > 0 and len(full_resp) > 50
    
    print(f"   {'✅' if stream_success else '❌'} Chunks: {chunk_count}, Length: {len(full_resp)}, Time: {elapsed:.2f}s")
    
    results.append({
        'test': 'Streaming',
        'success': stream_success,
        'time': elapsed
    })
    
    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    success_rate = (passed / total * 100) if total > 0 else 0
    avg_time = sum(r['time'] for r in results) / len(results)
    
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {total - passed}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Avg Time: {avg_time:.2f}s")
    
    print("\nDetails:")
    for r in results:
        status = '✅' if r['success'] else '❌'
        print(f"  {status} {r['test']}: {r['time']:.2f}s")
    
    print("\n" + "="*80)
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - PRODUCTION READY!")
    else:
        print("⚠️ SOME TESTS FAILED - NEEDS REVIEW")
    
    print("="*80 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(test_comprehensive())
    sys.exit(0 if success else 1)
