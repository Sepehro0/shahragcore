#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تولید گزارش تست جامع
"""

import sys
sys.path.insert(0, '/home/user01/qwen-api/enhanced_rag_system_dev')

import requests
import json
from datetime import datetime
import time

base_url = "http://localhost:8001"

test_queries = [
    # 1a
    ("اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403", "1a"),
    ("اعتبارات هزینه ای عمومی بنیاد ایران شناسی در سال 1403", "1a"),
    ("اعتبارات هزینه ای اختصاصی هیات عالی گزینش در سال 1403", "1a"),
    ("تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403", "1a"),
    ("تملک دارایی سرمایه ای متفرقه سازمان سنجش بند ج در سال 1403", "1a"),
    # 2a
    ("بودجه فرهنگستان هنر در سال 1403", "2a"),
    ("اعتبارات هزینه ای نهاد ریاست جمهوری در سال 1403", "2a"),
    ("درآمدهای وزارت نفت در سال 1401 چقدر است", "2a"),
    ("بودجه دانشگاه تهران", "2a"),
    # 2b
    ("درامد استانی اختصاصی دانشگاه تبریز در سال 1403", "2b"),
    ("درامد ملی سازمان تامین اجتماعی در سال 1403", "2b"),
    ("درامد کل موسسه کار و تامین اجتماعی در سال 1402", "2b"),
]

results = []

print("Starting tests...")
for i, (query, category) in enumerate(test_queries, 1):
    print(f"\n[{i}/{len(test_queries)}] {category}: {query[:60]}...")
    try:
        response = requests.post(
            f"{base_url}/query",
            json={"query": query, "collection_name": "budget_financial"},
            timeout=120
        )
        if response.status_code == 200:
            result = response.json()
            results.append({
                "query": query,
                "category": category,
                "success": result.get('success'),
                "answer": result.get('answer', ''),
                "sql": result.get('sql', ''),
                "error": result.get('error', ''),
            })
            if result.get('success'):
                print("  ✅")
            else:
                print(f"  ❌ {result.get('error', '')[:50]}")
        else:
            results.append({
                "query": query,
                "category": category,
                "success": False,
                "error": f"HTTP {response.status_code}"
            })
            print(f"  ❌ HTTP {response.status_code}")
    except Exception as e:
        results.append({
            "query": query,
            "category": category,
            "success": False,
            "error": str(e)
        })
        print(f"  ❌ {str(e)[:50]}")
    time.sleep(1)

# Save report
report_file = f"/tmp/rag_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(report_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n✅ Report saved: {report_file}")
print(f"✅ Successful: {sum(1 for r in results if r.get('success'))}/{len(results)}")


