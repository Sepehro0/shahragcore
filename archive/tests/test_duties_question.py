#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست برای سوال درباره وظایف معاونت
"""

import requests
import json
import sys

def test_duties_question():
    """تست سوال درباره وظایف"""
    
    url = "http://localhost:8010/v2/query/streaming"
    
    payload = {
        "query": "وظایف های معاونت برنامه ریزی و توسعه فناوری رو بگو",
        "collection_name": "karbaran_omomi",
        "top_k": 5,
        "use_reranking": True,
        "use_multi_hop": True,
        "temperature": 0.1
    }
    
    print("🧪 Testing duties question...")
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
                            print(f"✅ Success: Answer received")
                            print(f"📄 Answer length: {len(full_answer)} characters")
                            print(f"\n📝 Answer preview:\n{full_answer[:500]}...")
                
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
    success = test_duties_question()
    sys.exit(0 if success else 1)


