#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست برای بررسی رفع مشکل streaming در karbaran_omomi
"""

import requests
import json
import sys

def test_karbaran_omomi_query():
    """تست query مشکل‌دار"""
    
    url = "http://localhost:8010/v2/query/streaming"
    
    payload = {
        "query": "من برای پروژه خود در صندوق نواور پیش پرداخت لازم دارم .ایا امکانش هست ؟",
        "collection_name": "karbaran_omomi",
        "top_k": 5,
        "use_reranking": True,
        "use_multi_hop": True,
        "temperature": 0.1
    }
    
    print("🧪 Testing karbaran_omomi query...")
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
        
        has_error = False
        has_complete = False
        chunks_received = 0
        
        for line in response.iter_lines():
            if not line:
                continue
            
            line_str = line.decode('utf-8')
            
            if line_str.startswith('data: '):
                data_str = line_str[6:]  # Remove 'data: ' prefix
                try:
                    data = json.loads(data_str)
                    
                    if data.get('type') == 'error':
                        print(f"❌ ERROR: {data.get('error', 'Unknown error')}")
                        has_error = True
                        break
                    
                    elif data.get('type') == 'complete':
                        has_complete = True
                        if data.get('success'):
                            print(f"✅ Complete: Success")
                            if data.get('answer'):
                                answer = data.get('answer', '')[:200]
                                print(f"📄 Answer preview: {answer}...")
                        else:
                            print(f"❌ Complete: Failed")
                            print(f"Error: {data.get('error', 'Unknown error')}")
                    
                    elif data.get('type') == 'token':
                        chunks_received += 1
                        if chunks_received <= 3:  # Show first 3 chunks
                            token = data.get('token', '')
                            print(f"📝 Token {chunks_received}: {token[:50]}...")
                
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON decode error: {e}")
                    print(f"Line: {line_str[:100]}")
        
        print("-" * 80)
        if has_error:
            print("❌ TEST FAILED: Error occurred")
            return False
        elif has_complete:
            print(f"✅ TEST PASSED: Received {chunks_received} chunks")
            return True
        else:
            print("⚠️ TEST INCOMPLETE: No complete event received")
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
    success = test_karbaran_omomi_query()
    sys.exit(0 if success else 1)

