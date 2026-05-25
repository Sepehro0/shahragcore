#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:8010"

print("\n=== Testing V2 APIs (Production) ===\n")

# Test 1: V2 Query (non-streaming)
print("1. Testing /v2/query (non-streaming)...")
response = requests.post(
    f"{BASE_URL}/v2/query",
    json={"query": "تست سوال ساده", "collection_name": "budget_financial", "top_k": 3}
)
if response.status_code == 200:
    data = response.json()
    print(f"   ✅ PASS - Status: {response.status_code}, Has answer: {bool(data.get('answer'))}")
else:
    print(f"   ❌ FAIL - Status: {response.status_code}")

# Test 2: V2 Query (streaming)
print("\n2. Testing /v2/query/streaming...")
try:
    response = requests.post(
        f"{BASE_URL}/v2/query/streaming",
        json={"query": "تست سوال ساده", "collection_name": "budget_financial", "top_k": 3},
        stream=True,
        timeout=30
    )
    lines = 0
    for line in response.iter_lines():
        if line:
            lines += 1
            if lines >= 3:
                break
    print(f"   ✅ PASS - Status: {response.status_code}, Stream lines: {lines}")
except Exception as e:
    print(f"   ❌ FAIL - Error: {e}")

print("\n=== V2 API Tests Complete ===\n")
