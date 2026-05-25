# -*- coding: utf-8 -*-
"""
حذف و ساخت مجدد collection karbaran_omomi و تست
"""

import asyncio
import logging
from pathlib import Path
from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def recreate_and_test():
    """حذف، ساخت مجدد و تست collection"""
    rag = UltimateRAGSystem()
    collection_name = "karbaran_omomi"
    
    # 1. حذف collection موجود
    logger.info(f"🗑️  حذف collection {collection_name}...")
    try:
        collections = await rag.get_collections()
        if collection_name in collections:
            # حذف collection
            try:
                rag.chroma_client.delete_collection(collection_name)
                logger.info(f"✅ Collection {collection_name} حذف شد")
            except Exception as e:
                logger.warning(f"⚠️ خطا در حذف collection: {e}")
                # تلاش برای حذف با روش دیگر
                try:
                    collection = rag.chroma_client.get_collection(collection_name)
                    # حذف تمام اسناد
                    all_docs = collection.get()
                    if all_docs.get('ids'):
                        collection.delete(ids=all_docs['ids'])
                    logger.info(f"✅ اسناد collection {collection_name} حذف شدند")
                except Exception as e2:
                    logger.error(f"❌ نتوانست collection را حذف کند: {e2}")
        else:
            logger.info(f"ℹ️ Collection {collection_name} وجود ندارد")
    except Exception as e:
        logger.warning(f"⚠️ خطا در بررسی collection: {e}")
    
    # کمی صبر برای اطمینان از حذف
    await asyncio.sleep(2)
    
    # 2. خواندن فایل Excel
    excel_path = Path("/home/user01/qwen-api/enhanced_rag_system/karbaran-omomi.xlsx")
    if not excel_path.exists():
        logger.error(f"❌ فایل Excel پیدا نشد: {excel_path}")
        await rag.close()
        return
    
    logger.info(f"📄 خواندن فایل Excel: {excel_path}")
    with open(excel_path, 'rb') as f:
        excel_bytes = f.read()
    
    # 3. Process کردن دوباره
    logger.info(f"🔄 ساخت مجدد collection {collection_name}...")
    result = await rag.process_excel(
        file_bytes=excel_bytes,
        filename="karbaran-omomi.xlsx",
        collection_name=collection_name
    )
    
    if not result.get('success'):
        logger.error(f"❌ ساخت collection ناموفق بود: {result.get('error')}")
        await rag.close()
        return
    
    logger.info(f"✅ Collection با موفقیت ساخته شد!")
    logger.info(f"   - Chunks: {result.get('chunks_count', 0)}")
    logger.info(f"   - Documents: {result.get('documents_count', 0)}")
    
    # کمی صبر برای اطمینان از ذخیره‌سازی
    await asyncio.sleep(2)
    
    # 4. تست سوالات
    logger.info("\n" + "="*80)
    logger.info("🧪 شروع تست سوالات")
    logger.info("="*80)
    
    test_queries = [
        "من چطوری می تونم از موسسه دانشمند سرمایه بگیرم؟",
        "تمرکزتون روی چیه؟",
        "مزیت این صندوق چیه؟",
        "چه حوزه‌هایی رو پوشش می‌دید و چه مزایایی دارید؟",
        "فرآیند سرمایه‌گذاری چطوریه و چه مدت طول می‌کشه؟",
        "معیارهای پذیرش طرح‌ها چیه و چه نوع طرح‌هایی رو قبول می‌کنید؟",
        "اگر من یک استارتاپ در حوزه فناوری داشته باشم، چطور می‌تونم از شما سرمایه بگیرم و چه مراحلی باید طی کنم و چه مدت طول می‌کشه؟",
        "مزیت‌های سرمایه‌گذاری در این صندوق چیه و چه حوزه‌هایی رو پوشش می‌دید و فرآیند چطوریه؟",
        "چه معیارهایی برای پذیرش طرح‌ها دارید و چه نوع طرح‌هایی رو قبول می‌کنید و فرآیند ارزیابی چطوریه؟",
        "تفاوت این صندوق با صندوق‌های دیگه چیه و مزیت‌های خاص شما چیه؟",
        "اگر طرح من در حوزه کشاورزی باشه، چه مزایایی دارم و چطور می‌تونم اقدام کنم؟"
    ]
    
    results_summary = {
        'total': len(test_queries),
        'successful': 0,
        'failed': 0,
        'with_llm': 0,
        'with_multi_hop': 0,
        'issues': []
    }
    
    for i, query in enumerate(test_queries, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"📋 تست {i}/{len(test_queries)}")
        logger.info(f"🔍 سوال: {query}")
        logger.info(f"{'='*80}")
        
        try:
            result = await rag.retrieve_and_answer(
                query=query,
                collection_name=collection_name,
                top_k=5,
                use_reranking=True,
                use_multi_hop=True
            )
            
            if result.get('success'):
                answer = result.get('answer', '')
                used_multi_hop = result.get('used_multi_hop', False)
                is_llm_generated = result.get('is_llm_generated', False)
                answer_provider = result.get('answer_provider')
                answer_mode = result.get('metadata', {}).get('answer_mode', 'unknown')
                
                results_summary['successful'] += 1
                if is_llm_generated:
                    results_summary['with_llm'] += 1
                if used_multi_hop:
                    results_summary['with_multi_hop'] += 1
                
                logger.info(f"\n✅ پاسخ دریافت شد:")
                logger.info(f"   📝 طول: {len(answer)} کاراکتر")
                logger.info(f"   🧠 Query Understanding: ✅")
                logger.info(f"   🔄 Multi-Hop: {'✅' if used_multi_hop else '❌'}")
                logger.info(f"   🤖 LLM Generated: {'✅' if is_llm_generated else '❌'}")
                logger.info(f"   📊 Answer Provider: {answer_provider or 'N/A'}")
                logger.info(f"   🎯 Answer Mode: {answer_mode}")
                
                # بررسی مشکلات
                issues = []
                if len(answer) < 50:
                    issues.append("پاسخ خیلی کوتاه")
                if answer.count('،') > 5 and len(answer.split('،')) > 6:
                    issues.append("فقط لیست است")
                if "مالی و سرمایه گذاری" in answer and answer.count("مالی و سرمایه گذاری") > 1:
                    issues.append("تکرار عبارات")
                
                if issues:
                    results_summary['issues'].append({
                        'query': query[:50] + "...",
                        'issues': issues
                    })
                    logger.warning(f"   ⚠️ مشکلات: {', '.join(issues)}")
                
                # نمایش بخشی از پاسخ
                preview = answer[:300] + "..." if len(answer) > 300 else answer
                logger.info(f"\n📄 پاسخ:")
                logger.info(f"   {preview}")
            else:
                results_summary['failed'] += 1
                error = result.get('error', 'Unknown error')
                logger.error(f"\n❌ خطا: {error}")
        
        except Exception as e:
            results_summary['failed'] += 1
            logger.error(f"\n❌ استثنا: {e}")
            import traceback
            traceback.print_exc()
        
        await asyncio.sleep(1)
    
    # خلاصه نتایج
    logger.info("\n" + "="*80)
    logger.info("📊 خلاصه نتایج")
    logger.info("="*80)
    logger.info(f"✅ موفق: {results_summary['successful']}/{results_summary['total']}")
    logger.info(f"❌ ناموفق: {results_summary['failed']}/{results_summary['total']}")
    logger.info(f"🤖 LLM Generated: {results_summary['with_llm']}/{results_summary['total']}")
    logger.info(f"🔄 Multi-Hop: {results_summary['with_multi_hop']}/{results_summary['total']}")
    
    if results_summary['issues']:
        logger.info(f"\n⚠️ مشکلات شناسایی شده:")
        for item in results_summary['issues']:
            logger.info(f"   - {item['query']}: {', '.join(item['issues'])}")
    
    await rag.close()


if __name__ == "__main__":
    asyncio.run(recreate_and_test())

