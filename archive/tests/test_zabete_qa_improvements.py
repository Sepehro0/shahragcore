# -*- coding: utf-8 -*-
"""
Test Script for zabete_qa Collection Improvements
تست query های مشکل‌دار قبلی برای بررسی بهبودها
"""

import asyncio
import json
import aiohttp
from datetime import datetime
from typing import List, Dict, Any

# Query های مشکل‌دار قبلی
TEST_QUERIES = [
    {
        "query": "در مورد قراردادهای qbc امکان پاسخگویی به این سوال بر اساس دیتابیس وجود ندارد",
        "expected_behavior": "باید تشخیص دهد که query نامرتبط است و پیام مناسب بدهد",
        "issue": "قبلاً پاسخ اشتباه می‌داد"
    },
    {
        "query": "تاخیر در پرداخت قراردادهای طرح و ساخت چگونه است",
        "expected_behavior": "باید از چند منبع استنتاج کند و پاسخ جامع بدهد",
        "issue": "قبلاً فقط از منبع دوم استفاده می‌کرد"
    },
    {
        "query": "تاخیر در پرداخت قراردادهای EPC چگونه است",
        "expected_behavior": "باید نتایج مرتبط‌تر پیدا کند",
        "issue": "قبلاً نتایج نامرتبط پیدا می‌کرد"
    },
    {
        "query": "توضیح ماده 46 شرایط عمومی پیمان",
        "expected_behavior": "باید از محتوای متن استفاده کند و از maddeh_id استفاده نکند",
        "issue": "قبلاً از maddeh_id استفاده می‌کرد و اعداد اشتباه می‌داد"
    },
    {
        "query": "قراردادهای QBC چگونه است",
        "expected_behavior": "باید تشخیص دهد که query نامرتبط است",
        "issue": "قبلاً پاسخ اشتباه می‌داد"
    }
]

API_BASE_URL = "http://localhost:8010"
COLLECTION_NAME = "zabete_qa"


async def test_query(
    session: aiohttp.ClientSession,
    query: str,
    query_info: Dict[str, Any]
) -> Dict[str, Any]:
    """تست یک query"""
    print(f"\n{'='*80}")
    print(f"🔍 Testing Query: {query}")
    print(f"📋 Expected: {query_info['expected_behavior']}")
    print(f"⚠️  Previous Issue: {query_info['issue']}")
    print(f"{'='*80}\n")
    
    try:
        # ارسال درخواست به API
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
                    "query_info": query_info
                }
            
            result = await response.json()
            
            # استخراج اطلاعات مهم
            answer = result.get("answer", "")
            confidence = result.get("confidence", 0.0)
            # در V2، top_results به sources تبدیل شده
            top_results = result.get("sources", result.get("top_results", []))
            metadata = result.get("metadata", {})
            
            # بررسی relevance
            is_relevant = metadata.get("relevance_score", 1.0) >= 0.5
            relevance_message = metadata.get("relevance_message")
            
            # بررسی hallucination
            hallucination_detected = metadata.get("hallucination_detected", False)
            faithfulness_score = metadata.get("faithfulness_score", 1.0)
            
            # بررسی confidence breakdown
            confidence_breakdown = metadata.get("confidence_breakdown", {})
            
            # نمایش نتایج
            print(f"✅ Response received")
            print(f"📊 Confidence: {confidence:.2f}")
            print(f"🔗 Relevance: {is_relevant} (score: {metadata.get('relevance_score', 'N/A')})")
            if relevance_message:
                print(f"⚠️  Relevance Message: {relevance_message}")
            print(f"🎯 Hallucination Detected: {hallucination_detected}")
            print(f"📈 Faithfulness Score: {faithfulness_score:.2f}")
            
            if confidence_breakdown:
                print(f"📊 Confidence Breakdown:")
                for key, value in confidence_breakdown.items():
                    print(f"   - {key}: {value:.2f}" if isinstance(value, (int, float)) else f"   - {key}: {value}")
            
            print(f"\n📝 Answer ({len(answer)} chars):")
            print(f"{answer[:500]}..." if len(answer) > 500 else answer)
            
            print(f"\n📚 Top Results ({len(top_results)}):")
            for i, result_item in enumerate(top_results[:3], 1):
                score = result_item.get("score", 0.0)
                metadata_item = result_item.get("metadata", {})
                question = metadata_item.get("question", "N/A")[:50]
                print(f"   {i}. Score: {score:.2f} | Question: {question}...")
            
            return {
                "query": query,
                "success": True,
                "answer": answer,
                "confidence": confidence,
                "is_relevant": is_relevant,
                "relevance_message": relevance_message,
                "hallucination_detected": hallucination_detected,
                "faithfulness_score": faithfulness_score,
                "confidence_breakdown": confidence_breakdown,
                "top_results_count": len(top_results),
                "query_info": query_info
            }
            
    except asyncio.TimeoutError:
        return {
            "query": query,
            "success": False,
            "error": "Timeout",
            "query_info": query_info
        }
    except Exception as e:
        return {
            "query": query,
            "success": False,
            "error": str(e),
            "query_info": query_info
        }


async def check_api_health(session: aiohttp.ClientSession) -> bool:
    """بررسی سلامت API"""
    try:
        async with session.get(f"{API_BASE_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
            return response.status == 200
    except:
        return False


async def main():
    """تابع اصلی"""
    print("🚀 Starting zabete_qa Improvements Test")
    print(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 API URL: {API_BASE_URL}")
    print(f"📚 Collection: {COLLECTION_NAME}")
    print("\n" + "="*80)
    
    async with aiohttp.ClientSession() as session:
        # بررسی سلامت API
        print("\n🔍 Checking API health...")
        if not await check_api_health(session):
            print("❌ API is not responding. Please start the API server first.")
            print("   Run: cd /home/user01/qwen-api/enhanced_rag_system_dev && python api_server.py")
            return
        
        print("✅ API is healthy\n")
        
        # تست query ها
        results = []
        for query_info in TEST_QUERIES:
            result = await test_query(session, query_info["query"], query_info)
            results.append(result)
            await asyncio.sleep(1)  # کمی تاخیر بین query ها
        
        # خلاصه نتایج
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        
        successful = sum(1 for r in results if r.get("success"))
        total = len(results)
        
        print(f"\n✅ Successful: {successful}/{total}")
        print(f"❌ Failed: {total - successful}/{total}")
        
        print("\n📈 Confidence Scores:")
        for r in results:
            if r.get("success"):
                print(f"   - {r['query'][:50]}...: {r.get('confidence', 0):.2f}")
        
        print("\n🎯 Relevance Check:")
        for r in results:
            if r.get("success"):
                is_relevant = r.get("is_relevant", True)
                status = "✅ Relevant" if is_relevant else "❌ Not Relevant"
                print(f"   - {r['query'][:50]}...: {status}")
        
        print("\n🔍 Hallucination Detection:")
        for r in results:
            if r.get("success"):
                detected = r.get("hallucination_detected", False)
                faithfulness = r.get("faithfulness_score", 1.0)
                status = "⚠️  Detected" if detected else "✅ No Hallucination"
                print(f"   - {r['query'][:50]}...: {status} (faithfulness: {faithfulness:.2f})")
        
        # ذخیره نتایج
        output_file = f"zabete_qa_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "collection": COLLECTION_NAME,
                "api_url": API_BASE_URL,
                "results": results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(main())

