#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست برای سوالات کاملاً نامربوط
"""

import requests
import json
import sys

def test_irrelevant_question():
    """تست سوال کاملاً نامربوط"""
    
    url = "http://localhost:8010/v2/query/streaming"
    
    payload = {
        "query": "چطوری خونه بگیرم؟",
        "collection_name": "karbaran_omomi",
        "top_k": 5,
        "use_reranking": True,
        "use_multi_hop": True,
        "temperature": 0.1
    }
    
    print("🧪 Testing completely irrelevant question...")
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
        has_technical_details = False
        
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
                            print(f"✅ Complete event received (rejected)")
                            print(f"📄 Answer length: {len(full_answer)} characters")
                            print(f"\n📝 Answer:\n{full_answer}")
                            
                            # بررسی اینکه آیا جزئیات فنی در پاسخ است
                            answer_lower = full_answer.lower()
                            technical_keywords = ['gates_failed', 'keyword_coverage', 'quality_score', 'retrieval_quality', 'دلیل: gates']
                            has_technical_details = any(kw in answer_lower for kw in technical_keywords)
                            
                            # بررسی اینکه آیا پیام کاربرپسند است
                            user_friendly_keywords = ['خارج از حوزه', 'متأسفانه', 'لطفاً', 'مثال']
                            is_user_friendly = any(kw in full_answer for kw in user_friendly_keywords)
                            
                            print(f"\n📊 Analysis:")
                            print(f"   - Has technical details: {'❌' if has_technical_details else '✅'}")
                            print(f"   - Is user-friendly: {'✅' if is_user_friendly else '❌'}")
                            
                            if not has_technical_details and is_user_friendly:
                                print(f"\n✅ TEST PASSED: User-friendly rejection message")
                                return True
                            else:
                                print(f"\n⚠️ TEST FAILED: Message needs improvement")
                                return False
                
                except json.JSONDecodeError:
                    pass
        
        print("-" * 80)
        print("⚠️ TEST INCOMPLETE: No complete event received")
        return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_irrelevant_question()
    sys.exit(0 if success else 1)


