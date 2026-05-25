#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست کامل API برای توسعه‌دهندگان
بررسی تمام قابلیت‌های Query Preprocessor
"""

import requests
import json
import time
from typing import Dict, Any

API_BASE = "http://185.13.230.254:8010"
COLLECTION = "finance_combined_1762693261"

def test_api_query(query: str, description: str, expected_type: str = None) -> Dict[str, Any]:
    """تست یک query از طریق API"""
    print(f"\n{'='*80}")
    print(f"📝 {description}")
    print(f"{'='*80}")
    print(f"Query: {query}")
    
    url = f"{API_BASE}/v2/query"
    payload = {
        "query": query,
        "collection_name": COLLECTION,
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
            metadata = result.get('metadata', {})
            metadata_type = metadata.get('type', 'normal')
            
            print(f"\n📄 پاسخ ({len(answer)} کاراکتر):")
            print(f"{answer[:400]}...")
            
            print(f"\n📊 Metadata:")
            print(f"  - Type: {metadata_type}")
            print(f"  - Confidence: {result.get('confidence', 0):.2f}")
            print(f"  - Processing Time: {metadata.get('processing_time_seconds', 0):.2f}s")
            
            # بررسی نوع پاسخ
            if expected_type:
                if metadata_type == expected_type:
                    print(f"\n✅ نوع پاسخ صحیح است: {expected_type}")
                else:
                    print(f"\n❌ نوع پاسخ اشتباه است! انتظار: {expected_type}, دریافت: {metadata_type}")
            
            # بررسی محتوا
            if metadata_type == 'greeting':
                if 'دستیار' in answer and 'سازمان برنامه و بودجه' in answer:
                    print("✅ پاسخ سلام صحیح است - شامل معرفی دستیار است")
                else:
                    print("⚠️ پاسخ سلام ممکن است کامل نباشد")
            
            elif metadata_type == 'irrelevant':
                if 'فقط' in answer and 'برنامه و بودجه' in answer:
                    print("✅ پاسخ سوال نامرتبط صحیح است")
                else:
                    print("⚠️ پاسخ سوال نامرتبط ممکن است کامل نباشد")
            
            # بررسی تبدیل "منابع" به "درآمد"
            if 'منابع' in query.lower():
                if 'درآمد' in answer and 'منابع' not in answer:
                    print("✅ تبدیل 'منابع' به 'درآمد' انجام شد")
                elif 'درآمد' in answer:
                    print("⚠️ تبدیل انجام شد اما ممکن است LLM از 'منابع' هم استفاده کرده باشد")
                else:
                    print("❌ تبدیل 'منابع' به 'درآمد' انجام نشد")
            
            # بررسی تبدیل "مصارف" به "هزینه"
            if 'مصارف' in query.lower():
                if 'هزینه' in answer and 'مصارف' not in answer:
                    print("✅ تبدیل 'مصارف' به 'هزینه' انجام شد")
                elif 'هزینه' in answer:
                    print("⚠️ تبدیل انجام شد اما ممکن است LLM از 'مصارف' هم استفاده کرده باشد")
                else:
                    print("❌ تبدیل 'مصارف' به 'هزینه' انجام نشد")
            
            return {
                'success': True,
                'answer': answer,
                'metadata': metadata,
                'elapsed': elapsed
            }
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            return {
                'success': False,
                'error': result.get('error', 'Unknown error')
            }
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def main():
    print("\n" + "="*80)
    print("🧪 تست کامل API برای توسعه‌دهندگان")
    print("="*80)
    
    results = []
    
    # تست 1: سلام ساده
    results.append(test_api_query(
        "سلام",
        "تست 1: سلام ساده",
        expected_type="greeting"
    ))
    
    time.sleep(1)
    
    # تست 2: سلام با احوالپرسی
    results.append(test_api_query(
        "سلام علیکم",
        "تست 2: سلام با احوالپرسی",
        expected_type="greeting"
    ))
    
    time.sleep(1)
    
    # تست 3: سوال نامرتبط
    results.append(test_api_query(
        "هوا چطوره؟",
        "تست 3: سوال نامرتبط (هوا)",
        expected_type="irrelevant"
    ))
    
    time.sleep(1)
    
    # تست 4: سوال نامرتبط دیگر
    results.append(test_api_query(
        "امروز چه فیلمی ببینم؟",
        "تست 4: سوال نامرتبط (فیلم)",
        expected_type="irrelevant"
    ))
    
    time.sleep(1)
    
    # تست 5: تبدیل "منابع" به "درآمد"
    results.append(test_api_query(
        "انستیتو پاستور ایران در سال 1401 منابع اختصاصی چقدر داشته است؟",
        "تست 5: تبدیل 'منابع' به 'درآمد'",
        expected_type="normal"
    ))
    
    time.sleep(1)
    
    # تست 6: تبدیل "مصارف" به "هزینه"
    results.append(test_api_query(
        "انستیتو پاستور ایران در سال 1401 مصارف اختصاصی چقدر داشته است؟",
        "تست 6: تبدیل 'مصارف' به 'هزینه'",
        expected_type="normal"
    ))
    
    time.sleep(1)
    
    # تست 7: سوال عادی با "درآمد" (مقایسه)
    results.append(test_api_query(
        "انستیتو پاستور ایران در سال 1401 درآمد اختصاصی چقدر داشته است؟",
        "تست 7: سوال عادی با 'درآمد' (مقایسه)",
        expected_type="normal"
    ))
    
    time.sleep(1)
    
    # تست 8: سوال عادی با "هزینه" (مقایسه)
    results.append(test_api_query(
        "انستیتو پاستور ایران در سال 1401 هزینه اختصاصی چقدر داشته است؟",
        "تست 8: سوال عادی با 'هزینه' (مقایسه)",
        expected_type="normal"
    ))
    
    # خلاصه نتایج
    print("\n" + "="*80)
    print("📊 خلاصه نتایج")
    print("="*80)
    
    success_count = sum(1 for r in results if r.get('success', False))
    total_count = len(results)
    
    for i, result in enumerate(results, 1):
        status = "✅" if result.get('success', False) else "❌"
        elapsed = result.get('elapsed', 0)
        metadata_type = result.get('metadata', {}).get('type', 'unknown')
        print(f"{status} تست {i}: Success={result.get('success', False)}, Type={metadata_type}, Time={elapsed:.2f}s")
    
    print(f"\n✅ موفق: {success_count}/{total_count}")
    print(f"📈 نرخ موفقیت: {(success_count/total_count)*100:.1f}%")
    
    # بررسی قابلیت‌های خاص
    print("\n" + "="*80)
    print("🔍 بررسی قابلیت‌های خاص")
    print("="*80)
    
    greeting_count = sum(1 for r in results if r.get('metadata', {}).get('type') == 'greeting')
    irrelevant_count = sum(1 for r in results if r.get('metadata', {}).get('type') == 'irrelevant')
    
    print(f"✅ تشخیص سلام: {greeting_count}/2")
    print(f"✅ تشخیص سوال نامرتبط: {irrelevant_count}/2")
    
    print("\n" + "="*80)
    print("✅ تست‌ها کامل شد!")
    print("="*80)

if __name__ == "__main__":
    main()

