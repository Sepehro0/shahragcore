#!/usr/bin/env python3
"""
Test script for all queries - Complete API Response Report
"""
import json
import requests
import time
from datetime import datetime
from typing import Dict, Any

API_URL = "http://185.13.230.254:8010/v2/query"
COLLECTION = "finance_budget_new_1764252643"

QUERIES = [
    {
        "id": 1,
        "query": "مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور سال 1402",
        "type": "expense_summary"
    },
    {
        "id": 2,
        "query": "درآمد های گمرک جمهوری اسلامی ایران در سال 1398",
        "type": "income_entity_year"
    },
    {
        "id": 3,
        "query": "در امد های سازمان ملي استاندارد در سال ها 1399 تا 1402",
        "type": "income_entity_years"
    },
    {
        "id": 4,
        "query": "درامد های حاصل از واگذاری دارایی های سرمایه ای در سال 1402",
        "type": "income_component"
    },
    {
        "id": 5,
        "query": "درامدهای مالیاتی در سال 1402",
        "type": "income_component"
    },
    {
        "id": 6,
        "query": "درامد حاصل از جرایم و خسارات در سال های 1398 تا 1400",
        "type": "income_component_years"
    },
    {
        "id": 7,
        "query": "درامد های دانشگاه امیرکبیر در سال 1403 از چه جز هایی وصول شده است ؟",
        "type": "breakdown_entity"
    },
    {
        "id": 8,
        "query": "راه های در امدی بنیاد ملی نخبگان در سال 1402 چه مواردی بودند ؟",
        "type": "breakdown_entity"
    }
]


