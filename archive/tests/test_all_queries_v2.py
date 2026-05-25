# -*- coding: utf-8 -*-
"""
تست جامع همه query ها - نسخه 2
شامل سوالات قبلی + سوالات جدید
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any, List

API_URL = "http://185.13.230.254:8010/v2/query"
COLLECTION = "finance_budget_new_1764252643"

# سوالات قبلی
OLD_QUERIES = [
    "مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور سال 1402",
    "درآمد های گمرک جمهوری اسلامی ایران در سال 1398",
    "در امد های سازمان ملي استاندارد در سال ها 1399 تا 1402",
    "درامد های حاصل از واگذاری دارایی های سرمایه ای در سال 1402",
    "درامدهای مالیاتی در سال 1402",
    "درامد حاصل از جرایم و خسارات در سال های 1398 تا 1400",
    "درامد های دانشگاه امیرکبیر در سال 1403 از چه جز هایی وصول شده است ؟",
    "راه های در امدی بنیاد ملی نخبگان در سال 1402 چه مواردی بودند ؟",
]

# سوالات جدید
NEW_QUERIES = [
    "تملک دارایی های سرمایه ای متفرقه مرکز ملی فضای مجازی کشور سال های 98 تا 1402",
    "مصارف اختصاصی پژوهشکده آمار در سال 1399",
    "درامد های استانی سازمان پزشكي قانوني كشور در سال های 1401 تا 1403",
    "در سال 1403 وزارت ورزش و جوانان مصارف بیشتری داشته یا وزارت نیرو ؟",
    "مصارف دانشگاه تهران در سال 1401 چقدر بیشتر از مصارف ان در سال 1399 بوده است؟",
]

def test_query(query: str, query_num: int, query_type: str) -> Dict[str, Any]:
    """تست یک query و برگرداندن نتایج"""
    print(f"\n{'='*80}")
    print(f"Query {query_num} ({query_type}): {query}")
    print('='*80)
    
    payload = {
        "query": query,
        "collection_name": COLLECTION,
        "stream": False
    }
    
    try:
        response = requests.post(
            API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            metadata = result.get("metadata", {})
            route = metadata.get("retrieval_route", "unknown")
            rows = metadata.get("database_rows_count", 0)
            answer = result.get("answer", "")
            
            print(f"✅ Success | Route: {route} | Rows: {rows}")
            print(f"\nAnswer:\n{answer[:600]}...")
            
            return {
                "query": query,
                "success": True,
                "route": route,
                "rows": rows,
                "answer": answer,
                "full_response": result
            }
        else:
            error_msg = response.text[:300]
            print(f"❌ Failed | Status: {response.status_code} | Error: {error_msg}")
            return {
                "query": query,
                "success": False,
                "error": error_msg,
                "status_code": response.status_code
            }
    except Exception as e:
        print(f"❌ Exception: {str(e)[:200]}")
        return {
            "query": query,
            "success": False,
            "error": str(e)
        }

def generate_report(results: List[Dict], timestamp: str):
    """تولید گزارش کامل"""
    report_path = f"/home/user01/qwen-api/enhanced_rag_system/COMPREHENSIVE_TEST_REPORT_{timestamp}.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# گزارش جامع تست Query ها\n\n")
        f.write(f"**تاریخ:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Collection:** {COLLECTION}\n\n")
        
        # آمار کلی
        total = len(results)
        success = sum(1 for r in results if r.get('success'))
        db_route = sum(1 for r in results if r.get('route') == 'database_override')
        rag_route = sum(1 for r in results if r.get('route') == 'rag')
        
        f.write("## 📊 آمار کلی\n\n")
        f.write(f"- **تعداد کل query ها:** {total}\n")
        f.write(f"- **موفق:** {success} ({100*success/total:.1f}%)\n")
        f.write(f"- **Database Route:** {db_route} ({100*db_route/total:.1f}%)\n")
        f.write(f"- **RAG Route:** {rag_route} ({100*rag_route/total:.1f}%)\n\n")
        
        f.write("---\n\n")
        
        # جزئیات هر query
        f.write("## 📋 جزئیات Query ها\n\n")
        
        for i, result in enumerate(results, 1):
            query = result.get('query', '')
            success_flag = "✅" if result.get('success') else "❌"
            route = result.get('route', 'N/A')
            rows = result.get('rows', 0)
            answer = result.get('answer', result.get('error', 'N/A'))
            
            f.write(f"### Query {i}: {query[:50]}...\n\n")
            f.write(f"**وضعیت:** {success_flag}\n")
            f.write(f"**Route:** `{route}`\n")
            f.write(f"**Database Rows:** {rows}\n\n")
            
            f.write("**پاسخ کامل:**\n")
            f.write(f"```\n{answer}\n```\n\n")
            
            # اگر full_response داریم، metadata را هم اضافه کن
            if result.get('full_response'):
                metadata = result['full_response'].get('metadata', {})
                f.write("**Metadata:**\n")
                f.write(f"```json\n{json.dumps(metadata, ensure_ascii=False, indent=2)[:1000]}\n```\n\n")
            
            f.write("---\n\n")
        
        f.write("\n## نتیجه‌گیری\n\n")
        if db_route >= total * 0.7:
            f.write("✅ سیستم عملکرد عالی دارد - بیش از 70% query ها به database می‌روند.\n")
        elif db_route >= total * 0.5:
            f.write("⚠️ سیستم عملکرد خوبی دارد - بیش از 50% query ها به database می‌روند.\n")
        else:
            f.write("❌ سیستم نیاز به بهبود دارد - کمتر از 50% query ها به database می‌روند.\n")
    
    print(f"\n\n{'='*80}")
    print(f"✅ Report saved to: {report_path}")
    print('='*80)
    return report_path

def main():
    print("Starting comprehensive query testing...")
    print(f"Testing {len(OLD_QUERIES) + len(NEW_QUERIES)} queries against collection: {COLLECTION}\n")
    
    results = []
    
    # تست سوالات قبلی
    print("\n" + "="*80)
    print("سوالات قبلی")
    print("="*80)
    for i, query in enumerate(OLD_QUERIES, 1):
        result = test_query(query, i, "OLD")
        results.append(result)
    
    # تست سوالات جدید
    print("\n" + "="*80)
    print("سوالات جدید")
    print("="*80)
    for i, query in enumerate(NEW_QUERIES, 1):
        result = test_query(query, i + len(OLD_QUERIES), "NEW")
        results.append(result)
    
    # تولید گزارش
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    generate_report(results, timestamp)
    
    # خلاصه
    total = len(results)
    success = sum(1 for r in results if r.get('success'))
    db_route = sum(1 for r in results if r.get('route') == 'database_override')
    
    print(f"\n\nSummary: {success}/{total} queries succeeded, {db_route}/{total} went to database")

if __name__ == "__main__":
    main()

