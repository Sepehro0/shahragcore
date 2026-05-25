#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست دقیق برای سوالات کاملاً نامربوط
"""

import requests
import json
import sys

def test_irrelevant_detailed():
    """تست سوال کاملاً نامربوط با جزئیات بیشتر"""
    
    url = "http://localhost:8010/v2/query/streaming"
    
    queries = [
        "چطوری خونه بگیرم؟",
        "آب و هوا چطوره؟",
        "بهترین رستوران کجاست؟"
    ]
    
    print("🧪 Testing completely irrelevant questions...")
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
                                full_answer = data.get('answer', '')
                                
                                # بررسی نوع پیام
                                is_out_of_scope = 'خارج از حوزه' in full_answer
                                has_technical_details = any(kw in full_answer.lower() for kw in ['gates_failed', 'keyword_coverage', 'quality_score'])
                                
                                print(f"   Answer type: {'خارج از حوزه' if is_out_of_scope else 'اطلاعات کافی نیست'}")
                                print(f"   Has technical details: {'❌' if has_technical_details else '✅'}")
                                print(f"   Answer preview: {full_answer[:150]}...")
                                
                                if not has_technical_details:
                                    print(f"   ✅ Good rejection message")
                                else:
                                    print(f"   ❌ Still has technical details")
                                    all_passed = False
                    
                    except json.JSONDecodeError:
                        pass
        
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
    success = test_irrelevant_detailed()
    sys.exit(0 if success else 1)


