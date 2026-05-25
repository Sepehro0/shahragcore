#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Re-index karbaran_omomi collection with new Excel file (v2)
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.refactored_rag_system import RefactoredRAGSystem
import chromadb

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Collection name
COLLECTION_NAME = "karbaran_omomi"
EXCEL_FILE_PATH = "/home/user01/qwen-api/enhanced_rag_system_dev/archive/data_files/karbaran-omomi-v2.xlsx"

async def reindex_collection():
    """Re-index karbaran_omomi collection with new Excel file"""
    
    try:
        logger.info("="*80)
        logger.info("🚀 شروع Re-index کردن collection karbaran_omomi")
        logger.info("="*80)
        
        # Step 1: Check if file exists
        if not os.path.exists(EXCEL_FILE_PATH):
            raise FileNotFoundError(f"❌ فایل یافت نشد: {EXCEL_FILE_PATH}")
        
        logger.info(f"✅ فایل پیدا شد: {EXCEL_FILE_PATH}")
        file_size = os.path.getsize(EXCEL_FILE_PATH)
        logger.info(f"📊 حجم فایل: {file_size / 1024:.2f} KB")
        
        # Step 2: Delete existing collection
        logger.info("\n🗑️ حذف collection قدیمی...")
        try:
            client = chromadb.PersistentClient(path="./chroma_db")
            try:
                old_collection = client.get_collection(COLLECTION_NAME)
                old_count = old_collection.count()
                logger.info(f"   📊 تعداد اسناد قدیمی: {old_count}")
                client.delete_collection(COLLECTION_NAME)
                logger.info(f"   ✅ Collection قدیمی حذف شد")
            except Exception as e:
                logger.info(f"   ℹ️ Collection قدیمی وجود نداشت یا قبلاً حذف شده: {e}")
        except Exception as e:
            logger.warning(f"   ⚠️ خطا در حذف collection: {e}")
        
        # Step 3: Initialize RAG system
        logger.info("\n📦 در حال راه‌اندازی سیستم RAG...")
        rag_system = RefactoredRAGSystem(
            enable_semantic_chunking=True,
            enable_query_understanding=True,
            enable_advanced_retrieval=True,
            enable_multimodal=False,
            enable_self_rag=False,
            enable_corrective_rag=False,
            retrieval_strategy="hybrid"
        )
        
        # Step 4: Read Excel file
        logger.info(f"\n📖 در حال خواندن فایل Excel...")
        with open(EXCEL_FILE_PATH, 'rb') as f:
            file_bytes = f.read()
        
        filename = os.path.basename(EXCEL_FILE_PATH)
        logger.info(f"✅ فایل خوانده شد: {len(file_bytes)} بایت")
        
        # Step 5: Process Excel
        logger.info(f"\n🔄 در حال پردازش Excel و ایجاد collection: {COLLECTION_NAME}")
        # Use parent system's process_excel directly
        result = await rag_system._parent_system.process_excel(
            file_bytes=file_bytes,
            filename=filename,
            collection_name=COLLECTION_NAME
        )
        
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            logger.error(f"❌ پردازش ناموفق بود: {error_msg}")
            return False
        
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
                    logger.info(f"Text: {doc_text[:100]}...")
                    sheet_name = metadata.get('sheet_name', 'N/A')
                    logger.info(f"Sheet: {sheet_name}")
        except Exception as e:
            logger.warning(f"⚠️ خطا در بررسی collection: {e}")
        
        # Step 7: Add critical questions
        logger.info("\n📝 اضافه کردن critical questions...")
        try:
            import subprocess
            script_path = os.path.join(os.path.dirname(__file__), "add_critical_questions.py")
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(__file__)
            )
            if result.returncode == 0:
                logger.info("✅ Critical questions اضافه شدند")
                logger.info(result.stdout)
            else:
                logger.warning(f"⚠️ خطا در اضافه کردن critical questions: {result.stderr}")
        except Exception as e:
            logger.warning(f"⚠️ خطا در اضافه کردن critical questions: {e}")
        
        # Step 8: Final verification
        logger.info("\n🔍 بررسی نهایی...")
        try:
            collection = client.get_collection(COLLECTION_NAME)
            final_count = collection.count()
            logger.info(f"📊 تعداد نهایی اسناد: {final_count}")
            
            # Check sheet_name distribution
            all_docs = collection.get()
            sheet_counts = {}
            for metadata in all_docs['metadatas']:
                sheet = metadata.get('sheet_name', 'NO_SHEET')
                sheet_counts[sheet] = sheet_counts.get(sheet, 0) + 1
            
            logger.info(f"\n📊 توزیع sheet_name:")
            for sheet, count in sorted(sheet_counts.items(), key=lambda x: -x[1]):
                logger.info(f"   {sheet}: {count} documents")
        except Exception as e:
            logger.warning(f"⚠️ خطا در بررسی نهایی: {e}")
        
        logger.info("\n" + "="*80)
        logger.info("✅ Re-index با موفقیت انجام شد!")
        logger.info("="*80)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطا در re-index: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = asyncio.run(reindex_collection())
    sys.exit(0 if success else 1)

