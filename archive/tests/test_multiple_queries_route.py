#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست سریع چند query مختلف برای Database Route
"""

import requests
import json
from datetime import datetime

API_URL = "http://localhost:8010/v2/query/streaming"

QUERIES = [
    "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403",
    "بودجه فرهنگستان هنر در سال 1403",
    "تملک دارایی عمومی دانشگاه تهران در سال 1403",
    "درآمد عمومی ملی شرکت دولتی پست بانک در سال 1402",
]

print("="*80)
print("🧪 تست چند Query برای Database Route")
print("="*80)

results = []

for i, query in enumerate(QUERIES, 1):
    print(f"\n📋 Query {i}: {query[:50]}...")
    
    try:
        response = requests.post(API_URL, json={
            'query': query,
            'collection_name': 'budget_financial',
            'top_k': 5,
            'use_reranking': True,
            'use_multi_hop': True,
            'temperature': 0.1,
            'stream': True
        }, stream=True, timeout=120)
        
        route_path = None
        has_database_results = False
        answer_preview = None
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        
                        if data.get('type') == 'complete':
                            metadata = data.get('metadata', {})
                            route_path = metadata.get('route_path') or data.get('route_path')
                            has_database_results = data.get('database_results') is not None or \
                                                   metadata.get('database_results') is not None
                            answer_preview = data.get('answer', data.get('full_answer', ''))[:100]
                            
                    except json.JSONDecodeError:
                        pass
        
        result = {
            'query': query[:50],
            'route_path': route_path,
            'has_database_results': has_database_results,
            'answer_preview': answer_preview
        }
        results.append(result)
        
        print(f"   ✅ route_path: {route_path}")
        print(f"   📊 database_results: {has_database_results}")
        if answer_preview:
            print(f"   💬 Answer: {answer_preview}...")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        results.append({'query': query[:50], 'error': str(e)})

print("\n" + "="*80)
print("📊 خلاصه نتایج:")
print("="*80)

success_count = sum(1 for r in results if r.get('route_path') == 'database')
print(f"\n✅ تعداد query های با route_path=database: {success_count}/{len(results)}")

for r in results:
    status = "✅" if r.get('route_path') == 'database' else "❌"
    print(f"   {status} {r.get('query')} -> {r.get('route_path', 'N/A')}")

