#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug API query for 110103"""

import requests
import json

# تست query
query = "کد 110103 راجع به چیه؟"
collection_name = "jadval5-bodje"

print(f"Query: {query}")
print("="*80)

response = requests.post(
    "http://localhost:8000/query",
    json={"query": query, "collection_name": collection_name}
)

if response.status_code == 200:
    result = response.json()
    answer = result.get("answer", "")
    
    print(f"\nAnswer:\n{answer}")
    
    # بررسی صحت پاسخ
    if "مالیات عملکرد شرکتهای دولتی" in answer:
        print("\n✅ PASS: Correct title found")
    elif "110100" in answer and "مالیات اشخاص حقوقی" in answer and "اطلاعات دقیق" not in answer and "نیست" not in answer:
        print("\n❌ FAIL: Model returned wrong document (110100 instead of 110103)")
    else:
        print("\n❌ FAIL: Answer is incorrect")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)

