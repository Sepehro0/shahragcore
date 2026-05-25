# -*- coding: utf-8 -*-
"""
تست 6 سوال جدید با collection budget_complete_1398_1403
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any

API_URL = "http://185.13.230.254:8010"
COLLECTION_NAME = "budget_complete_1398_1403"

# سوالات جدید
TEST_QUERIES = [
    "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403",
    "اعتبارات هزینه ای عمومی بنیاد ایران شناسی در سال 1403",
    "تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403",
    "درآمد عمومی ملی شرکت دولتی پست بانک در سال 1402 چقدر است؟",
    "بودجه فرهنگستان هنر در سال 1403",
    "درآمد استانی اختصاصی دانشگاه تبریز در سال 1403"
]


def test_query(query: str, collection_name: str, timeout: int = 120) -> Dict[str, Any]:
    """تست یک query و برگرداندن نتیجه کامل"""
    result = {
        "query": query,
        "status": None,
        "http_code": None,
        "response": None,
        "error": None,
        "data_source": None,
        "database_route": False,
        "rag_route": False,
        "answer_preview": None,
        "processing_time": None,
        "metadata": {}
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
            result["response"] = response.json()
            
            # استخراج اطلاعات مهم
            result["data_source"] = result["response"].get("data_source", "unknown")
            result["database_route"] = "database" in result["data_source"].lower() or "database" in result["response"].get("metadata", {}).get("retrieval_route", "")
            result["rag_route"] = "rag" in result["data_source"].lower() or result["response"].get("sources", [])
            
            answer = result["response"].get("answer", "")
            result["answer_preview"] = answer[:300] + "..." if len(answer) > 300 else answer
            
            result["processing_time"] = result["response"].get("processing_time")
            result["metadata"] = result["response"].get("metadata", {})
            
            # نمایش خلاصه
            print(f"✅ Status: SUCCESS")
            print(f"⏱️  Processing Time: {result['processing_time']:.2f}s" if result["processing_time"] else "⏱️  Processing Time: N/A")
            print(f"📊 Data Source: {result['data_source']}")
            route_type = "💾 DATABASE" if result["database_route"] else "📚 RAG" if result["rag_route"] else "❓ UNKNOWN"
            print(f"🔀 Route: {route_type}")
            
            if result["database_route"]:
                db_rows = result["metadata"].get("database_rows_count", 0)
                print(f"📋 Database Rows: {db_rows}")
            
            print(f"📝 Answer Preview:")
            print(f"   {result['answer_preview'][:200]}...")
            
        else:
            result["status"] = "error"
            result["error"] = response.text[:500]
            print(f"❌ Status: ERROR (HTTP {response.status_code})")
            print(f"💥 Error: {result['error']}")
            
    except requests.exceptions.Timeout:
        result["status"] = "timeout"
        result["error"] = f"Request timeout after {timeout}s"
        print(f"⏰ Status: TIMEOUT")
        print(f"💥 Error: Request timeout after {timeout} seconds")
        
    except Exception as e:
        result["status"] = "exception"
        result["error"] = str(e)
        print(f"💥 Status: EXCEPTION")
        print(f"💥 Error: {str(e)}")
    
    return result


def generate_detailed_report(results: list):
    """تولید گزارش تفصیلی"""
    print("\n" + "="*80)
    print("📊 گزارش تفصیلی نتایج")
    print("="*80)
    
    # خلاصه آماری
    success_count = sum(1 for r in results if r["status"] == "success")
    db_routes = sum(1 for r in results if r.get("database_route", False))
    rag_routes = sum(1 for r in results if r.get("rag_route", False))
    errors = [r for r in results if r["status"] != "success"]
    
    print(f"\n📈 خلاصه آماری:")
    print(f"   ✅ موفق: {success_count}/{len(results)} ({success_count*100/len(results):.1f}%)")
    print(f"   💾 Database Routes: {db_routes}")
    print(f"   📚 RAG Routes: {rag_routes}")
    print(f"   ❌ خطا: {len(errors)}")
    
    # جدول نتایج
    print(f"\n📋 جدول نتایج:")
    print(f"{'='*80}")
    print(f"{'#':<4} {'Status':<12} {'Route':<10} {'Time':<8} {'Preview':<40}")
    print(f"{'-'*80}")
    
    for i, result in enumerate(results, 1):
        status_icon = "✅" if result["status"] == "success" else "❌"
        route = "DB" if result.get("database_route") else "RAG" if result.get("rag_route") else "?"
        time_str = f"{result.get('processing_time', 0):.1f}s" if result.get("processing_time") else "N/A"
        preview = result.get("answer_preview", "")[:35] + "..." if result.get("answer_preview") else result.get("error", "N/A")[:35]
        print(f"{i:<4} {status_icon} {result['status']:<12} {route:<10} {time_str:<8} {preview:<40}")
    
    # تحلیل خطاها
    if errors:
        print(f"\n⚠️  تحلیل خطاها:")
        for error in errors:
            print(f"   ❌ Query: {error['query'][:60]}...")
            print(f"      Error: {error.get('error', 'Unknown')[:100]}")
    
    # ذخیره گزارش JSON
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"/home/user01/qwen-api/enhanced_rag_system/TEST_6_QUERIES_{timestamp}.json"
    
    report_data = {
        "collection": COLLECTION_NAME,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(results),
            "success": success_count,
            "database_routes": db_routes,
            "rag_routes": rag_routes,
            "errors": len(errors)
        },
        "results": results
    }
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 گزارش JSON ذخیره شد: {report_file}")
    
    # تولید گزارش Markdown
    md_file = f"/home/user01/qwen-api/enhanced_rag_system/TEST_6_QUERIES_{timestamp}.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(f"# گزارش تست 6 سوال جدید\n\n")
        f.write(f"**Collection:** `{COLLECTION_NAME}`\n\n")
        f.write(f"**تاریخ:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## 📈 خلاصه آماری\n\n")
        f.write(f"| معیار | مقدار |\n")
        f.write(f"|-------|-------|\n")
        f.write(f"| **موفقیت** | {success_count}/{len(results)} ({success_count*100/len(results):.1f}%) |\n")
        f.write(f"| **Database Routes** | {db_routes} |\n")
        f.write(f"| **RAG Routes** | {rag_routes} |\n")
        f.write(f"| **خطا** | {len(errors)} |\n\n")
        
        f.write(f"## 📋 نتایج تفصیلی\n\n")
        for i, result in enumerate(results, 1):
            status_icon = "✅" if result["status"] == "success" else "❌"
            route = "💾 Database" if result.get("database_route") else "📚 RAG" if result.get("rag_route") else "❓ Unknown"
            
            f.write(f"### {i}. {result['query']}\n\n")
            f.write(f"| فیلد | مقدار |\n")
            f.write(f"|------|-------|\n")
            f.write(f"| **وضعیت** | {status_icon} {result['status']} |\n")
            f.write(f"| **Route** | {route} |\n")
            if result.get("processing_time"):
                f.write(f"| **زمان پردازش** | {result['processing_time']:.2f}s |\n")
            if result.get("database_route"):
                db_rows = result.get("metadata", {}).get("database_rows_count", 0)
                f.write(f"| **تعداد ردیف‌های DB** | {db_rows} |\n")
            f.write(f"\n**پاسخ:**\n\n")
            f.write(f"```\n{result.get('answer_preview', result.get('error', 'N/A'))}\n```\n\n")
            f.write(f"---\n\n")
    
    print(f"📄 گزارش Markdown ذخیره شد: {md_file}")
    
    return report_file, md_file


def main():
    """تابع اصلی"""
    print("="*80)
    print(f"🧪 تست 6 سوال جدید با collection: {COLLECTION_NAME}")
    print(f"⏰ زمان شروع: {datetime.now().isoformat()}")
    print("="*80)
    
    results = []
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n\n🔄 تست سوال {i}/{len(TEST_QUERIES)}")
        result = test_query(query, COLLECTION_NAME)
        results.append(result)
    
    # تولید گزارش
    json_file, md_file = generate_detailed_report(results)
    
    print("\n" + "="*80)
    print("✅ تست کامل شد!")
    print("="*80)
    
    return results


if __name__ == "__main__":
    main()

