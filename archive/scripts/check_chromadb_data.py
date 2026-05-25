#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت بررسی مستقیم داده‌های ChromaDB
برای بررسی اینکه آیا داده‌های مربوط به سوالات خاص در ChromaDB وجود دارند یا نه
"""

import sys
import asyncio
sys.path.insert(0, '.')

import chromadb
from chromadb.config import Settings
from services.persian_embedding_service import PersianEmbeddingClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_chromadb_for_queries():
    """بررسی مستقیم ChromaDB برای دو سوال خاص"""
    
    # Initialize ChromaDB client
    db_path = "/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    client = chromadb.PersistentClient(path=db_path, settings=Settings(anonymized_telemetry=False))
    
    collection_name = 'budget_financial'
    
    try:
        collection = client.get_collection(name=collection_name)
        logger.info(f"✅ Collection '{collection_name}' found")
    except Exception as e:
        logger.error(f"❌ Collection '{collection_name}' not found: {e}")
        return
    
    # Skip embedding client for now (CUDA issues)
    embedding_client = None
    logger.info("⚠️ Skipping embedding client (using text search only)")
    
    # سوالات برای بررسی
    queries = [
        "درامد استانی اختصاصی دانشگاه تبریز در سال 1403",
        "درآمدهای وزارت نفت چقدر است"
    ]
    
    # کلمات کلیدی برای جستجوی متنی
    keywords = [
        ["دانشگاه", "تبریز", "1403", "استانی", "اختصاصی"],
        ["وزارت", "نفت", "درآمد", "1403"]
    ]
    
    print("\n" + "="*90)
    print("بررسی مستقیم ChromaDB")
    print("="*90 + "\n")
    
    for i, query in enumerate(queries):
        print(f"\n{'='*90}")
        print(f"سوال {i+1}: {query}")
        print(f"{'='*90}\n")
        
        # 1. جستجوی متنی با کلمات کلیدی
        print("📝 جستجوی متنی با کلمات کلیدی:")
        print(f"   کلمات: {', '.join(keywords[i])}\n")
        
        # جستجو در metadata و documents
        try:
            # جستجو در documents - ChromaDB از where clause پشتیبانی نمی‌کند برای content
            # باید از query استفاده کنیم یا همه را بگیریم و فیلتر کنیم
            all_docs = collection.get(limit=1000)  # گرفتن نمونه
            
            # فیلتر کردن بر اساس کلمات کلیدی
            matching_ids = []
            matching_docs = []
            matching_metas = []
            
            for idx, (doc_id, content) in enumerate(zip(all_docs['ids'], all_docs['documents'])):
                # بررسی اینکه آیا هر کدام از کلمات کلیدی در content وجود دارد
                content_lower = content.lower() if content else ""
                if any(kw.lower() in content_lower for kw in keywords[i]):
                    matching_ids.append(doc_id)
                    matching_docs.append(content)
                    if all_docs.get('metadatas') and all_docs['metadatas'][idx]:
                        matching_metas.append(all_docs['metadatas'][idx])
                    else:
                        matching_metas.append({})
            
            results_text = {
                'ids': matching_ids[:10],
                'documents': matching_docs[:10],
                'metadata': matching_metas[:10]
            }
            
            if results_text['ids']:
                print(f"   ✅ {len(results_text['ids'])} نتیجه پیدا شد (از {len(all_docs['ids'])} document بررسی شده):")
                for idx, (doc_id, content) in enumerate(zip(results_text['ids'], results_text['documents'])):
                    print(f"\n   [{idx+1}] ID: {doc_id}")
                    # نمایش 300 کاراکتر اول
                    preview = content[:300] if len(content) > 300 else content
                    print(f"   Content: {preview}...")
                    if results_text['metadata'] and results_text['metadata'][idx]:
                        meta = results_text['metadata'][idx]
                        print(f"   Metadata: {meta}")
            else:
                print(f"   ❌ هیچ نتیجه‌ای پیدا نشد (از {len(all_docs['ids'])} document بررسی شده)")
        except Exception as e:
            logger.warning(f"   ⚠️ خطا در جستجوی متنی: {e}")
        
        # 2. جستجوی semantic با embedding
        if embedding_client:
            print(f"\n🔍 جستجوی semantic با embedding:")
            try:
                # تولید embedding برای query
                query_embedding = embedding_client.embed_query(query)
                
                # جستجو در ChromaDB
                results_semantic = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=10
                )
                
                if results_semantic['ids'] and results_semantic['ids'][0]:
                    print(f"   ✅ {len(results_semantic['ids'][0])} نتیجه پیدا شد:")
                    for idx, (doc_id, distance) in enumerate(zip(
                        results_semantic['ids'][0][:5], 
                        results_semantic['distances'][0][:5] if results_semantic['distances'] else [0]*5
                    )):
                        print(f"\n   [{idx+1}] ID: {doc_id} (distance: {distance:.4f})")
                        if results_semantic['documents'] and results_semantic['documents'][0]:
                            content = results_semantic['documents'][0][idx]
                            preview = content[:200] if len(content) > 200 else content
                            print(f"   Content: {preview}...")
                        if results_semantic['metadatas'] and results_semantic['metadatas'][0]:
                            meta = results_semantic['metadatas'][0][idx]
                            if meta:
                                print(f"   Metadata: {meta}")
                else:
                    print(f"   ❌ هیچ نتیجه‌ای پیدا نشد")
            except Exception as e:
                logger.warning(f"   ⚠️ خطا در جستجوی semantic: {e}")
        
        # 3. جستجوی دقیق‌تر با ترکیب کلمات
        print(f"\n🔎 جستجوی دقیق‌تر:")
        try:
            # گرفتن همه documents برای جستجو
            all_docs = collection.get(limit=2000)
            
            matching_ids = []
            matching_docs = []
            matching_metas = []
            
            # برای دانشگاه تبریز
            if i == 0:
                search_terms = ["دانشگاه تبریز", "تبریز", "استانی اختصاصی"]
            else:
                # برای وزارت نفت
                search_terms = ["وزارت نفت", "نفت", "درآمد"]
            
            for idx, (doc_id, content) in enumerate(zip(all_docs['ids'], all_docs['documents'])):
                content_lower = content.lower() if content else ""
                # بررسی metadata هم
                meta = all_docs.get('metadatas', [{}])[idx] if all_docs.get('metadatas') else {}
                meta_str = str(meta).lower()
                
                # بررسی اینکه آیا هر کدام از search terms در content یا metadata وجود دارد
                if any(term.lower() in content_lower or term.lower() in meta_str for term in search_terms):
                    matching_ids.append(doc_id)
                    matching_docs.append(content)
                    matching_metas.append(meta)
            
            results_exact = {
                'ids': matching_ids[:10],
                'documents': matching_docs[:10],
                'metadatas': matching_metas[:10]
            }
            
            if results_exact['ids']:
                print(f"   ✅ {len(results_exact['ids'])} نتیجه پیدا شد (از {len(all_docs['ids'])} document بررسی شده):")
                for idx, (doc_id, content) in enumerate(zip(results_exact['ids'][:5], results_exact['documents'][:5])):
                    print(f"\n   [{idx+1}] ID: {doc_id}")
                    # نمایش 400 کاراکتر اول
                    preview = content[:400] if len(content) > 400 else content
                    print(f"   Content: {preview}...")
                    if results_exact['metadatas'] and results_exact['metadatas'][idx]:
                        meta = results_exact['metadatas'][idx]
                        print(f"   Metadata: {meta}")
            else:
                print(f"   ❌ هیچ نتیجه‌ای پیدا نشد (از {len(all_docs['ids'])} document بررسی شده)")
        except Exception as e:
            logger.warning(f"   ⚠️ خطا در جستجوی دقیق: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    # 4. بررسی کلی collection
    print(f"\n{'='*90}")
    print("اطلاعات کلی Collection")
    print(f"{'='*90}\n")
    
    try:
        count = collection.count()
        print(f"📊 تعداد کل documents در collection: {count}")
        
        # نمونه‌ای از documents
        sample = collection.get(limit=3)
        if sample['ids']:
            print(f"\n📄 نمونه documents:")
            for idx, (doc_id, content) in enumerate(zip(sample['ids'], sample['documents'])):
                print(f"\n[{idx+1}] ID: {doc_id}")
                preview = content[:150] if len(content) > 150 else content
                print(f"Content: {preview}...")
    except Exception as e:
        logger.error(f"❌ خطا در بررسی collection: {e}")


if __name__ == "__main__":
    asyncio.run(check_chromadb_for_queries())

