#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست جامع سیستم کاملاً داینامیک
"""

import requests
import json
import sys

def test_comprehensive_questions():
    """تست سوالات مختلف برای اطمینان از عملکرد صحیح سیستم داینامیک"""
    
    url = "http://localhost:8010/v2/query/streaming"
    
    # مجموعه سوالات برای تست
    test_queries = [
        # سوالات مربوط به شکست (که قبلاً مشکل داشتند)
        {
            "query": "اگه تیم ما شکست بخوره چی میشه؟",
            "expected": "should_pass",
            "description": "سوال محاوره‌ای درباره شکست تیم"
        },
        {
            "query": "در صورت شکست در صندوق نوآور آیا باید پول را برگردانیم؟",
            "expected": "should_pass",
            "description": "سوال درباره بازگشت پول در شکست"
        },
        # سوالات عمومی درباره صندوق‌ها
        {
            "query": "سرمایه گذاری روی پروژه ها چجوری اتفاق میفته؟",
            "expected": "should_pass",
            "description": "سوال کلی درباره سرمایه‌گذاری"
        },
        {
            "query": "پروژه تهش مال کی میشه؟",
            "expected": "should_pass",
            "description": "سوال محاوره‌ای درباره مالکیت"
        },
        # سوالات مربوط به قرارداد و همکاری
        {
            "query": "چیکار کنیم باهامون قطع همکاری میشه؟",
            "expected": "should_pass",
            "description": "سوال درباره قطع همکاری"
        },
        {
            "query": "چه زمانی قرارداد فسخ میشود؟",
            "expected": "should_pass",
            "description": "سوال درباره فسخ قرارداد"
        },
        # سوالات مربوط به معرفی به سرمایه گذار
        {
            "query": "توی صندوق ها، چجوری به سرمایه گذار معرفی میشیم؟",
            "expected": "should_pass",
            "description": "سوال درباره معرفی به سرمایه‌گذار"
        },
        # سوالات مربوط به معاونت و وظایف
        {
            "query": "وظایف های معاونت برنامه ریزی و توسعه فناوری رو بگو",
            "expected": "should_pass",
            "description": "سوال درباره وظایف معاونت"
        },
        # سوالات نامربوط (باید reject شوند)
        {
            "query": "چطوری خونه بگیرم؟",
            "expected": "should_reject",
            "description": "سوال کاملاً نامربوط"
        },
        {
            "query": "فیلم خوب برای دیدن معرفی کن",
            "expected": "should_reject",
            "description": "سوال درباره فیلم (نامربوط)"
        },
        # سوالات مرزی
        {
            "query": "چطور میتونم تیم خوب بسازم؟",
            "expected": "should_pass",  # با semantic similarity باید بتواند ارتباط را تشخیص دهد
            "description": "سوال مرزی درباره تیم‌سازی"
        }
    ]
    
    print("🧪 Testing Fully Dynamic System")
    print("="  * 80)
    
    results = {
        "passed": 0,
        "failed": 0,
        "total": len(test_queries)
    }
    
    for test_case in test_queries:
        query = test_case["query"]
        expected = test_case["expected"]
        description = test_case["description"]
        
        print(f"\n📝 Testing: {description}")
        print(f"   Query: {query}")
        print(f"   Expected: {expected}")
        
        payload = {
            "query": query,
            "collection_name": "karbaran_omomi",
            "top_k": 5,
            "use_reranking": True,
            "use_multi_hop": True,
            "temperature": 0.1
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                stream=True,
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"   ❌ HTTP Error: Status code {response.status_code}")
                results["failed"] += 1
                continue
            
            was_rejected = False
            full_answer = ""
            
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
                            else:
                                full_answer = data.get('answer', '')
                    
                    except json.JSONDecodeError:
                        pass
            
            # بررسی نتیجه
            if expected == "should_pass":
                if not was_rejected and full_answer:
                    print(f"   ✅ PASS: Got answer ({len(full_answer)} chars)")
                    print(f"      Answer preview: {full_answer[:150]}...")
                    results["passed"] += 1
                else:
                    print(f"   ❌ FAIL: Query was rejected but should have passed")
                    if was_rejected:
                        print(f"      Rejection message: {full_answer[:200]}...")
                    results["failed"] += 1
            elif expected == "should_reject":
                if was_rejected:
                    print(f"   ✅ PASS: Query was correctly rejected")
                    print(f"      Rejection message: {full_answer[:150]}...")
                    results["passed"] += 1
                else:
                    print(f"   ❌ FAIL: Query was answered but should have been rejected")
                    print(f"      Answer: {full_answer[:200]}...")
                    results["failed"] += 1
        
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            results["failed"] += 1
        
        print("-" * 80)
    
    # خلاصه نتایج
    print("\n" + "=" * 80)
    print("📊 Test Results Summary:")
    print(f"   Total:  {results['total']}")
    print(f"   Passed: {results['passed']} ✅")
    print(f"   Failed: {results['failed']} ❌")
    print(f"   Success Rate: {results['passed']/results['total']*100:.1f}%")
    print("=" * 80)
    
    return results['failed'] == 0


if __name__ == "__main__":
    success = test_comprehensive_questions()
    sys.exit(0 if success else 1)



