#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست Collection budget_financial
"""

import requests
import json
import time

API_URL = "http://185.13.230.254:8010/v2/query/streaming"

# سوالات تست
TEST_QUERIES = [
    "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403",
    "بودجه فرهنگستان هنر در سال 1403",
    "اعتبارات هزینه ای نهاد ریاست جمهوری در سال 1403",
    "درآمدهای وزارت نفت در سال 1401 چقدر است",
    "بودجه دانشگاه تهران",
    "درامد استانی اختصاصی دانشگاه تبریز در سال 1403"
]

print("="*80)
print("🧪 تست Collection budget_financial")
print("="*80)

results = []

for i, query in enumerate(TEST_QUERIES, 1):
    print(f"\n[{i}/{len(TEST_QUERIES)}] {query[:60]}...")
    
    try:
        response = requests.post(API_URL, json={
            'query': query,
            'collection_name': 'budget_financial',
            'top_k': 5
        }, stream=True, timeout=60)
        
        complete_chunk = None
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data:'):
                    try:
                        chunk = json.loads(line_str[5:].strip())
                        if chunk.get('type') == 'complete' or chunk.get('done'):
                            complete_chunk = chunk
                            break
                    except:
                        pass
        
        if complete_chunk:
            success = complete_chunk.get('success')
            print(f"   ✅ Success: {success}")
            
            if success:
                answer = complete_chunk.get('answer', '')
                print(f"   📄 Answer: {answer[:150]}...")
                
                metadata = complete_chunk.get('metadata', {})
                if metadata.get('query_complexity'):
                    qc = metadata['query_complexity']
                    print(f"   📊 Type: {qc.get('type')}, Complexity: {qc.get('complexity_score', 0):.2f}")
                
                if metadata.get('confidence'):
                    print(f"   📊 Confidence: {metadata['confidence']:.2f}")
            else:
                metadata = complete_chunk.get('metadata', {})
                print(f"   🚫 Rejected: {metadata.get('rejected_by')}")
                print(f"   Reason: {metadata.get('reason')}")
            
            results.append({'query': query, 'success': success})
        else:
            print(f"   ❌ No complete chunk")
            results.append({'query': query, 'success': False})
        
        time.sleep(2)
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        results.append({'query': query, 'success': False})

print("\n" + "="*80)
print("📊 Summary:")
print("="*80)
success_count = sum(1 for r in results if r.get('success'))
print(f"✅ Successful: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")

if success_count == len(results):
    print("\n🎉 همه تست‌ها موفق بودند!")
else:
    print(f"\n⚠️  {len(results) - success_count} تست ناموفق")

print("="*80)

