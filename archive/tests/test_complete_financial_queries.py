#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست کامل سوالات مالی - ذخیره نتایج در JSON
"""

import sys
sys.path.insert(0, '/home/user01/qwen-api/enhanced_rag_system_dev')

import requests
import json
from datetime import datetime
import time
import os

base_url = "http://localhost:8010"
collection_name = "budget_financial"

# تمام سوالات تست مالی
test_cases = [
    # Category 1a: ارجاع یک سلول خاص - مصارف
    {
        "id": "1a-1",
        "category": "1a. ارجاع یک سلول خاص - مصارف",
        "query": "اعتبارات هزینه‌ای متفرقه ستاد مبارزه با مواد مخدر در سال 1403",
        "expected_column": "برآورد_اعتبارات_هزینه_ای_متفرقه",
        "expected_entity": "ستاد مبارزه با مواد مخدر",
        "expected_year": "1403"
    },
    {
        "id": "1a-2",
        "category": "1a. ارجاع یک سلول خاص - مصارف",
        "query": "اعتبارات هزینه ای عمومی بنیاد ایران شناسی در سال 1403",
        "expected_column": "براورد_اعتبارات_هزینه_ای_عمومی",
        "expected_entity": "بنیاد ایران شناسی",
        "expected_year": "1403"
    },
    {
        "id": "1a-3",
        "category": "1a. ارجاع یک سلول خاص - مصارف",
        "query": "اعتبارات هزینه ای اختصاصی هیات عالی گزینش در سال 1403",
        "expected_column": "براورد_اعتبارات_هزینه_ای_اختصاصی",
        "expected_entity": "هیات عالی گزینش",
        "expected_year": "1403"
    },
    {
        "id": "1a-4",
        "category": "1a. ارجاع یک سلول خاص - مصارف",
        "query": "تملک دارایی سرمایه ای عمومی معاونت علمی و فناوری در سال 1403",
        "expected_column": "براورد_تملك_دارايي_هاي_سرمايه_اي_ع",
        "expected_entity": "معاونت علمي ، فناوري  و اقتصاد دانش بنيان رييس جمهور",
        "expected_year": "1403",
        "note": "عنوان دقیق: معاونت علمي ، فناوري  و اقتصاد دانش بنيان رييس جمهور"
    },
    {
        "id": "1a-5",
        "category": "1a. ارجاع یک سلول خاص - مصارف",
        "query": "تملک دارایی سرمایه ای متفرقه سازمان سنجش بند ج در سال 1403",
        "expected_column": "براورد_تملك_دارايي_هاي_سرمايه_اي_م",
        "expected_entity": "سازمان سنجش آموزش كشور موضوع بند\"ج\" تبصره 49 قانون بودجه سال 1364 كل كشور",
        "expected_year": "1403",
        "note": "عنوان دقیق: سازمان سنجش آموزش كشور موضوع بند\"ج\" تبصره 49 قانون بودجه سال 1364 كل كشور"
    },
    # Category 2a: جمع
    {
        "id": "2a-1",
        "category": "2a. جمع",
        "query": "بودجه فرهنگستان هنر در سال 1403",
        "expected_column": "جمع_كل",
        "expected_entity": "فرهنگستان هنر",
        "expected_year": "1403"
    },
    {
        "id": "2a-2",
        "category": "2a. جمع",
        "query": "اعتبارات هزینه ای نهاد ریاست جمهوری در سال 1403",
        "expected_column": "جمع_براورد_اعتبارات_هزینه_ای",
        "expected_entity": "نهاد ریاست جمهوری",
        "expected_year": "1403"
    },
    {
        "id": "2a-3",
        "category": "2a. جمع",
        "query": "درآمدهای وزارت نفت در سال 1401 چقدر است",
        "expected_table": "incomes_sheet1",
        "expected_entity": "وزارت نفت",
        "expected_year": "1401"
    },
    {
        "id": "2a-4",
        "category": "2a. جمع",
        "query": "بودجه دانشگاه تهران",
        "expected_column": "جمع_كل",
        "expected_entity": "دانشگاه تهران",
        "expected_year": "1403",
        "note": "بدون سال - باید سال 1403 در نظر گرفته شود و هم دستگاه اصلی و هم اجرایی"
    },
    # Category 2b: درآمدها
    {
        "id": "2b-1",
        "category": "2b. درآمدها",
        "query": "درامد استانی اختصاصی دانشگاه تبریز در سال 1403",
        "expected_table": "incomes_sheet1",
        "expected_entity": "دانشگاه تبریز",
        "expected_year": "1403",
        "expected_income_type": "استانی اختصاصی"
    },
    {
        "id": "2b-2",
        "category": "2b. درآمدها",
        "query": "درامد ملی سازمان تامین اجتماعی در سال 1403",
        "expected_table": "incomes_sheet1",
        "expected_entity": "سازمان تامین اجتماعی",
        "expected_year": "1403",
        "expected_income_type": "ملی"
    },
    {
        "id": "2b-3",
        "category": "2b. درآمدها",
        "query": "درامد کل موسسه کار و تامین اجتماعی در سال 1402",
        "expected_table": "incomes_sheet1",
        "expected_entity": "موسسه کار و تامین اجتماعی",
        "expected_year": "1402",
        "expected_income_type": "کل"
    },
]

def test_query(test_case):
    """تست یک query و برگرداندن نتیجه"""
    query = test_case["query"]
    
    print(f"\n{'='*80}")
    print(f"Test ID: {test_case['id']}")
    print(f"Category: {test_case['category']}")
    print(f"Query: {query}")
    print(f"{'='*80}")
    
    try:
        response = requests.post(
            f"{base_url}/query",
            json={
                "query": query,
                "collection_name": collection_name,
                "top_k": 5,
                "use_reranking": True,
                "use_multi_hop": False
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # استخراج اطلاعات مهم
            test_result = {
                "test_id": test_case["id"],
                "category": test_case["category"],
                "query": query,
                "success": result.get("success", False),
                "answer": result.get("answer", ""),
                "answer_length": len(result.get("answer", "")),
                "confidence": result.get("confidence", 0.0),
                "processing_time": result.get("processing_time", 0.0),
                "metadata": result.get("metadata", {}),
                "sources_count": len(result.get("sources", [])),
                "used_features": result.get("used_features", {}),
                "error": result.get("error"),
                "has_database_results": False,
                "database_rows": 0,
                "sql_query": None
            }
            
            # استخراج اطلاعات database
            metadata = result.get("metadata", {})
            database_results = metadata.get("database_results")
            
            if database_results:
                test_result["has_database_results"] = True
                test_result["database_rows"] = len(database_results.get("rows", []))
                test_result["sql_query"] = database_results.get("prepared_sql") or database_results.get("sql")
            
            # مقایسه با expected values
            test_result["expected"] = {
                "entity": test_case.get("expected_entity"),
                "year": test_case.get("expected_year"),
                "column": test_case.get("expected_column"),
                "table": test_case.get("expected_table"),
                "income_type": test_case.get("expected_income_type")
            }
            
            print(f"✅ SUCCESS")
            print(f"   Answer length: {test_result['answer_length']} chars")
            print(f"   Confidence: {test_result['confidence']}")
            print(f"   Database rows: {test_result['database_rows']}")
            
            return test_result
            
        else:
            error_msg = f"HTTP {response.status_code}"
            try:
                error_detail = response.json().get("detail", "")
                error_msg += f": {error_detail}"
            except:
                error_msg += f": {response.text[:200]}"
            
            print(f"❌ FAILED: {error_msg}")
            
            return {
                "test_id": test_case["id"],
                "category": test_case["category"],
                "query": query,
                "success": False,
                "error": error_msg,
                "expected": {
                    "entity": test_case.get("expected_entity"),
                    "year": test_case.get("expected_year"),
                    "column": test_case.get("expected_column"),
                    "table": test_case.get("expected_table"),
                    "income_type": test_case.get("expected_income_type")
                }
            }
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ EXCEPTION: {error_msg}")
        
        return {
            "test_id": test_case["id"],
            "category": test_case["category"],
            "query": query,
            "success": False,
            "error": error_msg,
            "expected": {
                "entity": test_case.get("expected_entity"),
                "year": test_case.get("expected_year"),
                "column": test_case.get("expected_column"),
                "table": test_case.get("expected_table"),
                "income_type": test_case.get("expected_income_type")
            }
        }

def main():
    """اجرای تست کامل"""
    print("="*80)
    print("🧪 تست کامل سوالات مالی")
    print(f"تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Collection: {collection_name}")
    print(f"API URL: {base_url}")
    print("="*80)
    
    results = []
    start_time = time.time()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}]")
        result = test_query(test_case)
        results.append(result)
        time.sleep(0.5)  # کمی delay برای جلوگیری از overload
    
    total_time = time.time() - start_time
    
    # محاسبه آمار
    successful = sum(1 for r in results if r.get("success", False))
    failed = len(results) - successful
    
    # دسته‌بندی بر اساس category
    category_stats = {}
    for result in results:
        category = result.get("category", "Unknown")
        if category not in category_stats:
            category_stats[category] = {"total": 0, "successful": 0, "failed": 0}
        category_stats[category]["total"] += 1
        if result.get("success", False):
            category_stats[category]["successful"] += 1
        else:
            category_stats[category]["failed"] += 1
    
    # ساخت گزارش کامل
    report = {
        "test_info": {
            "date": datetime.now().isoformat(),
            "collection": collection_name,
            "api_url": base_url,
            "total_tests": len(test_cases),
            "successful": successful,
            "failed": failed,
            "success_rate": f"{(successful/len(test_cases)*100):.1f}%",
            "total_time_seconds": round(total_time, 2)
        },
        "category_statistics": category_stats,
        "test_results": results
    }
    
    # ذخیره در JSON
    output_dir = "/home/user01/qwen-api/enhanced_rag_system_dev/archive/json_files"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"financial_complete_test_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*80)
    print("📊 خلاصه نتایج")
    print("="*80)
    print(f"✅ موفق: {successful}/{len(test_cases)}")
    print(f"❌ ناموفق: {failed}/{len(test_cases)}")
    print(f"⏱️  زمان کل: {total_time:.2f} ثانیه")
    print(f"\n📋 بر اساس Category:")
    for category, stats in category_stats.items():
        print(f"   {category}:")
        print(f"     ✅ موفق: {stats['successful']}/{stats['total']}")
        print(f"     ❌ ناموفق: {stats['failed']}/{stats['total']}")
    
    print(f"\n📄 گزارش کامل ذخیره شد: {filepath}")
    print("="*80)
    
    return report

if __name__ == "__main__":
    main()

