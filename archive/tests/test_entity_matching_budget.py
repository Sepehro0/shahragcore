# -*- coding: utf-8 -*-
"""
تست جامع Entity Matching و سوالات نمونه budget_financial
این اسکریپت Entity Matching را تست می‌کند و سوالات نمونه را اجرا می‌کند
"""

import asyncio
import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Add project path
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== Test Results Storage ==========
test_results = {
    "entity_matching": [],
    "income_queries": [],
    "supplementary_income_queries": [],
    "expense_queries": [],
    "summary": {}
}


# ========== Entity Matching Tests ==========
def test_entity_matching_logic():
    """تست منطق Entity Matching بدون نیاز به API"""
    print("\n" + "="*80)
    print("🔍 تست Entity Matching Logic")
    print("="*80)
    
    from services.entity_disambiguator import EntityDisambiguator
    from services.hybrid_query_analyzer import HybridQueryAnalyzer
    from difflib import SequenceMatcher
    
    # تست‌های Entity Matching
    test_cases = [
        # (query_entity, expected_match, should_reject_wrong_match, wrong_match)
        ("معاونت علمی و فناوری", "معاونت علمی و فناوری رییس جمهور", True, "پارک علم و فناوری قم"),
        ("وزارت نفت", "وزارت نفت", False, None),
        ("بانک ملی", "بانک ملی ایران", False, None),
        ("سازمان امور مالیاتی", "سازمان امور مالیاتی کشور", False, None),
        ("فرهنگستان علوم ایران", "فرهنگستان علوم جمهوری اسلامی ایران", False, None),
        ("ستاد توسعه زیست فناوری", "ستاد توسعه فناوری نانو", False, None),  # باید رد شود
    ]
    
    results = []
    
    for test in test_cases:
        query_entity = test[0]
        expected_match = test[1]
        should_reject_wrong = test[2]
        wrong_match = test[3] if len(test) > 3 else None
        
        print(f"\n📌 تست: '{query_entity}'")
        print(f"   Match مورد انتظار: '{expected_match}'")
        
        # محاسبه word overlap
        def calculate_word_overlap(query: str, candidate: str) -> float:
            stop_words = {'و', 'در', 'به', 'از', 'با', 'که', 'این', 'آن', 'یک'}
            query_words = set(query.lower().split()) - stop_words
            candidate_words = set(candidate.lower().split()) - stop_words
            if len(query_words) == 0:
                return 0.0
            overlap = query_words & candidate_words
            return len(overlap) / len(query_words)
        
        # محاسبه similarity
        def calculate_similarity(a: str, b: str) -> float:
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()
        
        # تست match درست
        similarity_correct = calculate_similarity(query_entity, expected_match)
        word_overlap_correct = calculate_word_overlap(query_entity, expected_match)
        combined_correct = (0.4 * similarity_correct) + (0.6 * word_overlap_correct)
        
        print(f"   ✅ Match درست ({expected_match}):")
        print(f"      - Similarity: {similarity_correct:.3f}")
        print(f"      - Word Overlap: {word_overlap_correct:.3f}")
        print(f"      - Combined Score: {combined_correct:.3f}")
        
        # تست match نادرست (اگر وجود دارد)
        if wrong_match:
            similarity_wrong = calculate_similarity(query_entity, wrong_match)
            word_overlap_wrong = calculate_word_overlap(query_entity, wrong_match)
            combined_wrong = (0.4 * similarity_wrong) + (0.6 * word_overlap_wrong)
            
            print(f"   ❌ Match نادرست ({wrong_match}):")
            print(f"      - Similarity: {similarity_wrong:.3f}")
            print(f"      - Word Overlap: {word_overlap_wrong:.3f}")
            print(f"      - Combined Score: {combined_wrong:.3f}")
            
            # بررسی Primary Keyword Matching
            entity_type_words = {'معاونت', 'سازمان', 'وزارت', 'دانشگاه', 'بانک', 'شرکت', 
                                'موسسه', 'ستاد', 'نهاد', 'بنیاد', 'فرهنگستان', 'شورا', 'هیات',
                                'پارک', 'مرکز', 'اداره', 'کمیته', 'صندوق'}
            
            query_words = set(query_entity.lower().split())
            wrong_words = set(wrong_match.lower().split())
            
            query_primary = query_words & entity_type_words
            wrong_primary = wrong_words & entity_type_words
            
            primary_match = bool(query_primary & wrong_primary)
            
            print(f"   🔑 Primary Keywords:")
            print(f"      - Query: {query_primary}")
            print(f"      - Wrong: {wrong_primary}")
            print(f"      - Primary Match: {primary_match}")
            
            # آیا باید رد شود؟
            should_reject = (
                word_overlap_wrong < 0.50 or  # Word overlap کم
                (len(query_words) <= 2 and word_overlap_wrong < 0.70) or  # Query کوتاه
                not primary_match  # Primary keyword match نشده
            )
            
            status = "✅ PASS" if should_reject == should_reject_wrong else "❌ FAIL"
            print(f"   📊 نتیجه: {status} (باید رد شود: {should_reject_wrong}, رد شد: {should_reject})")
            
            results.append({
                "query": query_entity,
                "expected_match": expected_match,
                "wrong_match": wrong_match,
                "similarity_correct": similarity_correct,
                "word_overlap_correct": word_overlap_correct,
                "combined_correct": combined_correct,
                "similarity_wrong": similarity_wrong,
                "word_overlap_wrong": word_overlap_wrong,
                "combined_wrong": combined_wrong,
                "should_reject": should_reject,
                "pass": should_reject == should_reject_wrong
            })
        else:
            results.append({
                "query": query_entity,
                "expected_match": expected_match,
                "similarity": similarity_correct,
                "word_overlap": word_overlap_correct,
                "combined": combined_correct,
                "pass": combined_correct >= 0.60
            })
    
    # خلاصه نتایج
    passed = sum(1 for r in results if r.get("pass", False))
    total = len(results)
    
    print(f"\n📊 خلاصه Entity Matching: {passed}/{total} تست موفق")
    
    test_results["entity_matching"] = results
    return results


