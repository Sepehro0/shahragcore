#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست 6 سوال جدید و گزارش کامل پاسخ‌های API Server
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List

API_URL = "http://185.13.230.254:8010/v2/query"
COLLECTION = "finance_budget_new_1764252643"

QUERIES = [
    "تملک دارایی های سرمایه ای پارک فناوری پردیس در سال 1399",
    "اعتبارات هزینه ای ستاد مبارزه با مواد مخدر سال 98",
    "اعتبارات هزینه ای متفرقه بنیاد ایران شناسی در سال 98",
    "مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور سال 1402",
    "تملک دارایی های سرمایه ای متفرقه مرکز ملی فضای مجازی کشور سال های 98 تا 1402",
    "مصارف اختصاصی پژوهشکده آمار در سال 1403",
]

def test_query(query: str, query_num: int) -> Dict[str, Any]:
    """تست یک query و برگرداندن نتیجه کامل"""
    print(f"\n{'='*80}")
    print(f"📝 سوال {query_num}: {query}")
    print('='*80)
    
    payload = {
        "query": query,
        "collection_name": COLLECTION,
        "stream": False
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(
            API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        
        elapsed_time = time.time() - start_time
        
        result = {
            "query_num": query_num,
            "query": query,
            "status_code": response.status_code,
            "response_time": elapsed_time,
            "success": False,
            "error": None,
            "data": None
        }
        
        if response.status_code == 200:
            try:
                data = response.json()
                result["success"] = True
                result["data"] = data
                
                # استخراج اطلاعات کلیدی
                metadata = data.get("metadata", {})
                answer = data.get("answer", "")
                database_results = data.get("database_results")
                
                print(f"\n✅ Status Code: {response.status_code}")
                print(f"⏱️  Response Time: {elapsed_time:.2f}s")
                print(f"\n📋 Metadata:")
                print(f"  - Route: {metadata.get('retrieval_route', 'N/A')}")
                print(f"  - Database Rows: {metadata.get('database_rows_count', 0)}")
                print(f"  - Processing Time: {metadata.get('processing_time_seconds', 0):.2f}s")
                print(f"  - Retrieval Method: {metadata.get('retrieval_method', 'N/A')}")
                
                if database_results:
                    print(f"\n🗄️  Database Results:")
                    print(f"  - Success: {database_results.get('success', False)}")
                    print(f"  - Count: {database_results.get('count', 0)}")
                    print(f"  - Columns: {database_results.get('columns', [])}")
                    if database_results.get('results'):
                        print(f"  - Sample Row: {database_results['results'][0] if database_results['results'] else 'None'}")
                
                print(f"\n📝 پاسخ کامل:")
                print("-"*60)
                print(answer)
                print("-"*60)
                
            except json.JSONDecodeError as e:
                result["error"] = f"JSON decode error: {str(e)}"
                result["data"] = {"raw_response": response.text[:1000]}
                print(f"\n❌ JSON Decode Error: {str(e)}")
                print(f"Raw response: {response.text[:500]}")
        else:
            result["error"] = f"HTTP {response.status_code}"
            result["data"] = {"error_response": response.text[:1000]}
            print(f"\n❌ Error Status Code: {response.status_code}")
            print(f"Error Response: {response.text[:500]}")
        
        return result
        
    except requests.exceptions.Timeout:
        result["error"] = "Request timeout"
        print(f"\n❌ Request Timeout (>120s)")
        return result
    except Exception as e:
        result["error"] = str(e)
        print(f"\n❌ Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return result

def generate_report(results: List[Dict[str, Any]]) -> str:
    """تولید گزارش کامل"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""# گزارش تست 6 سوال جدید

**تاریخ:** {timestamp}  
**Collection:** {COLLECTION}  
**API URL:** {API_URL}

---

## 📊 خلاصه نتایج

| # | سوال | Route | موفقیت | زمان پاسخ | Rows |
|---|------|-------|--------|-----------|------|
"""
    
    success_count = 0
    db_count = 0
    
    for r in results:
        route = r.get("data", {}).get("metadata", {}).get("retrieval_route", "N/A") if r.get("success") else "ERROR"
        success = "✅" if r.get("success") else "❌"
        rows = r.get("data", {}).get("metadata", {}).get("database_rows_count", 0) if r.get("success") else 0
        
        if r.get("success"):
            success_count += 1
        if route in ["database", "database_override", "hybrid"]:
            db_count += 1
        
        query_short = r["query"][:50] + "..." if len(r["query"]) > 50 else r["query"]
        report += f"| {r['query_num']} | {query_short} | `{route}` | {success} | {r['response_time']:.2f}s | {rows} |\n"
    
    report += f"\n**موفق:** {success_count}/{len(results)} | **Database Routes:** {db_count}/{len(results)}\n\n"
    
    report += "---\n\n"
    
    # جزئیات هر سوال
    for r in results:
        report += f"""## سوال {r['query_num']}: {r['query']}

### وضعیت: {"✅ موفق" if r.get("success") else "❌ ناموفق"}

"""
        
        if r.get("success"):
            data = r["data"]
            metadata = data.get("metadata", {})
            answer = data.get("answer", "")
            database_results = data.get("database_results")
            
            report += f"""### پاسخ API:

```
{answer}
```

### Metadata:

```json
{json.dumps(metadata, ensure_ascii=False, indent=2)}
```

"""
            
            if database_results:
                report += f"""### Database Results:

```json
{json.dumps({
    "success": database_results.get("success"),
    "count": database_results.get("count"),
    "columns": database_results.get("columns", []),
    "rows_sample": database_results.get("results", [])[:2] if database_results.get("results") else []
}, ensure_ascii=False, indent=2)}
```

"""
            
            if database_results and database_results.get("sql"):
                report += f"""### SQL Query:

```sql
{database_results.get("sql", "")[:1000]}
```

"""
        else:
            report += f"""### خطا:

```
{r.get('error', 'Unknown error')}
```

"""
        
        report += f"""### زمان پاسخ: {r['response_time']:.2f} ثانیه

---

"""
    
    report += f"""
## 📈 آمار کلی

- **تعداد سوالات:** {len(results)}
- **موفق:** {success_count} ({success_count*100/len(results):.1f}%)
- **ناموفق:** {len(results)-success_count} ({(len(results)-success_count)*100/len(results):.1f}%)
- **مسیر Database:** {db_count} ({db_count*100/len(results):.1f}%)
- **میانگین زمان پاسخ:** {sum(r['response_time'] for r in results)/len(results):.2f} ثانیه

---

**گزارش تهیه شده توسط:** AI Assistant  
**تاریخ:** {timestamp}
"""
    
    return report

def main():
    """تابع اصلی"""
    print("="*80)
    print("🧪 شروع تست 6 سوال جدید")
    print("="*80)
    
    results = []
    
    for i, query in enumerate(QUERIES, 1):
        result = test_query(query, i)
        results.append(result)
        time.sleep(2)  # استراحت کوتاه بین درخواست‌ها
    
    # تولید گزارش
    print("\n" + "="*80)
    print("📊 تولید گزارش...")
    print("="*80)
    
    report = generate_report(results)
    
    # ذخیره گزارش
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"NEW_QUERIES_TEST_REPORT_{timestamp}.md"
    report_path = f"/home/user01/qwen-api/enhanced_rag_system/{report_filename}"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ گزارش ذخیره شد: {report_filename}")
    print("\n" + "="*80)
    print("📋 خلاصه نتایج:")
    print("="*80)
    
    success_count = sum(1 for r in results if r.get("success"))
    print(f"✅ موفق: {success_count}/{len(results)}")
    print(f"❌ ناموفق: {len(results)-success_count}/{len(results)}")
    
    db_routes = sum(1 for r in results 
                    if r.get("success") and 
                    r.get("data", {}).get("metadata", {}).get("retrieval_route") in 
                    ["database", "database_override", "hybrid"])
    print(f"🗄️  Database Routes: {db_routes}/{len(results)}")
    
    avg_time = sum(r['response_time'] for r in results) / len(results)
    print(f"⏱️  میانگین زمان: {avg_time:.2f}s")

if __name__ == "__main__":
    main()


