# -*- coding: utf-8 -*-
"""
اسکریپت ایجاد کالکشن azizashna
کالکشن قوانین و مقررات ایران شامل:
- قانون ایثارگران
- قانون جهاد دانشگاهی
- قانون دیوان عدالت اداری
- قانون وزارت بهداشت
- کلیات (قوانین وزارت علوم)
"""

import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
COLLECTION_NAME = "azizashna"
DISPLAY_NAME = "عزیزآشنا - قوانین و مقررات ایران"
COLLECTION_TYPE = "legal"
DESCRIPTION = "پایگاه دانش قوانین و مقررات جمهوری اسلامی ایران شامل قوانین ایثارگران، جهاد دانشگاهی، دیوان عدالت اداری، وزارت بهداشت و وزارت علوم"

# System Prompt مخصوص کالکشن
SYSTEM_PROMPT = """شما یک دستیار حقوقی تخصصی در زمینه قوانین و مقررات جمهوری اسلامی ایران هستید.

**وظایف شما:**
1. پاسخ دقیق و مستند به سوالات حقوقی و قانونی کاربران
2. ارجاع به شماره ماده و نام قانون مربوطه در پاسخ‌ها
3. توضیح مفاهیم حقوقی به زبان ساده و قابل فهم
4. ارائه تبصره‌ها و جزئیات مرتبط با موضوع سوال

**قوانین موجود در پایگاه دانش:**
- قانون جامع خدمات‌رسانی به ایثارگران (بنیاد شهید و امور ایثارگران)
- قانون جهاد دانشگاهی (سازمان تجاری‌سازی فناوری و اشتغال)
- قانون دیوان عدالت اداری (رسیدگی به تظلمات و شکایات)
- قانون وزارت بهداشت، درمان و آموزش پزشکی
- مجموعه قوانین و مقررات وزارت علوم، تحقیقات و فناوری

**اصول پاسخگویی:**
- همیشه به منبع (نام قانون و شماره ماده) اشاره کنید
- اگر اطلاعات دقیق در پایگاه دانش موجود نیست، صادقانه اعلام کنید
- در صورت نیاز، تبصره‌های مرتبط را نیز ذکر کنید
- از اصطلاحات تخصصی حقوقی با توضیح مناسب استفاده کنید
- پاسخ‌ها را منظم و با ساختار مناسب ارائه دهید

**فرمت پاسخ:**
1. ابتدا پاسخ کوتاه و مستقیم
2. سپس جزئیات و ارجاعات قانونی
3. در صورت لزوم، توضیحات تکمیلی و تبصره‌ها

به سوالات کاربر با دقت، صداقت و استناد به قوانین موجود پاسخ دهید."""


