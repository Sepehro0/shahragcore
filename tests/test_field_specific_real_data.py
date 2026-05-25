# -*- coding: utf-8 -*-
"""
Test Field-Specific Answer with Real Data
تست با داده‌های واقعی که کاربر داده
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.field_specific_answer_generator import get_field_answer_generator
from services.result_fusion import ResultFusion


def test_real_data():
    """تست با داده‌های واقعی"""
    print("=" * 80)
    print("🧪 Test with Real Data from User")
    print("=" * 80)
    
    # داده‌های واقعی از کاربر
    user_query = "اعتبارات هزینه ای عمومی دانشگاه هنر شیراز در سال 1403 چقدر بوده است؟"
    
    # نتایج واقعی دیتابیس
    database_results = {
        "success": True,
        "sql": "SELECT SUM(COALESCE(CAST(\"براورد_اعتبارات_هزینه_ای_عمومی\" AS DOUBLE PRECISION), 0)) AS total_amount FROM masaref2_sheet1 WHERE ...",
        "results": [
            {
                "total_amount": 418235.0  # ❌ این اشتباه است! (جمع_کل)
            }
        ],
        "count": 1,
        "columns": ["total_amount"],
        "detail_rows": [
            {
                "عنوان_دستگاه_اصلي": "وزارت علوم ، تحقيقات و فناوري",
                "کد_دستگاه_اجرايي": "115103",
                "عنوان_دستگاه_اجرايي": "دانشگاه هنر شيراز",
                "براورد_اعتبارات_هزینه_ای_عمومی": "252220",  # ✅ این صحیح است!
                "برآورد_اعتبارات_هزینه_ای_متفرقه": "0.0",
                "براورد_اعتبارات_هزینه_ای_اختصاصی": "28950.0",
                "جمع_براورد_اعتبارات_هزینه_ای": "281170.0",  # ✅ این هم صحیح است!
                "براورد_اعتبارات_هزینه_ای_یارانه_ها": None,
                "براورد_تملك_دارايي_هاي_سرمايه_اي_ع": "137065",
                "براورد_تملك_دارايي_هاي_سرمايه_اي_م": "0.0",
                "براورد_تملك_دارايي_هاي_سرمايه_اي_ا": "0.0",
                "جمع_برآورد_تملك_دارايي_هاي_سرمايه_": "137065.0",
                "براورد_تملک_دارایی_های_سرمایه_ای_ی": None,
                "جمع_كل": "418235.0",  # ❌ این total_amount است
                "سال": "1403"
            }
        ],
        "detail_columns": [
            "عنوان_دستگاه_اصلي",
            "کد_دستگاه_اجرايي",
            "عنوان_دستگاه_اجرايي",
            "براورد_اعتبارات_هزینه_ای_عمومی",
            "برآورد_اعتبارات_هزینه_ای_متفرقه",
            "براورد_اعتبارات_هزینه_ای_اختصاصی",
            "جمع_براورد_اعتبارات_هزینه_ای",
            "براورد_اعتبارات_هزینه_ای_یارانه_ها",
            "براورد_تملك_دارايي_هاي_سرمايه_اي_ع",
            "براورد_تملك_دارايي_هاي_سرمايه_اي_م",
            "براورد_تملك_دارايي_هاي_سرمايه_اي_ا",
            "جمع_برآورد_تملك_دارايي_هاي_سرمايه_",
            "براورد_تملک_دارایی_های_سرمایه_ای_ی",
            "جمع_كل",
            "سال"
        ]
    }
    
    print(f"\n📝 Query: {user_query}")
    print(f"\n📊 Database Results:")
    print(f"   - results[0]['total_amount']: {database_results['results'][0]['total_amount']} (❌ اشتباه - جمع_کل)")
    print(f"   - detail_rows[0]['براورد_اعتبارات_هزینه_ای_عمومی']: {database_results['detail_rows'][0]['براورد_اعتبارات_هزینه_ای_عمومی']} (✅ صحیح)")
    print(f"   - detail_rows[0]['جمع_براورد_اعتبارات_هزینه_ای']: {database_results['detail_rows'][0]['جمع_براورد_اعتبارات_هزینه_ای']} (✅ صحیح)")
    print(f"   - detail_rows[0]['جمع_كل']: {database_results['detail_rows'][0]['جمع_كل']} (= total_amount)")
    
    # تست با ResultFusion
    result_fusion = ResultFusion()
    
    fused_results = {
        "success": True,
        "components": [
            {
                "type": "database",
                "content": "...",
                "database_results": database_results
            }
        ],
        "database_results": database_results
    }
    
    answer = result_fusion.create_simple_answer_from_results(
        user_query=user_query,
        fused_results=fused_results,
        collection_name='budget_financial'
    )
    
    print(f"\n✅ Generated Answer:\n")
    print(answer)
    print(f"\n" + "=" * 80)
    
    # بررسی صحت پاسخ
    if "252,220" in answer or "252220" in answer:
        print("✅ SUCCESS: پاسخ صحیح است! (252,220 میلیون ریال)")
    elif "281,170" in answer or "281170" in answer:
        print("⚠️ PARTIAL: پاسخ جمع اعتبارات هزینه‌ای را نشان می‌دهد (281,170)")
    elif "418,235" in answer or "418235" in answer:
        print("❌ FAILED: پاسخ هنوز جمع_کل را نشان می‌دهد (418,235)")
    else:
        print("⚠️ UNKNOWN: عدد مورد انتظار در پاسخ یافت نشد")
    
    print("=" * 80)


if __name__ == "__main__":
    print("\n" + "🚀 " * 20)
    print("Field-Specific Answer Test with Real Data")
    print("🚀 " * 20 + "\n")
    
    try:
        test_real_data()
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()

