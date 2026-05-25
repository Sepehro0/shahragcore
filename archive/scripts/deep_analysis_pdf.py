#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تحلیل عمیق PDF - بررسی دقیق ساختار واقعی
"""

import sys
import os
import asyncio
import logging
import warnings
import re
from typing import Dict, List, Any

# اضافه کردن مسیر سیستم
sys.path.insert(0, '/home/user01/qwen-api/enhanced_rag_system')

# غیرفعال کردن warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# تنظیم logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def deep_analysis_pdf():
    """تحلیل عمیق PDF برای درک ساختار واقعی"""
    
    print("🔍 تحلیل عمیق PDF برای درک ساختار واقعی...")
    
    try:
        from ultimate_rag_system import UltimateRAGSystem
        
        # راه‌اندازی سیستم
        rag_system = UltimateRAGSystem(
            enable_semantic_chunking=False,  # غیرفعال برای تحلیل دقیق‌تر
            enable_query_understanding=False,
            enable_advanced_retrieval=False,
            retrieval_strategy='simple'
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
        
        # پردازش PDF
        print("🔄 شروع پردازش PDF...")
        
        result = await rag_system.process_pdf_advanced(
            file_bytes=pdf_bytes,
            filename='jadval5-bodje.pdf',
            collection_name='budget_deep_analysis'
        )
        
        print(f"✅ نتیجه پردازش:")
        print(f"   - موفقیت: {result.get('success', False)}")
        print(f"   - تعداد chunks: {result.get('chunks_count', 0)}")
        
        if result.get('success'):
            print("🎉 پردازش PDF موفقیت‌آمیز بود!")
            
            # تحلیل عمیق ساختار
            await deep_analyze_structure(rag_system)
        else:
            print(f"❌ پردازش PDF ناموفق: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ خطا در راه‌اندازی سیستم: {e}")
        import traceback
        traceback.print_exc()

async def deep_analyze_structure(rag_system):
    """تحلیل عمیق ساختار سند"""
    
    print("\n" + "="*100)
    print("🔍 تحلیل عمیق ساختار سند...")
    print("="*100)
    
    # جستجوی دقیق ساختار
    structure_queries = [
        "قسمت اول درآمدها",
        "بخش اول درآمدهای مالیاتی",
        "بخش دوم درآمدهای ناشی از کمکهای اجتماعی",
        "بخش سوم درآمدهای حاصل از مالکیت دولت",
        "بخش چهارم درآمدهای حاصل از فروش کالاها و خدمات",
        "بخش پنجم درآمدهای حاصل از جرایم و خسارات",
        "بخش ششم درآمدهای متفرقه",
        "100000",
        "110000",
        "120000",
        "130000",
        "140000",
        "150000",
        "160000"
    ]
    
    for query in structure_queries:
        try:
            result = await rag_system.retrieve_and_answer(
                query=query,
                collection_name="budget_deep_analysis",
                top_k=5
            )
            
            print(f"\n🔍 جستجو برای: '{query}'")
            print(f"📊 پاسخ: {result.get('answer', 'پاسخ یافت نشد')[:300]}...")
            
            # نمایش منابع
            if result.get('top_results'):
                print("📋 منابع:")
                for i, source in enumerate(result.get('top_results', [])[:2]):
                    text = source.get('text', '')
                    print(f"   {i+1}. {text[:200]}...")
            
        except Exception as e:
            print(f"❌ خطا در جستجوی {query}: {e}")
    
    # جستجوی ساختار کلی
    print("\n\n🌳 جستجوی ساختار کلی:")
    print("-" * 50)
    
    try:
        result = await rag_system.retrieve_and_answer(
            query="ساختار کامل سند با تمام قسمت‌ها و بخش‌ها و بندها",
            collection_name="budget_deep_analysis",
            top_k=10
        )
        
        print(f"📊 پاسخ: {result.get('answer', 'پاسخ یافت نشد')}")
        
    except Exception as e:
        print(f"❌ خطا در جستجوی ساختار کلی: {e}")

if __name__ == "__main__":
    asyncio.run(deep_analysis_pdf())
