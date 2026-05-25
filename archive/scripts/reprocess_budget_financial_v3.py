#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
پردازش مجدد کامل collection budget_financial با فایل‌های جدید
این اسکریپت از تمام features سیستم استفاده می‌کند
"""

import sys
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from ultimate_rag_system import UltimateRAGSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/home/user01/qwen-api/enhanced_rag_system_dev/reprocess_budget_v3.log')
    ]
)

logger = logging.getLogger(__name__)

# Configuration
COLLECTION_NAME = "budget_financial"
EXCEL_FILES = [
    "/home/user01/qwen-api/enhanced_rag_system_dev/archive/data_files/masaref3.xlsx",
    "/home/user01/qwen-api/enhanced_rag_system_dev/archive/data_files/manabe3.xlsx"
]


async def delete_existing_collection(rag_system: UltimateRAGSystem):
    """حذف collection موجود (اگر وجود دارد)"""
    try:
        logger.info(f"🗑️ بررسی وجود collection '{COLLECTION_NAME}'...")
        
        # Get existing collections
        collections = rag_system.chroma_client.list_collections()
        collection_names = [col.name for col in collections]
        
        if COLLECTION_NAME in collection_names:
            logger.info(f"✅ Collection '{COLLECTION_NAME}' پیدا شد. در حال حذف...")
            rag_system.chroma_client.delete_collection(COLLECTION_NAME)
            logger.info(f"✅ Collection '{COLLECTION_NAME}' با موفقیت حذف شد")
            
            # Wait a bit to ensure deletion is complete
            await asyncio.sleep(2)
        else:
            logger.info(f"ℹ️ Collection '{COLLECTION_NAME}' وجود ندارد (نیازی به حذف نیست)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطا در حذف collection: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def process_excel_files(rag_system: UltimateRAGSystem):
    """پردازش فایل‌های Excel و ایجاد collection جدید"""
    total_chunks = 0
    
    for file_path in EXCEL_FILES:
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"🚀 شروع پردازش فایل: {os.path.basename(file_path)}")
            logger.info(f"{'='*80}")
            
            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"❌ فایل یافت نشد: {file_path}")
                continue
            
            # Read Excel file
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
            
            filename = os.path.basename(file_path)
            logger.info(f"✅ فایل خوانده شد: {len(file_bytes)} بایت")
            
            # Process Excel with all features
            logger.info(f"🔄 در حال پردازش Excel با تمام features...")
            result = await rag_system.process_excel(
                file_bytes=file_bytes,
                filename=filename,
                collection_name=COLLECTION_NAME
            )
            
            if result.get("success"):
                chunks_count = result.get("chunks_count", 0)
                total_chunks += chunks_count
                logger.info(f"✅ پردازش موفق!")
                logger.info(f"📊 تعداد chunks از این فایل: {chunks_count}")
                
                # Get domain info if available
                domain_info = result.get("domain_info")
                if domain_info:
                    logger.info(f"🏷️ Domain: {domain_info.get('domain')}")
                    logger.info(f"📊 Confidence: {domain_info.get('confidence', 0):.2f}")
                
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"❌ پردازش ناموفق: {error_msg}")
                
        except Exception as e:
            logger.error(f"❌ خطا در پردازش فایل {file_path}: {e}", exc_info=True)
    
    return total_chunks


async def verify_collection(rag_system: UltimateRAGSystem):
    """بررسی collection ایجاد شده"""
    logger.info(f"\n{'='*80}")
    logger.info("🔍 بررسی collection ایجاد شده")
    logger.info(f"{'='*80}")
    
    try:
        collection = rag_system.chroma_client.get_collection(COLLECTION_NAME)
        doc_count = collection.count()
        
        logger.info(f"\n✅ Collection: {collection.name}")
        logger.info(f"📊 تعداد کل اسناد: {doc_count}")
        
        # Get sample documents
        if doc_count > 0:
            sample_results = collection.peek(limit=min(3, doc_count))
            
            logger.info(f"\n📄 نمونه اسناد:")
            for i, (doc_id, doc_text, metadata) in enumerate(zip(
                sample_results.get('ids', []),
                sample_results.get('documents', []),
                sample_results.get('metadatas', [])
            ), 1):
                logger.info(f"\n{'─'*80}")
                logger.info(f"سند {i}:")
                logger.info(f"{'─'*80}")
                logger.info(f"ID: {doc_id}")
                logger.info(f"Text Preview: {doc_text[:200]}...")
                logger.info(f"Metadata Keys: {list(metadata.keys())}")
        
        return True
            
    except Exception as e:
        logger.error(f"❌ خطا در بررسی collection: {e}", exc_info=True)
        return False


async def test_queries(rag_system: UltimateRAGSystem):
    """تست collection با سوالات مالی"""
    test_queries = [
        "اعتبارات هزینه ای مرکز آمار ایران در سال 1403 چقدره؟",
        "منابع پارک فناوری پردیس سال 99",
        "هزینه های سازمان تعزيرات حكومتی در سال 1400",
        "منابع شرکت پست بانک در سالهای 400 تا 403"
    ]
    
    results = []
    
    logger.info(f"\n{'='*80}")
    logger.info("🧪 شروع تست با سوالات مالی")
    logger.info(f"{'='*80}")
    
    for i, query in enumerate(test_queries, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"📝 تست {i}/{len(test_queries)}")
        logger.info(f"Query: {query}")
        logger.info(f"{'='*80}")
        
        try:
            start_time = datetime.now()
            
            # Query the collection
            response = await rag_system.retrieve_and_answer(
                query=query,
                collection_name=COLLECTION_NAME,
                top_k=8,
                use_reranking=True,
                use_multi_hop=True
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            if response.get("success"):
                answer = response.get("answer", "")
                sources = response.get("top_results", [])
                confidence = response.get("confidence", 0.0)
                
                logger.info(f"\n✅ موفق - زمان: {elapsed:.2f} ثانیه")
                logger.info(f"📊 Confidence: {confidence:.3f}")
                logger.info(f"📚 تعداد منابع: {len(sources)}")
                
                # Show top sources
                if sources:
                    logger.info(f"\n📚 Top 3 منابع:")
                    for idx, source in enumerate(sources[:3], 1):
                        score = source.get('score', 0.0)
                        metadata = source.get('metadata', {})
                        
                        # Extract key info
                        dastgah = metadata.get('عنوان دستگاه اجرايي ', 
                                              metadata.get('عنوان دستگاه اجرایی', 'N/A'))
                        sal = metadata.get('سال ', metadata.get('سال', 'N/A'))
                        
                        logger.info(f"\n   {idx}. Score: {score:.3f}")
                        logger.info(f"      دستگاه: {dastgah}")
                        logger.info(f"      سال: {sal}")
                
                logger.info(f"\n📄 پاسخ ({len(answer)} کاراکتر):")
                logger.info(f"{'─'*80}")
                logger.info(answer[:500] + "..." if len(answer) > 500 else answer)
                logger.info(f"{'─'*80}")
                
                results.append({
                    "query": query,
                    "success": True,
                    "answer": answer,
                    "sources_count": len(sources),
                    "confidence": confidence,
                    "elapsed": elapsed
                })
            else:
                error = response.get("error", "Unknown error")
                logger.error(f"\n❌ ناموفق: {error}")
                results.append({
                    "query": query,
                    "success": False,
                    "error": error,
                    "elapsed": elapsed
                })
                
        except Exception as e:
            logger.error(f"\n❌ خطا در تست: {e}", exc_info=True)
            results.append({
                "query": query,
                "success": False,
                "error": str(e)
            })
        
        # Wait between queries
        await asyncio.sleep(2)
    
    return results


async def main():
    """تابع اصلی"""
    logger.info("\n" + "="*80)
    logger.info("🚀 پردازش مجدد کامل collection budget_financial")
    logger.info(f"📁 فایل‌های منبع:")
    for f in EXCEL_FILES:
        logger.info(f"   - {os.path.basename(f)}")
    logger.info("="*80)
    
    try:
        # Step 1: Initialize RAG system
        logger.info("\n📦 در حال راه‌اندازی سیستم RAG...")
        rag_system = UltimateRAGSystem(
            db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db",
            enable_semantic_chunking=True,
            enable_query_understanding=True,
            enable_advanced_retrieval=True,
            retrieval_strategy="hybrid"
        )
        logger.info("✅ سیستم RAG راه‌اندازی شد")
        
        # Step 2: Delete existing collection
        logger.info("\n" + "="*80)
        logger.info("🗑️ مرحله 1: حذف collection موجود")
        logger.info("="*80)
        
        delete_success = await delete_existing_collection(rag_system)
        if not delete_success:
            logger.warning("⚠️ خطا در حذف collection، اما ادامه می‌دهیم...")
        
        # Step 3: Process Excel files
        logger.info("\n" + "="*80)
        logger.info("🔄 مرحله 2: پردازش فایل‌های Excel")
        logger.info("="*80)
        
        total_chunks = await process_excel_files(rag_system)
        
        if total_chunks == 0:
            logger.error("❌ هیچ chunk ایجاد نشد. خروج...")
            return
        
        logger.info(f"\n✅ پردازش فایل‌ها کامل شد!")
        logger.info(f"📊 تعداد کل chunks: {total_chunks}")
        
        # Step 4: Verify collection
        logger.info("\n" + "="*80)
        logger.info("🔍 مرحله 3: بررسی collection")
        logger.info("="*80)
        
        verify_success = await verify_collection(rag_system)
        if not verify_success:
            logger.warning("⚠️ خطا در بررسی collection")
        
        # Step 5: Test queries
        logger.info("\n" + "="*80)
        logger.info("🧪 مرحله 4: تست با سوالات مالی")
        logger.info("="*80)
        
        test_results = await test_queries(rag_system)
        
        # Step 6: Summary
        logger.info("\n" + "="*80)
        logger.info("📊 خلاصه نتایج")
        logger.info("="*80)
        
        logger.info(f"\n✅ Collection name: {COLLECTION_NAME}")
        logger.info(f"✅ فایل‌های پردازش شده: {len(EXCEL_FILES)}")
        logger.info(f"✅ تعداد chunks: {total_chunks}")
        
        successful_tests = sum(1 for r in test_results if r.get("success", False))
        total_tests = len(test_results)
        
        logger.info(f"\n🧪 نتایج تست:")
        logger.info(f"  ✅ موفق: {successful_tests}/{total_tests}")
        logger.info(f"  📈 نرخ موفقیت: {(successful_tests/total_tests)*100:.1f}%")
        
        logger.info(f"\n📋 جزئیات تست‌ها:")
        for i, result in enumerate(test_results, 1):
            status = "✅" if result.get("success", False) else "❌"
            query = result.get("query", "")
            
            if result.get("success"):
                elapsed = result.get("elapsed", 0)
                confidence = result.get("confidence", 0.0)
                sources = result.get("sources_count", 0)
                logger.info(
                    f"  {status} تست {i}: {query[:80]}... "
                    f"(زمان: {elapsed:.2f}s, Confidence: {confidence:.3f}, منابع: {sources})"
                )
            else:
                error = result.get("error", "Unknown")
                logger.info(f"  {status} تست {i}: {query[:80]}... (خطا: {error})")
        
        logger.info("\n" + "="*80)
        logger.info("✅ پردازش مجدد و تست کامل شد!")
        logger.info("="*80)
        logger.info(f"\n📁 Collection: {COLLECTION_NAME}")
        logger.info(f"📝 Log: /home/user01/qwen-api/enhanced_rag_system_dev/reprocess_budget_v3.log")
        
        # Final verdict
        if successful_tests == total_tests:
            logger.info("\n🎉 تمام تست‌ها موفق بودند! Collection آماده استفاده است.")
        elif successful_tests >= total_tests * 0.75:
            logger.info(f"\n✅ {(successful_tests/total_tests)*100:.0f}% تست‌ها موفق بودند.")
        else:
            logger.warning(f"\n⚠️ فقط {(successful_tests/total_tests)*100:.0f}% تست‌ها موفق بودند.")
        
    except Exception as e:
        logger.error(f"\n❌ خطای کلی: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
