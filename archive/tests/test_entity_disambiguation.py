#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست Entity Disambiguation System
"""

import requests
import json
import time
from datetime import datetime

API_URL = "http://localhost:8010/v2/query/streaming"
COLLECTION_NAME = "budget_financial"

# تست کیس‌های مختلف
TEST_CASES = [
    {
        "name": "معاونت علمی و فناوری (نباید پارک match شود)",
        "query": "تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403",
        "expected_entity": "معاونت",  # باید معاونت داشته باشد
        "wrong_entity": "پارک علم و فناوری"  # نباید پارک باشد
    },
    {
        "name": "سازمان سنجش (نام کوتاه)",
        "query": "تملک دارایی سرمایه ای متفرقه سازمان سنجش بند ج در سال 1403",
        "expected_entity": "سازمان سنجش",  # باید سازمان سنجش داشته باشد
        "wrong_entity": None
    },
    {
        "name": "پست بانک (نام کوتاه)",
        "query": "درآمد عمومی ملی پست بانک در سال 1402",
        "expected_entity": "پست بان",  # باید پست بانک یا شرکت دولتی پست بانک داشته باشد (partial match)
        "wrong_entity": "بانک سپه"  # نباید بانک سپه باشد
    },
    {
        "name": "فرهنگستان هنر (نباید دادگستری match شود)",
        "query": "بودجه فرهنگستان هنر در سال 1403",
        "expected_entity": "فرهنگستان هنر",
        "wrong_entity": "دادگستری"  # نباید دادگستری باشد
    }
]

def test_query(test_case):
    """تست یک query"""
    print(f"\n{'='*80}")
    print(f"🧪 Test: {test_case['name']}")
    print(f"{'='*80}")
    print(f"Query: {test_case['query']}")
    print()
    
    payload = {
        "query": test_case['query'],
        "collection_name": COLLECTION_NAME,
        "stream": True
    }
    
    try:
        start_time = time.time()
        response = requests.post(API_URL, json=payload, stream=True, timeout=60)
        
        entity_found = None
        route_path = None
        answer_preview = ""
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        
                        # استخراج entity از query_analysis
                        if 'metadata' in data and 'query_analysis' in data['metadata']:
                            qa = data['metadata']['query_analysis']
                            entity_found = qa.get('entity_names', [])
                        
                        # استخراج route_path
                        if 'route_path' in data:
                            route_path = data['route_path']
                        
                        # استخراج answer
                        if 'answer' in data and data['answer']:
                            answer_preview = data['answer'][:200]
                        
                    except json.JSONDecodeError:
                        pass
        
        elapsed = time.time() - start_time
        
        # نمایش نتایج
        print(f"⏱️  Time: {elapsed:.2f}s")
        print(f"🛣️  Route: {route_path}")
        print(f"🏷️  Entity Found: {entity_found}")
        
        # بررسی صحت
        success = True
        if test_case.get('expected_entity'):
            if entity_found and any(test_case['expected_entity'] in e for e in entity_found):
                print(f"✅ PASS: Expected entity found")
            else:
                print(f"❌ FAIL: Expected '{test_case['expected_entity']}' but got {entity_found}")
                success = False
        
        if test_case.get('wrong_entity'):
            if entity_found and any(test_case['wrong_entity'] in e for e in entity_found):
                print(f"❌ FAIL: Wrong entity '{test_case['wrong_entity']}' was matched")
                success = False
            else:
                print(f"✅ PASS: Wrong entity avoided")
        
        if route_path == "database":
            print(f"✅ PASS: Database route used")
        else:
            print(f"⚠️  WARNING: Route is '{route_path}' (expected 'database')")
        
        print(f"\n📝 Answer Preview:")
        print(answer_preview[:300] if answer_preview else "No answer")
        
        return success
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    """اجرای تست‌ها"""
    print("="*80)
    print("🚀 Entity Disambiguation System Test")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API: {API_URL}")
    print(f"Collection: {COLLECTION_NAME}")
    print()
    
    results = []
    for test_case in TEST_CASES:
        success = test_query(test_case)
        results.append({
            'name': test_case['name'],
            'success': success
        })
        time.sleep(2)  # کمی صبر کنیم
    
    # خلاصه نتایج
    print(f"\n{'='*80}")
    print("📊 Summary")
    print(f"{'='*80}")
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    for r in results:
        status = "✅ PASS" if r['success'] else "❌ FAIL"
        print(f"{status}: {r['name']}")
    
    print(f"\n🎯 Result: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Please review.")

if __name__ == "__main__":
    main()

