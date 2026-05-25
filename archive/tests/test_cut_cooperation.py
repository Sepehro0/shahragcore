#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست برای سوالات مربوط به قطع همکاری
"""

import requests
import json
import sys

def test_cut_cooperation_questions():
    """تست سوالات مربوط به قطع همکاری"""
    
    url = "http://localhost:8010/v2/query/streaming"
    
    queries = [
        "چیکار کنیم باهامون قطع همکاری میشه؟",
        "چه اشتباهی منجر به قطع همکاری میشه؟",
        "چه خطایی منجر به قطع همکاری میشود؟"
    ]
    
    print("🧪 Testing cut cooperation questions...")
    print("-" * 80)
    
    all_passed = True
    
    for query in queries:
        payload = {
            "query": query,
            "collection_name": "karbaran_omomi",
            "top_k": 5,
            "use_reranking": True,
            "use_multi_hop": True,
            "temperature": 0.1
        }
        
        print(f"\n📝 Query: {query}")
        
        try:
            response = requests.post(
                url,
                json=payload,
                stream=True,
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"❌ Error: Status code {response.status_code}")
                all_passed = False
                continue
            
            full_answer = ""
            was_rejected = False
            
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
                                full_answer = data.get('answer', '')
                                print(f"   ❌ Rejected: {full_answer[:150]}...")
                                print(f"   Rejected by: {data.get('metadata', {}).get('rejected_by')}")
                            else:
                                full_answer = data.get('answer', '')
                                print(f"   ✅ Success: Answer received ({len(full_answer)} chars)")
                                print(f"   Preview: {full_answer[:200]}...")
                    
                    except json.JSONDecodeError:
                        pass
            
            if was_rejected:
                all_passed = False
        
        except Exception as e:
            print(f"❌ Error: {e}")
            all_passed = False
    
    print("-" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("⚠️ SOME TESTS FAILED")
    
    return all_passed


if __name__ == "__main__":
    success = test_cut_cooperation_questions()
    sys.exit(0 if success else 1)

