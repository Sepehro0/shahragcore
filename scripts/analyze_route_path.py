#!/usr/bin/env python3
"""
تحلیل دقیق Route Path: Database vs RAG
بدون نیاز به اتصال دیتابیس
"""

import asyncio
import sys
import os

# اضافه کردن مسیر پروژه به sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from services.hybrid_query_analyzer import HybridQueryAnalyzer
import logging

# تنظیم لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def analyze_route():
    """
    تحلیل مسیر route برای سوالات مختلف
    """
    
    # تنظیم analyzer (بدون LLM برای این تست)
    analyzer = HybridQueryAnalyzer()
    
    # سوالات تست
    test_queries = [
        {
            "query": "درآمد وزارت نفت",
            "description": "سوال ساده درآمد (بدون سال صریح)",
            "expected_route": "database"
        },
        {
            "query": "درآمد وزارت نفت در سال 1403",
            "description": "سوال درآمد با سال صریح",
            "expected_route": "database"
        },
        {
            "query": "هزینه های سرمایه ای وزارت اطلاعات در سال 1402",
            "description": "سوال هزینه با سال",
            "expected_route": "database"
        },
        {
            "query": "تاریخچه وزارت نفت",
            "description": "سوال غیرمالی (باید RAG باشد)",
            "expected_route": "rag"
        },
        {
            "query": "چه مقدار بودجه برای آموزش و پرورش در سال 1401 اختصاص یافته",
            "description": "سوال مالی با سال",
            "expected_route": "database"
        }
    ]
    
    print("\n" + "="*100)
    print("🔍 تحلیل دقیق Route Path: Database vs RAG")
    print("="*100 + "\n")
    
    results = []
    
    for idx, test_case in enumerate(test_queries, 1):
        query = test_case["query"]
        description = test_case["description"]
        expected = test_case["expected_route"]
        
        print(f"\n{'='*100}")
        print(f"📝 Test {idx}: {description}")
        print(f"❓ Query: {query}")
        print(f"{'='*100}\n")
        
        # مرحله 1: Query Analysis
        print("📊 STAGE 1: Query Analysis")
        print("-" * 60)
        analysis = await analyzer.analyze(query)
        
        print(f"  ✓ query_category   : {analysis.get('query_category', 'N/A')}")
        print(f"  ✓ query_type       : {analysis.get('query_type', 'N/A')}")
        print(f"  ✓ entity_names     : {analysis.get('entity_names', [])}")
        print(f"  ✓ years            : {analysis.get('years', [])}")
        print(f"  ✓ income_component : {analysis.get('income_component', 'N/A')}")
        print(f"  ✓ expense_type     : {analysis.get('expense_type', 'N/A')}")
        
        # مرحله 2: Route Decision Logic
        print(f"\n🚦 STAGE 2: Route Decision Logic")
        print("-" * 60)
        
        # محاسبه expects_structured (مطابق database_handler.py)
        query_category = analysis.get("query_category")
        expects_structured = bool(
            query_category in {
                "simple_sum", "top_n", "breakdown", "cross_table", "comparison"
            }
        )
        
        print(f"  ✓ query_category      : {query_category}")
        print(f"  ✓ expects_structured  : {expects_structured}")
        
        # تعیین route مطابق کد database_handler.py
        collection_name = "budget_financial"
        
        if collection_name == "budget_financial" and expects_structured:
            final_route = "database"
            reason = "budget_financial collection + expects_structured=True"
            detail = "Force database route (lines 193-195 in database_handler.py)"
        elif expects_structured:
            final_route = "database"
            reason = "expects_structured=True"
            detail = "Text-to-SQL execution (line 197 in database_handler.py)"
        else:
            final_route = "rag"
            reason = "expects_structured=False"
            detail = "Fallback to RAG/ChromaDB (line 266: return None)"
        
        print(f"\n  Decision Logic:")
        print(f"    - Collection: {collection_name}")
        print(f"    - expects_structured: {expects_structured}")
        print(f"    - Condition: {reason}")
        print(f"    - Detail: {detail}")
        
        # مرحله 3: نتیجه نهایی
        print(f"\n✅ STAGE 3: Final Route Decision")
        print("-" * 60)
        
        match_emoji = "✅" if final_route == expected else "❌"
        
        if final_route == "database":
            print(f"  {match_emoji} ROUTE: 🗄️  DATABASE")
            print(f"      └─ Query will be executed via Text-to-SQL")
            print(f"      └─ Direct SQL query on MySQL: booklet_database")
            print(f"      └─ Tables: manabe_sheet1, masaref_sheet1")
        else:
            print(f"  {match_emoji} ROUTE: 📚 RAG (ChromaDB)")
            print(f"      └─ Query will use semantic search on ChromaDB")
            print(f"      └─ Retrieval-Augmented Generation from documents")
            print(f"      └─ Collection: {collection_name}")
        
        print(f"\n  Expected Route: {expected.upper()}")
        print(f"  Actual Route  : {final_route.upper()}")
        print(f"  Match         : {match_emoji} {'CORRECT' if final_route == expected else 'MISMATCH'}")
        
        results.append({
            "query": query,
            "expected": expected,
            "actual": final_route,
            "match": final_route == expected,
            "expects_structured": expects_structured,
            "query_category": query_category
        })
        
        print(f"\n{'='*100}\n")
        
        # فاصله بین تست‌ها
        await asyncio.sleep(0.3)
    
    # خلاصه نتایج
    print("\n" + "="*100)
    print("📊 خلاصه نتایج")
    print("="*100 + "\n")
    
    correct = sum(1 for r in results if r["match"])
    total = len(results)
    
    print(f"  ✅ Correct Routing: {correct}/{total} ({correct/total*100:.1f}%)")
    print(f"  ❌ Incorrect Routing: {total-correct}/{total}\n")
    
    for idx, result in enumerate(results, 1):
        status = "✅" if result["match"] else "❌"
        print(f"  {status} Test {idx}: Expected={result['expected'].upper()}, Actual={result['actual'].upper()}")
        print(f"      Query: {result['query']}")
        print(f"      expects_structured: {result['expects_structured']}, query_category: {result['query_category']}\n")
    
    print("="*100 + "\n")
    
    # توصیه‌های نهایی
    print("💡 نتیجه‌گیری:")
    print("-" * 60)
    if correct == total:
        print("  ✅ تمام query ها به درستی route شدند!")
        print("  ✅ سیستم routing به طور صحیح کار می‌کند")
    else:
        print("  ⚠️  برخی query ها به اشتباه route شدند")
        print("  💡 توصیه: بررسی منطق query_category و expects_structured")
    
    print("\n" + "="*100 + "\n")


if __name__ == "__main__":
    asyncio.run(analyze_route())

