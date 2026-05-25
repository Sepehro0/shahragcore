#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست جامع و تحلیل کامل سیستم RAG
"""

import sys
sys.path.insert(0, '/home/user01/qwen-api/enhanced_rag_system_dev')

import requests
import json
from datetime import datetime
import time
import re

base_url = "http://localhost:8010"  # Using production server

# تمام سوالات تست
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
        "expected_column": "استاني_در_آمد_اختصاصي",
        "expected_entity": "دانشگاه تبریز",
        "expected_year": "1403"
    },
    {
        "id": "2b-2",
        "category": "2b. درآمدها",
        "query": "درامد ملی سازمان تامین اجتماعی در سال 1403",
        "expected_column": "ملي_در_آمد_عمومي",
        "expected_entity": "سازمان تامین اجتماعی",
        "expected_year": "1403"
    },
    {
        "id": "2b-3",
        "category": "2b. درآمدها",
        "query": "درامد کل موسسه کار و تامین اجتماعی در سال 1402",
        "expected_column": "جمع_کل",
        "expected_table": "incomes_sheet1",
        "expected_entity": "موسسه کار و تامین اجتماعی",
        "expected_year": "1402"
    },
]

def analyze_answer(answer, test_case):
    """تحلیل پاسخ"""
    analysis = {
        "has_data": False,
        "mentions_no_data": False,
        "mentions_default_year": False,
        "has_value": False,
        "value_extracted": None,
        "mentions_entity": False,
        "mentions_year": False,
        "issues": []
    }
    
    if not answer:
        analysis["issues"].append("پاسخ خالی است")
        return analysis
    
    # بررسی وجود داده
    if "اسناد موجود نیست" in answer or "اسنادی موجود نیست" in answer or "داده‌ای موجود نیست" in answer:
        analysis["mentions_no_data"] = True
        analysis["issues"].append("⚠️ سیستم می‌گوید داده موجود نیست")
    else:
        analysis["has_data"] = True
    
    # بررسی ذکر سال پیش‌فرض
    if "با توجه به عدم ذکر سال" in answer or "عدم ذکر سال" in answer:
        if test_case.get("expected_year") == "1403" and "1403" in test_case.get("query", ""):
            analysis["mentions_default_year"] = True
            analysis["issues"].append("⚠️ سال در query ذکر شده اما سیستم می‌گوید 'عدم ذکر سال'")
    
    # استخراج مقدار عددی
    numbers = re.findall(r'[\d,]+\.?\d*', answer.replace(',', ''))
    if numbers:
        try:
            # بزرگترین عدد را به عنوان مقدار در نظر بگیر
            values = [float(n.replace(',', '')) for n in numbers if n.replace(',', '').replace('.', '').isdigit()]
            if values:
                analysis["has_value"] = True
                analysis["value_extracted"] = max(values)
        except:
            pass
    
    # بررسی ذکر entity
    entity = test_case.get("expected_entity", "")
    if entity and entity in answer:
        analysis["mentions_entity"] = True
    
    # بررسی ذکر سال
    year = test_case.get("expected_year", "")
    if year and year in answer:
        analysis["mentions_year"] = True
    
    return analysis

def analyze_sql(sql, test_case):
    """تحلیل SQL query"""
    analysis = {
        "has_sql": bool(sql),
        "correct_table": None,
        "correct_column": None,
        "has_year_filter": False,
        "has_entity_filter": False,
        "issues": []
    }
    
    if not sql:
        analysis["issues"].append("SQL query موجود نیست")
        return analysis
    
    sql_upper = sql.upper()
    
    # بررسی جدول
    expected_table = test_case.get("expected_table", "masaref2_sheet1")
    if expected_table.upper() in sql_upper:
        analysis["correct_table"] = True
    else:
        analysis["correct_table"] = False
        analysis["issues"].append(f"جدول صحیح نیست (انتظار: {expected_table})")
    
    # بررسی ستون
    expected_column = test_case.get("expected_column")
    if expected_column:
        # Normalize column name for comparison
        sql_normalized = sql.replace('"', '').replace("'", "")
        if expected_column in sql_normalized:
            analysis["correct_column"] = True
        else:
            analysis["correct_column"] = False
            analysis["issues"].append(f"ستون صحیح نیست (انتظار: {expected_column})")
    
    # بررسی فیلتر سال
    year = test_case.get("expected_year", "")
    if year and f"سال" in sql and year in sql:
        analysis["has_year_filter"] = True
    else:
        if year:
            analysis["issues"].append(f"فیلتر سال {year} موجود نیست")
    
    # بررسی فیلتر entity
    entity = test_case.get("expected_entity", "")
    if entity and ("ILIKE" in sql_upper or "LIKE" in sql_upper):
        analysis["has_entity_filter"] = True
    
    return analysis

def test_query(test_case):
    """تست یک query"""
    print(f"\n{'='*100}")
    print(f"Test ID: {test_case['id']}")
    print(f"Category: {test_case['category']}")
    print(f"Query: {test_case['query']}")
    print(f"{'='*100}")
    
    result = {
        "test_case": test_case,
        "success": False,
        "answer": "",
        "sql": "",
        "error": "",
        "answer_analysis": {},
        "sql_analysis": {},
        "overall_issues": []
    }
    
    try:
        response = requests.post(
            f"{base_url}/query",
            json={"query": test_case['query'], "collection_name": "budget_financial"},
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            result["success"] = data.get('success', False)
            result["answer"] = data.get('answer', '')
            result["sql"] = data.get('sql', '')
            result["error"] = data.get('error', '')
            
            if result["success"]:
                # تحلیل پاسخ
                result["answer_analysis"] = analyze_answer(result["answer"], test_case)
                # تحلیل SQL
                result["sql_analysis"] = analyze_sql(result["sql"], test_case)
                
                # جمع‌بندی مشکلات
                if result["answer_analysis"]["issues"]:
                    result["overall_issues"].extend(result["answer_analysis"]["issues"])
                if result["sql_analysis"]["issues"]:
                    result["overall_issues"].extend(result["sql_analysis"]["issues"])
                
                print(f"✅ SUCCESS")
                print(f"\n📝 Answer ({len(result['answer'])} chars):")
                print(result['answer'][:500] + ("..." if len(result['answer']) > 500 else ""))
                print(f"\n🔍 SQL:")
                print(result['sql'][:400] + ("..." if len(result['sql']) > 400 else ""))
                
                if result["overall_issues"]:
                    print(f"\n⚠️ Issues:")
                    for issue in result["overall_issues"]:
                        print(f"  - {issue}")
            else:
                print(f"❌ FAILED: {result['error'][:300]}")
        else:
            result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
            print(f"❌ HTTP {response.status_code}")
    except Exception as e:
        result["error"] = str(e)
        print(f"❌ Exception: {str(e)[:200]}")
    
    return result

def generate_report(all_results):
    """تولید گزارش کامل"""
    report = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "total_tests": len(all_results),
        "successful": sum(1 for r in all_results if r.get('success')),
        "failed": sum(1 for r in all_results if not r.get('success')),
        "results": all_results,
        "summary": {}
    }
    
    # خلاصه بر اساس category
    categories = {}
    for result in all_results:
        category = result['test_case']['category']
        if category not in categories:
            categories[category] = {"total": 0, "successful": 0, "failed": 0, "issues": []}
        
        categories[category]["total"] += 1
        if result.get('success'):
            categories[category]["successful"] += 1
        else:
            categories[category]["failed"] += 1
        
        if result.get('overall_issues'):
            categories[category]["issues"].extend(result['overall_issues'])
    
    report["summary"]["by_category"] = categories
    
    # مشکلات رایج
    all_issues = []
    for result in all_results:
        if result.get('overall_issues'):
            all_issues.extend(result['overall_issues'])
    
    issue_counts = {}
    for issue in all_issues:
        issue_counts[issue] = issue_counts.get(issue, 0) + 1
    
    report["summary"]["common_issues"] = issue_counts
    
    return report

def main():
    print("=" * 100)
    print("🧪 تست جامع و تحلیل کامل سیستم RAG")
    print(f"تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)
    
    all_results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n[{i}/{len(test_cases)}]")
        result = test_query(test_case)
        all_results.append(result)
        time.sleep(2)  # Wait between requests
    
    # تولید گزارش
    report = generate_report(all_results)
    
    # نمایش خلاصه
    print("\n\n" + "=" * 100)
    print("📊 خلاصه نتایج")
    print("=" * 100)
    print(f"\n✅ موفق: {report['successful']}/{report['total_tests']}")
    print(f"❌ ناموفق: {report['failed']}/{report['total_tests']}")
    
    print(f"\n📋 بر اساس Category:")
    for category, stats in report['summary']['by_category'].items():
        print(f"\n  {category}:")
        print(f"    ✅ موفق: {stats['successful']}/{stats['total']}")
        print(f"    ❌ ناموفق: {stats['failed']}/{stats['total']}")
        if stats['issues']:
            unique_issues = list(set(stats['issues']))
            print(f"    ⚠️ Issues: {len(unique_issues)} نوع")
            for issue in unique_issues[:5]:  # نمایش 5 مورد اول
                print(f"      - {issue}")
    
    if report['summary']['common_issues']:
        print(f"\n⚠️ مشکلات رایج:")
        for issue, count in sorted(report['summary']['common_issues'].items(), key=lambda x: x[1], reverse=True):
            print(f"  - {issue}: {count} بار")
    
    # ذخیره گزارش
    report_file = f"/tmp/rag_comprehensive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 گزارش کامل ذخیره شد: {report_file}")
    print("=" * 100)
    
    return report

if __name__ == "__main__":
    main()

