#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست جامع سیستم RAG برای بودجه و مالی
"""

import sys
sys.path.insert(0, '/home/user01/qwen-api/enhanced_rag_system_dev')

import requests
import json
from datetime import datetime
import time

base_url = "http://localhost:8001"

# Test queries
test_queries = [
    # 1. ارجاع یک سلول خاص
    {
        "category": "1a. ارجاع یک سلول خاص - مصارف",
        "queries": [
            "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403",
            "اعتبارات هزینه ای عمومی بنیاد ایران شناسی در سال 1403",
            "اعتبارات هزینه ای اختصاصی هیات عالی گزینش در سال 1403",
            "تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403",
            "تملک دارایی سرمایه ای متفرقه سازمان سنجش بند ج در سال 1403",
        ]
    },
    # 2. جمع دو یا چند سلول
    {
        "category": "2a. جمع",
        "queries": [
            "بودجه فرهنگستان هنر در سال 1403",
            "اعتبارات هزینه ای نهاد ریاست جمهوری در سال 1403",
            "درآمدهای وزارت نفت در سال 1401 چقدر است",
            "بودجه دانشگاه تهران",
        ]
    },
    # 3. درآمدها
    {
        "category": "2b. درآمدها",
        "queries": [
            "درامد استانی اختصاصی دانشگاه تبریز در سال 1403",
            "درامد ملی سازمان تامین اجتماعی در سال 1403",
            "درامد کل موسسه کار و تامین اجتماعی در سال 1402",
        ]
    }
]

def test_query(query, category):
    """تست یک query"""
    print(f"\n{'='*100}")
    print(f"Query: {query}")
    print(f"Category: {category}")
    print(f"{'='*100}")
    
    try:
        response = requests.post(
            f"{base_url}/query",
            json={"query": query, "collection_name": "budget_financial"},
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                answer = result.get('answer', '')
                sql = result.get('sql', '')
                rows = result.get('rows', [])
                
                print(f"✅ SUCCESS")
                print(f"\n📝 Answer:\n{answer}")
                print(f"\n🔍 SQL:\n{sql[:500] if sql else 'N/A'}")
                print(f"\n📊 Rows: {len(rows)}")
                
                # Check for issues
                issues = []
                if "اسناد موجود نیست" in answer or "اسنادی موجود نیست" in answer:
                    issues.append("⚠️ Mentions 'اسناد موجود نیست'")
                if "با توجه به عدم ذکر سال" in answer and "1403" in query:
                    issues.append("⚠️ Mentions 'عدم ذکر سال' when year is mentioned")
                if not rows or (rows and not any(row.get('total') or row.get('جمع_كل') for row in rows)):
                    if "بودجه" in query.lower() or "جمع" in query.lower():
                        issues.append("⚠️ No data returned for aggregation query")
                
                if issues:
                    print(f"\n⚠️ Issues: {', '.join(issues)}")
                
                return {
                    "query": query,
                    "category": category,
                    "success": True,
                    "answer": answer,
                    "sql": sql,
                    "rows_count": len(rows),
                    "issues": issues
                }
            else:
                error = result.get('error', '')
                print(f"❌ FAILED: {error[:300]}")
                return {
                    "query": query,
                    "category": category,
                    "success": False,
                    "error": error
                }
        else:
            print(f"❌ HTTP {response.status_code}: {response.text[:200]}")
            return {
                "query": query,
                "category": category,
                "success": False,
                "error": f"HTTP {response.status_code}"
            }
    except requests.exceptions.ConnectionError:
        print("❌ Server not running")
        return None
    except Exception as e:
        print(f"❌ Exception: {str(e)[:200]}")
        return {
            "query": query,
            "category": category,
            "success": False,
            "error": str(e)
        }

def main():
    print("=" * 100)
    print("🧪 تست کامل سیستم RAG - بودجه و مالی")
    print(f"تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)
    
    all_results = []
    
    for category_data in test_queries:
        category = category_data["category"]
        queries = category_data["queries"]
        
        print(f"\n\n{'#'*100}")
        print(f"# {category}")
        print(f"{'#'*100}\n")
        
        for query in queries:
            result = test_query(query, category)
            if result:
                all_results.append(result)
            time.sleep(2)  # Wait between requests
    
    # Summary
    print("\n\n" + "=" * 100)
    print("📊 خلاصه نتایج")
    print("=" * 100)
    
    total = len(all_results)
    successful = sum(1 for r in all_results if r.get('success'))
    failed = total - successful
    
    print(f"\n✅ موفق: {successful}/{total}")
    print(f"❌ ناموفق: {failed}/{total}")
    
    # Issues summary
    all_issues = []
    for r in all_results:
        if r.get('success') and r.get('issues'):
            all_issues.extend(r.get('issues', []))
    
    if all_issues:
        print(f"\n⚠️ Issues found:")
        for issue in set(all_issues):
            count = sum(1 for r in all_results if r.get('success') and issue in r.get('issues', []))
            print(f"  - {issue}: {count} times")
    
    # Save detailed report
    report_file = f"/tmp/rag_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 گزارش کامل ذخیره شد: {report_file}")
    print("=" * 100)

if __name__ == "__main__":
    main()