def load_json_file(file_path: Path) -> List[Dict[str, Any]]:
    """بارگذاری فایل JSON"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"✅ فایل {file_path.name} بارگذاری شد: {len(data)} رکورد")
        return data
    except Exception as e:
        logger.error(f"❌ خطا در بارگذاری {file_path}: {e}")
        return []


def prepare_document(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    آماده‌سازی یک سند برای امبد کردن
    
    ساختار سند:
    - text: متن کامل قابل جستجو
    - metadata: متادیتای غنی
    """
    payload = record.get("payload", {})
    
    # متن اصلی
    text = payload.get("text", "")
    
    # metadata
    metadata = payload.get("metadata", {})
    source = payload.get("source", {})
    
    # ساخت متن غنی‌تر برای جستجوی بهتر
    book_title = metadata.get("book_title", "")
    major_division = metadata.get("major_division_title", "")
    section_type = metadata.get("section_type", "")
    section_number = metadata.get("section_number", "")
    semantic_summary = metadata.get("semantic_summary", "")
    keywords = metadata.get("keywords", [])
    
    # متن کامل برای امبد کردن
    full_text = f"""[{book_title}]
{major_division}
{section_type} {section_number}:

{text}

"""
    
    # اضافه کردن خلاصه معنایی
    if semantic_summary:
        full_text += f"خلاصه: {semantic_summary}\n"
    
    # اضافه کردن کلمات کلیدی
    if keywords:
        full_text += f"کلمات کلیدی: {', '.join(keywords)}"
    
    # ساخت metadata برای ChromaDB
    chroma_metadata = {
        "id": record.get("id", "") or "",
        "book_title": book_title or "",
        "book_type": metadata.get("book_type", "") or "",
        "major_division_title": major_division or "",
        "major_division_type": metadata.get("major_division_type", "") or "",
        "section_type": section_type or "",
        "section_number": section_number or "",
        "section_title": metadata.get("section_title", "") or "",
        "semantic_summary": semantic_summary or "",
        "keywords": "|".join(keywords) if keywords else "",
        "article_type": metadata.get("article_type", "") or "",
        "has_subsections": str(metadata.get("has_subsections", False)),
        "organization": source.get("organization", "") or "",
        "page_number": source.get("page_number", "") or "",
        "content_type": payload.get("type", "law_content") or "law_content",
        "created_at": datetime.now().isoformat()
    }
    
    # اضافه کردن فیلدهای اضافی اگر وجود داشته باشند (بدون None)
    if metadata.get("subsection_number"):
        chroma_metadata["subsection_number"] = str(metadata["subsection_number"])
    if metadata.get("parent_section"):
        chroma_metadata["parent_section"] = str(metadata["parent_section"])
    if metadata.get("approval_date"):
        chroma_metadata["approval_date"] = str(metadata["approval_date"])
    if metadata.get("approval_body"):
        chroma_metadata["approval_body"] = str(metadata["approval_body"])
    
    return {
        "text": full_text.strip(),
        "metadata": chroma_metadata,
        "original_text": text
    }


