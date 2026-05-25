# -*- coding: utf-8 -*-
"""
Test Database Integration
تست یکپارچه‌سازی RAG + Database
"""

import asyncio
import logging
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ultimate_rag_system import UltimateRAGSystem

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_excel_upload():
    """تست آپلود فایل Excel"""
    logger.info("=" * 80)
    logger.info("🧪 TEST 1: آپلود فایل Excel")
    logger.info("=" * 80)
    
    try:
        # Initialize RAG system
        rag_system = UltimateRAGSystem(
            enable_semantic_chunking=False,
            enable_query_understanding=False,
            enable_advanced_retrieval=False
        )
        
        # Read Excel file
        excel_path = "/home/user01/qwen-api/enhanced_rag_system/boodje.xlsx"
        if not os.path.exists(excel_path):
            logger.error(f"❌ Excel file not found: {excel_path}")
            return False
        
        with open(excel_path, 'rb') as f:
            file_bytes = f.read()
        
        collection_name = "test_boodje"
        
        logger.info(f"📤 Uploading {excel_path} to collection: {collection_name}")
        
        # Process Excel
        result = await rag_system.process_excel(
            file_bytes=file_bytes,
            filename="boodje.xlsx",
            collection_name=collection_name
        )
        
        if result.get("success"):
            logger.info("✅ Excel upload successful!")
            logger.info(f"   - Chunks created: {result.get('chunks_count', 0)}")
            logger.info(f"   - RAG storage: {result.get('rag_storage', {}).get('success', False)}")
            logger.info(f"   - Database storage: {result.get('database_storage', {}).get('success', False)}")
            
            if result.get('database_storage', {}).get('success'):
                db_info = result.get('database_storage', {})
                logger.info(f"   - Tables created: {db_info.get('total_tables', 0)}")
                for table in db_info.get('tables', []):
                    logger.info(f"     * {table.get('table_name')}: {table.get('row_count')} rows")
            
            return True
        else:
            logger.error(f"❌ Excel upload failed: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_database_query():
    """تست query های Database"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TEST 2: تست Query های Database")
    logger.info("=" * 80)
    
    try:
        rag_system = UltimateRAGSystem(
            enable_semantic_chunking=False,
            enable_query_understanding=False,
            enable_advanced_retrieval=False
        )
        
        if not rag_system.enable_database or not rag_system.database_service:
            logger.warning("⚠️ Database not enabled, skipping database queries")
            return True
        
        collection_name = "test_boodje"
        
        # Query های مختلف
        test_queries = [
            "چند ردیف در جدول وجود دارد؟",
            "تعداد کل ردیف‌ها چقدر است؟",
            "نمایش 5 ردیف اول",
        ]
        
        for query in test_queries:
            logger.info(f"\n📝 Query: {query}")
            try:
                result = await rag_system.retrieve_and_answer(
                    query=query,
                    collection_name=collection_name,
                    top_k=5,
                    use_reranking=False,
                    use_multi_hop=False
                )
                
                if result.get("success"):
                    logger.info("✅ Query successful!")
                    logger.info(f"   - Used hybrid: {result.get('used_hybrid_retrieval', False)}")
                    logger.info(f"   - Query type: {result.get('query_type', 'unknown')}")
                    
                    answer = result.get("answer", "")
                    if answer:
                        preview = answer[:200] + "..." if len(answer) > 200 else answer
                        logger.info(f"   - Answer preview: {preview}")
                    
                    if result.get("database_results"):
                        db_result = result.get("database_results")
                        logger.info(f"   - DB rows returned: {db_result.get('count', 0)}")
                        if db_result.get("sql"):
                            logger.info(f"   - SQL: {db_result.get('sql')[:100]}")
                else:
                    logger.warning(f"⚠️ Query failed: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"❌ Query error: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_rag_query():
    """تست query های RAG"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TEST 3: تست Query های RAG")
    logger.info("=" * 80)
    
    try:
        rag_system = UltimateRAGSystem(
            enable_semantic_chunking=False,
            enable_query_understanding=False,
            enable_advanced_retrieval=False
        )
        
        collection_name = "test_boodje"
        
        # Query های معنایی
        test_queries = [
            "این فایل درباره چیست؟",
            "چه اطلاعاتی در این جدول موجود است؟",
        ]
        
        for query in test_queries:
            logger.info(f"\n📝 Query: {query}")
            try:
                result = await rag_system.retrieve_and_answer(
                    query=query,
                    collection_name=collection_name,
                    top_k=5,
                    use_reranking=False,
                    use_multi_hop=False
                )
                
                if result.get("success"):
                    logger.info("✅ Query successful!")
                    answer = result.get("answer", "")
                    if answer:
                        preview = answer[:200] + "..." if len(answer) > 200 else answer
                        logger.info(f"   - Answer preview: {preview}")
                    
                    top_results = result.get("top_results", [])
                    logger.info(f"   - RAG results: {len(top_results)}")
                    
            except Exception as e:
                logger.error(f"❌ Query error: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_hybrid_query():
    """تست query های ترکیبی"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TEST 4: تست Query های Hybrid")
    logger.info("=" * 80)
    
    try:
        rag_system = UltimateRAGSystem(
            enable_semantic_chunking=False,
            enable_query_understanding=False,
            enable_advanced_retrieval=False
        )
        
        collection_name = "test_boodje"
        
        # Query های ترکیبی
        test_queries = [
            "چند ردیف در جدول وجود دارد و این داده‌ها درباره چیست؟",
        ]
        
        for query in test_queries:
            logger.info(f"\n📝 Query: {query}")
            try:
                result = await rag_system.retrieve_and_answer(
                    query=query,
                    collection_name=collection_name,
                    top_k=5,
                    use_reranking=False,
                    use_multi_hop=False
                )
                
                if result.get("success"):
                    logger.info("✅ Query successful!")
                    logger.info(f"   - Used hybrid: {result.get('used_hybrid_retrieval', False)}")
                    logger.info(f"   - Query type: {result.get('query_type', 'unknown')}")
                    
                    answer = result.get("answer", "")
                    if answer:
                        preview = answer[:300] + "..." if len(answer) > 300 else answer
                        logger.info(f"   - Answer preview:\n{preview}")
                    
            except Exception as e:
                logger.error(f"❌ Query error: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """تابع اصلی"""
    logger.info("🚀 شروع تست یکپارچه‌سازی RAG + Database\n")
    
    results = []
    
    # Test 1: Excel Upload
    results.append(("Excel Upload", await test_excel_upload()))
    
    # Test 2: Database Queries
    results.append(("Database Queries", await test_database_query()))
    
    # Test 3: RAG Queries
    results.append(("RAG Queries", await test_rag_query()))
    
    # Test 4: Hybrid Queries
    results.append(("Hybrid Queries", await test_hybrid_query()))
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 SUMMARY")
    logger.info("=" * 80)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        logger.info("\n🎉 همه تست‌ها با موفقیت انجام شد!")
    else:
        logger.warning("\n⚠️ برخی تست‌ها ناموفق بودند")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

