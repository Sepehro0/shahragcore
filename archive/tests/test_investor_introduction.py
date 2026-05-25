#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست برای سوالات مربوط به معرفی به سرمایه گذار
"""

import requests
import json
import sys

def test_investor_introduction():
    """تست سوال درباره معرفی به سرمایه گذار"""
    
    url = "http://localhost:8010/v2/query/streaming"
    
    payload = {
        "query": "توی صندوق ها، چجوری به سرمایه گذار معرفی میشیم؟",
        "collection_name": "karbaran_omomi",
        "top_k": 5,
        "use_reranking": True,
        "use_multi_hop": True,
        "temperature": 0.1
    }
    
    print("🧪 Testing investor introduction question...")
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
                            print(f"❌ Rejected: {full_answer[:200]}...")
                            print(f"   Rejected by: {data.get('metadata', {}).get('rejected_by')}")
                            print(f"   Reason: {data.get('metadata', {}).get('reason')}")
                        else:
                            full_answer = data.get('answer', '')
                            print(f"✅ Success: Answer received ({len(full_answer)} chars)")
                            print(f"📝 Answer preview:\n{full_answer[:500]}...")
                            
                            # بررسی اینکه آیا درباره همه صندوق‌ها پاسخ داده شده
                            answer_lower = full_answer.lower()
                            has_bavar = 'باور' in answer_lower or 'bavar' in answer_lower
                            has_noavar = 'نوآور' in answer_lower or 'نواور' in answer_lower or 'noavar' in answer_lower
                            has_forsat = 'فرصت' in answer_lower or 'forsat' in answer_lower
                            
                            print(f"\n📊 Fund coverage:")
                            print(f"   - صندوق باور: {'✅' if has_bavar else '❌'}")
                            print(f"   - صندوق نوآور: {'✅' if has_noavar else '❌'}")
                            print(f"   - صندوق فرصت: {'✅' if has_forsat else '❌'}")
                
                except json.JSONDecodeError:
                    pass
        
        print("-" * 80)
        if was_rejected:
            print("❌ TEST FAILED: Question was rejected")
            return False
        else:
            print("✅ TEST PASSED: Question answered")
            return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_investor_introduction()
    sys.exit(0 if success else 1)

