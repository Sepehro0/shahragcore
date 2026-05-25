# -*- coding: utf-8 -*-
"""
Comprehensive Test for zabete_qa with RAGAS Metrics
تست جامع با متریک‌های RAGAS
"""

import asyncio
import json
import aiohttp
from datetime import datetime
from typing import List, Dict, Any

# تست‌های جامع‌تر
COMPREHENSIVE_TESTS = [
    {
        "query": "ماده 46 شرایط عمومی پیمان چیه؟",
        "expected": "باید در فیلد answer جستجو کند و پاسخ بدهد",
        "category": "answer_field_search"
    },
    {
        "query": "توضیح ماده 48 شرایط عمومی پیمان",
        "expected": "باید در فیلد answer جستجو کند",
        "category": "answer_field_search"
    },
    {
        "query": "قراردادهای QBC چگونه است",
        "expected": "باید تشخیص دهد نامرتبط است یا پاسخ مناسب بدهد",
        "category": "irrelevant_query"
    },
    {
        "query": "تاخیر در پرداخت قراردادهای EPC",
        "expected": "باید نتایج مرتبط با EPC پیدا کند",
        "category": "specific_contract_type"
    },
    {
        "query": "تاخیر در پرداخت قراردادهای طرح و ساخت",
        "expected": "باید از چند منبع استنتاج کند",
        "category": "multi_source_inference"
    },
    {
        "query": "تفاوت بین قراردادهای EPC و طرح و ساخت",
        "expected": "باید مقایسه کند و dynamic_top_k بالاتر باشد",
        "category": "comparison"
    },
    {
        "query": "نحوه محاسبه تعدیل در پیمان‌ها",
        "expected": "باید از keyword matching استفاده کند",
        "category": "keyword_based"
    },
    {
        "query": "چگونگی اجرای بخشنامه 54/842",
        "expected": "باید بخشنامه را شناسایی و پاسخ بدهد",
        "category": "bokshname_code"
    }
]

API_BASE_URL = "http://localhost:8010"
COLLECTION_NAME = "zabete_qa"