# ========== Full API Tests ==========
async def test_budget_queries_via_api():
    """تست سوالات از طریق API"""
    print("\n" + "="*80)
    print("🔬 تست سوالات budget_financial از طریق API")
    print("="*80)
    
    import httpx
    
    API_URL = "http://localhost:8010/v2/query/streaming"
    
    # سوالات نمونه درآمد
    income_queries = [
        ("درآمد های حاصل از بخش درآمد های مالیاتی در سال 1401", "1401", "درآمدهای مالیاتی"),
        ("منابع حاصل از بند درآمد های حاصل از خدمات در سال 402", "1402", "درآمدهای حاصل از خدمات"),
        ("درآمد وزارت نفت", "1403", "وزارت نفت"),
        ("درآمد حاصل از قسمت واگذاری دارایی های سرمایه ای در سال 400", "1400", "واگذاری دارایی‌های سرمایه‌ای"),
        ("درآمد سازمان امور مالیاتی در سال 98", "1398", "سازمان امور مالیاتی"),
        ("درآمد حاصل از بند درآمد های متفرقه در سال های 98 تا 400", "1398-1400", "درآمدهای متفرقه"),
    ]
    
    # سوالات تکمیلی درآمد
    supplementary_queries = [
        ("درآمد عمومی شرکت بازرگانی گاز ایران در سال 98", "1398", "شرکت بازرگانی گاز ایران"),
        ("درآمد استانی اختصاصی وزارت اموزش پرورش در سال های 98 تا 403", "1398-1403", "وزارت آموزش و پرورش"),
        ("درآمد ملی بانک ملی", "1403", "بانک ملی ایران"),
    ]
    
    # سوالات هزینه
    expense_queries = [
        ("اعتبارات هزینه ای فرهنگستان علوم ایران در سال های 98 تا 403", "1398-1403", "فرهنگستان علوم ایران"),
        ("هزینه های سرمایه ای وزارت اطلاعات در سال 1402", "1402", "وزارت اطلاعات"),
        ("هزینه های سرمایه ای عمومی ستاد توسعه زیست فناوری", "1403", "ستاد توسعه زیست فناوری"),
        ("اعتبارات هزینه ای اختصاصی انسستیو پاستور 401", "1401", "انستیتو پاستور"),
    ]
    
    async def run_query(query: str, expected_year: str, expected_entity: str, category: str) -> Dict[str, Any]:
        """اجرای یک query و ذخیره نتیجه"""
        print(f"\n📝 Query: {query}")
        print(f"   Expected Year: {expected_year}")
        print(f"   Expected Entity: {expected_entity}")
        
        result = {
            "query": query,
            "expected_year": expected_year,
            "expected_entity": expected_entity,
            "category": category,
            "success": False,
            "answer": None,
            "route_path": None,
            "confidence": None,
            "metadata": {},
            "error": None
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    API_URL,
                    json={
                        "query": query,
                        "collection_name": "budget_financial",
                        "top_k": 5,
                        "use_reranking": True
                    }
                )
                
                if response.status_code == 200:
                    full_response = ""
                    metadata = {}
                    
                    # Parse SSE response
                    for line in response.text.split('\n'):
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                if data.get('done'):
                                    full_response = data.get('full_response', full_response)
                                    metadata = data.get('metadata', {})
                                elif 'chunk' in data:
                                    full_response += data.get('chunk', '')
                            except json.JSONDecodeError:
                                continue
                    
                    result["success"] = True
                    result["answer"] = full_response[:500] + "..." if len(full_response) > 500 else full_response
                    result["route_path"] = metadata.get("route_path", "unknown")
                    result["confidence"] = metadata.get("confidence", 0)
                    result["metadata"] = metadata
                    
                    print(f"   ✅ Success!")
                    print(f"   Route: {result['route_path']}")
                    print(f"   Confidence: {result['confidence']}")
                    print(f"   Answer Preview: {result['answer'][:200]}...")
                else:
                    result["error"] = f"HTTP {response.status_code}"
                    print(f"   ❌ Error: {result['error']}")
                    
        except Exception as e:
            result["error"] = str(e)
            print(f"   ❌ Exception: {e}")
        
        return result
    
    # اجرای تست‌ها
    print("\n" + "-"*60)
    print("📊 تست سوالات درآمد")
    print("-"*60)
    
    for query, year, entity in income_queries:
        result = await run_query(query, year, entity, "income")
        test_results["income_queries"].append(result)
    
    print("\n" + "-"*60)
    print("📊 تست سوالات درآمد تکمیلی")
    print("-"*60)
    
    for query, year, entity in supplementary_queries:
        result = await run_query(query, year, entity, "supplementary_income")
        test_results["supplementary_income_queries"].append(result)
    
    print("\n" + "-"*60)
    print("📊 تست سوالات هزینه")
    print("-"*60)
    
    for query, year, entity in expense_queries:
        result = await run_query(query, year, entity, "expense")
        test_results["expense_queries"].append(result)


