#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test for qavanin collection
"""

import requests
import json

API_URL = "http://185.13.230.254:8010/v2/query/streaming"

def test_simple():
    """Simple test"""
    question = "تعریف «محیط کسب‌وکار» چیست؟"
    
    payload = {
        'query': question,
        'collection_name': 'qavanin',
        'top_k': 5
    }
    
    print(f"📤 Sending request...")
    print(f"Question: {question}")
    print(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.post(API_URL, json=payload, stream=True, timeout=60)
        print(f"\n📥 Response status: {response.status_code}")
        
        print(f"\n📊 Streaming chunks:")
        chunk_count = 0
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                print(f"\n[Chunk {chunk_count}] {line_str[:200]}...")
                
                if line_str.startswith('data:'):
                    try:
                        chunk = json.loads(line_str[5:].strip())
                        print(f"  Type: {chunk.get('type')}")
                        print(f"  Keys: {list(chunk.keys())}")
                        
                        if chunk.get('type') == 'answer':
                            content = chunk.get('content', '')
                            print(f"  Content: {content[:100]}...")
                        
                        if chunk.get('type') == 'complete' or chunk.get('done'):
                            print(f"  ✅ COMPLETE CHUNK RECEIVED")
                            print(f"  Full data: {json.dumps(chunk, ensure_ascii=False, indent=2)[:500]}...")
                            break
                    except json.JSONDecodeError as e:
                        print(f"  ❌ JSON decode error: {e}")
                
                chunk_count += 1
                
                if chunk_count > 50:
                    print("\n⚠️ Too many chunks, stopping...")
                    break
        
        print(f"\n✅ Test completed. Total chunks: {chunk_count}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple()
