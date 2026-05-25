#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست API با Query Preprocessor
"""

import requests
import json

API_BASE = "http://185.13.230.254:8010"

def test_query(query, collection_name="finance_combined_1762693261"):
    """تست یک query"""
    url = f"{API_BASE}/v2/query"
    payload = {
        "query": query,
        "collection_name": collection_name,
        "top_k": 10,
        "use_reranking": True,
        "use_multi_hop": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def main():
    print("=" * 70)
    print("🧪 تست API با Query Preprocessor")
    print("=" * 70)
    
    # تست 1: سلام
    print("\n1️⃣ تست سلام:")
    result = test_query("سلام")
    if result.get("success"):
        print(f"  ✅ پاسخ: {result.get('answer', '')[:100]}...")
    else:
        print(f"  ❌ خطا: {result.get('error', 'Unknown error')}")
    
    # تست 2: سوال نامرتبط
    print("\n2️⃣ تست سوال نامرتبط:")
    result = test_query("هوا چطوره؟")
    if result.get("success"):
        print(f"  ✅ پاسخ: {result.get('answer', '')[:100]}...")
    else:
        print(f"  ❌ خطا: {result.get('error', 'Unknown error')}")
    
    # تست 3: تبدیل "منابع" به "درآمد"
    print("\n3️⃣ تست تبدیل 'منابع' به 'درآمد':")
    result = test_query("انستیتو پاستور ایران در سال 1401 منابع اختصاصی چقدر داشته است؟")
    if result.get("success"):
        answer = result.get('answer', '')
        print(f"  ✅ پاسخ: {answer[:200]}...")
        # بررسی اینکه آیا "درآمد" در پاسخ است (نه "منابع")
        if 'درآمد' in answer or 'منابع' not in answer:
            print("  ✅ تبدیل 'منابع' به 'درآمد' انجام شد")
        else:
            print("  ⚠️ ممکن است تبدیل انجام نشده باشد")
    else:
        print(f"  ❌ خطا: {result.get('error', 'Unknown error')}")
    
    # تست 4: تبدیل "مصارف" به "هزینه"
    print("\n4️⃣ تست تبدیل 'مصارف' به 'هزینه':")
    result = test_query("انستیتو پاستور ایران در سال 1401 مصارف اختصاصی چقدر داشته است؟")
    if result.get("success"):
        answer = result.get('answer', '')
        print(f"  ✅ پاسخ: {answer[:200]}...")
        # بررسی اینکه آیا "هزینه" در پاسخ است (نه "مصارف")
        if 'هزینه' in answer or 'مصارف' not in answer:
            print("  ✅ تبدیل 'مصارف' به 'هزینه' انجام شد")
        else:
            print("  ⚠️ ممکن است تبدیل انجام نشده باشد")
    else:
        print(f"  ❌ خطا: {result.get('error', 'Unknown error')}")
    
    # تست 5: سوال عادی (برای مقایسه)
    print("\n5️⃣ تست سوال عادی (برای مقایسه):")
    result = test_query("انستیتو پاستور ایران در سال 1401 درآمد اختصاصی چقدر داشته است؟")
    if result.get("success"):
        answer = result.get('answer', '')
        print(f"  ✅ پاسخ: {answer[:200]}...")
        print(f"  📊 Confidence: {result.get('confidence', 0):.2f}")
    else:
        print(f"  ❌ خطا: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 70)
    print("✅ تست‌ها کامل شد!")
    print("=" * 70)

if __name__ == "__main__":
    main()

