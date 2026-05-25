# -*- coding: utf-8 -*-
"""
تست سوالات با collection جدید budget_complete_1398_1403
"""

import requests
import json
from datetime import datetime

API_URL = "http://185.13.230.254:8010"
COLLECTION_NAME = "budget_complete_1398_1403"

# سوالاتی که قبلاً مشکل داشتند + سوالات جدید
TEST_QUERIES = [
    # سوالات هزینه‌ای
    "تملک دارایی های سرمایه ای پارک فناوری پردیس در سال 1399",
    "اعتبارات هزینه ای ستاد مبارزه با مواد مخدر سال 98",
    "اعتبارات هزینه ای متفرقه بنیاد ایران شناسی در سال 98",
    "مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور سال 1402",
    "تملک دارایی های سرمایه ای متفرقه مرکز ملی فضای مجازی کشور سال های 98 تا 1402",
    "مصارف اختصاصی پژوهشکده آمار در سال 1403",
    # سوالات درآمدی
    "درآمد های گمرک جمهوری اسلامی ایران در سال 1398",
    "در امد های سازمان ملي استاندارد در سال ها 1399 تا 1402",
    # سوالات مقایسه‌ای
    "در سال 1403 وزارت ورزش و جوانان مصارف بیشتری داشته یا وزارت نیرو؟",
    "مصارف دانشگاه تهران در سال 1401 چقدر بیشتر از مصارف ان در سال 1399 بوده است؟",
]


def test_query(query: str, collection_name: str) -> dict:
    """تست یک query و برگرداندن نتیجه"""
    try:
        response = requests.post(
            f"{API_URL}/query",
            json={
                "query": query,
                "collection_name": collection_name,
                "use_streaming": False,
                "use_enhanced_prompts": True
            },
            timeout=120
        )
        
        if response.status_code == 200:
            return {
                "status": "success",
                "http_code": 200,
                "response": response.json()
            }
        else:
            return {
                "status": "error",
                "http_code": response.status_code,
                "error": response.text[:500]
            }
    except Exception as e:
        return {
            "status": "exception",
            "error": str(e)
        }


def generate_report():
    """اجرای تست‌ها و تولید گزارش"""
    print("=" * 80)
    print(f"🧪 تست سوالات با collection: {COLLECTION_NAME}")
    print(f"⏰ زمان شروع: {datetime.now().isoformat()}")
    print("=" * 80)
    
    results = []
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n📝 Query {i}/{len(TEST_QUERIES)}: {query[:60]}...")
        result = test_query(query, COLLECTION_NAME)
        result["query"] = query
        result["query_num"] = i
        results.append(result)
        
        if result["status"] == "success":
            data_source = result["response"].get("data_source", "unknown")
            answer = result["response"].get("answer", "")[:200]
            print(f"   ✅ Status: SUCCESS")
            print(f"   📊 Data Source: {data_source}")
            print(f"   📝 Answer: {answer}...")
        else:
            print(f"   ❌ Status: {result['status']}")
            print(f"   💥 Error: {result.get('error', 'Unknown')[:200]}")
    
    # خلاصه
    print("\n" + "=" * 80)
    print("📊 خلاصه نتایج")
    print("=" * 80)
    
    success_count = sum(1 for r in results if r["status"] == "success")
    db_routes = sum(1 for r in results if r["status"] == "success" and "database" in r["response"].get("data_source", "").lower())
    rag_routes = sum(1 for r in results if r["status"] == "success" and "rag" in r["response"].get("data_source", "").lower())
    
    print(f"✅ موفق: {success_count}/{len(results)}")
    print(f"💾 Database Routes: {db_routes}")
    print(f"📚 RAG Routes: {rag_routes}")
    print(f"❌ خطا: {len(results) - success_count}")
    
    # ذخیره گزارش
    report_file = f"/home/user01/qwen-api/enhanced_rag_system/NEW_COLLECTION_TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n📁 گزارش ذخیره شد: {report_file}")
    
    return results


if __name__ == "__main__":
    generate_report()


