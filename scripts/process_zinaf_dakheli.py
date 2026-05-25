#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
پردازش فایل zinaf-dakheli.xlsx و ایجاد collection برای RAG با RefactoredRAGSystem
"""

import sys
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.refactored_rag_system import RefactoredRAGSystem
import chromadb

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/home/user01/qwen-api/enhanced_rag_system_dev/process_zinaf_dakheli.log')
    ]
)

logger = logging.getLogger(__name__)

# Collection name
COLLECTION_NAME = "zinaf_dakheli"
EXCEL_FILE_PATH = "/home/user01/qwen-api/enhanced_rag_system_dev/archive/data_files/zinaf-dakheli.xlsx"

async def process_excel_file():
    """پردازش فایل Excel و ایجاد collection"""
    try:
        logger.info("="*80)
        logger.info("🚀 شروع پردازش فایل Excel: zinaf-dakheli.xlsx")
        logger.info("="*80)
        
        # Step 1: Check if file exists
        if not os.path.exists(EXCEL_FILE_PATH):
            raise FileNotFoundError(f"❌ فایل یافت نشد: {EXCEL_FILE_PATH}")
        
        logger.info(f"✅ فایل پیدا شد: {EXCEL_FILE_PATH}")
        file_size = os.path.getsize(EXCEL_FILE_PATH)
        logger.info(f"📊 حجم فایل: {file_size / 1024:.2f} KB")
        
        # Step 2: Check if collection exists and delete if needed
        logger.info("\n🔍 بررسی collection موجود...")
        try:
            client = chromadb.PersistentClient(path="./chroma_db")
            try:
                old_collection = client.get_collection(COLLECTION_NAME)
                old_count = old_collection.count()
                logger.info(f"   📊 Collection '{COLLECTION_NAME}' موجود است با {old_count} سند")
                logger.info("   🗑️ حذف collection قدیمی...")
                client.delete_collection(COLLECTION_NAME)
                logger.info(f"   ✅ Collection قدیمی حذف شد")
            except Exception as e:
                logger.info(f"   ℹ️ Collection '{COLLECTION_NAME}' وجود ندارد - ایجاد جدید")
        except Exception as e:
            logger.warning(f"   ⚠️ خطا در بررسی collection: {e}")
        
        # Step 3: Initialize RAG system
        logger.info("\n📦 در حال راه‌اندازی RefactoredRAGSystem...")
        rag_system = RefactoredRAGSystem(
            enable_semantic_chunking=True,
            enable_query_understanding=True,
            enable_advanced_retrieval=True,
            enable_multimodal=False,
            enable_self_rag=False,
            enable_corrective_rag=False,
            retrieval_strategy="hybrid"
        )
        logger.info("✅ RefactoredRAGSystem راه‌اندازی شد")
        
        # Step 4: Read Excel file
        logger.info(f"\n📖 در حال خواندن فایل Excel...")
        with open(EXCEL_FILE_PATH, 'rb') as f:
            file_bytes = f.read()
        
        filename = os.path.basename(EXCEL_FILE_PATH)
        logger.info(f"✅ فایل خوانده شد: {len(file_bytes)} بایت")
        
        # Step 5: Process Excel
        logger.info(f"\n🔄 در حال پردازش Excel و ایجاد collection: {COLLECTION_NAME}")
        
        # Use parent system's process_excel (like reindex_karbaran_v2.py)
        result = await rag_system._parent_system.process_excel(
            file_bytes=file_bytes,
            filename=filename,
            collection_name=COLLECTION_NAME
        )
        
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            logger.error(f"❌ پردازش ناموفق بود: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        
        chunks_count = result.get("chunks_count", 0)
        logger.info(f"✅ پردازش با موفقیت انجام شد!")
        logger.info(f"📊 تعداد chunks ایجاد شده: {chunks_count}")
        
        # Step 6: Verify collection
        logger.info("\n🔍 بررسی collection جدید...")
        try:
            collection = client.get_collection(COLLECTION_NAME)
            doc_count = collection.count()
            logger.info(f"✅ Collection '{COLLECTION_NAME}' ایجاد شد")
            logger.info(f"📈 تعداد اسناد در collection: {doc_count}")
            
            # Get sample documents
            if doc_count > 0:
                sample = collection.peek(limit=3)
                logger.info(f"\n📄 نمونه اسناد (اولین 3 سند):")
                for i, (doc_id, doc_text, metadata) in enumerate(zip(
                    sample.get('ids', []),
                    sample.get('documents', []),
                    sample.get('metadatas', [])
                ), 1):
                    logger.info(f"\n--- سند {i} ---")
                    logger.info(f"ID: {doc_id[:50]}...")
                    logger.info(f"Text: {doc_text[:200]}...")
                    sheet_name = metadata.get('sheet_name', 'N/A')
                    row_index = metadata.get('row_index', 'N/A')
                    logger.info(f"Sheet: {sheet_name}, Row: {row_index}")
        except Exception as e:
            logger.warning(f"⚠️ خطا در بررسی collection: {e}")
        
        return {
            "success": True,
            "collection_name": COLLECTION_NAME,
            "chunks_count": chunks_count,
            "result": result
        }
            
    except Exception as e:
        logger.error(f"❌ خطا در پردازش: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

async def test_collection(rag_system: RefactoredRAGSystem):
    """تست collection با چند query"""
    test_queries = [
        "واحد آموزشهای تخصصی چیست؟",
        "چه نوع آموزش هایی توسط واحد آموزش های تخصصی انجام می شود؟",
        "دوره های آموزشی به چه صورت برگزار می شوند؟",
        "مخاطبان رویدادهای آموزشی چه کسانی هستند؟",
        "رویداد جایزه نوآوری و فناوری چیست؟",
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

async def analyze_collection(rag_system: RefactoredRAGSystem):
    """آنالیز دقیق collection"""
    logger.info("\n" + "="*80)
    logger.info("🔍 آنالیز دقیق collection")
    logger.info("="*80)
    
    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        # Get collection
        collection = client.get_collection(COLLECTION_NAME)
        
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
                logger.info(f"ID: {doc_id[:50]}...")
                logger.info(f"Text: {doc_text[:200]}...")
                logger.info(f"Metadata: {metadata}")
        
        # Get collection metadata
        collection_metadata = collection.metadata or {}
        logger.info(f"\n📋 Collection Metadata:")
        for key, value in collection_metadata.items():
            logger.info(f"  {key}: {value}")
        
        # Analyze sheet distribution
        all_docs = collection.get()
        sheet_counts = {}
        for metadata in all_docs['metadatas']:
            sheet = metadata.get('sheet_name', 'NO_SHEET')
            sheet_counts[sheet] = sheet_counts.get(sheet, 0) + 1
        
        logger.info(f"\n📊 توزیع sheet_name:")
        for sheet, count in sorted(sheet_counts.items(), key=lambda x: -x[1]):
            logger.info(f"   {sheet}: {count} documents")
            
    except Exception as e:
        logger.error(f"❌ خطا در آنالیز: {e}", exc_info=True)

async def main():
    """تابع اصلی"""
    logger.info("\n" + "="*80)
    logger.info("🚀 پردازش فایل zinaf-dakheli.xlsx با RefactoredRAGSystem")
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
    rag_system = RefactoredRAGSystem(
        enable_semantic_chunking=True,
        enable_query_understanding=True,
        enable_advanced_retrieval=True,
        enable_multimodal=False,
        enable_self_rag=False,
        enable_corrective_rag=False,
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
    if total_tests > 0:
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









