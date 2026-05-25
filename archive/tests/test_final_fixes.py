#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست نهایی تمام رفع مشکلات
"""

import requests
import json
import time

API_BASE = "http://localhost:8010"

def test_query(query: str, collection_name: str, test_name: str):
    """تست یک سوال"""
    print(f"\n{'='*90}")
    print(f"🧪 {test_name}")
    print(f"{'='*90}")
    print(f"📝 سوال: {query}")
    print(f"📚 Collection: {collection_name}")
    print(f"{'-'*90}\n")
    
    url = f"{API_BASE}/query"
    data = {
        "query": query,
        "collection_name": collection_name,
        "top_k": 5,
        "use_reranking": True,
        "use_multi_hop": False,
        "temperature": 0.1
    }
    
    try:
        response = requests.post(url, json=data, timeout=120)
        
        if response.status_code != 200:
            print(f"❌ خطا: {response.status_code}")
            print(response.text[:500])
            return False
        
        result = response.json()
        answer = result.get('answer', '')
        
        print("✅ پاسخ:")
        print(f"{'='*90}")
        print(answer)
        print(f"{'='*90}\n")
        
        # تحلیل
        answer_length = len(answer)
        word_count = len(answer.split())
        
        print(f"📊 تحلیل:")
        print(f"  - طول پاسخ: {answer_length} کاراکتر")
        print(f"  - تعداد کلمات: {word_count}")
        print(f"  - اعتماد: {result.get('confidence', 0):.2f}")
        print(f"  - تعداد sources: {len(result.get('sources', []))}")
        
        # بررسی مشکلات
        issues = []
        if "شما یک دستیار" in answer and "پاسخ می‌دهید" in answer:
            issues.append("⚠️ System prompt در پاسخ وجود دارد!")
        if "CODE_PLACEHOLDER" in answer:
            issues.append("⚠️ CODE_PLACEHOLDER در پاسخ وجود دارد!")
        if "لطفاً سوال خود را مطرح کنید" in answer:
            issues.append("⚠️ دستورالعمل system prompt در پاسخ وجود دارد!")
        
        if issues:
            print("\n❌ مشکلات یافت شده:")
            for issue in issues:
                print(f"  {issue}")
            return False
        else:
            print("\n✅ هیچ مشکلی یافت نشد!")
            return True
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*90)
    print("🚀 تست نهایی رفع تمام مشکلات")
    print("="*90 + "\n")
    
    time.sleep(3)
    
    results = {}
    
    # Test 1: پاسخ کوتاه - اجباری بودن دوره
    results['test1'] = test_query(
        query="ایا اجباریه شرکت تو دوره های ضمن خدمت ؟",
        collection_name="zinaf_dakheli",
        test_name="Test 1: پاسخ کامل - اجباری بودن دوره"
    )
    
    time.sleep(1)
    
    # Test 2: پاسخ کوتاه - حداقل نمره قبولی
    results['test2'] = test_query(
        query="حداقل نمره قبولی چیه ؟",
        collection_name="zinaf_dakheli",
        test_name="Test 2: پاسخ کامل - حداقل نمره قبولی"
    )
    
    time.sleep(1)
    
    # Test 3: سوال نامربوط - صندوق فرصت در zinaf_dakheli
    results['test3'] = test_query(
        query="صندوق فرصت چیه ؟",
        collection_name="zinaf_dakheli",
        test_name="Test 3: سوال نامربوط - صندوق فرصت"
    )
    
    time.sleep(1)
    
    # Test 4: سوال نامربوط - صندوق نوآور در zinaf_dakheli
    results['test4'] = test_query(
        query="صندوق نوآور چیه",
        collection_name="zinaf_dakheli",
        test_name="Test 4: سوال نامربوط - صندوق نوآور"
    )
    
    time.sleep(1)
    
    # Test 5: سوال معاون هولدینگ
    results['test5'] = test_query(
        query="من معاون یکی از هولدینگام دوره خاصی برای من وجود داره ؟",
        collection_name="zinaf_dakheli",
        test_name="Test 5: سوال معاون هولدینگ"
    )
    
    time.sleep(1)
    
    # Test 6: شماره تماس
    results['test6'] = test_query(
        query="با چه شماره ای تماس بگیرم ؟",
        collection_name="karbaran_omomi",
        test_name="Test 6: شماره تماس (بدون CODE_PLACEHOLDER)"
    )
    
    # خلاصه نتایج
    print("\n" + "="*90)
    print("📊 خلاصه نتایج تست‌ها")
    print("="*90 + "\n")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ موفق" if passed_test else "❌ ناموفق"
        print(f"  {test_name}: {status}")
    
    print(f"\n{'='*90}")
    print(f"🎯 نتیجه کلی: {passed}/{total} تست موفق ({passed*100//total}%)")
    print(f"{'='*90}\n")
    
    if passed == total:
        print("🎉 تمام تست‌ها با موفقیت انجام شدند!")
    else:
        print("⚠️ برخی تست‌ها ناموفق بودند. نیاز به بررسی بیشتر.")

if __name__ == "__main__":
    main()


