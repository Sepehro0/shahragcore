#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست کامل zabete_qa
"""

import requests
import json
import sys

def test_zabete_complete():
    url = "http://localhost:8010/v2/query/streaming"
    
    queries = [
        ("قراردادهای epc رو توضیح بده", "should_pass"),
        ("در قراردادهای EPC تاخیر در پرداخت ها چگونه است؟", "should_pass"),
        ("قراردادهای bot رو توضیح بده", "check_data"),
        ("تفاوت epc و bot چیست؟", "should_pass"),
        ("قرارداد qbs چیست؟", "should_pass"),
    ]
    
    print("🧪 Testing zabete_qa")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for query, expected in queries:
        print(f"\n📝 Query: {query}")
        
        payload = {
            "query": query,
            "collection_name": "zabete_qa",
            "top_k": 5,
            "use_reranking": True,
            "use_multi_hop": False,
            "temperature": 0.1
        }
        
        try:
            response = requests.post(url, json=payload, stream=True, timeout=30)
            
            was_rejected = False
            answer = ""
            
            for line in response.iter_lines():
                if not line:
                    continue
                
                line_str = line.decode('utf-8')
                
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    try:
                        data = json.loads(data_str)
                        
                        if data.get('type') == 'complete':
                            if data.get('success') == False:
                                was_rejected = True
                                answer = data.get('answer', '')
                            else:
                                answer = data.get('answer', '')
                    except:
                        pass
            
            if was_rejected:
                print(f"   ❌ REJECTED")
                print(f"      {answer[:150]}...")
                if expected == "should_pass":
                    failed += 1
                else:
                    passed += 1
            else:
                print(f"   ✅ ANSWERED ({len(answer)} chars)")
                print(f"      {answer[:150]}...")
                passed += 1
        
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"📊 Results: {passed}/{len(queries)} passed")
    print("=" * 80)
    
    return failed == 0

if __name__ == "__main__":
    success = test_zabete_complete()
    sys.exit(0 if success else 1)