async def test_query_analyzer_directly():
    """تست مستقیم Query Analyzer بدون API"""
    print("\n" + "="*80)
    print("🔬 تست مستقیم Query Analyzer")
    print("="*80)
    
    from services.query_analyzer import QueryAnalyzer
    
    analyzer = QueryAnalyzer()
    
    test_queries = [
        "درآمد های حاصل از بخش درآمد های مالیاتی در سال 1401",
        "منابع حاصل از بند درآمد های حاصل از خدمات در سال 402",
        "درآمد وزارت نفت",
        "درآمد حاصل از قسمت واگذاری دارایی های سرمایه ای در سال 400",
        "درآمد سازمان امور مالیاتی در سال 98",
        "درآمد حاصل از بند درآمد های متفرقه در سال های 98 تا 400",
        "درآمد عمومی شرکت بازرگانی گاز ایران در سال 98",
        "درآمد استانی اختصاصی وزارت اموزش پرورش در سال های 98 تا 403",
        "درآمد ملی بانک ملی",
        "اعتبارات هزینه ای فرهنگستان علوم ایران در سال های 98 تا 403",
        "هزینه های سرمایه ای وزارت اطلاعات در سال 1402",
        "هزینه های سرمایه ای عمومی ستاد توسعه زیست فناوری",
        "اعتبارات هزینه ای اختصاصی انسستیو پاستور 401",
    ]
    
    results = []
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        
        # Analyze query - check if it's async or sync
        try:
            analysis_result = analyzer.analyze(query)
            # Check if it's a coroutine
            if asyncio.iscoroutine(analysis_result):
                analysis = await analysis_result
            else:
                analysis = analysis_result
        except Exception as e:
            print(f"   ❌ Error analyzing: {e}")
            analysis = {}
        
        print(f"   📊 Analysis:")
        print(f"      - Query Type: {analysis.get('query_type', 'N/A')}")
        print(f"      - Years: {analysis.get('years', [])}")
        print(f"      - Entity Names: {analysis.get('entity_names', [])}")
        print(f"      - Income Components: {analysis.get('income_components', [])}")
        print(f"      - Query Category: {analysis.get('query_category', 'N/A')}")
        print(f"      - Table Type: {analysis.get('table_type', 'N/A')}")
        
        results.append({
            "query": query,
            "analysis": analysis
        })
    
    return results


