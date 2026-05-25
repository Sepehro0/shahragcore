# -*- coding: utf-8 -*-
"""
Test Field-Specific Answer Generation
تست تولید پاسخ بر اساس فیلد خاص
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.field_specific_answer_generator import get_field_answer_generator
from config.collection_instructions import CollectionInstructions


def test_field_detection():
    """تست تشخیص فیلد از query"""
    print("=" * 80)
    print("🧪 Test 1: Field Detection")
    print("=" * 80)
    
    generator = get_field_answer_generator()
    
    test_queries = [
        "اعتبارات هزینه ای عمومی دانشگاه هنر شیراز در سال 1403 چقدر بوده است؟",
        "تملک دارایی سرمایه ای عمومی دانشگاه تهران چقدر است؟",
        "اعتبارات هزینه ای اختصاصی وزارت علوم در سال 1402",
        "جمع اعتبارات هزینه ای دانشگاه امیرکبیر",
        "بودجه کل دانشگاه صنعتی شریف",
    ]
    
    for query in test_queries:
        detected_field = generator.detect_requested_field(query, 'budget_financial')
        display_name = generator.get_field_display_name(detected_field)
        print(f"\n📝 Query: {query}")
        print(f"   ✅ Detected Field: {detected_field}")
        print(f"   📊 Display Name: {display_name}")


def test_field_extraction():
    """تست استخراج مقدار فیلد از row"""
    print("\n" + "=" * 80)
    print("🧪 Test 2: Field Value Extraction")
    print("=" * 80)
    
    generator = get_field_answer_generator()
    
    # Mock row data
    test_row = {
        'عنوان_دستگاه_اجرایی': 'دانشگاه هنر شیراز',
        'سال': '1403',
        'براورد_اعتبارات_هزینه_ای_عمومی': 418235,
        'جمع_براورد_اعتبارات_هزینه_ای': 850000,
        'جمع_كل': 1200000,
        'total_amount': 1200000
    }
    
    fields_to_test = [
        'براورد_اعتبارات_هزینه_ای_عمومی',
        'جمع_براورد_اعتبارات_هزینه_ای',
        'جمع_كل'
    ]
    
    print(f"\n📦 Test Row: {test_row['عنوان_دستگاه_اجرایی']} - {test_row['سال']}")
    
    for field in fields_to_test:
        value = generator.extract_field_value_from_row(test_row, field)
        display_name = generator.get_field_display_name(field)
        print(f"\n   🔍 Field: {display_name}")
        print(f"      Value: {value:,} میلیون ریال" if value else "      Value: Not Found")


def test_answer_formatting():
    """تست فرمت کردن پاسخ"""
    print("\n" + "=" * 80)
    print("🧪 Test 3: Answer Formatting")
    print("=" * 80)
    
    generator = get_field_answer_generator()
    
    # Mock database results
    mock_results = {
        'success': True,
        'rows': [{
            'عنوان_دستگاه_اجرایی': 'دانشگاه هنر شیراز',
            'سال': '1403',
            'براورد_اعتبارات_هزینه_ای_عمومی': 418235,
            'جمع_براورد_اعتبارات_هزینه_ای': 850000,
            'جمع_كل': 1200000,
            'total_amount': 418235  # این از SQL می‌آید
        }]
    }
    
    test_query = "اعتبارات هزینه ای عمومی دانشگاه هنر شیراز در سال 1403 چقدر بوده است؟"
    
    answer = generator.format_answer_with_specific_field(
        user_query=test_query,
        database_results=mock_results,
        collection_name='budget_financial'
    )
    
    print(f"\n📝 Query: {test_query}")
    print(f"\n✅ Generated Answer:\n{answer}")


def test_collection_instructions():
    """تست detect_target_column از CollectionInstructions"""
    print("\n" + "=" * 80)
    print("🧪 Test 4: CollectionInstructions.detect_target_column")
    print("=" * 80)
    
    test_queries = [
        "اعتبارات هزینه ای عمومی دانشگاه هنر شیراز در سال 1403",
        "تملک دارایی سرمایه ای متفرقه",
        "اعتبارات هزینه ای اختصاصی",
        "جمع اعتبارات هزینه ای",
        "بودجه کل",
    ]
    
    for query in test_queries:
        target_column = CollectionInstructions.detect_target_column(query, 'budget_financial')
        print(f"\n📝 Query: {query}")
        print(f"   ✅ Target Column: {target_column}")


def test_enhance_database_results():
    """تست بهبود نتایج دیتابیس"""
    print("\n" + "=" * 80)
    print("🧪 Test 5: Enhance Database Results")
    print("=" * 80)
    
    generator = get_field_answer_generator()
    
    mock_results = {
        'success': True,
        'rows': [
            {
                'عنوان_دستگاه_اجرایی': 'دانشگاه هنر شیراز',
                'سال': '1403',
                'براورد_اعتبارات_هزینه_ای_عمومی': 418235,
                'total_amount': 418235
            }
        ]
    }
    
    test_query = "اعتبارات هزینه ای عمومی دانشگاه هنر شیراز در سال 1403"
    
    enhanced = generator.enhance_database_results(
        user_query=test_query,
        database_results=mock_results,
        collection_name='budget_financial'
    )
    
    print(f"\n📝 Query: {test_query}")
    print(f"\n✅ Enhanced Results:")
    print(f"   - Requested Field: {enhanced.get('requested_field')}")
    print(f"   - Display Name: {enhanced.get('requested_field_display')}")
    print(f"   - Field Values: {enhanced.get('field_values')}")
    print(f"   - Field Total: {enhanced.get('field_total'):,}" if enhanced.get('field_total') else "   - Field Total: N/A")


if __name__ == "__main__":
    print("\n" + "🚀 " * 20)
    print("Field-Specific Answer Generation Tests")
    print("🚀 " * 20 + "\n")
    
    try:
        test_field_detection()
        test_field_extraction()
        test_answer_formatting()
        test_collection_instructions()
        test_enhance_database_results()
        
        print("\n" + "=" * 80)
        print("✅ All Tests Completed Successfully!")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()