def test_query(query_data: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single query and return full response"""
    print(f"\n{'='*80}")
    print(f"Query {query_data['id']}: {query_data['query']}")
    print(f"{'='*80}")
    
    payload = {
        "query": query_data["query"],
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
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "status_code": 200,
                "elapsed_time": elapsed_time,
                "query_id": query_data["id"],
                "query": query_data["query"],
                "query_type": query_data["type"],
                "response": result
            }
        else:
            return {
                "success": False,
                "status_code": response.status_code,
                "elapsed_time": elapsed_time,
                "query_id": query_data["id"],
                "query": query_data["query"],
                "query_type": query_data["type"],
                "error": response.text
            }
    except Exception as e:
        elapsed_time = time.time() - start_time
        return {
            "success": False,
            "status_code": 0,
            "elapsed_time": elapsed_time,
            "query_id": query_data["id"],
            "query": query_data["query"],
            "query_type": query_data["type"],
            "error": str(e)
        }


def extract_key_metrics(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key metrics from API response"""
    if not result.get("success"):
        return {
            "error": result.get("error", "Unknown error")
        }
    
    resp = result.get("response")
    if not resp:
        return {
            "error": "No response data"
        }
    
    if not isinstance(resp, dict):
        return {
            "error": f"Invalid response type: {type(resp)}"
        }
    
    metadata = resp.get("metadata", {}) or {}
    raw_table_data = resp.get("raw_table_data") or {}
    detailed_sources = resp.get("detailed_sources") or []
    
    metrics = {
        "route": metadata.get("retrieval_route", "unknown") if metadata else "unknown",
        "has_answer": bool(resp.get("answer") or resp.get("response")),
        "answer_preview": (resp.get("answer") or resp.get("response") or "")[:150],
        "row_count": raw_table_data.get("row_count", 0) if isinstance(raw_table_data, dict) else 0,
        "has_table_data": bool(raw_table_data.get("rows") if isinstance(raw_table_data, dict) else False),
        "has_sources": bool(detailed_sources),
        "sources_count": len(detailed_sources) if isinstance(detailed_sources, list) else 0,
        "has_chart_data": bool(resp.get("chart_data")),
        "has_statistics": bool(resp.get("statistics")),
        "confidence": metadata.get("confidence_score", 0) if metadata else 0,
        "processing_time": metadata.get("processing_time_seconds", 0) if metadata else 0,
        "elapsed_time": result.get("elapsed_time", 0)
    }
    
    return metrics


def generate_report(results: list) -> str:
    """Generate comprehensive report"""
    report = []
    report.append("# گزارش کامل تست سوالات API Server\n")
    report.append(f"**تاریخ تست:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"**Collection:** {COLLECTION}\n")
    report.append(f"**API URL:** {API_URL}\n\n")
    
    report.append("## خلاصه نتایج\n")
    total = len(results)
    success = sum(1 for r in results if r.get("success"))
    failed = total - success
    
    report.append(f"- **تعداد کل سوالات:** {total}\n")
    report.append(f"- **موفق:** {success} ({success*100/total:.1f}%)\n")
    report.append(f"- **ناموفق:** {failed} ({failed*100/total:.1f}%)\n\n")
    
    # Group by route
    routes = {}
    for r in results:
        if r.get("success"):
            metrics = extract_key_metrics(r)
            route = metrics.get("route", "unknown")
            if route not in routes:
                routes[route] = []
            routes[route].append(r)
    
    report.append("## توزیع Route\n")
    for route, route_results in routes.items():
        report.append(f"- **{route}:** {len(route_results)} سوال\n")
    report.append("\n")
    
    # Detailed results
    report.append("## جزئیات نتایج\n\n")
    
    for result in results:
        query_id = result.get("query_id")
        query = result.get("query")
        query_type = result.get("query_type")
        
        report.append(f"### Query {query_id}: {query_type}\n\n")
        report.append(f"**سوال:** {query}\n\n")
        
        if result.get("success"):
            metrics = extract_key_metrics(result)
            resp = result.get("response", {})
            
            report.append("#### نتایج:\n\n")
            report.append(f"- **Route:** `{metrics.get('route')}`\n")
            report.append(f"- **زمان پاسخ:** {metrics.get('elapsed_time', 0):.2f} ثانیه\n")
            report.append(f"- **Confidence:** {metrics.get('confidence', 0):.2f}\n")
            report.append(f"- **تعداد ردیف:** {metrics.get('row_count', 0)}\n")
            report.append(f"- **تعداد منابع:** {metrics.get('sources_count', 0)}\n\n")
            
            # Answer
            answer = resp.get("answer") or resp.get("response", "")
            report.append("#### پاسخ:\n\n")
            report.append(f"```\n{answer}\n```\n\n")
            
            # Table data
            if metrics.get("has_table_data"):
                table_data = resp.get("raw_table_data", {})
                rows = table_data.get("rows", [])
                if rows:
                    report.append(f"#### نمونه داده‌های جدول (اولین {min(3, len(rows))} ردیف):\n\n")
                    for i, row in enumerate(rows[:3], 1):
                        report.append(f"**ردیف {i}:**\n")
                        report.append(f"```json\n{json.dumps(row, ensure_ascii=False, indent=2)}\n```\n\n")
            
            # Sources
            if metrics.get("has_sources"):
                sources = resp.get("detailed_sources", [])
                report.append(f"#### منابع ({len(sources)} مورد):\n\n")
                for i, source in enumerate(sources[:3], 1):
                    report.append(f"**منبع {i}:**\n")
                    report.append(f"- صفحه: {source.get('page', 'N/A')}\n")
                    content = source.get('content', '')[:200] if source.get('content') else ''
                    report.append(f"- متن: {content}...\n\n")
            
            # Chart data
            if metrics.get("has_chart_data"):
                chart_data = resp.get("chart_data", {})
                report.append("#### داده‌های نمودار:\n\n")
                report.append(f"```json\n{json.dumps(chart_data, ensure_ascii=False, indent=2)}\n```\n\n")
            
            # Statistics
            if metrics.get("has_statistics"):
                stats = resp.get("statistics", {})
                report.append("#### آمار:\n\n")
                report.append(f"```json\n{json.dumps(stats, ensure_ascii=False, indent=2)}\n```\n\n")
            
            # Full response (truncated)
            report.append("#### پاسخ کامل API (JSON):\n\n")
            report.append(f"<details>\n<summary>مشاهده پاسخ کامل</summary>\n\n")
            report.append(f"```json\n{json.dumps(resp, ensure_ascii=False, indent=2)[:5000]}...\n```\n\n")
            report.append("</details>\n\n")
        else:
            report.append("#### خطا:\n\n")
            report.append(f"```\n{result.get('error', 'Unknown error')}\n```\n\n")
            report.append(f"- **Status Code:** {result.get('status_code')}\n")
            report.append(f"- **زمان:** {result.get('elapsed_time', 0):.2f} ثانیه\n\n")
        
        report.append("---\n\n")
    
    return "\n".join(report)


def main():
    """Main test function"""
    print("Starting comprehensive query testing...")
    print(f"Testing {len(QUERIES)} queries against collection: {COLLECTION}\n")
    
    results = []
    for query_data in QUERIES:
        result = test_query(query_data)
        results.append(result)
        
        if result.get("success"):
            metrics = extract_key_metrics(result)
            print(f"✅ Success | Route: {metrics.get('route')} | Rows: {metrics.get('row_count')} | Time: {metrics.get('elapsed_time', 0):.2f}s")
        else:
            print(f"❌ Failed | Error: {result.get('error', 'Unknown')[:50]}")
        
        time.sleep(1)  # Rate limiting
    
    # Generate report
    report = generate_report(results)
    
    # Save report
    report_file = f"/home/user01/qwen-api/enhanced_rag_system/QUERY_TEST_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n{'='*80}")
    print(f"✅ Report saved to: {report_file}")
    print(f"{'='*80}\n")
    
    # Print summary
    success_count = sum(1 for r in results if r.get("success"))
    print(f"Summary: {success_count}/{len(results)} queries succeeded")
    
    return results


if __name__ == "__main__":
    main()
