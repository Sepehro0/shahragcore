#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست query بدون collection_name (حالت general)
"""

import requests
import json
import sys

API_URL = "http://localhost:8010"

def test_health():
    """تست health endpoint"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check successful")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_general_query(query_text):
    """تست query بدون collection_name"""
    print(f"\n🔍 Testing general query (without collection_name):")
    print(f"Query: {query_text}")
    print("-" * 60)
    
    try:
        payload = {
            "query": query_text,
            "top_k": 5
            # collection_name intentionally omitted
        }
        
        response = requests.post(
            f"{API_URL}/query",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Query successful!")
            print(f"\n📊 Response:")
            print(f"  - Answer: {result.get('answer', 'N/A')[:200]}...")
            print(f"  - Results count: {len(result.get('results', []))}")
            print(f"  - Confidence: {result.get('confidence', 'N/A')}")
            
            if result.get('results'):
                print(f"\n📄 Top results:")
                for i, res in enumerate(result['results'][:3], 1):
                    print(f"  {i}. Score: {res.get('score', 'N/A'):.3f}")
                    print(f"     Text: {res.get('text', '')[:100]}...")
            
            return True
        else:
            print(f"❌ Query failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ Query error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """تابع اصلی"""
    print("=" * 60)
    print("  🧪 تست حالت General (بدون collection_name)")
    print("=" * 60)
    
    # تست health
    if not test_health():
        print("\n❌ Server is not responding. Please check the server.")
        sys.exit(1)
    
    # تست‌های مختلف
    test_queries = [
        "تست سیستم",
        "سلام",
        "چی کار می‌کنی؟"
    ]
    
    success_count = 0
    for query in test_queries:
        if test_general_query(query):
            success_count += 1
        print("\n" + "=" * 60 + "\n")
    
    print(f"📊 Results: {success_count}/{len(test_queries)} tests passed")
    
    if success_count == len(test_queries):
        print("✅ All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
