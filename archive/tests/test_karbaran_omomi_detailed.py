#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست دقیق برای بررسی rejection handling
"""

import requests
import json
import sys

def test_karbaran_omomi_detailed():
    """تست query مشکل‌دار با جزئیات بیشتر"""
    
    url = "http://localhost:8010/v2/query/streaming"
    
    payload = {
        "query": "من برای پروژه خود در صندوق نواور پیش پرداخت لازم دارم .ایا امکانش هست ؟",
        "collection_name": "karbaran_omomi",
        "top_k": 5,
        "use_reranking": True,
        "use_multi_hop": True,
        "temperature": 0.1
    }
    
    print("🧪 Testing karbaran_omomi query (detailed)...")
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
            print(f"Response: {response.text}")
            return False
        
        print("✅ Connection established")
        print("-" * 80)
        
        events_received = []
        
        for line in response.iter_lines():
            if not line:
                continue
            
            line_str = line.decode('utf-8')
            
            if line_str.startswith('event: '):
                event_type = line_str[7:]
                print(f"\n📨 Event: {event_type}")
                events_received.append(event_type)
            
            elif line_str.startswith('data: '):
                data_str = line_str[6:]
                try:
                    data = json.loads(data_str)
                    
                    print(f"📦 Data type: {data.get('type')}")
                    
                    if data.get('type') == 'error':
                        print(f"❌ ERROR: {data.get('error', 'Unknown error')}")
                        print(f"📄 Full error data: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    
                    elif data.get('type') == 'complete':
                        print(f"✅ Complete event received")
                        print(f"   Success: {data.get('success')}")
                        if data.get('answer'):
                            answer = data.get('answer', '')[:300]
                            print(f"   Answer preview: {answer}...")
                        if data.get('metadata'):
                            metadata = data.get('metadata', {})
                            print(f"   Rejected by: {metadata.get('rejected_by')}")
                            print(f"   Type: {metadata.get('type')}")
                            print(f"   Reason: {metadata.get('reason')}")
                        print(f"📄 Full complete data: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    
                    elif data.get('type') == 'start':
                        print(f"🚀 Start event")
                        print(f"   Query: {data.get('query', '')[:50]}...")
                    
                    elif data.get('type') == 'context':
                        print(f"📚 Context event")
                        print(f"   Sources count: {data.get('sources_count', 0)}")
                    
                    elif data.get('type') == 'token':
                        token = data.get('token', '')
                        if token:
                            print(f"📝 Token: {token[:50]}...")
                
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON decode error: {e}")
                    print(f"Line: {line_str[:200]}")
        
        print("-" * 80)
        print(f"📊 Events received: {', '.join(events_received)}")
        
        if 'error' in events_received:
            print("❌ TEST FAILED: Error event received")
            return False
        elif 'complete' in events_received:
            print("✅ TEST PASSED: Complete event received")
            return True
        else:
            print("⚠️ TEST INCOMPLETE: No complete/error event received")
            return False
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_karbaran_omomi_detailed()
    sys.exit(0 if success else 1)

