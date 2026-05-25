#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
پردازش مجدد کامل collection karbaran_omomi با فایل جدید v3
این اسکریپت از تمام features سیستم استفاده می‌کند:
- Dynamic Schema Analysis
- Domain Classification
- Persian Embedding
- Advanced Chunking
- Reranking & Multi-hop
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
        logging.FileHandler('/home/user01/qwen-api/enhanced_rag_system_dev/reprocess_karbaran_omomi_v3.log')
    ]
)

logger = logging.getLogger(__name__)

# Configuration
COLLECTION_NAME = "karbaran_omomi"
EXCEL_FILE_PATH = "/home/user01/qwen-api/enhanced_rag_system_dev/archive/data_files/karbaran_omomi-v3.xlsx"


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


async def process_excel_file(rag_system: UltimateRAGSystem):
    """پردازش فایل Excel و ایجاد collection جدید"""
    try:
        logger.info("🚀 شروع پردازش فایل Excel...")
        
        # Check if file exists
        logger.info(f"📖 بررسی فایل: {EXCEL_FILE_PATH}")
        if not os.path.exists(EXCEL_FILE_PATH):
            raise FileNotFoundError(f"فایل یافت نشد: {EXCEL_FILE_PATH}")
        
        # Read Excel file
        with open(EXCEL_FILE_PATH, 'rb') as f:
            file_bytes = f.read()
        
        filename = os.path.basename(EXCEL_FILE_PATH)
        logger.info(f"✅ فایل خوانده شد: {len(file_bytes)} بایت")
        
        # Process Excel with all features
        logger.info(f"🔄 در حال پردازش Excel با تمام features سیستم...")
        logger.info(f"   📊 Dynamic Schema Analysis: ENABLED")
        logger.info(f"   🏷️ Domain Classification: ENABLED")
        logger.info(f"   🇮🇷 Persian Embedding: ENABLED")
        logger.info(f"   📝 Advanced Chunking: ENABLED")
        
        result = await rag_system.process_excel(
            file_bytes=file_bytes,
            filename=filename,
            collection_name=COLLECTION_NAME
        )
        
        if result.get("success"):
            chunks_count = result.get("chunks_count", 0)
            logger.info(f"✅ پردازش با موفقیت انجام شد!")
            logger.info(f"📊 تعداد chunks ایجاد شده: {chunks_count}")
            logger.info(f"📁 Collection name: {COLLECTION_NAME}")
            
            # Get collection info
            try:
                collection = rag_system.chroma_client.get_collection(COLLECTION_NAME)
                doc_count = collection.count()
                logger.info(f"📈 تعداد اسناد در collection: {doc_count}")
                
                # Get domain info if available
                domain_info = result.get("domain_info")
                if domain_info:
                    logger.info(f"🏷️ Domain: {domain_info.get('domain')}")
                    logger.info(f"📊 Confidence: {domain_info.get('confidence', 0):.2f}")
                    logger.info(f"🔑 Keywords: {domain_info.get('keywords', [])}")
                
            except Exception as e:
                logger.warning(f"⚠️ نتوانست اطلاعات collection را دریافت کند: {e}")
            
            return {
                "success": True,
                "collection_name": COLLECTION_NAME,
                "chunks_count": chunks_count,
                "result": result
            }
        else:
            error_msg = result.get("error", "Unknown error")
            logger.error(f"❌ پردازش ناموفق بود: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
            
    except Exception as e:
        logger.error(f"❌ خطا در پردازش: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


async def test_collection(rag_system: UltimateRAGSystem):
    """تست collection با سوالات مختلف"""
    test_queries = [
        # سوالات عمومی
        "سناریوی شکست چیست؟",
        "استراتژی خروج چیه؟",
        "چطوری به سرمایه گذار معرفی میشیم؟",
        
        # سوالات اختصاصی
        "وظایف معاونت برنامه ریزی و توسعه فناوری چیه؟",
        "مدیریت پایانه های فروش رو چه کسی انجام میده؟",
        
        # سوالات colloquial
        "اگه تیم ما شکست بخوره چی میشه؟",
        "توی صندوق ها، چجوری به سرمایه گذار معرفی میشیم؟",
    ]
    
    results = []
    
    logger.info("\n" + "="*80)
    logger.info("🧪 شروع تست collection با سوالات مختلف")
    logger.info("="*80)
    
    for i, query in enumerate(test_queries, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"📝 تست {i}/{len(test_queries)}")
        logger.info(f"Query: {query}")
        logger.info(f"{'='*80}")
        
        try:
            start_time = datetime.now()
            
            # Query the collection with all features enabled
            response = await rag_system.retrieve_and_answer(
                query=query,
                collection_name=COLLECTION_NAME,
                top_k=5,
                use_reranking=True,
                use_multi_hop=True
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            if response.get("success"):
                answer = response.get("answer", "")
                sources = response.get("top_results", [])
                confidence = response.get("confidence", 0.0)
                top_score = response.get("top_score", 0.0)
                
                logger.info(f"\n✅ موفق - زمان: {elapsed:.2f} ثانیه")
                logger.info(f"📊 Confidence: {confidence:.3f}")
                logger.info(f"📊 Top Score: {top_score:.3f}")
                logger.info(f"📚 تعداد منابع: {len(sources)}")
                
                # Show top sources
                if sources:
                    logger.info(f"\n📚 Top {min(3, len(sources))} منابع:")
                    for idx, source in enumerate(sources[:3], 1):
                        score = source.get('score', 0.0)
                        content_preview = source.get('content', '')[:100]
                        metadata = source.get('metadata', {})
                        
                        logger.info(f"\n   {idx}. Score: {score:.3f}")
                        logger.info(f"      Content: {content_preview}...")
                        logger.info(f"      Metadata: {metadata}")
                
                logger.info(f"\n📄 پاسخ ({len(answer)} کاراکتر):")
                logger.info(f"{'─'*80}")
                logger.info(answer)
                logger.info(f"{'─'*80}")
                
                results.append({
                    "query": query,
                    "success": True,
                    "answer": answer,
                    "sources_count": len(sources),
                    "confidence": confidence,
                    "top_score": top_score,
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
        
        # Wait a bit between queries
        await asyncio.sleep(1)
    
    return results


async def analyze_collection(rag_system: UltimateRAGSystem):
    """آنالیز دقیق collection"""
    logger.info("\n" + "="*80)
    logger.info("🔍 آنالیز دقیق collection")
    logger.info("="*80)
    
    try:
        # Get collection
        collection = rag_system.chroma_client.get_collection(COLLECTION_NAME)
        
        # Count documents
        doc_count = collection.count()
        logger.info(f"\n📊 تعداد کل اسناد: {doc_count}")
        
        # Get sample documents
        if doc_count > 0:
            sample_results = collection.peek(limit=min(5, doc_count))
            
            logger.info(f"\n📄 نمونه اسناد (اولین {len(sample_results.get('ids', []))} سند):")
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
                
                # Show important metadata
                if 'question' in metadata:
                    logger.info(f"   Question: {metadata['question']}")
                if 'answer' in metadata:
                    logger.info(f"   Answer Preview: {metadata['answer'][:100]}...")
                if 'dataset_type' in metadata:
                    logger.info(f"   Dataset Type: {metadata['dataset_type']}")
        
        # Get collection metadata
        collection_metadata = collection.metadata or {}
        if collection_metadata:
            logger.info(f"\n📋 Collection Metadata:")
            for key, value in collection_metadata.items():
                logger.info(f"  {key}: {value}")
        
        return True
            
    except Exception as e:
        logger.error(f"❌ خطا در آنالیز: {e}", exc_info=True)
        return False


async def main():
    """تابع اصلی"""
    logger.info("\n" + "="*80)
    logger.info("🚀 پردازش مجدد کامل collection karbaran_omomi")
    logger.info(f"📁 فایل جدید: {EXCEL_FILE_PATH}")
    logger.info("="*80)
    
    try:
        # Step 1: Initialize RAG system with all features
        logger.info("\n📦 در حال راه‌اندازی سیستم RAG با تمام features...")
        rag_system = UltimateRAGSystem(
            db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db",
            enable_semantic_chunking=True,
            enable_query_understanding=True,
            enable_advanced_retrieval=True,
            enable_multimodal=False,
            enable_self_rag=True,
            enable_corrective_rag=True,
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
        
        # Step 3: Process new Excel file
        logger.info("\n" + "="*80)
        logger.info("🔄 مرحله 2: پردازش فایل Excel جدید")
        logger.info("="*80)
        
        process_result = await process_excel_file(rag_system)
        
        if not process_result.get("success"):
            logger.error("❌ پردازش فایل ناموفق بود. خروج...")
            return
        
        logger.info("\n✅ پردازش فایل با موفقیت انجام شد!")
        
        # Step 4: Analyze collection
        logger.info("\n" + "="*80)
        logger.info("🔍 مرحله 3: آنالیز collection جدید")
        logger.info("="*80)
        
        await analyze_collection(rag_system)
        
        # Step 5: Test collection
        logger.info("\n" + "="*80)
        logger.info("🧪 مرحله 4: تست collection با سوالات مختلف")
        logger.info("="*80)
        
        test_results = await test_collection(rag_system)
        
        # Step 6: Summary
        logger.info("\n" + "="*80)
        logger.info("📊 خلاصه نتایج")
        logger.info("="*80)
        
        logger.info(f"\n✅ Collection name: {COLLECTION_NAME}")
        logger.info(f"✅ تعداد chunks ایجاد شده: {process_result.get('chunks_count', 0)}")
        
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
                top_score = result.get("top_score", 0.0)
                logger.info(
                    f"  {status} تست {i}: {query[:60]}... "
                    f"(زمان: {elapsed:.2f}s, Confidence: {confidence:.3f}, Score: {top_score:.3f})"
                )
            else:
                error = result.get("error", "Unknown")
                logger.info(f"  {status} تست {i}: {query[:60]}... (خطا: {error})")
        
        logger.info("\n" + "="*80)
        logger.info("✅ پردازش مجدد و تست کامل شد!")
        logger.info("="*80)
        logger.info(f"\n📁 Collection name برای استفاده در API: {COLLECTION_NAME}")
        logger.info(f"📝 Log file: /home/user01/qwen-api/enhanced_rag_system_dev/reprocess_karbaran_omomi_v3.log")
        
        # Final verdict
        if successful_tests == total_tests:
            logger.info("\n🎉 تمام تست‌ها موفق بودند! Collection آماده استفاده است.")
        elif successful_tests >= total_tests * 0.8:
            logger.info(f"\n✅ {(successful_tests/total_tests)*100:.0f}% تست‌ها موفق بودند. Collection قابل استفاده است.")
        else:
            logger.warning(f"\n⚠️ فقط {(successful_tests/total_tests)*100:.0f}% تست‌ها موفق بودند. نیاز به بررسی بیشتر.")
        
    except Exception as e:
        logger.error(f"\n❌ خطای کلی در اجرای برنامه: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
