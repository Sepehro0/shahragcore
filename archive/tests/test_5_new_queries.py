# -*- coding: utf-8 -*-
"""
تست جامع 5 سوال جدید با گزارش کامل
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any

API_URL = "http://185.13.230.254:8010"
COLLECTION = "budget_complete_1398_1403"

QUERIES = [
    "تملک دارایی اختصاصی کد دستگاه اجرایی 111400 در سال 1400",
    "جمع تملک دارایی سرمایه ای عمومی مجمع تشخیص مصلحت نظام از سال 1398 تا 1403",
    "درامد استانی اختصاصی دانشگاه تبریزدر سال 1403",
    "هزینه عمومی نهاد ریاست  جمهوری در سال 1403  بیشتر بوده یا شورای عالی امنیت ملی",
    "هزینه عمومی کدام یک از مجموعه های نهاد ریاست جمهوری در سال 1403 از بقیه بیشتر است؟"
]

def test_query(query: str, query_num: int, timeout: int = 120) -> Dict[str, Any]:
    """تست یک query و استخراج اطلاعات کامل"""
    print(f"\n{'='*80}")
    print(f"📝 Query {query_num}/5: {query}")
    print(f"{'='*80}")
    
    try:
        response = requests.post(
            f"{API_URL}/v2/query",
            json={
                "query": query,
                "collection_name": COLLECTION,
                "use_streaming": False
            },
            timeout=timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # استخراج اطلاعات
            success = data.get("success", False)
            answer = data.get("answer", "")
            full_answer = data.get("full_answer", data.get("full_text", ""))
            table_data = data.get("table_data")
            database_results = data.get("database_results")
            sources = data.get("sources", [])
            used_features = data.get("used_features", {})
            metadata = data.get("metadata", {})
            
            # تشخیص مسیر (Database یا RAG)
            route = "UNKNOWN"
            if database_results and (
                database_results.get("results") or 
                database_results.get("rows") or 
                database_results.get("detail_rows") or
                database_results.get("success", False)
            ):
                route = "DATABASE"
            elif sources and len(sources) > 0:
                route = "RAG"
            
            # استخراج اطلاعات Database
            db_info = {}
            if database_results:
                db_info = {
                    "has_results": bool(database_results.get("results")),
                    "row_count": len(database_results.get("rows", [])) if database_results.get("rows") else 0,
                    "detail_count": len(database_results.get("detail_rows", [])) if database_results.get("detail_rows") else 0,
                    "sql_query": database_results.get("sql_query", ""),
                    "success": database_results.get("success", False)
                }
            
            # استخراج اطلاعات RAG
            rag_info = {}
            if sources:
                rag_info = {
                    "source_count": len(sources),
                    "top_scores": [s.get("score", 0) for s in sources[:3]] if sources else [],
                    "top_sources": [s.get("source", "")[:100] for s in sources[:3]] if sources else []
                }
            
            result = {
                "query": query,
                "query_num": query_num,
                "status": "success" if success else "failed",
                "http_code": response.status_code,
                "route": route,
                "answer": answer,
                "full_answer": full_answer,
                "table_data": table_data,
                "database_info": db_info,
                "rag_info": rag_info,
                "used_features": used_features,
                "metadata": metadata,
                "full_response": data
            }
            
            # نمایش خلاصه
            print(f"✅ Status: {'SUCCESS' if success else 'FAILED'}")
            print(f"🔀 Route: {'💾 DATABASE' if route == 'DATABASE' else '📚 RAG' if route == 'RAG' else '❓ UNKNOWN'}")
            if route == "DATABASE":
                print(f"📋 Database Rows: {db_info.get('row_count', 0)}")
                if db_info.get("sql_query"):
                    print(f"🔍 SQL Query: {db_info['sql_query'][:150]}...")
            elif route == "RAG":
                print(f"📚 RAG Sources: {rag_info.get('source_count', 0)}")
            print(f"📝 Answer Preview: {answer[:200]}...")
            
            return result
            
        else:
            error_msg = response.text[:200]
            print(f"❌ HTTP Error {response.status_code}: {error_msg}")
            return {
                "query": query,
                "query_num": query_num,
                "status": "http_error",
                "http_code": response.status_code,
                "error": error_msg,
                "full_response": response.text
            }
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return {
            "query": query,
            "query_num": query_num,
            "status": "exception",
            "error": str(e)
        }


def generate_report(results: list):
    """تولید گزارش جامع"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"/home/user01/qwen-api/enhanced_rag_system/COMPREHENSIVE_TEST_REPORT_{timestamp}.md"
    json_file = f"/home/user01/qwen-api/enhanced_rag_system/COMPREHENSIVE_TEST_RESPONSES_{timestamp}.json"
    
    # ذخیره JSON کامل
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # تولید گزارش Markdown
    report = f"""# گزارش جامع تست 5 سوال جدید

**تاریخ تست:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Collection:** {COLLECTION}

---

## 📊 خلاصه نتایج

"""
    
    success_count = sum(1 for r in results if r.get("status") == "success")
    db_count = sum(1 for r in results if r.get("route") == "DATABASE")
    rag_count = sum(1 for r in results if r.get("route") == "RAG")
    
    report += f"""
- ✅ **موفق:** {success_count}/5 ({success_count*20}%)
- 💾 **Database Routes:** {db_count}/5
- 📚 **RAG Routes:** {rag_count}/5
- ⚠️ **خطا:** {5 - success_count}/5

---

## 📝 جزئیات هر سوال

"""
    
    for result in results:
        query_num = result.get("query_num", 0)
        query = result.get("query", "")
        status = result.get("status", "unknown")
        route = result.get("route", "UNKNOWN")
        answer = result.get("answer", "")
        full_answer = result.get("full_answer", "")
        
        report += f"""
### سوال {query_num}: {query}

**وضعیت:** {'✅ موفق' if status == 'success' else '❌ ناموفق'}
**مسیر پردازش:** {'💾 Database' if route == 'DATABASE' else '📚 RAG' if route == 'RAG' else '❓ Unknown'}

"""
        
        # اطلاعات Database
        if route == "DATABASE":
            db_info = result.get("database_info", {})
            report += f"""
#### 💾 اطلاعات Database:
- **تعداد ردیف‌ها:** {db_info.get('row_count', 0)}
- **SQL Query:** 
```sql
{db_info.get('sql_query', 'N/A')}
```

"""
        
        # اطلاعات RAG
        elif route == "RAG":
            rag_info = result.get("rag_info", {})
            report += f"""
#### 📚 اطلاعات RAG:
- **تعداد Sources:** {rag_info.get('source_count', 0)}
- **Top Scores:** {rag_info.get('top_scores', [])}

"""
        
        # پاسخ
        report += f"""
#### 📝 پاسخ:

{answer}

"""
        
        # پاسخ کامل
        if full_answer and full_answer != answer:
            report += f"""
#### 📄 پاسخ کامل:

{full_answer[:500]}...

"""
        
        # Table Data
        table_data = result.get("table_data")
        if table_data:
            report += f"""
#### 📊 داده‌های جدولی:

{table_data}

"""
        
        # Full Response (خلاصه)
        report += f"""
#### 🔍 اطلاعات تکمیلی:
- **Used Features:** {result.get('used_features', {})}
- **Metadata:** {result.get('metadata', {})}

---

"""
    
    # بخش تحلیل
    report += f"""
## 🔍 تحلیل مسیر پردازش

"""
    
    for result in results:
        query_num = result.get("query_num", 0)
        query = result.get("query", "")
        route = result.get("route", "UNKNOWN")
        
        report += f"""
### سوال {query_num}: {query[:50]}...

**مسیر:** {route}

"""
        
        if route == "DATABASE":
            db_info = result.get("database_info", {})
            report += f"""
- سیستم این سوال را به عنوان یک **سوال مالی ساختاریافته** تشخیص داد
- Query Analyzer موفق به استخراج entity و سال‌ها شد
- SQL Query تولید شد و به Database ارسال شد
- **{db_info.get('row_count', 0)} ردیف** از Database برگشت داده شد
- پاسخ بر اساس داده‌های Database تولید شد

"""
        elif route == "RAG":
            rag_info = result.get("rag_info", {})
            report += f"""
- سیستم این سوال را به عنوان یک **سوال مفهومی** تشخیص داد
- Query Analyzer نتوانست entity یا سال‌های مشخصی استخراج کند
- سیستم به RAG fallback کرد
- **{rag_info.get('source_count', 0)} source** از ChromaDB بازیابی شد
- پاسخ بر اساس RAG و LLM تولید شد

"""
        else:
            report += f"""
- مسیر پردازش نامشخص است
- احتمالاً خطایی در پردازش رخ داده است

"""
    
    report += f"""
---

## 📎 فایل‌های مرتبط

- **JSON کامل پاسخ‌ها:** `{json_file}`
- **این گزارش:** `{report_file}`

---

*گزارش تولید شده در {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n{'='*80}")
    print(f"📁 گزارش ذخیره شد:")
    print(f"   - Markdown: {report_file}")
    print(f"   - JSON: {json_file}")
    print(f"{'='*80}")
    
    return report_file, json_file


def main():
    print("="*80)
    print(f"🧪 تست جامع 5 سوال جدید")
    print(f"⏰ زمان شروع: {datetime.now().isoformat()}")
    print(f"📁 Collection: {COLLECTION}")
    print("="*80)
    
    results = []
    
    for i, query in enumerate(QUERIES, 1):
        result = test_query(query, i)
        results.append(result)
    
    # تولید گزارش
    report_file, json_file = generate_report(results)
    
    # خلاصه نهایی
    print(f"\n{'='*80}")
    print("📊 خلاصه نهایی")
    print(f"{'='*80}")
    
    success_count = sum(1 for r in results if r.get("status") == "success")
    db_count = sum(1 for r in results if r.get("route") == "DATABASE")
    rag_count = sum(1 for r in results if r.get("route") == "RAG")
    
    print(f"\n✅ موفق: {success_count}/5")
    print(f"💾 Database Routes: {db_count}/5")
    print(f"📚 RAG Routes: {rag_count}/5")
    print(f"\n📁 گزارش‌ها:")
    print(f"   - {report_file}")
    print(f"   - {json_file}")


if __name__ == "__main__":
    main()

