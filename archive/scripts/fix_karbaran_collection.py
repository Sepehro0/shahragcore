# -*- coding: utf-8 -*-
"""
اسکریپت برای رفع مشکل collection karbaran_omomi
"""

import asyncio
import logging
from pathlib import Path
from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fix_collection():
    """رفع مشکل collection"""
    rag = UltimateRAGSystem()
    collection_name = "karbaran_omomi"
    
    # بررسی وجود collection
    collections = await rag.get_collections()
    logger.info(f"Collections: {collections}")
    
    if collection_name not in collections:
        logger.error(f"Collection {collection_name} not found!")
        return
    
    # بررسی وجود فایل Excel
    excel_path = Path("/home/user01/qwen-api/enhanced_rag_system/karbaran-omomi.xlsx")
    if not excel_path.exists():
        logger.error(f"Excel file not found: {excel_path}")
        return
    
    logger.info(f"📄 Found Excel file: {excel_path}")
    logger.info("🔄 Re-processing collection to fix ChromaDB schema issue...")
    
    # خواندن فایل Excel
    with open(excel_path, 'rb') as f:
        excel_bytes = f.read()
    
    # Process کردن دوباره
    result = await rag.process_excel(
        file_bytes=excel_bytes,
        filename="karbaran-omomi.xlsx",
        collection_name=collection_name
    )
    
    if result.get('success'):
        logger.info(f"✅ Collection re-processed successfully!")
        logger.info(f"   Chunks: {result.get('chunks_count', 0)}")
    else:
        logger.error(f"❌ Re-processing failed: {result.get('error')}")
    
    await rag.close()


if __name__ == "__main__":
    asyncio.run(fix_collection())

