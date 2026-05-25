#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست سریع برای بررسی Database Route
"""

import requests
import json

API_URL = "http://localhost:8010/v2/query/streaming"

# یک سوال ساده برای تست
query = "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403"

print("="*80)
print("🧪 تست Database Route")
print("="*80)
print(f"Query: {query}")
print("")

try:
    response = requests.post(API_URL, json={
        'query': query,
        'collection_name': 'budget_financial',
        'top_k': 5
    }, stream=True, timeout=30)
    
    chunks = []
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data:'):
                try:
                    chunk = json.loads(line_str[5:].strip())
                    chunks.append(chunk)
                    
                    # نمایش chunk های مهم
                    if chunk.get('type') == 'start':
                        print(f"✅ Start event received")
                    elif chunk.get('type') == 'context':
                        print(f"📚 Context received: {len(chunk.get('sources', []))} sources")
                        print(f"   route_path: {chunk.get('route_path', 'N/A')}")
                    elif chunk.get('type') == 'complete':
                        print(f"✅ Complete event received")
                        print(f"   Success: {chunk.get('success')}")
                        metadata = chunk.get('metadata', {})
                        print(f"   Metadata:")
                        if 'query_complexity' in metadata:
                            qc = metadata['query_complexity']
                            print(f"      - query_type: {qc.get('type')}")
                            print(f"      - complexity: {qc.get('complexity_score')}")
                        if 'route_path' in metadata:
                            print(f"      - route_path: {metadata.get('route_path')}")
                        if 'retrieval_route' in metadata:
                            print(f"      - retrieval_route: {metadata.get('retrieval_route')}")
                        if 'database_results' in chunk:
                            print(f"   Database results: Yes")
                        break
                except:
                    pass
    
    print("")
    print("="*80)
    print(f"Total chunks: {len(chunks)}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

