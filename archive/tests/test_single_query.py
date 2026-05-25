# -*- coding: utf-8 -*-
"""تست تک سوال"""
import requests
import json
import sys

API_BASE_URL = "http://localhost:8010"
COLLECTION_NAME = "comprehensive_budget_test"

if len(sys.argv) < 2:
    print("Usage: python test_single_query.py 'your question here'")
    sys.exit(1)

question = sys.argv[1]

print(f"سوال: {question}\n")
print("="*80)

try:
    payload = {
        "query": question,
        "collection_name": COLLECTION_NAME,
        "top_k": 10,
        "use_reranking": True,
        "enable_multi_hop": True,
        "temperature": 0.1
    }
    
    response = requests.post(
        f"{API_BASE_URL}/query/stream",
        json=payload,
        stream=True,
        timeout=60
    )
    
    if response.status_code != 200:
        print(f"خطا: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    full_answer = ""
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            
            if line_str.startswith('event:'):
                event = line_str.split(':', 1)[1].strip()
                print(f"\n[{event}]")
                continue
            
            if line_str.startswith('data:'):
                try:
                    data_str = line_str.split(':', 1)[1].strip()
                    data = json.loads(data_str)
                    
                    if 'token' in data:
                        token = data.get('token', '')
                        full_answer = data.get('full_answer', token)
                        
                    if 'answer' in data:
                        full_answer = data.get('answer', full_answer)
                    
                    if 'route_path' in data:
                        print(f"مسیر: {data.get('route_path')}")
                    
                    if 'database_rows_count' in data:
                        print(f"تعداد ردیف: {data.get('database_rows_count')}")
                    
                except json.JSONDecodeError:
                    pass
    
    print("\n" + "="*80)
    print("\nپاسخ نهایی:")
    print("-"*80)
    print(full_answer)
    print("\n" + "="*80)
    print(f"طول پاسخ: {len(full_answer)} کاراکتر")

except Exception as e:
    print(f"خطا: {e}")
    import traceback
    traceback.print_exc()

