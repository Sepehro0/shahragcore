#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست سیستم Accurate - بررسی دقیق ساختار سند
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

async def test_accurate_system():
    """تست سیستم Accurate"""
    
    print("🚀 راه‌اندازی سیستم Accurate...")
    
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
            collection_name='budget_accurate_analysis'
        )
        
        print(f"✅ نتیجه پردازش:")
        print(f"   - موفقیت: {result.get('success', False)}")
        print(f"   - تعداد chunks: {result.get('chunks_count', 0)}")
        print(f"   - خطا: {result.get('error', 'None')}")
        
        if result.get('success'):
            print("🎉 پردازش PDF موفقیت‌آمیز بود!")
            
            # تست‌های دقیق
            await test_accurate_queries(rag_system)
        else:
            print(f"❌ پردازش PDF ناموفق: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ خطا در راه‌اندازی سیستم: {e}")
        import traceback
        traceback.print_exc()

async def test_accurate_queries(rag_system):
    """تست‌های دقیق ساختار سند"""
    
    print("\n" + "="*100)
    print("🧪 شروع تست‌های دقیق ساختار سند...")
    print("="*100)
    
    # تست 1: چند قسمت داریم؟ (انتظار: 1)
    print("\n❓ Test 1: چند قسمت داریم؟ (انتظار: 1)")
    print("="*100)
    
    try:
        result1 = await rag_system.retrieve_and_answer(
            query="چند قسمت داریم؟",
            collection_name="budget_accurate_analysis",
            top_k=15
        )
        
        print("📊 پاسخ:")
        print(f"{result1.get('answer', 'پاسخ یافت نشد')[:800]}")
        
    except Exception as e:
        print(f"❌ خطا در تست 1: {e}")
    
    # تست 2: چند بخش داریم؟ (انتظار: 6)
    print("\n❓ Test 2: چند بخش داریم؟ (انتظار: 6)")
    print("="*100)
    
    try:
        result2 = await rag_system.retrieve_and_answer(
            query="چند بخش داریم؟",
            collection_name="budget_accurate_analysis",
            top_k=15
        )
        
        print("📊 پاسخ:")
        print(f"{result2.get('answer', 'پاسخ یافت نشد')[:800]}")
        
    except Exception as e:
        print(f"❌ خطا در تست 2: {e}")
    
    # تست 3: چند بند داریم؟ (انتظار: 13)
    print("\n❓ Test 3: چند بند داریم؟ (انتظار: 13)")
    print("="*100)
    
    try:
        result3 = await rag_system.retrieve_and_answer(
            query="چند بند داریم؟",
            collection_name="budget_accurate_analysis",
            top_k=15
        )
        
        print("📊 پاسخ:")
        print(f"{result3.get('answer', 'پاسخ یافت نشد')[:800]}")
        
    except Exception as e:
        print(f"❌ خطا در تست 3: {e}")
    
    # تست 4: شماره 100000 چیست؟ (انتظار: قسمت اول: درآمدها)
    print("\n❓ Test 4: شماره 100000 چیست؟ (انتظار: قسمت اول: درآمدها)")
    print("="*100)
    
    try:
        result4 = await rag_system.retrieve_and_answer(
            query="شماره 100000 چیست؟",
            collection_name="budget_accurate_analysis",
            top_k=10
        )
        
        print("📊 پاسخ:")
        print(f"{result4.get('answer', 'پاسخ یافت نشد')[:800]}")
        
    except Exception as e:
        print(f"❌ خطا در تست 4: {e}")
    
    # تست 5: شماره 110000 چیست؟ (انتظار: بخش اول: درآمدهای مالیاتی)
    print("\n❓ Test 5: شماره 110000 چیست؟ (انتظار: بخش اول: درآمدهای مالیاتی)")
    print("="*100)
    
    try:
        result5 = await rag_system.retrieve_and_answer(
            query="شماره 110000 چیست؟",
            collection_name="budget_accurate_analysis",
            top_k=10
        )
        
        print("📊 پاسخ:")
        print(f"{result5.get('answer', 'پاسخ یافت نشد')[:800]}")
        
    except Exception as e:
        print(f"❌ خطا در تست 5: {e}")
    
    # تست 6: شماره 110100 چیست؟ (انتظار: بند اول: مالیات اشخاص حقوقی)
    print("\n❓ Test 6: شماره 110100 چیست؟ (انتظار: بند اول: مالیات اشخاص حقوقی)")
    print("="*100)
    
    try:
        result6 = await rag_system.retrieve_and_answer(
            query="شماره 110100 چیست؟",
            collection_name="budget_accurate_analysis",
            top_k=10
        )
        
        print("📊 پاسخ:")
        print(f"{result6.get('answer', 'پاسخ یافت نشد')[:800]}")
        
    except Exception as e:
        print(f"❌ خطا در تست 6: {e}")
    
    # تست 7: ساختار کلی سند چیست؟
    print("\n❓ Test 7: ساختار کلی سند چیست؟")
    print("="*100)
    
    try:
        result7 = await rag_system.retrieve_and_answer(
            query="ساختار کلی سند چیست؟",
            collection_name="budget_accurate_analysis",
            top_k=15
        )
        
        print("📊 پاسخ:")
        print(f"{result7.get('answer', 'پاسخ یافت نشد')[:1000]}")
        
    except Exception as e:
        print(f"❌ خطا در تست 7: {e}")

if __name__ == "__main__":
    asyncio.run(test_accurate_system())
