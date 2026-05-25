#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست ساده zabete_qa
"""

import requests
import json

def test_simple():
    url = "http://localhost:8010/v2/query/streaming"
    
    query = "قراردادهای epc رو توضیح بده"
    
    payload = {
        "query": query,
        "collection_name": "zabete_qa",
        "top_k": 5,
        "use_reranking": True,
        "use_multi_hop": False,
        "temperature": 0.1
    }
    
    print(f"Testing: {query}")
    
    response = requests.post(url, json=payload, stream=True, timeout=30)
    
    for line in response.iter_lines():
        if not line:
            continue
        
        line_str = line.decode('utf-8')
        
        if line_str.startswith('data: '):
            data_str = line_str[6:]
            try:
                data = json.loads(data_str)
                
                if data.get('type') == 'complete':
                    print(f"\nSuccess: {data.get('success')}")
                    if data.get('success') == False:
                        print(f"Rejected by: {data.get('metadata', {}).get('rejected_by')}")
                        print(f"Reason: {data.get('metadata', {}).get('reason')}")
                    print(f"Answer: {data.get('answer', '')[:300]}...")
            except:
                pass

if __name__ == "__main__":
    test_simple()



