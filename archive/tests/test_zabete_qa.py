#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست سوالات zabete_qa
"""

import requests
import json
import sys

def test_zabete_questions():
    """تست سوالات zabete_qa"""
    
    url = "http://localhost:8010/v2/query/streaming"
    
    queries = [
        {
            "query": "قراردادهای epc رو توضیح بده",
            "expected": "should_pass",
            "description": "سوال کلی درباره EPC"
        },
        {
            "query": "در قراردادهای EPC تاخیر در پرداخت ها چگونه است؟",
            "expected": "should_pass",
            "description": "سوال مشخص درباره EPC"
        },
        {
            "query": "قراردادهای bot رو توضیح بده",
            "expected": "should_check",
            "description": "سوال کلی درباره BOT"
        },
        {
            "query": "تفاوت epc و bot چیست؟",
            "expected": "should_pass",
            "description": "سوال مقایسه‌ای"
        },
        {
            "query": "قرارداد qbs چیست؟",
            "expected": "should_pass",
            "description": "سوال درباره QBS"
        }
    ]
    
    print("🧪 Testing zabete_qa Questions")
    print("=" * 80)
    
    results = {"passed": 0, "failed": 0, "total": len(queries)}
    
    for test_case in queries:
        query = test_case["query"]
        expected = test_case["expected"]
        description = test_case["description"]
        
        print(f"\n📝 {description}")
        print(f"   Query: {query}")
        
        payload = {
            "query": query,
            "collection_name": "zabete_qa",
            "top_k": 5,
            "use_reranking": True,
            "use_multi_hop": True,
            "temperature": 0.1
        }
        
        try:
            response = requests.post(url, json=payload, stream=True, timeout=60)
            
            if response.status_code != 200:
                print(f"   ❌ HTTP Error: {response.status_code}")
                results["failed"] += 1
                continue
            
            was_rejected = False
            full_answer = ""
            rejected_by = None
            
            for line in response.iter_lines():
                if not line:
                    continue
                
                line_str = line.decode('utf-8')
                
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    try:
                        data = json.loads(data_str)
                        
                        if data.get('type') == 'complete':
                            if data.get('success') == False:
                                was_rejected = True
                                full_answer = data.get('answer', '')
                                rejected_by = data.get('metadata', {}).get('rejected_by')
                            else:
                                full_answer = data.get('answer', '')
                    except json.JSONDecodeError:
                        pass
            
            if was_rejected:
                print(f"   ❌ REJECTED by: {rejected_by}")
                print(f"      Message: {full_answer[:200]}...")
                if expected == "should_pass":
                    results["failed"] += 1
                else:
                    results["passed"] += 1
            else:
                print(f"   ✅ GOT ANSWER ({len(full_answer)} chars)")
                print(f"      Preview: {full_answer[:150]}...")
                if expected in ["should_pass", "should_check"]:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
        
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            results["failed"] += 1
        
        print("-" * 80)
    
    print("\n" + "=" * 80)
    print(f"📊 Results: {results['passed']}/{results['total']} passed")
    print("=" * 80)
    
    return results['failed'] == 0


if __name__ == "__main__":
    success = test_zabete_questions()
    sys.exit(0 if success else 1)



