#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Final Fix - تست نهایی با سوال اصلی کاربر
"""

import asyncio
from loguru import logger
from ultimate_rag_system import UltimateRAGSystem

async def test_final_fix():
    """Test with user's original question"""
    logger.info("🧪 Testing with Original User Question...")
    
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    # سوال اصلی کاربر
    query = "110103 راجع به چیه ؟"
    
    logger.info("\n" + "="*80)
    logger.info(f"❓ سوال: {query}")
    logger.info("="*80)
    
    response = await rag_system.retrieve_and_answer(query, collection_name="jadval5-bodje")
    
    if response.get('success'):
        answer = response.get('answer', '')
        logger.info(f"\n✅ پاسخ:\n{answer}\n")
        
        # بررسی صحت پاسخ
        logger.info("=" * 80)
        logger.info("📊 بررسی صحت پاسخ:")
        logger.info("=" * 80)
        
        correct_title = "مالیات عملکرد شرکتهای دولتی"
        
        if correct_title in answer:
            logger.info(f"✅ پاسخ صحیح است! عنوان '{correct_title}' در پاسخ یافت شد.")
        else:
            logger.error(f"❌ پاسخ نادرست! عنوان '{correct_title}' در پاسخ یافت نشد.")
        
        # بررسی عدم وجود اشتباهات قبلی
        wrong_phrases = [
            "در متن ارائه‌شده نیامده",
            "اطلاعات دقیق مربوط به آن",
            "در دسترس نیست",
            "نیاز به ادامه متن جدول",
            "سطر 7",
            "سطر 8"
        ]
        
        has_errors = False
        for phrase in wrong_phrases:
            if phrase in answer:
                logger.warning(f"⚠️ عبارت نادرست '{phrase}' در پاسخ یافت شد!")
                has_errors = True
        
        if not has_errors:
            logger.info("✅ پاسخ عاری از اشتباهات قبلی است!")
        
    else:
        logger.error(f"❌ خطا: {response.get('error', '')}")
    
    # تست‌های اضافی
    logger.info("\n" + "="*80)
    logger.info("📊 تست‌های اضافی:")
    logger.info("="*80)
    
    additional_tests = [
        ("110103", "مالیات عملکرد شرکتهای دولتی"),
        ("110102", "یک دوازدهم رقم مالیات علی الحساب"),
        ("110309", "درآمد حاصل از مالیات بر واحدهای مسکونی خالی از سکنه"),
        ("110205", "مالیاتهای متفرقه درآمد"),
    ]
    
    all_passed = True
    for code, expected_title in additional_tests:
        query = f"{code} راجع به چیه؟"
        response = await rag_system.retrieve_and_answer(query, collection_name="jadval5-bodje")
        
        if response.get('success'):
            answer = response.get('answer', '')
            if expected_title in answer:
                logger.info(f"✅ {code}: صحیح - '{expected_title[:40]}...'")
            else:
                logger.error(f"❌ {code}: نادرست - عنوان مورد انتظار یافت نشد")
                all_passed = False
        else:
            logger.error(f"❌ {code}: خطا در دریافت پاسخ")
            all_passed = False
    
    logger.info("\n" + "="*80)
    if all_passed:
        logger.info("🎉 تمام تست‌ها موفق بود!")
    else:
        logger.error("❌ برخی تست‌ها ناموفق بودند")
    logger.info("="*80)

if __name__ == "__main__":
    asyncio.run(test_final_fix())

