#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست مستقیم سیستم RAG بدون API
"""

import sys
sys.path.insert(0, '/home/user01/qwen-api/enhanced_rag_system_dev')

import json
from datetime import datetime
import re

# Import RAG system directly
from core.orchestrators.query_orchestrator import QueryOrchestrator
from core.orchestrators.retrieval_orchestrator import RetrievalOrchestrator
from core.orchestrators.answer_orchestrator import AnswerOrchestrator

# Test cases
test_cases = [
    # Category 1a
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
        "expected_year": "1403"
    },
    {
        "id": "1a-5",
        "category": "1a. ارجاع یک سلول خاص - مصارف",
        "query": "تملک دارایی سرمایه ای متفرقه سازمان سنجش بند ج در سال 1403",
        "expected_column": "براورد_تملك_دارايي_هاي_سرمايه_اي_م",
        "expected_entity": "سازمان سنجش آموزش كشور موضوع بند\"ج\" تبصره 49 قانون بودجه سال 1364 كل كشور",
        "expected_year": "1403"
    },
    # Category 2a
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
        "note": "بدون سال - باید سال 1403 در نظر گرفته شود"
    },
    # Category 2b
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
        "issues": []
    }
    
    if not answer:
        analysis["issues"].append("پاسخ خالی است")
        return analysis
    
    if "اسناد موجود نیست" in answer or "اسنادی موجود نیست" in answer:
        analysis["mentions_no_data"] = True
        analysis["issues"].append("⚠️ سیستم می‌گوید داده موجود نیست")
    else:
        analysis["has_data"] = True
    
    if "با توجه به عدم ذکر سال" in answer:
        if test_case.get("expected_year") == "1403" and "1403" in test_case.get("query", ""):
            analysis["mentions_default_year"] = True
            analysis["issues"].append("⚠️ سال در query ذکر شده اما سیستم می‌گوید 'عدم ذکر سال'")
    
    numbers = re.findall(r'[\d,]+\.?\d*', answer.replace(',', ''))
    if numbers:
        try:
            values = [float(n.replace(',', '')) for n in numbers if n.replace(',', '').replace('.', '').isdigit()]
            if values:
                analysis["has_value"] = True
                analysis["value_extracted"] = max(values)
        except:
            pass
    
    return analysis

def test_query_direct(test_case):
    """تست مستقیم query"""
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
        "overall_issues": []
    }
    
    try:
        # Initialize orchestrators
        query_orch = QueryOrchestrator()
        retrieval_orch = RetrievalOrchestrator()
        answer_orch = AnswerOrchestrator()
        
        # Process query
        query_result = query_orch.process_query(test_case['query'], collection_name="budget_financial")
        
        if query_result.get('success'):
            # Get retrieval result
            retrieval_result = retrieval_orch.process_retrieval(query_result, collection_name="budget_financial")
            
            if retrieval_result.get('success'):
                # Generate answer
                answer_result = answer_orch.generate_answer(
                    query_result,
                    retrieval_result,
                    collection_name="budget_financial"
                )
                
                if answer_result.get('success'):
                    result["success"] = True
                    result["answer"] = answer_result.get('answer', '')
                    result["sql"] = retrieval_result.get('sql', '')
                    
                    # Analyze
                    result["answer_analysis"] = analyze_answer(result["answer"], test_case)
                    if result["answer_analysis"]["issues"]:
                        result["overall_issues"].extend(result["answer_analysis"]["issues"])
                    
                    print(f"✅ SUCCESS")
                    print(f"\n📝 Answer ({len(result['answer'])} chars):")
                    print(result['answer'][:800])
                    print(f"\n🔍 SQL:")
                    print(result['sql'][:500] if result['sql'] else 'N/A')
                    
                    if result["overall_issues"]:
                        print(f"\n⚠️ Issues:")
                        for issue in result["overall_issues"]:
                            print(f"  - {issue}")
                else:
                    result["error"] = answer_result.get('error', '')
                    print(f"❌ Answer generation failed: {result['error'][:300]}")
            else:
                result["error"] = retrieval_result.get('error', '')
                print(f"❌ Retrieval failed: {result['error'][:300]}")
        else:
            result["error"] = query_result.get('error', '')
            print(f"❌ Query processing failed: {result['error'][:300]}")
    except Exception as e:
        result["error"] = str(e)
        import traceback
        print(f"❌ Exception: {str(e)[:300]}")
        print(traceback.format_exc()[:500])
    
    return result

def main():
    print("=" * 100)
    print("🧪 تست مستقیم سیستم RAG")
    print(f"تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)
    
    all_results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n[{i}/{len(test_cases)}]")
        result = test_query_direct(test_case)
        all_results.append(result)
    
    # خلاصه
    print("\n\n" + "=" * 100)
    print("📊 خلاصه نتایج")
    print("=" * 100)
    
    successful = sum(1 for r in all_results if r.get('success'))
    print(f"\n✅ موفق: {successful}/{len(all_results)}")
    print(f"❌ ناموفق: {len(all_results) - successful}/{len(all_results)}")
    
    # ذخیره گزارش
    report_file = f"/tmp/rag_direct_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 گزارش ذخیره شد: {report_file}")
    print("=" * 100)
    
    return all_results

if __name__ == "__main__":
    main()


