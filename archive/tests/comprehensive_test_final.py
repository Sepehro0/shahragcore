#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست جامع سیستم بعد از اعمال تغییرات
"""

import requests
import json
import time
from typing import Dict, List, Tuple

API_URL = "http://localhost:8001/query"

# لیست query های مشکل‌دار قبلی
TEST_QUERIES = [
    # Query های که قبلاً مشکل داشتند
    {
        "query": "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403",
        "collection": "budget_financial",
        "expected_issues": ["اسناد موجود نیست", "با توجه به عدم ذکر سال"],
        "description": "تست 1: اعتبارات متفرقه - باید پاسخ مستقیم بدهد"
    },
    {
        "query": "بودجه فرهنگستان هنر در سال 1403",
        "collection": "budget_financial",
        "expected_issues": ["اسناد موجود نیست", "با توجه به عدم ذکر سال"],
        "description": "تست 2: بودجه فرهنگستان - باید پاسخ مستقیم بدهد"
    },
    {
        "query": "تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403",
        "collection": "budget_financial",
        "expected_issues": ["اسناد موجود نیست", "با توجه به عدم ذکر سال"],
        "description": "تست 3: تملک دارایی - باید پاسخ مستقیم بدهد"
    },
    {
        "query": "اعتبارات هزینه ای عمومی بنیاد ایران شناسی در سال 1403",
        "collection": "budget_financial",
        "expected_issues": ["اسناد موجود نیست", "با توجه به عدم ذکر سال"],
        "description": "تست 4: اعتبارات عمومی - باید پاسخ مستقیم بدهد"
    },
    {
        "query": "بودجه وزارت ورزش و جوانان در سال 1403 چقدر است؟",
        "collection": "budget_financial",
        "expected_issues": ["اسناد موجود نیست", "با توجه به عدم ذکر سال"],
        "description": "تست 5: بودجه وزارت ورزش - باید پاسخ مستقیم بدهد"
    },
    {
        "query": "تملک دارایی های سرمایه ای وزارت بهداشت در سال 1403 چقدر است؟",
        "collection": "budget_financial",
        "expected_issues": ["اسناد موجود نیست", "با توجه به عدم ذکر سال"],
        "description": "تست 6: تملک دارایی بهداشت - باید پاسخ مستقیم بدهد"
    },
    {
        "query": "درآمدهای وزارت نفت در سال 1401 چقدر است",
        "collection": "budget_financial",
        "expected_issues": ["اسناد موجود نیست"],
        "description": "تست 7: درآمد وزارت نفت - باید پاسخ مستقیم بدهد"
    },
    {
        "query": "درامد استانی اختصاصی دانشگاه تبریز در سال 1403",
        "collection": "budget_financial",
        "expected_issues": ["اسناد موجود نیست"],
        "description": "تست 8: درآمد استانی - باید پاسخ مستقیم بدهد"
    },
    # Query های که سال ذکر نشده (باید سال پیش‌فرض استفاده شود)
    {
        "query": "بودجه دانشگاه تهران",
        "collection": "budget_financial",
        "expected_issues": ["اسناد موجود نیست"],
        "description": "تست 9: بودجه بدون سال - باید سال پیش‌فرض استفاده شود"
    },
    # Query های که باید کوتاه و مستقیم پاسخ دهند
    {
        "query": "اعتبارات هزینه ای نهاد ریاست جمهوری در سال 1403",
        "collection": "budget_financial",
        "expected_issues": ["اسناد موجود نیست", "با توجه به عدم ذکر سال"],
        "description": "تست 10: اعتبارات نهاد - باید پاسخ کوتاه بدهد"
    },
]

def test_query(query_data: Dict) -> Tuple[bool, str, Dict]:
    """تست یک query"""
    try:
        payload = {
            "query": query_data["query"],
            "collection_name": query_data["collection"],
            "top_k": 5
        }
        
        response = requests.post(API_URL, json=payload, timeout=120)
        
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}", {}
        
        result = response.json()
        
        if not result.get("success"):
            return False, result.get("detail", result.get("error", "Unknown error")), result
        
        answer = result.get("answer", "")
        
        # بررسی مشکلات
        issues_found = []
        for issue in query_data.get("expected_issues", []):
            if issue in answer:
                issues_found.append(issue)
        
        # بررسی طول پاسخ (نباید خیلی طولانی باشد)
        is_too_long = len(answer) > 3000
        
        # بررسی اینکه آیا پاسخ خالی است
        is_empty = len(answer.strip()) < 50
        
        status = "✅"
        if issues_found:
            status = "❌"
        elif is_too_long:
            status = "⚠️"
        elif is_empty:
            status = "❌"
        
        return True, status, {
            "answer": answer[:500] + "..." if len(answer) > 500 else answer,
            "length": len(answer),
            "issues_found": issues_found,
            "is_too_long": is_too_long,
            "is_empty": is_empty
        }
        
    except Exception as e:
        return False, f"Exception: {str(e)}", {}

def run_comprehensive_test():
    """اجرای تست جامع"""
    print("=" * 80)
    print("🧪 تست جامع سیستم بعد از اعمال تغییرات")
    print("=" * 80)
    print()
    
    results = []
    
    for i, query_data in enumerate(TEST_QUERIES, 1):
        print(f"📋 {query_data['description']}")
        print(f"   Query: {query_data['query']}")
        
        success, status, details = test_query(query_data)
        
        if success:
            print(f"   {status} Status: {status}")
            print(f"   📊 Answer length: {details.get('length', 0)} chars")
            
            if details.get('issues_found'):
                print(f"   ❌ Issues found: {', '.join(details['issues_found'])}")
            
            if details.get('is_too_long'):
                print(f"   ⚠️ Answer is too long ({details['length']} chars)")
            
            if details.get('is_empty'):
                print(f"   ❌ Answer is empty or too short")
            
            print(f"   📄 Answer preview: {details.get('answer', '')[:200]}...")
        else:
            print(f"   ❌ Failed: {status}")
        
        results.append({
            "test_num": i,
            "description": query_data['description'],
            "query": query_data['query'],
            "success": success,
            "status": status,
            "details": details
        })
        
        print()
        time.sleep(1)  # کمی تاخیر بین تست‌ها
    
    # خلاصه نتایج
    print("=" * 80)
    print("📊 خلاصه نتایج")
    print("=" * 80)
    
    total = len(results)
    successful = sum(1 for r in results if r["success"] and r["status"] == "✅")
    with_issues = sum(1 for r in results if r["success"] and r["status"] == "❌")
    too_long = sum(1 for r in results if r["success"] and r["status"] == "⚠️")
    failed = sum(1 for r in results if not r["success"])
    
    print(f"✅ موفق: {successful}/{total}")
    print(f"❌ با مشکل: {with_issues}/{total}")
    print(f"⚠️ خیلی طولانی: {too_long}/{total}")
    print(f"💥 خطا: {failed}/{total}")
    print()
    
    # نمایش جزئیات مشکلات
    if with_issues > 0:
        print("=" * 80)
        print("❌ Query های با مشکل:")
        print("=" * 80)
        for r in results:
            if r["success"] and r["status"] == "❌":
                print(f"\nTest {r['test_num']}: {r['description']}")
                print(f"  Query: {r['query']}")
                if r['details'].get('issues_found'):
                    print(f"  Issues: {', '.join(r['details']['issues_found'])}")
    
    return results

if __name__ == "__main__":
    # بررسی اینکه سرور در دسترس است
    try:
        health = requests.get("http://localhost:8001/health", timeout=5)
        if health.status_code == 200:
            print("✅ Server is running")
            print()
            run_comprehensive_test()
        else:
            print("❌ Server is not healthy")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Please make sure the server is running on port 8001")

