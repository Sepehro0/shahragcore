#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
پردازش batch-based collection budget_financial
با مدیریت batch size برای فایل‌های بزرگ
"""

import sys
import os
import asyncio
import logging
from datetime import datetime
import chromadb

sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from utils.multilingual_embeddings import get_embedding_function

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/home/user01/qwen-api/enhanced_rag_system_dev/reprocess_budget_batch.log')
    ]
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = "budget_financial"
DB_PATH = "/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
BATCH_SIZE = 2000  # Process 2000 rows at a time

EXCEL_FILES = [
    {"path": "archive/data_files/masaref3.xlsx", "type": "masaref"},
    {"path": "archive/data_files/manabe3.xlsx", "type": "manabe"}
]


async def process_excel_batch():
    """پردازش batch-based فایل‌های Excel"""
    import pandas as pd
    import io
    
    logger.info("🚀 شروع پردازش batch-based")
    
    # Initialize ChromaDB
    logger.info("📦 اتصال به ChromaDB...")
    client = chromadb.PersistentClient(path=DB_PATH)
    
    # Delete existing collection
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info(f"🗑️ Collection قبلی حذف شد")
    except:
        pass
    
    await asyncio.sleep(2)
    
    # Create new collection with embedding function
    logger.info(f"📝 ایجاد collection جدید: {COLLECTION_NAME}")
    embedding_function = get_embedding_function()
    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"}
    )
    
    total_added = 0
    
    for file_info in EXCEL_FILES:
        file_path = file_info["path"]
        file_type = file_info["type"]
        
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 پردازش فایل: {os.path.basename(file_path)} ({file_type})")
        logger.info(f"{'='*80}")
        
        # Read Excel
        df = pd.read_excel(file_path)
        total_rows = len(df)
        logger.info(f"📈 تعداد کل rows: {total_rows}")
        
        # Process in batches
        for batch_start in range(0, total_rows, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total_rows)
            batch_df = df.iloc[batch_start:batch_end]
            
            logger.info(f"\n🔄 پردازش batch {batch_start}-{batch_end} ({len(batch_df)} rows)...")
            
            documents = []
            metadatas = []
            ids = []
            
            for idx, row in batch_df.iterrows():
                # Create document text
                text_parts = []
                metadata = {"file_type": file_type, "row_index": int(idx)}
                
                for col in df.columns:
                    value = row[col]
                    if pd.notna(value) and value != '':
                        col_clean = str(col).strip()
                        val_str = str(value).strip()
                        
                        text_parts.append(f"{col_clean}: {val_str}")
                        metadata[col_clean] = val_str
                
                if text_parts:
                    doc_text = " | ".join(text_parts)
                    documents.append(doc_text)
                    metadatas.append(metadata)
                    ids.append(f"{file_type}_row_{idx}")
            
            if documents:
                # Add to collection in smaller sub-batches
                sub_batch_size = 500
                for sub_start in range(0, len(documents), sub_batch_size):
                    sub_end = min(sub_start + sub_batch_size, len(documents))
                    
                    try:
                        collection.add(
                            documents=documents[sub_start:sub_end],
                            metadatas=metadatas[sub_start:sub_end],
                            ids=ids[sub_start:sub_end]
                        )
                        total_added += (sub_end - sub_start)
                        logger.info(f"  ✅ اضافه شد: {sub_end - sub_start} docs (کل: {total_added})")
                    except Exception as e:
                        logger.error(f"  ❌ خطا: {e}")
            
            await asyncio.sleep(0.5)  # Small delay between batches
    
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ پردازش کامل شد!")
    logger.info(f"📊 تعداد کل documents اضافه شده: {total_added}")
    logger.info(f"{'='*80}")
    
    # Verify
    final_count = collection.count()
    logger.info(f"\n📈 تعداد نهایی documents در collection: {final_count}")
    
    return final_count


async def test_queries():
    """تست با سوالات"""
    from ultimate_rag_system import UltimateRAGSystem
    
    logger.info(f"\n{'='*80}")
    logger.info("🧪 تست سوالات")
    logger.info(f"{'='*80}")
    
    rag_system = UltimateRAGSystem(db_path=DB_PATH)
    
    test_queries = [
        "اعتبارات هزینه ای مرکز آمار ایران در سال 1403 چقدره؟",
        "منابع پارک فناوری پردیس سال 99",
        "هزینه های سازمان تعزيرات حكومتی در سال 1400",
        "منابع شرکت پست بانک در سالهای 400 تا 403"
    ]
    
    results = []
    for i, query in enumerate(test_queries, 1):
        logger.info(f"\n📝 تست {i}: {query}")
        
        try:
            response = await rag_system.retrieve_and_answer(
                query=query,
                collection_name=COLLECTION_NAME,
                top_k=8
            )
            
            if response.get("success"):
                answer = response.get("answer", "")
                confidence = response.get("confidence", 0)
                sources = len(response.get("top_results", []))
                
                logger.info(f"✅ موفق - Confidence: {confidence:.3f}, Sources: {sources}")
                logger.info(f"📄 پاسخ: {answer[:200]}...")
                results.append(True)
            else:
                logger.error(f"❌ ناموفق: {response.get('error')}")
                results.append(False)
        except Exception as e:
            logger.error(f"❌ خطا: {e}")
            results.append(False)
        
        await asyncio.sleep(2)
    
    success_rate = (sum(results) / len(results)) * 100
    logger.info(f"\n📊 نرخ موفقیت: {success_rate:.0f}% ({sum(results)}/{len(results)})")
    
    return results


async def main():
    """تابع اصلی"""
    logger.info("="*80)
    logger.info("🚀 پردازش Budget Financial Collection (Batch Mode)")
    logger.info("="*80)
    
    try:
        # Step 1: Process files
        doc_count = await process_excel_batch()
        
        if doc_count == 0:
            logger.error("❌ هیچ document اضافه نشد!")
            return
        
        # Step 2: Test
        await test_queries()
        
        logger.info(f"\n{'='*80}")
        logger.info("✅ Process Complete!")
        logger.info(f"{'='*80}")
        
    except Exception as e:
        logger.error(f"❌ خطای کلی: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
