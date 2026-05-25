# -*- coding: utf-8 -*-
"""
Test Production Queries
تست سوالات واقعی که قبلاً مشکل داشتند
"""

import asyncio
import logging
import json
from ultimate_rag_system import UltimateRAGSystem

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# سوالات تست که قبلاً مشکل داشتند
TEST_QUERIES = [
    {
        "query": "درامد پژوهکشده هنر در سال 98",
        "collection": "budget_financial",
        "expected": "باید از database جواب بدهد، نه RAG",
        "key_check": "پژوهشکده هنر"
    },
    {
        "query": "منابع ازمایشگاه نقشه برداری مغز",
        "collection": "budget_financial",
        "expected": "باید از database (manabe) جواب بدهد",
        "key_check": "آزمایشگاه"
    },
    {
        "query": "هزینه های بسیج سازندگی در سال 99",
        "collection": "budget_financial",
        "expected": "باید قرارگاه سازندگی خاتم‌الانبیاء را پیدا کند",
        "key_check": "قرارگاه سازندگی"
    },
    {
        "query": "مجموع هزینه های ستاد مبارزه با مواد مخدر از سال 98 تا 403",
        "collection": "budget_financial",
        "expected": "باید مجموع چند سال را محاسبه کند",
        "key_check": "ستاد مبارزه"
    },
    {
        "query": "هزینه های دانشگاه صنعتی قم در سال 1401",
        "collection": "budget_financial",
        "expected": "باید فقط دانشگاه صنعتی قم را پیدا کند، نه دانشگاه‌های دیگر",
        "key_check": "دانشگاه صنعتی قم"
    },
    {
        "query": "هزینه های دانشگاه علوم پزشکی تهران در سال 1401",
        "collection": "budget_financial",
        "expected": "باید دانشگاه علوم پزشکی و خدمات بهداشتی، درمانی تهران را پیدا کند",
        "key_check": "علوم پزشکی"
    },
    {
        "query": "هزینه های وزارت کار در سال 1401",
        "collection": "budget_financial",
        "expected": "باید وزارت تعاون، کار و رفاه اجتماعی را پیدا کند",
        "key_check": "تعاون"
    }
]


async def test_query(system: UltimateRAGSystem, test_case: dict):
    """تست یک query"""
    query = test_case["query"]
    collection = test_case["collection"]
    expected = test_case["expected"]
    key_check = test_case["key_check"]
    
    print("\n" + "="*80)
    print(f"🧪 TEST: {query}")
    print(f"   Collection: {collection}")
    print(f"   Expected: {expected}")
    print("="*80)
    
    try:
        result = await system.query(
            query=query,
            collection_name=collection,
            top_k=5
        )
        
        # بررسی نتایج
        success = result.get("success", False)
        answer = result.get("answer", "")
        route = result.get("metadata", {}).get("route_path", "unknown")
        db_results = result.get("database_results", {})
        
        print(f"\n✅ Success: {success}")
        print(f"📍 Route: {route}")
        
        if db_results:
            detail_rows = db_results.get("detail_rows", [])
            print(f"📊 Database rows: {len(detail_rows)}")
            
            if detail_rows:
                print(f"\n📋 Sample results (first 3):")
                for i, row in enumerate(detail_rows[:3], 1):
                    entity = row.get("عنوان_دستگاه_اجرايي", "N/A")
                    amount = row.get("جمع_كل", "N/A")
                    print(f"   {i}. {entity}: {amount}")
        
        print(f"\n💬 Answer (first 300 chars):")
        print(f"   {answer[:300]}...")
        
        # بررسی key_check
        if key_check.lower() in answer.lower():
            print(f"\n✅ KEY CHECK PASSED: '{key_check}' found in answer")
        else:
            print(f"\n⚠️  KEY CHECK WARNING: '{key_check}' NOT found in answer")
        
        # بررسی route
        if route == "database":
            print(f"✅ ROUTE CHECK PASSED: Using database")
        elif route == "rag":
            print(f"⚠️  ROUTE CHECK WARNING: Using RAG instead of database")
        
        return {
            "query": query,
            "success": success,
            "route": route,
            "key_check_passed": key_check.lower() in answer.lower(),
            "has_db_results": bool(db_results and db_results.get("detail_rows"))
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            "query": query,
            "success": False,
            "error": str(e)
        }


async def main():
    """اجرای تمام تست‌ها"""
    print("\n" + "="*80)
    print("🚀 PRODUCTION QUERIES TEST SUITE")
    print("="*80)
    
    # Initialize system
    print("\n📦 Initializing RAG System...")
    system = UltimateRAGSystem()
    print("✅ System initialized")
    
    # Run tests
    results = []
    for test_case in TEST_QUERIES:
        result = await test_query(system, test_case)
        results.append(result)
        await asyncio.sleep(1)  # کمی صبر کنیم بین queries
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    total = len(results)
    successful = sum(1 for r in results if r.get("success"))
    db_route = sum(1 for r in results if r.get("route") == "database")
    key_checks = sum(1 for r in results if r.get("key_check_passed"))
    
    print(f"\nTotal queries: {total}")
    print(f"Successful: {successful}/{total} ({successful/total*100:.1f}%)")
    print(f"Database route: {db_route}/{total} ({db_route/total*100:.1f}%)")
    print(f"Key checks passed: {key_checks}/{total} ({key_checks/total*100:.1f}%)")
    
    # Detailed results
    print("\n📋 Detailed Results:")
    for i, result in enumerate(results, 1):
        query = result["query"]
        success = "✅" if result.get("success") else "❌"
        route = result.get("route", "unknown")
        key_check = "✅" if result.get("key_check_passed") else "⚠️"
        
        print(f"\n{i}. {success} {query[:50]}...")
        print(f"   Route: {route}, Key check: {key_check}")
    
    print("\n" + "="*80)
    if successful == total and db_route == total and key_checks == total:
        print("✅ ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED - Review results above")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

