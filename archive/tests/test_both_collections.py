#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست کامل هر دو collection: qavanin و budget_financial
"""

import requests
import json
from datetime import datetime

API_URL = "http://185.13.230.254:8010/v2/query/streaming"

# تست Qavanin
QAVANIN_TESTS = [
    "تعریف «محیط کسب‌وکار» چیست؟",
    "آیا لازم‌الاجرا شدن مقررات منوط به ثبت در پایگاه است؟"
]

# تست Budget
BUDGET_TESTS = [
    "درامد استانی اختصاصی وزارت آموزش و پرورش در سال های 98 تا 403",
    "اعتبارات هزینه ای فرهنگستان علوم ایران در سال های 98 تا 403"
]

def test_question(question, collection):
    """تست یک سوال"""
    payload = {
        "query": question,
        "collection_name": collection,
        "top_k": 5,
        "temperature": 0.1
    }
    
    try:
        response = requests.post(API_URL, json=payload, stream=True, timeout=90)
        
        complete_data = None
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data:'):
                    try:
                        chunk = json.loads(line_str[5:].strip())
                        if chunk.get('type') == 'complete':
                            complete_data = chunk
                            break
                    except:
                        pass
        
        if complete_data:
            db_results = complete_data.get("database_results", {})
            table_data = complete_data.get("table_data") or ""
            
            return {
                "success": True,
                "question": question,
                "collection": complete_data.get("metadata", {}).get("collection", "unknown"),
                "answer_length": len(complete_data.get("answer", "")),
                "sources_count": len(complete_data.get("sources", [])),
                "top_similarity": complete_data.get("sources", [{}])[0].get("similarity_score", 0) if complete_data.get("sources") else 0,
                "db_rows": db_results.get("count", 0),
                "detail_rows": len(db_results.get("detail_rows", [])),
                "table_rows": len([l for l in table_data.split('\n') if l.startswith('|') and '---' not in l]) if table_data else 0,
                "table_length": len(table_data) if table_data else 0,
                "has_summary": ("خلاصه" in table_data or "نتایج کلی" in table_data) if table_data else False,
                "has_details": "جزئیات" in table_data if table_data else False
            }
        else:
            return {
                "success": False,
                "question": question,
                "error": "No complete response"
            }
    except Exception as e:
        return {
            "success": False,
            "question": question,
            "error": str(e)
        }

def main():
    print("=" * 80)
    print("🚀 Testing Collections: Qavanin & Budget_Financial")
    print("=" * 80)
    print()
    
    # Test Qavanin
    print("📦 Testing Qavanin Collection...")
    print("-" * 80)
    for q in QAVANIN_TESTS:
        print(f"🔍 {q[:60]}...")
        result = test_question(q, "qavanin")
        
        if result.get("success"):
            print(f"   ✅ Collection: {result['collection']}")
            print(f"   📊 Similarity: {result['top_similarity']:.4f}")
            print(f"   📚 Sources: {result['sources_count']}")
            print(f"   💬 Answer: {result['answer_length']} chars")
        else:
            print(f"   ❌ Error: {result.get('error')}")
        print()
    
    # Test Budget
    print("\n📦 Testing Budget_Financial Collection...")
    print("-" * 80)
    for q in BUDGET_TESTS:
        print(f"🔍 {q[:60]}...")
        result = test_question(q, "budget_financial")
        
        if result.get("success"):
            print(f"   ✅ Collection: {result['collection']}")
            print(f"   🗄️ DB Rows: {result['db_rows']}")
            print(f"   📋 Detail Rows: {result['detail_rows']}")
            print(f"   📊 Table Rows: {result['table_rows']}")
            print(f"   📝 Summary: {result['has_summary']}, Details: {result['has_details']}")
            print(f"   💬 Answer: {result['answer_length']} chars, Table: {result['table_length']} chars")
        else:
            print(f"   ❌ Error: {result.get('error')}")
        print()
    
    print("=" * 80)
    print("✅ Tests Completed!")
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    exit(main())
