# -*- coding: utf-8 -*-
"""
Test script for qavanin collection
تست کالکشن قوانین
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import Settings
from services.persian_embedding_service import PersianEmbeddingService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_qavanin_collection():
    """تست جستجو در کالکشن qavanin"""
    
    # 1. بارگذاری تنظیمات
    settings = Settings()
    
    # 2. اتصال به ChromaDB
    logger.info("اتصال به ChromaDB...")
    chroma_settings = ChromaSettings(
        persist_directory=settings.database.chroma_db_path,
        anonymized_telemetry=False
    )
    
    chroma_client = chromadb.PersistentClient(
        path=settings.database.chroma_db_path,
        settings=chroma_settings
    )
    
    # 3. دریافت collection
    collection = chroma_client.get_collection("qavanin")
    count = collection.count()
    logger.info(f"تعداد اسناد در collection: {count}")
    
    # 4. ایجاد embedding service
    logger.info("بارگذاری embedding service...")
    embedding_service = PersianEmbeddingService()
    
    # 5. سوالات تست
    test_queries = [
        "ماده 11 چیست؟",
        "شورای گفت و گو چیست؟",
        "وظایف شورای گفت و گو چیست؟",
        "قانون در مورد مناقصات چه می گوید؟",
        "تشکل اقتصادی چیست؟",
    ]
    
    # 6. تست جستجو
    for query in test_queries:
        logger.info(f"\n{'='*60}")
        logger.info(f"سوال: {query}")
        logger.info(f"{'='*60}")
        
        # ایجاد embedding برای سوال
        query_embedding = embedding_service.generate_embedding(query)
        
        # جستجو در collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3
        )
        
        # نمایش نتایج
        if results['documents'] and results['documents'][0]:
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                logger.info(f"\nنتیجه {i+1} (فاصله: {distance:.4f}):")
                logger.info(f"نوع: {metadata.get('type')}")
                logger.info(f"شماره ماده: {metadata.get('article_number')}")
                if metadata.get('note_number'):
                    logger.info(f"تبصره: {metadata.get('note_number')}")
                logger.info(f"متن: {doc[:200]}...")
        else:
            logger.info("نتیجه‌ای یافت نشد")
    
    logger.info(f"\n{'='*60}")
    logger.info("✅ تست با موفقیت تکمیل شد")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    try:
        test_qavanin_collection()
    except Exception as e:
        logger.error(f"خطا در اجرای تست: {e}", exc_info=True)
        sys.exit(1)
