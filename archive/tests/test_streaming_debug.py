# -*- coding: utf-8 -*-
import requests
import json

API_BASE_URL = "http://localhost:8010"
COLLECTION_NAME = "comprehensive_budget_test"

question = "تمامی هزینه های اورژانس استان تهران در سال 1403 چقدر بوده است ؟"

print(f"Testing streaming query: {question}\n")
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
        timeout=120
    )
    
    print(f"Status Code: {response.status_code}\n")
    
    if response.status_code != 200:
        print(f"Error: {response.text}")
    else:
        print("Raw streaming output:\n")
        print("-"*80)
        
        for i, line in enumerate(response.iter_lines()):
            if line:
                line_str = line.decode('utf-8')
                print(f"[{i}] {line_str}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