def generate_report():
    """تولید گزارش نهایی"""
    print("\n" + "="*80)
    print("📋 گزارش نهایی تست‌ها")
    print("="*80)
    
    # Entity Matching Summary
    entity_results = test_results.get("entity_matching", [])
    entity_passed = sum(1 for r in entity_results if r.get("pass", False))
    entity_total = len(entity_results)
    
    print(f"\n🔍 Entity Matching: {entity_passed}/{entity_total} موفق")
    
    # Income Queries Summary
    income_results = test_results.get("income_queries", [])
    income_success = sum(1 for r in income_results if r.get("success", False))
    income_total = len(income_results)
    
    print(f"📊 سوالات درآمد: {income_success}/{income_total} موفق")
    
    # Supplementary Income Summary
    supp_results = test_results.get("supplementary_income_queries", [])
    supp_success = sum(1 for r in supp_results if r.get("success", False))
    supp_total = len(supp_results)
    
    print(f"📊 سوالات درآمد تکمیلی: {supp_success}/{supp_total} موفق")
    
    # Expense Queries Summary
    expense_results = test_results.get("expense_queries", [])
    expense_success = sum(1 for r in expense_results if r.get("success", False))
    expense_total = len(expense_results)
    
    print(f"📊 سوالات هزینه: {expense_success}/{expense_total} موفق")
    
    # Overall Summary
    total_api_tests = income_total + supp_total + expense_total
    total_api_success = income_success + supp_success + expense_success
    
    print(f"\n📈 مجموع تست‌های API: {total_api_success}/{total_api_tests} موفق")
    print(f"📈 Success Rate: {total_api_success/total_api_tests*100:.1f}%" if total_api_tests > 0 else "N/A")
    
    # Route Path Analysis
    all_api_results = income_results + supp_results + expense_results
    route_paths = {}
    for r in all_api_results:
        route = r.get("route_path", "unknown")
        route_paths[route] = route_paths.get(route, 0) + 1
    
    print(f"\n🛤️ Route Paths:")
    for route, count in route_paths.items():
        print(f"   - {route}: {count}")
    
    # Save summary
    test_results["summary"] = {
        "entity_matching": {"passed": entity_passed, "total": entity_total},
        "income_queries": {"success": income_success, "total": income_total},
        "supplementary_income": {"success": supp_success, "total": supp_total},
        "expense_queries": {"success": expense_success, "total": expense_total},
        "total_api": {"success": total_api_success, "total": total_api_tests},
        "route_paths": route_paths,
        "timestamp": datetime.now().isoformat()
    }
    
    # Save to file
    report_file = f"/home/user01/qwen-api/enhanced_rag_system_dev/entity_matching_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 گزارش ذخیره شد: {report_file}")
    
    return test_results


async def main():
    """Main function"""
    print("="*80)
    print("🚀 شروع تست جامع Entity Matching و سوالات budget_financial")
    print(f"⏰ زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 1. تست Entity Matching Logic
    test_entity_matching_logic()
    
    # 2. تست Query Analyzer
    await test_query_analyzer_directly()
    
    # 3. تست API (اگر سرور در حال اجراست)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8010/health")
            if response.status_code == 200:
                print("\n✅ API Server is running, proceeding with API tests...")
                await test_budget_queries_via_api()
            else:
                print("\n⚠️ API Server returned non-200 status, skipping API tests")
    except Exception as e:
        print(f"\n⚠️ API Server not available ({e}), skipping API tests")
    
    # 4. تولید گزارش
    generate_report()
    
    print("\n" + "="*80)
    print("✅ تست‌ها به پایان رسید")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())

