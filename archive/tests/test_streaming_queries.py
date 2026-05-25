#!/usr/bin/env python3
"""
تست سوالات مشخص با استفاده از Streaming API
"""
import asyncio
import httpx
import json
import logging
from typing import Dict, Any, List
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_URL = "http://localhost:8010/v2/query/streaming"

# سوالات برای تست
TEST_QUERIES = {
    "karbaran_omomi": [
        "راه های ارتباطی با تیم سرمایه گذاری",
        "چگونه می توانم طرحم را برای شما ارسال کنم؟",
        "پس از ثبت نام در فراخوان پروژه های فناورانه پشتیبانی و ارتباط با شبکه به چه صورت خواهد بود؟",
        "آیا امکان دریافت راهنمایی مستقیم از کارشناسان وجود دارد؟",
        "در صورت موفقیت پروژه، ادامه همکاری با صنعت چگونه پیگیری می‌شود؟"
    ],
    "zinaf_dakheli": [
        "اگر به مشکل خوردم چیکار کنم ؟",
        "چه نوع آموزش‌هایی داده میشه؟",
        "آیا دوره‌ها به‌صورت حضوری، آنلاین یا ترکیبی برگزار می‌شوند؟"
    ]
}


async def test_streaming_query(query: str, collection_name: str) -> Dict[str, Any]:
    """
    تست یک سوال با streaming API
    """
    payload = {
        "query": query,
        "collection_name": collection_name,
        "top_k": 10,
        "use_reranking": True,
        "use_multi_hop": False,
        "temperature": 0.1
    }
    
    logger.info(f"\n{'='*80}")
    logger.info(f"📝 سوال: {query}")
    logger.info(f"📁 Collection: {collection_name}")
    logger.info(f"{'='*80}")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                API_URL,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()
                
                full_answer = ""
                full_text = ""
                answer = ""
                events_received = []
                sources = []
                metadata = {}
                confidence = 0.0
                success = False
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        try:
                            event_data = json.loads(data_str)
                            event_type = event_data.get("type", "unknown")
                            events_received.append(event_type)
                            
                            if event_type == "start":
                                logger.info("✅ [START] Streaming started")
                                
                            elif event_type == "token":
                                token = event_data.get("token", "")
                                if token:
                                    answer += token
                                    print(token, end="", flush=True)
                                
                                # جمع‌آوری full_answer و full_text از token events
                                if "full_answer" in event_data:
                                    full_answer = event_data.get("full_answer", "")
                                if "full_text" in event_data:
                                    full_text = event_data.get("full_text", "")
                                
                            elif event_type == "complete":
                                success = event_data.get("success", False)
                                full_answer = event_data.get("full_answer", full_answer)
                                full_text = event_data.get("full_text", full_text)
                                answer = event_data.get("answer", answer)
                                sources = event_data.get("sources", [])
                                metadata = event_data.get("metadata", {})
                                confidence = event_data.get("confidence", 0.0)
                                
                                logger.info(f"\n\n✅ [COMPLETE] Streaming completed")
                                logger.info(f"   Success: {success}")
                                logger.info(f"   Confidence: {confidence:.3f}")
                                logger.info(f"   Answer length: {len(answer)} chars")
                                logger.info(f"   Full answer length: {len(full_answer)} chars")
                                logger.info(f"   Full text length: {len(full_text)} chars")
                                logger.info(f"   Sources count: {len(sources)}")
                                
                                # نمایش سوال منبع
                                if sources:
                                    source_question = sources[0].get("metadata", {}).get("question", "")
                                    if source_question:
                                        logger.info(f"   📄 Source question: {source_question[:100]}...")
                                
                                # بررسی تفاوت full_answer و full_text
                                if full_answer and full_text:
                                    if full_answer == full_text:
                                        logger.warning("   ⚠️  full_answer و full_text یکسان هستند!")
                                    else:
                                        logger.info("   ✅ full_answer و full_text متفاوت هستند (خوب است)")
                                
                                # بررسی events
                                logger.info(f"   Events received: {', '.join(set(events_received))}")
                                
                        except json.JSONDecodeError as e:
                            logger.warning(f"⚠️  Failed to parse JSON: {e}")
                            logger.warning(f"   Line: {line[:200]}")
                
                return {
                    "success": success,
                    "query": query,
                    "collection": collection_name,
                    "answer": answer,
                    "full_answer": full_answer,
                    "full_text": full_text,
                    "sources": sources,
                    "metadata": metadata,
                    "confidence": confidence,
                    "events": events_received
                }
                
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error: {e.response.status_code}")
        logger.error(f"   Response: {e.response.text[:500]}")
        return {
            "success": False,
            "error": f"HTTP {e.response.status_code}",
            "query": query,
            "collection": collection_name
        }
    except httpx.RequestError as e:
        logger.error(f"❌ Request error: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "collection": collection_name
        }
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "collection": collection_name
        }


