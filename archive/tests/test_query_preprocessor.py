#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست Query Preprocessor
"""

import sys
import asyncio
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system")

from services.query_preprocessor import QueryPreprocessor

def test_preprocessor():
    """تست Query Preprocessor"""
    preprocessor = QueryPreprocessor()
    
    print("=" * 60)
    print("🧪 تست Query Preprocessor")
    print("=" * 60)
    
    # تست 1: سلام
    print("\n1️⃣ تست سلام:")
    test_queries = [
        "سلام",
        "سلام علیک",
        "سلام علیکم",
        "سلام علیکم السلام",
        "سلام چطوری",
        "سلام خوبی",
        "صبح بخیر",
        "درود"
    ]
    
    for query in test_queries:
        result = preprocessor.preprocess(query)
        status = "✅" if result['is_greeting'] else "❌"
        print(f"  {status} '{query}' -> is_greeting: {result['is_greeting']}")
    
    # تست 2: سوالات نامرتبط
    print("\n2️⃣ تست سوالات نامرتبط:")
    irrelevant_queries = [
        "هوا چطوره؟",
        "امروز چه خبر؟",
        "فوتبال چی شد؟",
        "فیلم جدید چی دیدی؟",
        "کتاب خوبی می‌شناسی؟"
    ]
    
    for query in irrelevant_queries:
        result = preprocessor.preprocess(query)
        status = "✅" if result['is_irrelevant'] else "❌"
        print(f"  {status} '{query}' -> is_irrelevant: {result['is_irrelevant']}")
    
    # تست 3: تبدیل "منابع" به "درآمد"
    print("\n3️⃣ تست تبدیل 'منابع' به 'درآمد':")
    source_queries = [
        "منابع انستیتو پاستور چقدر است؟",
        "جمع کل منابع در سال 1401",
        "منابع اختصاصی دستگاه‌ها",
        "منبع درآمد سازمان چقدر است؟"
    ]
    
    for query in source_queries:
        result = preprocessor.preprocess(query)
        has_income = 'درآمد' in result['processed_query']
        status = "✅" if has_income else "❌"
        print(f"  {status} '{query}' -> '{result['processed_query']}'")
    
    # تست 4: تبدیل "مصارف" به "هزینه"
    print("\n4️⃣ تست تبدیل 'مصارف' به 'هزینه':")
    expense_queries = [
        "مصارف انستیتو پاستور چقدر است؟",
        "جمع کل مصارف در سال 1401",
        "مصارف اختصاصی دستگاه‌ها",
        "مصرف هزینه سازمان چقدر است؟"
    ]
    
    for query in expense_queries:
        result = preprocessor.preprocess(query)
        has_expense = 'هزینه' in result['processed_query']
        status = "✅" if has_expense else "❌"
        print(f"  {status} '{query}' -> '{result['processed_query']}'")
    
    # تست 5: سوالات مرتبط (نباید فیلتر شوند)
    print("\n5️⃣ تست سوالات مرتبط (نباید فیلتر شوند):")
    relevant_queries = [
        "انستیتو پاستور در سال 1401 چقدر درآمد داشته است؟",
        "جمع کل هزینه‌های دستگاه‌ها",
        "بودجه سازمان برنامه و بودجه",
        "درآمد اختصاصی دستگاه‌ها چقدر است؟"
    ]
    
    for query in relevant_queries:
        result = preprocessor.preprocess(query)
        should_process = result['should_process']
        status = "✅" if should_process else "❌"
        print(f"  {status} '{query}' -> should_process: {should_process}")
    
    print("\n" + "=" * 60)
    print("✅ تست‌ها کامل شد!")
    print("=" * 60)

if __name__ == "__main__":
    test_preprocessor()