async def create_azizashna_collection():
    """ایجاد و پر کردن کالکشن azizashna"""
    
    logger.info("=" * 80)
    logger.info("🚀 شروع ایجاد کالکشن azizashna")
    logger.info("=" * 80)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # مرحله 1: بارگذاری داده‌ها
    # ═══════════════════════════════════════════════════════════════════════════════
    logger.info("\n📂 مرحله 1: بارگذاری فایل‌های JSON")
    
    data_dir = project_root / "archive" / "data_files"
    
    json_files = [
        "قانون ایثارگران.json",
        "قانون جهاد.json",
        "قانون دیوان عدالت اداری.json",
        "قانون وزارت بهداشت.json",
        "کلیات.json"
    ]
    
    all_records = []
    for json_file in json_files:
        file_path = data_dir / json_file
        if file_path.exists():
            records = load_json_file(file_path)
            all_records.extend(records)
        else:
            logger.warning(f"⚠️ فایل یافت نشد: {json_file}")
    
    logger.info(f"\n📊 مجموع رکوردها: {len(all_records)}")
    
    if not all_records:
        logger.error("❌ هیچ داده‌ای برای پردازش یافت نشد!")
        return {"success": False, "error": "No data found"}
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # مرحله 2: آماده‌سازی اسناد
    # ═══════════════════════════════════════════════════════════════════════════════
    logger.info("\n📝 مرحله 2: آماده‌سازی اسناد")
    
    documents = []
    metadatas = []
    
    for record in all_records:
        doc = prepare_document(record)
        if doc["text"].strip():
            documents.append(doc["text"])
            metadatas.append(doc["metadata"])
    
    logger.info(f"✅ {len(documents)} سند آماده شد")
    
    # آمار منابع
    source_stats = {}
    for meta in metadatas:
        book = meta.get("book_title", "نامشخص")
        source_stats[book] = source_stats.get(book, 0) + 1
    
    logger.info("\n📋 آمار منابع:")
    for book, count in source_stats.items():
        logger.info(f"   - {book}: {count} سند")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # مرحله 3: ایجاد کالکشن
    # ═══════════════════════════════════════════════════════════════════════════════
    logger.info("\n🗂️ مرحله 3: ایجاد کالکشن در ChromaDB")
    
    try:
        from ultimate_rag_system import UltimateRAGSystem
        from services.persian_embedding_service import PersianEmbeddingClient
        
        # Initialize RAG system
        rag_system = UltimateRAGSystem()
        chroma_client = rag_system.chroma_client
        
        # Delete existing collection if exists
        try:
            chroma_client.delete_collection(COLLECTION_NAME)
            logger.info(f"✅ کالکشن قبلی {COLLECTION_NAME} حذف شد")
        except:
            logger.info(f"ℹ️ کالکشن قبلی وجود نداشت")
        
        # Create new collection
        collection = chroma_client.create_collection(
            name=COLLECTION_NAME,
            metadata={
                "display_name": DISPLAY_NAME,
                "collection_type": COLLECTION_TYPE,
                "processing_mode": "rag_only",
                "description": DESCRIPTION,
                "created_at": datetime.now().isoformat()
            }
        )
        logger.info(f"✅ کالکشن {COLLECTION_NAME} ایجاد شد")
        
    except Exception as e:
        logger.error(f"❌ خطا در ایجاد کالکشن: {e}")
        return {"success": False, "error": str(e)}
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # مرحله 4: تولید Embeddings
    # ═══════════════════════════════════════════════════════════════════════════════
    logger.info("\n🧠 مرحله 4: تولید Embeddings")
    
    try:
        embedding_service = PersianEmbeddingClient()
        
        # Generate embeddings in batches
        BATCH_SIZE = 50
        all_embeddings = []
        
        for i in range(0, len(documents), BATCH_SIZE):
            batch_docs = documents[i:i+BATCH_SIZE]
            logger.info(f"  📦 پردازش batch {i//BATCH_SIZE + 1}/{(len(documents)-1)//BATCH_SIZE + 1}")
            
            if hasattr(embedding_service, "generate_embeddings"):
                batch_embeddings = await embedding_service.generate_embeddings(batch_docs)
            else:
                # Fallback: generate one by one
                tasks = [embedding_service.generate_embedding(doc) for doc in batch_docs]
                batch_embeddings = await asyncio.gather(*tasks)
            
            all_embeddings.extend(batch_embeddings)
        
        logger.info(f"✅ {len(all_embeddings)} embedding تولید شد")
        
    except Exception as e:
        logger.error(f"❌ خطا در تولید embeddings: {e}")
        return {"success": False, "error": str(e)}
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # مرحله 5: افزودن اسناد به کالکشن
    # ═══════════════════════════════════════════════════════════════════════════════
    logger.info("\n📤 مرحله 5: افزودن اسناد به کالکشن")
    
    try:
        # Generate IDs
        ids = [f"azizashna_{uuid.uuid4().hex[:8]}" for _ in documents]
        
        # Add to collection in batches
        ADD_BATCH_SIZE = 100
        for i in range(0, len(documents), ADD_BATCH_SIZE):
            batch_end = min(i + ADD_BATCH_SIZE, len(documents))
            
            collection.add(
                ids=ids[i:batch_end],
                embeddings=all_embeddings[i:batch_end],
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end]
            )
            
            logger.info(f"  📦 batch {i//ADD_BATCH_SIZE + 1}: {batch_end - i} سند اضافه شد")
        
        logger.info(f"✅ مجموع {len(documents)} سند به کالکشن اضافه شد")
        
    except Exception as e:
        logger.error(f"❌ خطا در افزودن اسناد: {e}")
        return {"success": False, "error": str(e)}
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # مرحله 6: ذخیره config کالکشن
    # ═══════════════════════════════════════════════════════════════════════════════
    logger.info("\n💾 مرحله 6: ذخیره config کالکشن")
    
    try:
        config_path = project_root / "collections_config"
        config_path.mkdir(exist_ok=True, parents=True)
        
        config = {
            "collection_name": COLLECTION_NAME,
            "display_name": DISPLAY_NAME,
            "collection_type": COLLECTION_TYPE,
            "processing_mode": "rag_only",
            "description": DESCRIPTION,
            "system_prompt": SYSTEM_PROMPT,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "documents_count": len(documents),
            "retrieval_config": {
                "top_k": 5,
                "use_reranking": True,
                "semantic_weight": 0.7,
                "keyword_weight": 0.3
            },
            "generation_config": {
                "temperature": 0.2,
                "max_tokens": 2048,
                "top_p": 0.9
            },
            "metadata": {
                "sources": list(source_stats.keys()),
                "total_documents": len(documents),
                "source_stats": source_stats
            }
        }
        
        config_file = config_path / f"{COLLECTION_NAME}.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Config ذخیره شد: {config_file}")
        
    except Exception as e:
        logger.warning(f"⚠️ خطا در ذخیره config: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # مرحله 7: اعتبارسنجی
    # ═══════════════════════════════════════════════════════════════════════════════
    logger.info("\n✅ مرحله 7: اعتبارسنجی")
    
    final_count = collection.count()
    logger.info(f"📊 تعداد اسناد در کالکشن: {final_count}")
    
    if final_count != len(documents):
        logger.warning(f"⚠️ تعداد اسناد مطابقت ندارد: {final_count} vs {len(documents)}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # خلاصه نهایی
    # ═══════════════════════════════════════════════════════════════════════════════
    logger.info("\n" + "=" * 80)
    logger.info("✅ کالکشن azizashna با موفقیت ایجاد شد!")
    logger.info("=" * 80)
    logger.info(f"\n📊 خلاصه:")
    logger.info(f"   - نام کالکشن: {COLLECTION_NAME}")
    logger.info(f"   - نام نمایشی: {DISPLAY_NAME}")
    logger.info(f"   - نوع کالکشن: {COLLECTION_TYPE}")
    logger.info(f"   - تعداد اسناد: {final_count}")
    logger.info(f"\n📋 منابع:")
    for book, count in source_stats.items():
        logger.info(f"   ✅ {book}: {count} سند")
    logger.info(f"\n🚀 سیستم آماده پاسخگویی به سوالات حقوقی است!")
    
    return {
        "success": True,
        "collection_name": COLLECTION_NAME,
        "documents_count": final_count,
        "source_stats": source_stats
    }


async def test_collection():
    """تست کالکشن"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 تست کالکشن azizashna")
    logger.info("=" * 80)
    
    test_queries = [
        "ماده ۳ قانون ایثارگران چیست؟",
        "وظایف دیوان عدالت اداری کدامند؟",
        "آیا ایثارگران از سهمیه وکالت برخوردارند؟",
        "معاونت‌های وزارت بهداشت چه نام دارند؟",
        "هدف از قانون جهاد دانشگاهی چیست؟"
    ]
    
    try:
        import httpx
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            for query in test_queries:
                logger.info(f"\n❓ سوال: {query}")
                
                response = await client.post(
                    "http://localhost:8010/v2/query/streaming",
                    json={
                        "query": query,
                        "collection_name": COLLECTION_NAME
                    }
                )
                
                if response.status_code == 200:
                    # Parse SSE response
                    content = response.text
                    # Extract the answer from SSE events
                    logger.info(f"✅ پاسخ دریافت شد")
                else:
                    logger.error(f"❌ خطا: {response.status_code}")
    
    except Exception as e:
        logger.warning(f"⚠️ تست انجام نشد (سرور احتمالاً در حال اجرا نیست): {e}")


if __name__ == "__main__":
    async def main():
        # ایجاد کالکشن
        result = await create_azizashna_collection()
        
        if result.get("success"):
            # تست کالکشن
            await test_collection()
            sys.exit(0)
        else:
            logger.error(f"❌ خطا: {result.get('error')}")
            sys.exit(1)
    
    asyncio.run(main())
