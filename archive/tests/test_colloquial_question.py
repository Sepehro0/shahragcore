#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست برای سوالات محاوره‌ای
"""

import requests
import json
import sys

def test_colloquial_question():
    """تست سوال محاوره‌ای"""
    
    url = "http://localhost:8010/v2/query/streaming"
    
    payload = {
        "query": "پروژه تهش مال کی میشه؟",
        "collection_name": "karbaran_omomi",
        "top_k": 5,
        "use_reranking": True,
        "use_multi_hop": True,
        "temperature": 0.1
    }
    
    print("🧪 Testing colloquial question...")
    print(f"📝 Query: {payload['query']}")
    print(f"📚 Collection: {payload['collection_name']}")
    print("-" * 80)
    
    try:
        response = requests.post(
            url,
            json=payload,
            stream=True,
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"❌ Error: Status code {response.status_code}")
            return False
        
        print("✅ Connection established")
        print("-" * 80)
        
        full_answer = ""
        has_ownership_info = False
        
        for line in response.iter_lines():
            if not line:
                continue
            
            line_str = line.decode('utf-8')
            
            if line_str.startswith('data: '):
                data_str = line_str[6:]
                try:
                    data = json.loads(data_str)
                    
                    if data.get('type') == 'complete':
                        if data.get('success'):
                            full_answer = data.get('answer', '')
                            print(f"✅ Complete event received")
                            print(f"📄 Answer length: {len(full_answer)} characters")
                            print(f"\n📝 Answer:\n{full_answer}")
                            
                            # بررسی اینکه آیا اطلاعات مالکیت در پاسخ است
                            answer_lower = full_answer.lower()
                            ownership_keywords = ['مالکیت', 'سهام', 'متعلق', 'صندوق', 'باور', 'نوآور']
                            has_ownership_info = any(kw in answer_lower for kw in ownership_keywords)
                            
                            print(f"\n📊 Ownership info: {'✅' if has_ownership_info else '❌'}")
                        else:
                            print(f"❌ Rejected: {data.get('answer', 'Unknown error')}")
                            return False
                
                except json.JSONDecodeError:
                    pass
        
        print("-" * 80)
        if has_ownership_info:
            print("✅ TEST PASSED: Ownership information found in answer")
            return True
        else:
            print("⚠️ TEST FAILED: No ownership information in answer")
            return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_colloquial_question()
    sys.exit(0 if success else 1)

