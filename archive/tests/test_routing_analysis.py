#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تحلیل دقیق routing برای queries مالی
"""

import requests
import json
import sys
import re
from typing import Dict, Any

API_URL = "http://185.13.230.254:8010/v2/query"

# سوالات برای تست
QUERIES = [
    {
        "query": "انستيتو پاستور ايران در سال های 401 تا 403 مجموعا چقدر درامد اختصاصی داشته است ؟",
        "expected_route": "database",
        "type": "عدد + سال + دستگاه"
    },
    {
        "query": "تملک دارایی های سرمایه ای پارک فناوری پردیس در سال 1399",
        "expected_route": "database",
        "type": "عدد + سال + دستگاه"
    },
    {
        "query": "اعتبارات هزینه ای ستاد مبارزه با مواد مخدر سال 98",
        "expected_route": "database",
        "type": "عدد + سال + دستگاه"
    },
    {
        "query": "اعتبارات هزینه ای متفرقه بنیاد ایران شناسی در سال 98",
        "expected_route": "database",
        "type": "عدد + سال + دستگاه"
    },
    {
        "query": "مجموع تمامی مصارف معاونت علمی و فناوری رییس جمهور سال 1402",
        "expected_route": "database",
        "type": "مجموع + سال + دستگاه"
    },
    {
        "query": "تملک دارایی های سرمایه ای متفرقه مرکز ملی فضای مجازی کشور سال های 98 تا 1402",
        "expected_route": "database",
        "type": "عدد + محدوده سال + دستگاه"
    },
]

def analyze_query_patterns(query: str) -> Dict[str, Any]:
    """تحلیل الگوهای query"""
    normalized = query.lower()
    
    # الگوهای SQL-oriented
    sql_patterns = [
        r'\b(چند|چقدر|تعداد|مجموع|میانگین|حداکثر|حداقل|بیشترین|کمترین)\b',
        r'پر\s*هزینه',
        r'\b(جمع|SUM|COUNT|AVG|MAX|MIN)\b',
    ]
    
    # الگوهای عددی و مالی
    has_number_query = bool(re.search(r'\b(چقدر|چند|مجموع|تعداد)\b', normalized))
    has_year = bool(re.search(r'(13|14)\d{2}|سال\s*\d{2,4}', normalized))
    has_year_range = bool(re.search(r'\d{2,4}\s*(?:تا|-)\s*\d{2,4}|سال\s*های\s*\d+', normalized))
    has_device = bool(re.search(r'(پارک|ستاد|بنیاد|معاونت|مرکز|انستیتو)', normalized))
    has_financial_term = bool(re.search(r'(درآمد|هزینه|اعتبارات|تملک|دارایی|مصارف)', normalized))
    
    sql_score = sum(1 for pattern in sql_patterns if re.search(pattern, normalized, re.IGNORECASE))
    
    return {
        "has_number_query": has_number_query,
        "has_year": has_year,
        "has_year_range": has_year_range,
        "has_device": has_device,
        "has_financial_term": has_financial_term,
        "sql_score": sql_score,
        "should_be_database": has_number_query and (has_year or has_device) and has_financial_term
    }

def test_query(query_data: Dict[str, Any]) -> Dict[str, Any]:
    """تست یک query"""
    query = query_data["query"]
    expected_route = query_data["expected_route"]
    
    print("\n" + "="*80)
    print(f"📝 Query: {query}")
    print(f"🎯 Expected Route: {expected_route}")
    print("="*80)
    
    # تحلیل الگوها
    pattern_analysis = analyze_query_patterns(query)
    print(f"\n📊 Pattern Analysis:")
    for key, value in pattern_analysis.items():
        print(f"   - {key}: {value}")
    
    # تست API
    payload = {
        "query": query,
        "collection_name": "finance_combined_1762693261",
        "top_k": 10,
        "use_reranking": True,
        "use_multi_hop": False,
        "conversation_id": f"test-{hash(query) % 10000}"
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=90)
        response.raise_for_status()
        result = response.json()
        
        route = result.get("metadata", {}).get("retrieval_route", "unknown")
        answer = result.get("answer", "")
        db_results = result.get("database_results")
        success = result.get("success", False)
        processing_time = result.get("processing_time", 0)
        
        print(f"\n✅ API Response:")
        print(f"   - Success: {success}")
        print(f"   - Route: {route}")
        print(f"   - Processing Time: {processing_time:.2f}s")
        print(f"   - Answer Length: {len(answer)} chars")
        
        if db_results:
            rows = db_results.get("results") or db_results.get("rows") or []
            print(f"   - Database Results: {len(rows)} rows")
            if rows:
                print(f"   - First Row Keys: {list(rows[0].keys())}")
                # بررسی null values
                has_values = any(v not in (None, "", 0, "0") for v in rows[0].values())
                print(f"   - Has Valid Values: {has_values}")
        else:
            print(f"   - Database Results: None")
        
        print(f"\n📄 Full Answer:")
        print(f"   {answer}")
        
        # بررسی match
        is_correct = route == expected_route
        status = "✅ CORRECT" if is_correct else "❌ WRONG"
        print(f"\n{status} Route: Got '{route}', Expected '{expected_route}'")
        
        return {
            "query": query,
            "expected_route": expected_route,
            "actual_route": route,
            "is_correct": is_correct,
            "pattern_analysis": pattern_analysis,
            "answer": answer,
            "has_db_results": bool(db_results),
            "processing_time": processing_time,
            "success": success
        }
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🔍 ANALYZING QUERY ROUTING")
    print("="*80)
    
    results = []
    
    for i, query_data in enumerate(QUERIES, 1):
        print(f"\n\n🧪 TEST {i}/{len(QUERIES)}")
        result = test_query(query_data)
        if result:
            results.append(result)
    
    # خلاصه
    print("\n\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    total = len(results)
    correct = sum(1 for r in results if r.get("is_correct"))
    wrong = total - correct
    
    print(f"\nTotal Queries: {total}")
    print(f"Correct Routes: {correct} ({correct/total*100:.1f}%)")
    print(f"Wrong Routes: {wrong} ({wrong/total*100:.1f}%)")
    
    print(f"\n📋 Detailed Results:")
    for i, r in enumerate(results, 1):
        status = "✅" if r.get("is_correct") else "❌"
        print(f"{status} [{i}] Expected: {r.get('expected_route'):15s} | Got: {r.get('actual_route'):15s} | {r.get('query', '')[:50]}...")
    
    # تحلیل مشکل
    if wrong > 0:
        print(f"\n⚠️ PROBLEM DETECTED:")
        print(f"   - {wrong} queries went to wrong route")
        print(f"   - All should go to 'database' but they went to '{results[0].get('actual_route') if results else 'unknown'}'")
        print(f"\n🔍 Possible Causes:")
        print(f"   1. QueryRouter not detecting financial patterns correctly")
        print(f"   2. _try_database_before_rag not being called")
        print(f"   3. Database results returning null → fallback to RAG")
        print(f"   4. QueryRouter threshold too high")
    
    print("\n" + "="*80)

