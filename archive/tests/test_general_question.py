#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست برای سوالات کلی درباره سرمایه‌گذاری
"""

import requests
import json
import sys

def test_general_question():
    """تست سوال کلی"""
    
    url = "http://localhost:8010/v2/query/streaming"
    
    payload = {
        "query": "سرمایه گذاری روی پروژه ها چجوری اتفاق میفته؟",
        "collection_name": "karbaran_omomi",
        "top_k": 5,
        "use_reranking": True,
        "use_multi_hop": True,
        "temperature": 0.1
    }
    
    print("🧪 Testing general question about investment...")
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
        has_bavar = False
        has_noavar = False
        has_forsat = False
        
        for line in response.iter_lines():
            if not line:
                continue
            
            line_str = line.decode('utf-8')
            
            if line_str.startswith('data: '):
                data_str = line_str[6:]
                try:
                    data = json.loads(data_str)
                    
                    if data.get('type') == 'complete' and data.get('success'):
                        full_answer = data.get('answer', '')
                        print(f"✅ Complete event received")
                        print(f"📄 Answer length: {len(full_answer)} characters")
                        print(f"\n📝 Answer preview (first 500 chars):\n{full_answer[:500]}...")
                        
                        # بررسی اینکه آیا همه صندوق‌ها در پاسخ هستند
                        answer_lower = full_answer.lower()
                        has_bavar = 'باور' in answer_lower or 'bavar' in answer_lower
                        has_noavar = 'نوآور' in answer_lower or 'نواور' in answer_lower or 'noavar' in answer_lower
                        has_forsat = 'فرصت' in answer_lower or 'forsat' in answer_lower or 'تبادل فناوری' in answer_lower
                        
                        print(f"\n📊 Fund coverage:")
                        print(f"   - صندوق باور: {'✅' if has_bavar else '❌'}")
                        print(f"   - صندوق نوآور: {'✅' if has_noavar else '❌'}")
                        print(f"   - صندوق فرصت: {'✅' if has_forsat else '❌'}")
                
                except json.JSONDecodeError:
                    pass
        
        print("-" * 80)
        if has_bavar and has_noavar and has_forsat:
            print("✅ TEST PASSED: All three funds mentioned in answer")
            return True
        else:
            print("⚠️ TEST PARTIAL: Not all funds mentioned")
            print(f"   Missing: ", end="")
            missing = []
            if not has_bavar: missing.append("باور")
            if not has_noavar: missing.append("نوآور")
            if not has_forsat: missing.append("فرصت")
            print(", ".join(missing))
            return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_general_question()
    sys.exit(0 if success else 1)

