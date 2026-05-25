# -*- coding: utf-8 -*-
"""
تست یکپارچگی برای budget_financial collection
بر اساس test cases پیشنهادی در plan
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.budget_query_processor import (
    BudgetQueryProcessor, 
    BudgetTableDetector, 
    BudgetYearHandler,
    BudgetHierarchySearcher,
    BudgetResponseFormatter,
    TableType
)
from services.query_analyzer import QueryAnalyzer


def test_table_detection():
    """تست تشخیص نوع جدول"""
    print("\n" + "="*60)
    print("🧪 تست تشخیص نوع جدول (Table Detection)")
    print("="*60)
    
    detector = BudgetTableDetector()
    
    test_cases = [
        # MASAREF cases
        ("بودجه وزارت بهداشت 1401", "masaref"),
        ("اعتبارات دستگاه قضایی", "masaref"),
        ("هزینه جاری فراجا", "masaref"),
        ("برآورد تملک دارایی سرمایه‌ای", "masaref"),
        
        # MANABE cases
        ("درآمد عمرانی سال 98", "manabe"),
        ("منابع درآمدی وزارت نفت", "manabe"),
        ("واگذاری دارایی‌های مالی", "manabe"),
        
        # Mixed/Ambiguous
        ("بودجه سال 1403", "masaref"),  # پیش‌فرض
    ]
    
    passed = 0
    for query, expected in test_cases:
        table_type, confidence, reason = detector.detect_table(query)
        result = table_type.value
        status = "✅" if result == expected else "❌"
        if result == expected:
            passed += 1
        print(f"{status} Query: '{query[:40]}...' -> {result} (expected: {expected}, confidence: {confidence:.2f})")
    
    print(f"\n📊 نتیجه: {passed}/{len(test_cases)} تست موفق")
    return passed == len(test_cases)


def test_year_extraction():
    """تست استخراج و نرمال‌سازی سال"""
    print("\n" + "="*60)
    print("🧪 تست استخراج سال (Year Extraction)")
    print("="*60)
    
    handler = BudgetYearHandler()
    
    test_cases = [
        ("بودجه سال 98", ["1398"]),
        ("درآمد 1401", ["1401"]),
        ("هزینه 400", ["1400"]),
        ("بودجه 01", ["1401"]),
        ("مقایسه 1399 تا 1401", ["1399", "1400", "1401"]),
        ("بودجه امسال", ["1403"]),  # پیش‌فرض
    ]
    
    passed = 0
    for query, expected in test_cases:
        years = handler.extract_years(query)
        status = "✅" if years == expected else "❌"
        if years == expected:
            passed += 1
        print(f"{status} Query: '{query}' -> {years} (expected: {expected})")
    
    print(f"\n📊 نتیجه: {passed}/{len(test_cases)} تست موفق")
    return passed == len(test_cases)


def test_subsidy_rules():
    """تست قوانین یارانه"""
    print("\n" + "="*60)
    print("🧪 تست قوانین یارانه (Subsidy Rules)")
    print("="*60)
    
    handler = BudgetYearHandler()
    
    test_cases = [
        ("1399", "separate"),
        ("1400", "separate"),
        ("1401", "include"),
        ("1402", "none"),
        ("1403", "none"),
    ]
    
    passed = 0
    for year, expected in test_cases:
        rule = handler.get_subsidy_rule(year)
        status = "✅" if rule == expected else "❌"
        if rule == expected:
            passed += 1
        print(f"{status} Year: {year} -> Rule: {rule} (expected: {expected})")
    
    print(f"\n📊 نتیجه: {passed}/{len(test_cases)} تست موفق")
    return passed == len(test_cases)


def test_hierarchy_detection():
    """تست تشخیص سطح سلسله‌مراتبی"""
    print("\n" + "="*60)
    print("🧪 تست تشخیص سطح سلسله‌مراتبی (Hierarchy Detection)")
    print("="*60)
    
    searcher = BudgetHierarchySearcher()
    
    test_cases = [
        ("بودجه قسمت امور اقتصادی", "قسمت"),
        ("هزینه بخش آموزش", "بخش"),
        ("اعتبارات بند ج", "بند"),
        ("بودجه دستگاه اجرایی وزارت بهداشت", "دستگاه اجرایی"),
        ("جزء یک تبصره 5", "جزء"),  # تست جزء بدون بند
        ("بودجه وزارت نفت", "دستگاه"),  # دستگاه عمومی
    ]
    
    passed = 0
    for query, expected in test_cases:
        level = searcher.detect_hierarchy_level(query)
        status = "✅" if level == expected else "❌"
        if level == expected:
            passed += 1
        print(f"{status} Query: '{query[:40]}...' -> Level: {level} (expected: {expected})")
    
    print(f"\n📊 نتیجه: {passed}/{len(test_cases)} تست موفق")
    return passed == len(test_cases)


def test_query_analyzer_budget():
    """تست QueryAnalyzer برای budget queries"""
    print("\n" + "="*60)
    print("🧪 تست QueryAnalyzer برای budget queries")
    print("="*60)
    
    analyzer = QueryAnalyzer()
    
    test_cases = [
        "بودجه وزارت بهداشت 1401",
        "درآمد عمرانی سال 98",
        "هزینه جاری فراجا",
        "اعتبارات دستگاه قضایی",
        "یارانه‌های سال 1400",
    ]
    
    for query in test_cases:
        print(f"\n📝 Query: '{query}'")
        
        # تست تشخیص جدول
        table_result = analyzer.detect_budget_table_type(query)
        print(f"   📊 Table Type: {table_result['table_type']} (confidence: {table_result['confidence']:.2f})")
        
        # تست تشخیص سطح
        hierarchy = analyzer.detect_hierarchy_level(query)
        print(f"   📊 Hierarchy: {hierarchy['level']} (column: {hierarchy['column_name']})")
        
        # تست تشخیص نوع هزینه
        cost_type = analyzer.detect_cost_type(query)
        print(f"   📊 Cost Type: {cost_type['cost_type']}")
        
        # تست تحلیل کامل
        full_analysis = analyzer.analyze_budget_query(query)
        print(f"   📊 Years: {full_analysis['years']}")
        print(f"   📊 Subsidy Rule: {full_analysis['subsidy_rule']['rule']}")
    
    return True


def test_response_formatter():
    """تست فرمت‌دهی پاسخ"""
    print("\n" + "="*60)
    print("🧪 تست فرمت‌دهی پاسخ (Response Formatter)")
    print("="*60)
    
    formatter = BudgetResponseFormatter()
    
    # داده نمونه MASAREF
    masaref_data = {
        'level': 'دستگاه اجرایی',
        'cost_public': 1000000000,
        'cost_misc': 500000000,
        'cost_special': 200000000,
        'cost_total': 1700000000,
        'capital_public': 800000000,
        'capital_misc': 300000000,
        'capital_special': 100000000,
        'capital_total': 1200000000,
        'grand_total': 2900000000
    }
    
    response = formatter.format_masaref_response(
        entity_name="وزارت بهداشت",
        year="1401",
        data=masaref_data,
        subsidy_rule='include'
    )
    
    print("📄 پاسخ MASAREF:")
    print("-" * 40)
    print(response)
    print("-" * 40)
    
    # داده نمونه MANABE
    manabe_data = {
        'public_national': 500000000,
        'public_provincial': 300000000,
        'public_total': 800000000,
        'special_national': 200000000,
        'special_provincial': 100000000,
        'special_total': 300000000,
        'grand_total': 1100000000
    }
    
    response = formatter.format_manabe_response(
        entity_name="وزارت نفت",
        year="1402",
        data=manabe_data
    )
    
    print("\n📄 پاسخ MANABE:")
    print("-" * 40)
    print(response)
    print("-" * 40)
    
    # تست پاسخ عدم یافتن نتیجه
    not_found = formatter.format_not_found_response(
        query="بودجه سازمان ناشناخته",
        table_type=TableType.MASAREF,
        searched_keywords=["سازمان ناشناخته"],
        year="1403",
        searched_levels=["دستگاه اجرایی", "دستگاه اصلی"]
    )
    
    print("\n📄 پاسخ عدم یافتن نتیجه:")
    print("-" * 40)
    print(not_found)
    print("-" * 40)
    
    return True


def test_budget_processor():
    """تست BudgetQueryProcessor"""
    print("\n" + "="*60)
    print("🧪 تست BudgetQueryProcessor")
    print("="*60)
    
    processor = BudgetQueryProcessor()
    
    test_queries = [
        "بودجه وزارت بهداشت 1401",
        "درآمد عمرانی سال 98",
        "هزینه جاری فراجا",
        "اعتبارات دستگاه قضایی",
        "یارانه‌های سال 1400",
        "مقایسه بودجه 1399 تا 1401",
        "تملک دارایی سرمایه‌ای وزارت نیرو",
        "منابع درآمدی استانی"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        analysis = processor.analyze_query(query)
        
        print(f"   📊 Table Type: {analysis.table_type.value}")
        print(f"   📊 Years: {analysis.years}")
        print(f"   📊 Hierarchy: {analysis.hierarchy_level}")
        print(f"   📊 Cost Type: {analysis.cost_type}")
        print(f"   📊 Income Type: {analysis.income_type}")
        print(f"   📊 Subsidy Rule: {analysis.subsidy_rule}")
        print(f"   📊 Confidence: {analysis.confidence:.2f}")
        
        # تست get_target_table
        target_table = processor.get_target_table(analysis)
        print(f"   📊 Target Table: {target_table}")
    
    return True


def run_all_tests():
    """اجرای همه تست‌ها"""
    print("\n" + "="*60)
    print("🚀 شروع تست‌های یکپارچگی budget_financial")
    print("="*60)
    
    results = {}
    
    # تست‌های واحد
    results['table_detection'] = test_table_detection()
    results['year_extraction'] = test_year_extraction()
    results['subsidy_rules'] = test_subsidy_rules()
    results['hierarchy_detection'] = test_hierarchy_detection()
    
    # تست‌های یکپارچگی
    results['query_analyzer'] = test_query_analyzer_budget()
    results['response_formatter'] = test_response_formatter()
    results['budget_processor'] = test_budget_processor()
    
    # خلاصه نتایج
    print("\n" + "="*60)
    print("📊 خلاصه نتایج تست‌ها")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print(f"\n🎯 نتیجه کلی: {passed}/{total} تست موفق")
    
    if passed == total:
        print("✅ همه تست‌ها با موفقیت پاس شدند!")
    else:
        print("❌ برخی تست‌ها ناموفق بودند.")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

