# -*- coding: utf-8 -*-
"""
Test without Qwen - فقط تست آپلود و Database
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_upload_and_database():
    """تست آپلود و بررسی Database"""
    logger.info("🧪 تست آپلود و Database...")
    
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    # Check database
    if rag_system.enable_database and rag_system.database_service:
        logger.info("✅ Database service available")
        from services.database_service import DatabaseService
        tables = rag_system.database_service.list_tables("test_boodje")
        logger.info(f"   Tables in test_boodje: {len(tables)}")
        for table in tables[:3]:
            logger.info(f"     - {table.table_name}: {table.row_count} rows")
    else:
        logger.warning("⚠️ Database service not available")
    
    # Test upload
    excel_path = "/home/user01/qwen-api/enhanced_rag_system/boodje.xlsx"
    if os.path.exists(excel_path):
        with open(excel_path, 'rb') as f:
            file_bytes = f.read()
        
        result = await rag_system.process_excel(
            file_bytes=file_bytes,
            filename="boodje.xlsx",
            collection_name="test_boodje_final"
        )
        
        if result.get("success"):
            logger.info("✅ Upload successful!")
            logger.info(f"   - Chunks: {result.get('chunks_count')}")
            logger.info(f"   - RAG: {result.get('rag_storage', {}).get('success')}")
            logger.info(f"   - DB: {result.get('database_storage', {}).get('success')}")
            
            if result.get('database_storage', {}).get('success'):
                db_info = result.get('database_storage', {})
                logger.info(f"   - Tables: {db_info.get('total_tables')}")
        else:
            logger.error(f"❌ Upload failed: {result.get('error')}")
    else:
        logger.error(f"❌ File not found: {excel_path}")


if __name__ == "__main__":
    asyncio.run(test_upload_and_database())

