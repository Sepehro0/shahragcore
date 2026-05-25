#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Test Script - فقط نتایج نهایی
"""

import requests
import json

API_URL = "http://185.13.230.254:8010/v2/query/streaming"

queries = [
    ("karbaran_omomi", "آیا آرد خام هم پذیرفته می‌شود؟", "out_of_scope"),
    ("karbaran_omomi", "برای شروع فوتبال بازی کردن چیکار باید بکنم؟", "out_of_scope"),
    ("zinaf_dakheli", "صندوق نوآور چیه", "cross_domain"),
    ("zinaf_dakheli", "چطور از صندوق ها سرمایه بگیرم ؟", "cross_domain"),
]

for collection, query, expected in queries:
    print(f"\n{'='*60}")
    print(f"Collection: {collection}")
    print(f"Query: {query}")
    print(f"Expected: {expected}")
    print(f"{'='*60}")
    
    payload = {"query": query, "collection_name": collection, "top_k": 5}
    
    response = requests.post(API_URL, json=payload, stream=True, timeout=60)
    
    complete_chunk = None
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data:'):
                try:
                    chunk = json.loads(line_str[5:].strip())
                    if chunk.get('type') == 'complete':
                        complete_chunk = chunk
                        break
                except:
                    pass
    
    if complete_chunk:
        print(f"Success: {complete_chunk.get('success')}")
        print(f"Answer: {complete_chunk.get('answer', '')[:100]}...")
        print(f"Metadata: {json.dumps(complete_chunk.get('metadata', {}), ensure_ascii=False, indent=2)}")
        print(f"Used Features: {json.dumps(complete_chunk.get('used_features', {}), ensure_ascii=False)}")
        
        rejected_by = complete_chunk.get('metadata', {}).get('rejected_by')
        if rejected_by:
            print(f"✅ REJECTED by: {rejected_by}")
        else:
            print(f"⚠️ NOT REJECTED (should be rejected for {expected})")
    else:
        print("❌ No complete chunk found")

