#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
پردازش فایل zinaf-dakheli.xlsx و ایجاد collection برای RAG
"""

import sys
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system")

from ultimate_rag_system import UltimateRAGSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/home/user01/qwen-api/enhanced_rag_system/process_zinaf_dakheli.log')
    ]
)

logger = logging.getLogger(__name__)

# Collection name
COLLECTION_NAME = "zinaf_dakheli"
EXCEL_FILE_PATH = "/home/user01/qwen-api/enhanced_rag_system/zinaf-dakheli.xlsx"

async def process_excel_file():
    """پردازش فایل Excel و ایجاد collection"""
    try:
        logger.info("🚀 شروع پردازش فایل Excel...")
        
        # Initialize RAG system
        logger.info("📦 در حال راه‌اندازی سیستم RAG...")
        rag_system = UltimateRAGSystem(
            enable_semantic_chunking=True,
            enable_query_understanding=True,
            enable_advanced_retrieval=True,
            enable_multimodal=False,
            enable_self_rag=True,
            enable_corrective_rag=True,
            retrieval_strategy="hybrid"
        )
        
        # Read Excel file
        logger.info(f"📖 در حال خواندن فایل: {EXCEL_FILE_PATH}")
        if not os.path.exists(EXCEL_FILE_PATH):
            raise FileNotFoundError(f"فایل یافت نشد: {EXCEL_FILE_PATH}")
        
        with open(EXCEL_FILE_PATH, 'rb') as f:
            file_bytes = f.read()
        
        filename = os.path.basename(EXCEL_FILE_PATH)
        logger.info(f"✅ فایل خوانده شد: {len(file_bytes)} بایت")
        
        # Process Excel
        logger.info(f"🔄 در حال پردازش Excel و ایجاد collection: {COLLECTION_NAME}")
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
                collections = await rag_system.get_collections()
                if COLLECTION_NAME in collections:
                    logger.info(f"✅ Collection '{COLLECTION_NAME}' در لیست collections موجود است")
                    
                    # Get collection details
                    try:
                        collection = rag_system.chroma_client.get_collection(COLLECTION_NAME)
                        doc_count = collection.count()
                        logger.info(f"📈 تعداد اسناد در collection: {doc_count}")
                    except Exception as e:
                        logger.warning(f"⚠️ نتوانست اطلاعات collection را دریافت کند: {e}")
                else:
                    logger.warning(f"⚠️ Collection '{COLLECTION_NAME}' در لیست collections یافت نشد")
            except Exception as e:
                logger.warning(f"⚠️ خطا در دریافت لیست collections: {e}")
            
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
    """تست collection با چند query"""
    test_queries = [
        "واحد آموزشهای تخصصی چیست؟",
        "چه نوع آموزش هایی توسط واحد آموزش های تخصصی انجام می شود؟",
        "دوره های آموزشی به چه صورت برگزار می شوند؟",
        "مخاطبان رویدادهای آموزشی چه کسانی هستند؟",
    ]
    
    results = []
    
    logger.info("\n" + "="*80)
    logger.info("🧪 شروع تست collection")
    logger.info("="*80)
    
    for i, query in enumerate(test_queries, 1):
        logger.info(f"\n📝 تست {i}/{len(test_queries)}")
        logger.info(f"Query: {query}")
        
        try:
            start_time = datetime.now()
            
            # Query the collection
            response = await rag_system.retrieve_and_answer(
                query=query,
                collection_name=COLLECTION_NAME,
                top_k=5,
                use_reranking=True,
                use_multi_hop=False
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            if response.get("success"):
                answer = response.get("answer", "")
                sources = response.get("sources", [])
                confidence = response.get("confidence", 0.0)
                
                logger.info(f"✅ موفق - زمان: {elapsed:.2f} ثانیه")
                logger.info(f"📊 Confidence: {confidence:.2f}")
                logger.info(f"📚 تعداد منابع: {len(sources)}")
                logger.info(f"📄 پاسخ ({len(answer)} کاراکتر):")
                logger.info(f"{answer[:300]}...")
                
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
                logger.error(f"❌ ناموفق: {error}")
                results.append({
                    "query": query,
                    "success": False,
                    "error": error
                })
                
        except Exception as e:
            logger.error(f"❌ خطا در تست: {e}", exc_info=True)
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
        logger.info(f"📊 تعداد کل اسناد: {doc_count}")
        
        # Get sample documents
        if doc_count > 0:
            sample_results = collection.peek(limit=min(5, doc_count))
            
            logger.info(f"\n📄 نمونه اسناد (اولین {len(sample_results.get('ids', []))} سند):")
            for i, (doc_id, doc_text, metadata) in enumerate(zip(
                sample_results.get('ids', []),
                sample_results.get('documents', []),
                sample_results.get('metadatas', [])
            ), 1):
                logger.info(f"\n--- سند {i} ---")
                logger.info(f"ID: {doc_id}")
                logger.info(f"Text: {doc_text[:200]}...")
                logger.info(f"Metadata: {metadata}")
        
        # Get collection metadata
        collection_metadata = collection.metadata or {}
        logger.info(f"\n📋 Collection Metadata:")
        for key, value in collection_metadata.items():
            logger.info(f"  {key}: {value}")
            
    except Exception as e:
        logger.error(f"❌ خطا در آنالیز: {e}", exc_info=True)

async def main():
    """تابع اصلی"""
    logger.info("\n" + "="*80)
    logger.info("🚀 پردازش فایل zinaf-dakheli.xlsx")
    logger.info("="*80)
    
    # Step 1: Process Excel file
    process_result = await process_excel_file()
    
    if not process_result.get("success"):
        logger.error("❌ پردازش فایل ناموفق بود. خروج...")
        return
    
    logger.info("\n✅ پردازش فایل با موفقیت انجام شد!")
    logger.info(f"📁 Collection name: {COLLECTION_NAME}")
    
    # Step 2: Initialize RAG system for testing
    logger.info("\n📦 در حال راه‌اندازی سیستم RAG برای تست...")
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=True,
        enable_query_understanding=True,
        enable_advanced_retrieval=True,
        enable_multimodal=False,
        enable_self_rag=True,
        enable_corrective_rag=True,
        retrieval_strategy="hybrid"
    )
    
    # Step 3: Analyze collection
    await analyze_collection(rag_system)
    
    # Step 4: Test collection
    test_results = await test_collection(rag_system)
    
    # Step 5: Summary
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
    
    for i, result in enumerate(test_results, 1):
        status = "✅" if result.get("success", False) else "❌"
        query = result.get("query", "")
        if result.get("success"):
            elapsed = result.get("elapsed", 0)
            confidence = result.get("confidence", 0.0)
            logger.info(f"  {status} تست {i}: {query[:50]}... (زمان: {elapsed:.2f}s, Confidence: {confidence:.2f})")
        else:
            error = result.get("error", "Unknown")
            logger.info(f"  {status} تست {i}: {query[:50]}... (خطا: {error})")
    
    logger.info("\n" + "="*80)
    logger.info("✅ پردازش و تست کامل شد!")
    logger.info("="*80)
    logger.info(f"\n📁 Collection name برای استفاده: {COLLECTION_NAME}")

if __name__ == "__main__":
    asyncio.run(main())

