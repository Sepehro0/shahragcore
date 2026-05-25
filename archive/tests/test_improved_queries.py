# -*- coding: utf-8 -*-
"""
تست سوالات بهبود یافته - بررسی مشکلات entity matching و column detection
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any

API_URL = "http://185.13.230.254:8010"
COLLECTION_NAME = "budget_complete_1398_1403"

# سوالاتی که قبلاً مشکل داشتند
TEST_QUERIES = [
    # سوالات مشکل‌دار قبلی
    "اعتبارات هزینه ای عمومی بنیاد ایران شناسی در سال 1403",
    "تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403",
    "بودجه فرهنگستان هنر در سال 1403",
    # سوالات جدید برای تست
    "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403",
    "درآمد عمومی ملی شرکت دولتی پست بانک در سال 1402 چقدر است؟",
    "درآمد استانی اختصاصی دانشگاه تبریز در سال 1403",
]


def test_query(query: str, collection_name: str, timeout: int = 120) -> Dict[str, Any]:
    """تست یک query و برگرداندن نتیجه کامل"""
    result = {
        "query": query,
        "status": None,
        "http_code": None,
        "data_source": None,
        "database_route": False,
        "answer_preview": None,
        "processing_time": None,
        "error": None
    }
    
    try:
        print(f"\n{'='*80}")
        print(f"📝 Query: {query}")
        print(f"{'='*80}")
        
        response = requests.post(
            f"{API_URL}/query",
            json={
                "query": query,
                "collection_name": collection_name,
                "use_streaming": False,
                "use_enhanced_prompts": True
            },
            timeout=timeout
        )
        
        result["http_code"] = response.status_code
        
        if response.status_code == 200:
            result["status"] = "success"
            resp_json = response.json()
            
            result["data_source"] = resp_json.get("data_source", "unknown")
            metadata = resp_json.get("metadata", {})
            retrieval_route = metadata.get("retrieval_route", "")
            result["database_route"] = "database" in retrieval_route.lower() or "database" in result["data_source"].lower()
            
            answer = resp_json.get("answer", "")
            result["answer_preview"] = answer[:400] + "..." if len(answer) > 400 else answer
            result["processing_time"] = resp_json.get("processing_time")
            
            # نمایش خلاصه
            print(f"✅ Status: SUCCESS")
            print(f"⏱️  Processing Time: {result['processing_time']:.2f}s" if result["processing_time"] else "⏱️  Processing Time: N/A")
            route_type = "💾 DATABASE" if result["database_route"] else "📚 RAG"
            print(f"🔀 Route: {route_type}")
            
            if result["database_route"]:
                db_rows = metadata.get("database_rows_count", 0)
                print(f"📋 Database Rows: {db_rows}")
            
            print(f"📝 Answer Preview:")
            print(f"   {result['answer_preview'][:300]}...")
            
        else:
            result["status"] = "error"
            result["error"] = response.text[:500]
            print(f"❌ Status: ERROR (HTTP {response.status_code})")
            print(f"💥 Error: {result['error']}")
            
    except requests.exceptions.Timeout:
        result["status"] = "timeout"
        result["error"] = f"Request timeout after {timeout}s"
        print(f"⏰ Status: TIMEOUT")
        
    except Exception as e:
        result["status"] = "exception"
        result["error"] = str(e)
        print(f"💥 Status: EXCEPTION")
        print(f"💥 Error: {str(e)}")
    
    return result


def main():
    """تابع اصلی"""
    print("="*80)
    print(f"🧪 تست سوالات بهبود یافته با collection: {COLLECTION_NAME}")
    print(f"⏰ زمان شروع: {datetime.now().isoformat()}")
    print("="*80)
    
    results = []
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n\n🔄 تست سوال {i}/{len(TEST_QUERIES)}")
        result = test_query(query, COLLECTION_NAME)
        results.append(result)
    
    # خلاصه نتایج
    print("\n\n" + "="*80)
    print("📊 خلاصه نتایج")
    print("="*80)
    
    success_count = sum(1 for r in results if r["status"] == "success")
    db_routes = sum(1 for r in results if r.get("database_route", False))
    
    print(f"\n📈 نتایج کلی:")
    print(f"   ✅ موفق: {success_count}/{len(results)} ({success_count*100/len(results):.1f}%)")
    print(f"   💾 Database Routes: {db_routes}")
    print(f"   📚 RAG Routes: {sum(1 for r in results if r['status'] == 'success' and not r['database_route'])}")
    
    # ذخیره گزارش
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"/home/user01/qwen-api/enhanced_rag_system/IMPROVED_QUERIES_TEST_{timestamp}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n📁 گزارش ذخیره شد: {report_file}")
    
    return results


if __name__ == "__main__":
    main()

