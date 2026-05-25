#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست جامع ساختار سند - بررسی دقیق بندها و بخش‌ها
"""

import sys
import os
import asyncio
import logging
import warnings

# اضافه کردن مسیر سیستم
sys.path.insert(0, '/home/user01/qwen-api/enhanced_rag_system')

# غیرفعال کردن warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# تنظیم logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_comprehensive_structure():
    """تست جامع ساختار سند"""
    
    print("🚀 راه‌اندازی سیستم برای تست جامع...")
    
    try:
        from ultimate_rag_system import UltimateRAGSystem
        
        # راه‌اندازی سیستم
        rag_system = UltimateRAGSystem(
            enable_semantic_chunking=True,
            enable_query_understanding=True,
            enable_advanced_retrieval=True,
            retrieval_strategy='hybrid'
        )
        
        print("✅ سیستم راه‌اندازی شد")
        
        # خواندن PDF
        pdf_path = '/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf'
        
        if not os.path.exists(pdf_path):
            print(f"❌ فایل PDF یافت نشد: {pdf_path}")
            return
        
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        print(f"📄 فایل PDF خوانده شد: {len(pdf_bytes)} بایت")
        
        # پردازش PDF کامل
        print("🔄 شروع پردازش PDF کامل...")
        
        result = await rag_system.process_pdf_advanced(
            file_bytes=pdf_bytes,
            filename='jadval5-bodje.pdf',
            collection_name='budget_document_full'
        )
        
        print(f"✅ نتیجه پردازش:")
        print(f"   - موفقیت: {result.get('success', False)}")
        print(f"   - تعداد chunks: {result.get('chunks_count', 0)}")
        print(f"   - خطا: {result.get('error', 'None')}")
        
        if result.get('success'):
            print("🎉 پردازش PDF موفقیت‌آمیز بود!")
            
            # تست‌های جامع
            await test_comprehensive_queries(rag_system)
        else:
            print(f"❌ پردازش PDF ناموفق: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ خطا در راه‌اندازی سیستم: {e}")
        import traceback
        traceback.print_exc()

async def test_comprehensive_queries(rag_system):
    """تست‌های جامع ساختار سند"""
    
    print("\n" + "="*100)
    print("🧪 شروع تست‌های جامع ساختار سند...")
    print("="*100)
    
    # تست 1: چند بند داریم؟
    print("\n❓ Test 1: چند بند داریم؟")
    print("="*100)
    
    try:
        result1 = await rag_system.retrieve_and_answer(
            query="چند بند داریم؟",
            collection_name="budget_document_full",
            top_k=15
        )
        
        print("📊 پاسخ:")
        print(f"✅ خلاصه: {result1.get('answer', 'پاسخ یافت نشد')}")
        print(f"📋 منابع: {len(result1.get('top_results', []))} منبع")
        
        # نمایش جزئیات منابع
        if result1.get('top_results'):
            print("\n📋 جزئیات منابع:")
            for i, source in enumerate(result1.get('top_results', [])[:5]):
                print(f"   {i+1}. {source.get('text', '')[:150]}...")
        
    except Exception as e:
        print(f"❌ خطا در تست 1: {e}")
    
    # تست 2: چند بخش داریم؟
    print("\n❓ Test 2: چند بخش داریم؟")
    print("="*100)
    
    try:
        result2 = await rag_system.retrieve_and_answer(
            query="چند بخش داریم؟",
            collection_name="budget_document_full",
            top_k=15
        )
        
        print("📊 پاسخ:")
        print(f"✅ خلاصه: {result2.get('answer', 'پاسخ یافت نشد')}")
        print(f"📋 منابع: {len(result2.get('top_results', []))} منبع")
        
        # نمایش جزئیات منابع
        if result2.get('top_results'):
            print("\n📋 جزئیات منابع:")
            for i, source in enumerate(result2.get('top_results', [])[:5]):
                print(f"   {i+1}. {source.get('text', '')[:150]}...")
        
    except Exception as e:
        print(f"❌ خطا در تست 2: {e}")
    
    # تست 3: ساختار کامل سند
    print("\n❓ Test 3: ساختار کامل این سند چیست؟")
    print("="*100)
    
    try:
        result3 = await rag_system.retrieve_and_answer(
            query="ساختار کامل این سند چیست؟ شامل بخش‌ها و بندها",
            collection_name="budget_document_full",
            top_k=20
        )
        
        print("📊 پاسخ:")
        print(f"✅ خلاصه: {result3.get('answer', 'پاسخ یافت نشد')}")
        print(f"📋 منابع: {len(result3.get('top_results', []))} منبع")
        
        # نمایش جزئیات منابع
        if result3.get('top_results'):
            print("\n📋 جزئیات منابع:")
            for i, source in enumerate(result3.get('top_results', [])[:5]):
                print(f"   {i+1}. {source.get('text', '')[:150]}...")
        
    except Exception as e:
        print(f"❌ خطا در تست 3: {e}")
    
    # تست 4: لیست تمام بندها
    print("\n❓ Test 4: لیست تمام بندها با شماره و عنوان")
    print("="*100)
    
    try:
        result4 = await rag_system.retrieve_and_answer(
            query="لیست تمام بندها با شماره و عنوان کامل",
            collection_name="budget_document_full",
            top_k=20
        )
        
        print("📊 پاسخ:")
        print(f"✅ خلاصه: {result4.get('answer', 'پاسخ یافت نشد')}")
        print(f"📋 منابع: {len(result4.get('top_results', []))} منبع")
        
        # نمایش جزئیات منابع
        if result4.get('top_results'):
            print("\n📋 جزئیات منابع:")
            for i, source in enumerate(result4.get('top_results', [])[:5]):
                print(f"   {i+1}. {source.get('text', '')[:150]}...")
        
    except Exception as e:
        print(f"❌ خطا در تست 4: {e}")
    
    # تست 5: لیست تمام بخش‌ها
    print("\n❓ Test 5: لیست تمام بخش‌ها با شماره و عنوان")
    print("="*100)
    
    try:
        result5 = await rag_system.retrieve_and_answer(
            query="لیست تمام بخش‌ها با شماره و عنوان کامل",
            collection_name="budget_document_full",
            top_k=20
        )
        
        print("📊 پاسخ:")
        print(f"✅ خلاصه: {result5.get('answer', 'پاسخ یافت نشد')}")
        print(f"📋 منابع: {len(result5.get('top_results', []))} منبع")
        
        # نمایش جزئیات منابع
        if result5.get('top_results'):
            print("\n📋 جزئیات منابع:")
            for i, source in enumerate(result5.get('top_results', [])[:5]):
                print(f"   {i+1}. {source.get('text', '')[:150]}...")
        
    except Exception as e:
        print(f"❌ خطا در تست 5: {e}")
    
    # تست 6: شماره 110100 چیست؟
    print("\n❓ Test 6: شماره 110100 چیست؟")
    print("="*100)
    
    try:
        result6 = await rag_system.retrieve_and_answer(
            query="شماره 110100 چیست؟",
            collection_name="budget_document_full",
            top_k=10
        )
        
        print("📊 پاسخ:")
        print(f"✅ خلاصه: {result6.get('answer', 'پاسخ یافت نشد')}")
        print(f"📋 منابع: {len(result6.get('top_results', []))} منبع")
        
        # نمایش جزئیات منابع
        if result6.get('top_results'):
            print("\n📋 جزئیات منابع:")
            for i, source in enumerate(result6.get('top_results', [])[:3]):
                print(f"   {i+1}. {source.get('text', '')[:150]}...")
        
    except Exception as e:
        print(f"❌ خطا در تست 6: {e}")
    
    # تست 7: شماره 110102 چیست؟
    print("\n❓ Test 7: شماره 110102 چیست؟")
    print("="*100)
    
    try:
        result7 = await rag_system.retrieve_and_answer(
            query="شماره 110102 چیست؟",
            collection_name="budget_document_full",
            top_k=10
        )
        
        print("📊 پاسخ:")
        print(f"✅ خلاصه: {result7.get('answer', 'پاسخ یافت نشد')}")
        print(f"📋 منابع: {len(result7.get('top_results', []))} منبع")
        
        # نمایش جزئیات منابع
        if result7.get('top_results'):
            print("\n📋 جزئیات منابع:")
            for i, source in enumerate(result7.get('top_results', [])[:3]):
                print(f"   {i+1}. {source.get('text', '')[:150]}...")
        
    except Exception as e:
        print(f"❌ خطا در تست 7: {e}")
    
    # تست 8: شماره 110000 چیست؟
    print("\n❓ Test 8: شماره 110000 چیست؟")
    print("="*100)
    
    try:
        result8 = await rag_system.retrieve_and_answer(
            query="شماره 110000 چیست؟",
            collection_name="budget_document_full",
            top_k=10
        )
        
        print("📊 پاسخ:")
        print(f"✅ خلاصه: {result8.get('answer', 'پاسخ یافت نشد')}")
        print(f"📋 منابع: {len(result8.get('top_results', []))} منبع")
        
        # نمایش جزئیات منابع
        if result8.get('top_results'):
            print("\n📋 جزئیات منابع:")
            for i, source in enumerate(result8.get('top_results', [])[:3]):
                print(f"   {i+1}. {source.get('text', '')[:150]}...")
        
    except Exception as e:
        print(f"❌ خطا در تست 8: {e}")

if __name__ == "__main__":
    asyncio.run(test_comprehensive_structure())
