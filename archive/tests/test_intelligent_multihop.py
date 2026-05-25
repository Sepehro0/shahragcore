# -*- coding: utf-8 -*-
"""
تست سیستم هوشمند Multi-Hop
"""

import asyncio
import sys
sys.path.insert(0, '.')

from search.multi_hop_retriever import MultiHopRetriever

async def test_intelligent_multihop():
    print("\n" + "="*80)
    print("🧠 تست سیستم هوشمند Multi-Hop")
    print("="*80)
    
    retriever = MultiHopRetriever()
    
    test_queries = [
        {
            'query': 'تفاوت صندوق نوآور و باور چیه؟',
            'expected_multihop': True,
            'expected_type': 'comparison'
        },
        {
            'query': 'صندوق باور چیست؟',
            'expected_multihop': False,
            'expected_type': 'factual'
        },
        {
            'query': 'تمام دوره‌های آموزشی موسسه دانشمند',
            'expected_multihop': True,
            'expected_type': 'aggregation'
        },
        {
            'query': 'صندوق نوآور و صندوق باور و شبکه تحقیق چه خدماتی دارند؟',
            'expected_multihop': True,
            'expected_type': 'multi_entity'
        },
        {
            'query': 'چگونه می‌توانم در جایزه نوآوری ثبت‌نام کنم؟',
            'expected_multihop': False,
            'expected_type': 'procedural'
        }
    ]
    
    success_count = 0
    total_count = len(test_queries)
    
    for i, test in enumerate(test_queries, 1):
        query = test['query']
        expected_multihop = test['expected_multihop']
        expected_type = test['expected_type']
        
        print(f"\n{'─'*80}")
        print(f"Test {i}/{total_count}: {query}")
        print('─'*80)
        
        # تحلیل query
        analysis = retriever.analyze_query(query)
        
        # نمایش نتایج
        print(f"📊 نوع سوال: {analysis.get('type', 'unknown')}")
        print(f"🎯 Multi-hop: {analysis.get('requires_multi_hop', False)}")
        print(f"📈 Confidence: {analysis.get('confidence', 0):.2f}")
        print(f"🔢 Estimated rows: {analysis.get('estimated_rows', 0)}")
        
        if analysis.get('entities'):
            print(f"💡 Entities: {analysis['entities']}")
        
        if analysis.get('hops'):
            print(f"🔄 Hops count: {len(analysis['hops'])}")
            for j, hop in enumerate(analysis['hops'], 1):
                print(f"   Hop {j}: {hop.get('query', '')} ({hop.get('purpose', '')})")
        
        if analysis.get('reasoning'):
            print(f"🧠 Reasoning: {analysis['reasoning']}")
        
        # بررسی صحت
        is_correct = (
            analysis.get('requires_multi_hop') == expected_multihop and
            expected_type in analysis.get('type', '')
        )
        
        if is_correct:
            success_count += 1
            print(f"✅ PASSED")
        else:
            print(f"❌ FAILED (Expected multi-hop={expected_multihop}, type={expected_type})")
    
    print(f"\n{'='*80}")
    print(f"📈 نتیجه نهایی: {success_count}/{total_count} ({success_count/total_count*100:.0f}% موفق)")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_intelligent_multihop())

