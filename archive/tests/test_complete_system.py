# -*- coding: utf-8 -*-
"""
Complete System Test
تست کامل سیستم RAG + Database + Qwen3-30B
"""
import asyncio
import logging
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ultimate_rag_system import UltimateRAGSystem
import requests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
def check_postgresql():
    """بررسی PostgreSQL"""
    logger.info("🔍 Checking PostgreSQL...")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="rag_user",
            password="rag_password",
            database="rag_database",
            connect_timeout=5
        )
        conn.close()
        logger.info("✅ PostgreSQL connection successful!")
        return True
    except Exception as e:
        logger.error(f"❌ PostgreSQL connection failed: {e}")
        logger.info("   Please run: bash scripts/setup_postgresql.sh")
        return False
def check_qwen_service():
    """بررسی Qwen Service"""
    logger.info("🔍 Checking Qwen Service...")
    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            logger.info("✅ Qwen service is running!")
            return True
    except:
        pass
    
    try:
        response = requests.get("http://localhost:8080/v1/models", timeout=5)
        if response.status_code == 200:
            logger.info("✅ Qwen service is running (v1/models endpoint)!")
            return True
    except:
        pass
    
    logger.warning("⚠️ Qwen service not responding")
    logger.info("   Please run: bash /home/user01/qwen-api/start_qwen3_30b_sglang.sh")
    return False
async def test_excel_upload():
    """تست آپلود Excel"""
    logger.info('\n' + '=' * 80)
    logger.info("🧪 TEST: Excel Upload")
    logger.info("=" * 80)
    
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    try:
        excel_path = "/home/user01/qwen-api/enhanced_rag_system/boodje.xlsx"
        if not os.path.exists(excel_path):
            logger.error(f"❌ Excel file not found: {excel_path}")
            return False
        
        with open(excel_path, 'rb') as f:
            file_bytes = f.read()
        
        collection_name = f"test_boodje_{int(time.time())}"
        logger.info(f"📤 Uploading to collection: {collection_name}")
        
        result = await rag_system.process_excel(
            file_bytes=file_bytes,
            filename="boodje.xlsx",
            collection_name=collection_name
        )
        
        if result.get("success"):
            logger.info("✅ Excel upload successful!")
            logger.info(f"   - Chunks: {result.get('chunks_count', 0)}")
            logger.info(f"   - RAG storage: {result.get('rag_storage', {}).get('success')}")
            logger.info(f"   - DB storage: {result.get('database_storage', {}).get('success')}")
            
            if result.get('database_storage', {}).get('success'):
                db_info = result.get('database_storage', {})
                logger.info(f"   - Tables: {db_info.get('total_tables', 0)}")
                for table in db_info.get('tables', []):
                    logger.info(f"     * {table.get('table_name')}: {table.get('row_count')} rows")
            
            return collection_name
        logger.error(f"❌ Upload failed: {result.get('error')}")
        return None
            
    except Exception as e:
        logger.error(f"❌ Upload test failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        await rag_system.close()

async def test_database_query(collection_name: str):
    """تست Database Query"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TEST: Database Query")
    logger.info("=" * 80)
    
    if not collection_name:
        logger.warning("⚠️ Skipping - no collection")
        return False
    
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    try:
        query = "چند ردیف در جدول وجود دارد؟"
        logger.info(f"📝 Query: {query}")
        
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
                logger.info(f"   - Answer:\n{preview}")
            
            if result.get("database_results"):
                db_result = result.get("database_results")
                logger.info(f"   - DB rows: {db_result.get('count', 0)}")
                if db_result.get("sql"):
                    logger.info(f"   - SQL: {db_result.get('sql')[:100]}")
            
            return True
        logger.warning(f"⚠️ Query failed: {result.get('error')}")
        return False
            
    except Exception as e:
        logger.error(f"❌ Query test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await rag_system.close()

async def test_rag_query(collection_name: str):
    """تست RAG Query"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TEST: RAG Query")
    logger.info("=" * 80)
    
    if not collection_name:
        logger.warning("⚠️ Skipping - no collection")
        return False
    
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    try:
        query = "این فایل درباره چیست؟"
        logger.info(f"📝 Query: {query}")
        
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
                preview = answer[:300] + "..." if len(answer) > 300 else answer
                logger.info(f"   - Answer:\n{preview}")
            
            top_results = result.get("top_results", [])
            logger.info(f"   - RAG results: {len(top_results)}")
            
            return True
        logger.warning(f"⚠️ Query failed: {result.get('error')}")
        return False
            
    except Exception as e:
        logger.error(f"❌ Query test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await rag_system.close()

async def test_hybrid_query(collection_name: str):
    """تست Hybrid Query"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TEST: Hybrid Query")
    logger.info("=" * 80)
    
    if not collection_name:
        logger.warning("⚠️ Skipping - no collection")
        return False
    
    rag_system = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    try:
        query = "چند ردیف وجود دارد و این داده‌ها درباره چیست؟"
        logger.info(f"📝 Query: {query}")
        
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
            logger.info(f"   - Route: {result.get('route', {}).get('primary_path')}")
            
            answer = result.get("answer", "")
            if answer:
                preview = answer[:300] + "..." if len(answer) > 300 else answer
                logger.info(f"   - Answer:\n{preview}")
            
            return True
        logger.warning(f"⚠️ Hybrid query failed: {result.get('error')}")
        return False
            
    except Exception as e:
        logger.error(f"❌ Hybrid query test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await rag_system.close()

async def main():
    """تابع اصلی"""
    logger.info("🚀 شروع تست کامل سیستم RAG + Database + Qwen3-30B\n")
    
    results = []
    
    # Check prerequisites
    logger.info("=" * 80)
    logger.info("📋 PREREQUISITES CHECK")
    logger.info("=" * 80)
    
    pg_ok = check_postgresql()
    qwen_ok = check_qwen_service()
    
    if not pg_ok or not qwen_ok:
        logger.warning("\n⚠️ Some prerequisites are missing. Please setup:")
        if not pg_ok:
            logger.info("   1. bash scripts/setup_postgresql.sh")
        if not qwen_ok:
            logger.info("   2. bash /home/user01/qwen-api/start_qwen3_30b_sglang.sh")
        logger.info("\nThen run this test again.")
        return False
    
    # Test 1: Excel Upload
    collection_name = await test_excel_upload()
    results.append(("Excel Upload", collection_name is not None))
    
    if not collection_name:
        logger.error("\n❌ Upload failed, skipping query tests")
        return False
    
    # Test 2: Database Query
    results.append(("Database Query", await test_database_query(collection_name)))
    
    # Test 3: RAG Query
    results.append(("RAG Query", await test_rag_query(collection_name)))
    
    # Test 4: Hybrid Query
    results.append(("Hybrid Query", await test_hybrid_query(collection_name)))
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 SUMMARY")
    logger.info("=" * 80)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    all_passed = all(success for _, success in results)
    
    logger.info("\n" + "=" * 80)
    if all_passed:
        logger.info("🎉 همه تست‌ها با موفقیت انجام شد!")
    else:
        logger.warning("⚠️ برخی تست‌ها ناموفق بودند")
    logger.info("=" * 80)
    
    return all_passed
if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    finally:
        # Clean up any lingering connections
        import gc
        gc.collect()