async def test_single_query(
    session: aiohttp.ClientSession,
    test_case: Dict[str, Any]
) -> Dict[str, Any]:
    """تست یک query"""
    query = test_case['query']
    print(f"\n{'='*80}")
    print(f"🔍 Query: {query}")
    print(f"📋 Expected: {test_case['expected']}")
    print(f"🏷️  Category: {test_case['category']}")
    print(f"{'='*80}\n")
    
    try:
        async with session.post(
            f"{API_BASE_URL}/v2/query",
            json={
                "query": query,
                "collection_name": COLLECTION_NAME,
                "top_k": 5,
                "use_reranking": True,
                "use_multi_hop": True
            },
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                return {
                    "query": query,
                    "success": False,
                    "error": f"HTTP {response.status}: {error_text}",
                    "test_case": test_case
                }
            
            result = await response.json()
            
            # استخراج اطلاعات
            answer = result.get("answer", "")
            confidence = result.get("confidence", 0.0)
            sources = result.get("sources", [])
            metadata = result.get("metadata", {})
            
            # RAGAS metrics
            ragas_metrics = metadata.get("ragas_metrics", {})
            
            # Dynamic Top-K
            dynamic_top_k = metadata.get("dynamic_top_k", "N/A")
            original_top_k = metadata.get("original_top_k", "N/A")
            
            # نمایش نتایج
            print(f"✅ Response received")
            print(f"📊 Confidence: {confidence:.2f}")
            print(f"🔢 Dynamic Top-K: {dynamic_top_k} (original: {original_top_k})")
            print(f"📚 Sources: {len(sources)}")
            print(f"🔗 Relevance Score: {metadata.get('relevance_score', 'N/A')}")
            
            # RAGAS Metrics
            if ragas_metrics:
                print(f"\n📊 RAGAS Metrics:")
                for category, vals in ragas_metrics.items():
                    if isinstance(vals, dict):
                        print(f"  {category}:")
                        for key, value in vals.items():
                            if isinstance(value, (int, float)):
                                # user_satisfaction باید به صورت عدد (0-5) نمایش داده شود، نه درصد
                                if key == 'user_satisfaction':
                                    print(f"    - {key}: {value:.2f}/5.0")
                                else:
                                    print(f"    - {key}: {value:.2%}")
                            else:
                                print(f"    - {key}: {value}")
            
            # Confidence Breakdown
            conf_breakdown = metadata.get("confidence_breakdown", {})
            if conf_breakdown:
                print(f"\n📊 Confidence Breakdown:")
                for key, value in conf_breakdown.items():
                    if isinstance(value, (int, float)):
                        print(f"  - {key}: {value:.2f}")
            
            print(f"\n📝 Answer ({len(answer)} chars):")
            print(f"{answer[:300]}..." if len(answer) > 300 else answer)
            
            print(f"\n📚 Top Sources ({len(sources)}):")
            for i, src in enumerate(sources[:3], 1):
                score = src.get("score", 0.0)
                meta = src.get("metadata", {})
                question = meta.get("question", "N/A")[:60]
                print(f"   {i}. Score: {score:.2f} | Q: {question}...")
            
            return {
                "query": query,
                "success": True,
                "answer": answer,
                "confidence": confidence,
                "sources_count": len(sources),
                "dynamic_top_k": dynamic_top_k,
                "ragas_metrics": ragas_metrics,
                "test_case": test_case
            }
            
    except Exception as e:
        return {
            "query": query,
            "success": False,
            "error": str(e),
            "test_case": test_case
        }


async def main():
    """تابع اصلی"""
    print("🚀 Comprehensive zabete_qa Test with RAGAS")
    print(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 API URL: {API_BASE_URL}")
    print(f"📚 Collection: {COLLECTION_NAME}")
    print(f"🧪 Total Tests: {len(COMPREHENSIVE_TESTS)}")
    print("\n" + "="*80)
    
    async with aiohttp.ClientSession() as session:
        # بررسی سلامت API
        print("\n🔍 Checking API health...")
        try:
            async with session.get(f"{API_BASE_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    print("✅ API is healthy\n")
                else:
                    print("❌ API is not healthy")
                    return
        except:
            print("❌ API is not responding")
            return
        
        # تست query ها
        results = []
        for test_case in COMPREHENSIVE_TESTS:
            result = await test_single_query(session, test_case)
            results.append(result)
            await asyncio.sleep(1)
        
        # خلاصه نتایج
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("="*80)
        
        successful = sum(1 for r in results if r.get("success"))
        total = len(results)
        
        print(f"\n✅ Successful: {successful}/{total}")
        print(f"❌ Failed: {total - successful}/{total}")
        
        # دسته‌بندی بر اساس category
        categories = {}
        for r in results:
            if r.get("success"):
                cat = r['test_case']['category']
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(r)
        
        print("\n📊 Results by Category:")
        for cat, cat_results in categories.items():
            avg_conf = sum(r.get('confidence', 0) for r in cat_results) / len(cat_results) if cat_results else 0
            print(f"  {cat}: {len(cat_results)} tests, avg confidence: {avg_conf:.2f}")
        
        # Dynamic Top-K Analysis
        print("\n🔢 Dynamic Top-K Analysis:")
        for r in results:
            if r.get("success"):
                dtk = r.get('dynamic_top_k', 'N/A')
                print(f"  {r['query'][:50]}...: {dtk}")
        
        # RAGAS Metrics Summary
        print("\n📊 RAGAS Metrics Summary:")
        all_ragas = [r.get('ragas_metrics', {}) for r in results if r.get('success') and r.get('ragas_metrics')]
        if all_ragas:
            # محاسبه میانگین
            import numpy as np
            for category in ['retrieval', 'generation', 'end_to_end']:
                cat_metrics = [m.get(category, {}) for m in all_ragas if category in m]
                if cat_metrics:
                    print(f"\n  {category.upper()}:")
                    # استخراج کلیدهای مشترک
                    all_keys = set()
                    for cm in cat_metrics:
                        all_keys.update(cm.keys())
                    
                    for key in all_keys:
                        values = [cm.get(key, 0) for cm in cat_metrics if key in cm]
                        if values:
                            avg = np.mean(values)
                            # user_satisfaction باید به صورت عدد (0-5) نمایش داده شود، نه درصد
                            if key == 'user_satisfaction':
                                print(f"    - {key}: {avg:.2f}/5.0")
                            else:
                                print(f"    - {key}: {avg:.2%}")
        else:
            print("  No RAGAS metrics available")
        
        # ذخیره نتایج
        output_file = f"zabete_comprehensive_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "collection": COLLECTION_NAME,
                "api_url": API_BASE_URL,
                "total_tests": total,
                "successful": successful,
                "results": results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        print("\n✅ Comprehensive test completed!")


if __name__ == "__main__":
    asyncio.run(main())

