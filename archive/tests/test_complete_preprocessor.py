#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست کامل Query Preprocessor با API
"""

import requests
import json
import time

API_BASE = "http://185.13.230.254:8010"

def test_query(query, collection_name="finance_combined_1762693261", description=""):
    """تست یک query"""
    print(f"\n{'='*70}")
    print(f"📝 {description}")
    print(f"Query: {query}")
    print(f"{'='*70}")
    
    url = f"{API_BASE}/v2/query"
    payload = {
        "query": query,
        "collection_name": collection_name,
        "top_k": 10,
        "use_reranking": True,
        "use_multi_hop": False
    }
    
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=60)
        elapsed = time.time() - start_time
        response.raise_for_status()
        result = response.json()
        
        print(f"⏱️  زمان پردازش: {elapsed:.2f} ثانیه")
        print(f"✅ Success: {result.get('success', False)}")
        
        if result.get('success'):
            answer = result.get('answer', '')
            print(f"\n📄 پاسخ ({len(answer)} کاراکتر):")
            print(f"{answer[:300]}...")
            
            # بررسی metadata
            metadata = result.get('metadata', {})
            if metadata.get('type') == 'greeting':
                print("\n✅ نوع: سلام - Query Preprocessor کار می‌کند!")
            elif metadata.get('type') == 'irrelevant':
                print("\n✅ نوع: سوال نامرتبط - Query Preprocessor کار می‌کند!")
            else:
                print(f"\n📊 Metadata: {json.dumps(metadata, ensure_ascii=False, indent=2)[:200]}")
            
            # بررسی تبدیل منابع/مصارف
            if 'منابع' in query and 'درآمد' in answer:
                print("\n✅ تبدیل 'منابع' به 'درآمد' انجام شد!")
            elif 'مصارف' in query and 'هزینه' in answer:
                print("\n✅ تبدیل 'مصارف' به 'هزینه' انجام شد!")
            
            return True
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def main():
    print("\n" + "="*70)
    print("🧪 تست کامل Query Preprocessor با API")
    print("="*70)
    
    results = []
    
    # تست 1: سلام
    results.append((
        "سلام",
        "تست 1: تشخیص سلام و احوالپرسی",
        test_query("سلام", description="تست 1: تشخیص سلام و احوالپرسی")
    ))
    
    time.sleep(1)
    
    # تست 2: سلام با احوالپرسی
    results.append((
        "سلام علیکم",
        "تست 2: سلام با احوالپرسی",
        test_query("سلام علیکم", description="تست 2: سلام با احوالپرسی")
    ))
    
    time.sleep(1)
    
    # تست 3: سوال نامرتبط
    results.append((
        "هوا چطوره؟",
        "تست 3: تشخیص سوال نامرتبط",
        test_query("هوا چطوره؟", description="تست 3: تشخیص سوال نامرتبط")
    ))
    
    time.sleep(1)
    
    # تست 4: تبدیل "منابع" به "درآمد"
    results.append((
        "انستیتو پاستور ایران در سال 1401 منابع اختصاصی چقدر داشته است؟",
        "تست 4: تبدیل 'منابع' به 'درآمد'",
        test_query(
            "انستیتو پاستور ایران در سال 1401 منابع اختصاصی چقدر داشته است؟",
            description="تست 4: تبدیل 'منابع' به 'درآمد'"
        )
    ))
    
    time.sleep(1)
    
    # تست 5: تبدیل "مصارف" به "هزینه"
    results.append((
        "انستیتو پاستور ایران در سال 1401 مصارف اختصاصی چقدر داشته است؟",
        "تست 5: تبدیل 'مصارف' به 'هزینه'",
        test_query(
            "انستیتو پاستور ایران در سال 1401 مصارف اختصاصی چقدر داشته است؟",
            description="تست 5: تبدیل 'مصارف' به 'هزینه'"
        )
    ))
    
    time.sleep(1)
    
    # تست 6: سوال عادی (برای مقایسه)
    results.append((
        "انستیتو پاستور ایران در سال 1401 درآمد اختصاصی چقدر داشته است؟",
        "تست 6: سوال عادی (مقایسه)",
        test_query(
            "انستیتو پاستور ایران در سال 1401 درآمد اختصاصی چقدر داشته است؟",
            description="تست 6: سوال عادی (مقایسه)"
        )
    ))
    
    # خلاصه نتایج
    print("\n" + "="*70)
    print("📊 خلاصه نتایج")
    print("="*70)
    
    success_count = sum(1 for _, _, r in results if r)
    total_count = len(results)
    
    for i, (query, desc, result) in enumerate(results, 1):
        status = "✅" if result else "❌"
        print(f"{status} تست {i}: {desc}")
    
    print(f"\n✅ موفق: {success_count}/{total_count}")
    print("="*70)

if __name__ == "__main__":
    main()