async def main():
    """
    اجرای تست‌های streaming
    """
    logger.info("🚀 شروع تست Streaming API")
    logger.info(f"API URL: {API_URL}\n")
    
    results = []
    
    # تست سوالات karbaran_omomi
    logger.info("\n" + "="*80)
    logger.info("📚 تست کالکشن: karbaran_omomi")
    logger.info("="*80)
    
    for i, query in enumerate(TEST_QUERIES["karbaran_omomi"], 1):
        logger.info(f"\n[Test {i}/{len(TEST_QUERIES['karbaran_omomi'])}]")
        result = await test_streaming_query(query, "karbaran_omomi")
        results.append(result)
        await asyncio.sleep(1)  # کمی تاخیر بین تست‌ها
    
    # تست سوالات zinaf_dakheli
    logger.info("\n" + "="*80)
    logger.info("📚 تست کالکشن: zinaf_dakheli")
    logger.info("="*80)
    
    for i, query in enumerate(TEST_QUERIES["zinaf_dakheli"], 1):
        logger.info(f"\n[Test {i}/{len(TEST_QUERIES['zinaf_dakheli'])}]")
        result = await test_streaming_query(query, "zinaf_dakheli")
        results.append(result)
        await asyncio.sleep(1)  # کمی تاخیر بین تست‌ها
    
    # خلاصه نتایج
    logger.info("\n" + "="*80)
    logger.info("📊 خلاصه نتایج")
    logger.info("="*80)
    
    total = len(results)
    successful = sum(1 for r in results if r.get("success", False))
    failed = total - successful
    
    logger.info(f"✅ موفق: {successful}/{total}")
    logger.info(f"❌ ناموفق: {failed}/{total}")
    
    # نمایش جزئیات تست‌های ناموفق
    if failed > 0:
        logger.warning("\n⚠️  تست‌های ناموفق:")
        for r in results:
            if not r.get("success", False):
                logger.warning(f"   - {r.get('query', 'Unknown')} ({r.get('collection', 'Unknown')})")
                if "error" in r:
                    logger.warning(f"     Error: {r['error']}")
    
    # بررسی مشکلات احتمالی
    logger.info("\n" + "="*80)
    logger.info("🔍 بررسی مشکلات احتمالی")
    logger.info("="*80)
    
    identical_full_text_count = 0
    empty_answer_count = 0
    low_confidence_count = 0
    
    for r in results:
        if r.get("success", False):
            full_answer = r.get("full_answer", "")
            full_text = r.get("full_text", "")
            answer = r.get("answer", "")
            confidence = r.get("confidence", 0.0)
            
            if full_answer and full_text and full_answer == full_text:
                identical_full_text_count += 1
                logger.warning(f"⚠️  {r.get('query', 'Unknown')[:50]}...: full_answer == full_text")
            
            if not answer or len(answer.strip()) < 10:
                empty_answer_count += 1
                logger.warning(f"⚠️  {r.get('query', 'Unknown')[:50]}...: پاسخ خالی یا خیلی کوتاه")
            
            if confidence < 0.2:
                low_confidence_count += 1
                logger.warning(f"⚠️  {r.get('query', 'Unknown')[:50]}...: confidence پایین ({confidence:.3f})")
    
    if identical_full_text_count == 0 and empty_answer_count == 0 and low_confidence_count == 0:
        logger.info("✅ هیچ مشکل خاصی یافت نشد!")
    else:
        logger.info(f"   - full_answer == full_text: {identical_full_text_count} مورد")
        logger.info(f"   - پاسخ خالی/کوتاه: {empty_answer_count} مورد")
        logger.info(f"   - confidence پایین: {low_confidence_count} مورد")
    
    logger.info("\n" + "="*80)
    logger.info("✅ تست‌ها کامل شد")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())




