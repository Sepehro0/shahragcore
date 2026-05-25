#!/usr/bin/env python3
"""
تست تشخیص سوالات غیرمالی و پیام مناسب
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from services.hybrid_query_analyzer import HybridQueryAnalyzer
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_non_financial():
    """تست تشخیص سوالات غیرمالی"""
    
    analyzer = HybridQueryAnalyzer()
    
    # سوالات تست
    test_queries = [
        # سوالات غیرمالی (باید non_financial شوند)
        {
            "query": "تاریخچه وزارت نفت",
            "expected_category": "non_financial",
            "description": "سوال تاریخچه"
        },
        {
            "query": "وظایف وزارت اطلاعات چیست",
            "expected_category": "non_financial",
            "description": "سوال وظایف"
        },
        {
            "query": "معرفی سازمان برنامه و بودجه",
            "expected_category": "non_financial",
            "description": "سوال معرفی"
        },
        {
            "query": "وزیر آموزش و پرورش کیست",
            "expected_category": "non_financial",
            "description": "سوال شخصیت"
        },
        {
            "query": "ساختار سازمانی وزارت کشور",
            "expected_category": "non_financial",
            "description": "سوال ساختار"
        },
        {
            "query": "چگونه می‌توانم با وزارت نفت تماس بگیرم",
            "expected_category": "non_financial",
            "description": "سوال تماس"
        },
        
        # سوالات مالی (نباید non_financial شوند)
        {
            "query": "درآمد وزارت نفت در سال 1403",
            "expected_category": "simple_sum",
            "description": "سوال درآمد"
        },
        {
            "query": "هزینه های سرمایه ای وزارت اطلاعات",
            "expected_category": "simple_sum",
            "description": "سوال هزینه"
        },
        {
            "query": "بیشترین بودجه به کدام وزارتخانه تعلق دارد",
            "expected_category": "top_n",
            "description": "سوال بیشترین"
        },
        {
            "query": "مقایسه درآمد وزارت نفت در سال های 1401 و 1402",
            "expected_category": "comparison",
            "description": "سوال مقایسه"
        },
    ]
    
    print("\n" + "="*100)
    print("🧪 تست تشخیص سوالات غیرمالی")
    print("="*100 + "\n")
    
    results = []
    
    for idx, test_case in enumerate(test_queries, 1):
        query = test_case["query"]
        expected = test_case["expected_category"]
        description = test_case["description"]
        
        print(f"\n{'='*100}")
        print(f"📝 Test {idx}: {description}")
        print(f"❓ Query: {query}")
        print(f"{'='*100}\n")
        
        analysis = await analyzer.analyze(query)
        actual_category = analysis.get('query_category')
        
        match = actual_category == expected
        match_emoji = "✅" if match else "❌"
        
        print(f"  Expected Category: {expected}")
        print(f"  Actual Category  : {actual_category}")
        print(f"  Result           : {match_emoji} {'PASS' if match else 'FAIL'}")
        
        results.append({
            "query": query,
            "expected": expected,
            "actual": actual_category,
            "match": match,
            "description": description
        })
        
        print(f"\n{'='*100}\n")
        await asyncio.sleep(0.2)
    
    # خلاصه
    print("\n" + "="*100)
    print("📊 خلاصه نتایج")
    print("="*100 + "\n")
    
    correct = sum(1 for r in results if r["match"])
    total = len(results)
    
    print(f"✅ Correct: {correct}/{total} ({correct/total*100:.1f}%)")
    print(f"❌ Failed : {total-correct}/{total}\n")
    
    # جزئیات هر تست
    for idx, result in enumerate(results, 1):
        status = "✅" if result["match"] else "❌"
        print(f"{status} Test {idx}: {result['description']}")
        print(f"   Query: {result['query']}")
        print(f"   Expected: {result['expected']}, Got: {result['actual']}\n")
    
    print("="*100 + "\n")
    
    if correct == total:
        print("🎉 تمام تست‌ها موفق بودند!")
    else:
        print("⚠️  برخی تست‌ها ناموفق بودند. لطفاً بررسی کنید.")
    
    print("\n" + "="*100 + "\n")


if __name__ == "__main__":
    asyncio.run(test_non_financial())

