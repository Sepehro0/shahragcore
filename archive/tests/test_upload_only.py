# -*- coding: utf-8 -*-
"""
Test Upload Only - فقط تست آپلود بدون query
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_upload():
    """تست آپلود"""
    logger.info("🧪 تست آپلود فایل Excel...")
    
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    excel_path = "/home/user01/qwen-api/enhanced_rag_system/boodje.xlsx"
    with open(excel_path, 'rb') as f:
        file_bytes = f.read()
    
    result = await rag_system.process_excel(
        file_bytes=file_bytes,
        filename="boodje.xlsx",
        collection_name="test_boodje"
    )
    
    logger.info(f"✅ Success: {result.get('success')}")
    logger.info(f"   Chunks: {result.get('chunks_count', 0)}")
    logger.info(f"   RAG: {result.get('rag_storage', {}).get('success')}")
    logger.info(f"   DB: {result.get('database_storage', {}).get('success')}")
    
    if result.get('database_storage', {}).get('success'):
        db_info = result.get('database_storage', {})
        logger.info(f"   Tables: {db_info.get('total_tables', 0)}")
        for table in db_info.get('tables', []):
            logger.info(f"     - {table.get('table_name')}: {table.get('row_count')} rows")
    
    return result.get('success', False)


if __name__ == "__main__":
    success = asyncio.run(test_upload())
    sys.exit(0 if success else 1)

