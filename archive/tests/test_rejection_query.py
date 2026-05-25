#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست برای بررسی rejection query
"""

import requests
import json
import sys

def test_rejection_query():
    """تست query که reject می‌شود"""
    
    url = "http://localhost:8010/v2/query/streaming"
    
    payload = {
        "query": "من یک شرکت هستم و می خواهم طرحم رو تجاری سازی کنم .در کدام صندوق موسسه دانشمند میتونم ورود کنم",
        "collection_name": "karbaran_omomi",
        "top_k": 5,
        "use_reranking": True,
        "use_multi_hop": True,
        "temperature": 0.1
    }
    
    print("🧪 Testing rejection query...")
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
                    
                    elif data.get('type') == 'complete':
                        print(f"✅ Complete event received")
                        print(f"   Success: {data.get('success')}")
                        if data.get('answer'):
                            answer = data.get('answer', '')[:500]
                            print(f"   Answer: {answer}")
                        if data.get('metadata'):
                            metadata = data.get('metadata', {})
                            print(f"   Rejected by: {metadata.get('rejected_by')}")
                            print(f"   Type: {metadata.get('type')}")
                            print(f"   Reason: {metadata.get('reason')}")
                            if metadata.get('intent_type'):
                                print(f"   Intent type: {metadata.get('intent_type')}")
                            if metadata.get('gate_confidence'):
                                print(f"   Gate confidence: {metadata.get('gate_confidence')}")
                        print(f"📄 Full metadata: {json.dumps(data.get('metadata', {}), indent=2, ensure_ascii=False)}")
                    
                    elif data.get('type') == 'start':
                        print(f"🚀 Start event")
                
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON decode error: {e}")
        
        print("-" * 80)
        print(f"📊 Events received: {', '.join(events_received)}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_rejection_query()

