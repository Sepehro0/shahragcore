# -*- coding: utf-8 -*-
"""
بازسازی کامل کالکشن azizashna - نسخه ۲
با ساختار document text بهینه‌تر برای retrieval دقیق‌تر
"""

import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

COLLECTION_NAME = "azizashna"
DISPLAY_NAME = "عزیزآشنا - قوانین و مقررات ایران"
COLLECTION_TYPE = "legal"
DESCRIPTION = "پایگاه دانش قوانین و مقررات جمهوری اسلامی ایران"

SYSTEM_PROMPT = """شما یک دستیار حقوقی تخصصی در زمینه قوانین و مقررات جمهوری اسلامی ایران هستید.

**قوانین موجود در پایگاه دانش:**
- قانون جامع خدمات‌رسانی به ایثارگران (بنیاد شهید و امور ایثارگران)
- قانون جهاد دانشگاهی (سازمان تجاری‌سازی فناوری و اشتغال)
- قانون دیوان عدالت اداری (رسیدگی به تظلمات و شکایات)
- قانون وزارت بهداشت، درمان و آموزش پزشکی
- مجموعه قوانین و مقررات وزارت علوم، تحقیقات و فناوری

**اصول مهم پاسخگویی:**
- هر ماده را با ذکر دقیق شماره ماده و نام قانون مربوطه بیاورید
- اگر کاربر از "این مجموعه" یا "این قانون" استفاده کرد، به آخرین قانون مورد بحث در مکالمه توجه کنید
- تمام مواد مرتبط را از تمام قوانین موجود بیاورید، نه فقط یک قانون
- اگر ماده‌ای در چند قانون مختلف وجود دارد، همه را ذکر کنید
- فقط زمانی بگویید "موجود نیست" که واقعاً در هیچ‌کدام از اسناد نباشد
- پاسخ‌ها را با ساختار منظم و ارجاع به منبع ارائه دهید

**فرمت پاسخ:**
1. پاسخ مستقیم با ذکر نام قانون و شماره ماده
2. متن کامل ماده
3. توضیحات تکمیلی در صورت نیاز"""


def to_str(val) -> str:
    """تبدیل هر مقدار به string برای ChromaDB"""
    if val is None:
        return ""
    if isinstance(val, list):
        return "|".join(str(v) for v in val)
    return str(val)


def num_to_persian(n: str) -> str:
    """تبدیل عدد انگلیسی به فارسی برای matching بهتر"""
    mapping = {'0':'۰','1':'۱','2':'۲','3':'۳','4':'۴','5':'۵','6':'۶','7':'۷','8':'۸','9':'۹'}
    return ''.join(mapping.get(c, c) for c in str(n))


def prepare_document_v2(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    آماده‌سازی سند با ساختار بهینه برای retrieval دقیق:
    - نام قانون و شماره ماده در ابتدای متن (برای matching سریع)
    - متن اصلی + خلاصه + کلمات کلیدی
    - هم شماره فارسی هم انگلیسی برای جستجوی بهتر
    """
    payload = record.get("payload", {})
    text = payload.get("text", "")
    metadata = payload.get("metadata", {})
    source = payload.get("source", {})

    book_title = to_str(metadata.get("book_title"))
    major_div_type = to_str(metadata.get("major_division_type"))
    major_div_title = to_str(metadata.get("major_division_title"))
    section_type = to_str(metadata.get("section_type"))
    section_number = to_str(metadata.get("section_number"))
    section_title = to_str(metadata.get("section_title"))
    semantic_summary = to_str(metadata.get("semantic_summary"))
    keywords_raw = metadata.get("keywords", [])
    if isinstance(keywords_raw, str):
        keywords_list = [k.strip() for k in keywords_raw.replace('|', ',').split(',') if k.strip()]
    elif isinstance(keywords_raw, list):
        keywords_list = keywords_raw
    else:
        keywords_list = []

    # شماره فارسی برای matching بهتر با queries فارسی
    sec_num_persian = num_to_persian(section_number) if section_number.isdigit() else section_number

    # ===== ساختار جدید document text =====
    # خط اول: شناسه کامل (برای retrieval دقیق)
    header = f"قانون: {book_title}"
    if section_type and section_number:
        header += f"\n{section_type} {section_number}"
        if sec_num_persian != section_number:
            header += f" ({section_type} {sec_num_persian})"
    if section_title:
        header += f" - {section_title}"

    # بخش دوم: موقعیت در قانون
    location_parts = []
    if major_div_type:
        location_parts.append(major_div_type)
    if major_div_title:
        location_parts.append(major_div_title)
    location = " | ".join(location_parts) if location_parts else ""

    # ساخت متن کامل
    parts = [header]
    if location:
        parts.append(f"بخش: {location}")
    parts.append("")
    parts.append(text)

    if semantic_summary:
        parts.append(f"\nخلاصه: {semantic_summary}")

    if keywords_list:
        parts.append(f"کلمات کلیدی: {' | '.join(keywords_list)}")

    full_text = "\n".join(parts).strip()

    # metadata برای ChromaDB
    chroma_metadata = {
        "id": to_str(record.get("id")),
        "book_title": book_title,
        "book_type": to_str(metadata.get("book_type")),
        "major_division_type": major_div_type,
        "major_division_title": major_div_title,
        "section_type": section_type,
        "section_number": section_number,
        "section_number_persian": sec_num_persian,
        "section_title": section_title,
        "semantic_summary": semantic_summary,
        "keywords": "|".join(keywords_list),
        "article_type": to_str(metadata.get("article_type")),
        "has_subsections": to_str(metadata.get("has_subsections", False)),
        "organization": to_str(source.get("organization")),
        "page_number": to_str(source.get("page_number")),
        "content_type": to_str(payload.get("type")) or "law_content",
        "created_at": datetime.now().isoformat()
    }

    # فیلدهای اختیاری
    for field in ["subsection_number", "parent_section", "approval_date", "approval_body"]:
        val = metadata.get(field)
        if val:
            chroma_metadata[field] = to_str(val)

    return {
        "text": full_text,
        "metadata": chroma_metadata,
        "original_text": text
    }


async def rebuild_collection():
    """بازسازی کامل کالکشن azizashna"""
    logger.info("=" * 70)
    logger.info("🔄 بازسازی کالکشن azizashna (نسخه ۲)")
    logger.info("=" * 70)

    # بارگذاری داده‌ها
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
        fp = data_dir / json_file
        if fp.exists():
            with open(fp, 'r', encoding='utf-8') as f:
                records = json.load(f)
            all_records.extend(records)
            logger.info(f"  ✅ {json_file}: {len(records)} رکورد")
        else:
            logger.warning(f"  ⚠️ فایل نیافت: {json_file}")

    logger.info(f"\n📊 مجموع: {len(all_records)} رکورد")

    # آماده‌سازی اسناد
    documents = []
    metadatas = []
    for rec in all_records:
        doc = prepare_document_v2(rec)
        if doc["text"].strip():
            documents.append(doc["text"])
            metadatas.append(doc["metadata"])

    source_stats = {}
    for m in metadatas:
        b = m.get("book_title", "?")
        source_stats[b] = source_stats.get(b, 0) + 1

    logger.info("\n📋 آمار منابع:")
    for book, cnt in source_stats.items():
        logger.info(f"   {book}: {cnt}")

    # نمونه سند برای بررسی
    logger.info("\n🔍 نمونه سند (ماده ۱ وزارت علوم):")
    for i, (doc, meta) in enumerate(zip(documents, metadatas)):
        if 'وزارت علوم' in meta.get('book_title', '') and meta.get('section_number') == '1':
            logger.info(f"\n{doc[:600]}\n...")
            break

    # ایجاد کالکشن ChromaDB
    try:
        from ultimate_rag_system import UltimateRAGSystem
        from services.persian_embedding_service import PersianEmbeddingClient

        rag = UltimateRAGSystem()
        chroma = rag.chroma_client

        try:
            chroma.delete_collection(COLLECTION_NAME)
            logger.info(f"\n✅ کالکشن قبلی حذف شد")
        except Exception:
            pass

        collection = chroma.create_collection(
            name=COLLECTION_NAME,
            metadata={
                "display_name": DISPLAY_NAME,
                "collection_type": COLLECTION_TYPE,
                "processing_mode": "rag_only",
                "description": DESCRIPTION,
                "created_at": datetime.now().isoformat()
            }
        )
        logger.info(f"✅ کالکشن جدید ایجاد شد")

    except Exception as e:
        logger.error(f"❌ خطا در ایجاد کالکشن: {e}")
        return False

    # تولید embeddings
    logger.info("\n🧠 تولید Embeddings...")
    try:
        embed_svc = PersianEmbeddingClient()
        BATCH = 50
        all_embeddings = []

        for i in range(0, len(documents), BATCH):
            batch = documents[i:i+BATCH]
            batch_num = i // BATCH + 1
            total_batches = (len(documents) - 1) // BATCH + 1
            logger.info(f"  📦 Batch {batch_num}/{total_batches} ({len(batch)} سند)...")

            if hasattr(embed_svc, "generate_embeddings"):
                embs = await embed_svc.generate_embeddings(batch)
            else:
                tasks = [embed_svc.generate_embedding(d) for d in batch]
                embs = await asyncio.gather(*tasks)

            all_embeddings.extend(embs)

        logger.info(f"✅ {len(all_embeddings)} embedding تولید شد")

    except Exception as e:
        logger.error(f"❌ خطا در embeddings: {e}")
        return False

    # افزودن به ChromaDB
    logger.info("\n📤 افزودن اسناد به ChromaDB...")
    try:
        ids = [f"azizashna_{uuid.uuid4().hex[:8]}" for _ in documents]
        BATCH = 100
        for i in range(0, len(documents), BATCH):
            end = min(i + BATCH, len(documents))
            collection.add(
                ids=ids[i:end],
                embeddings=all_embeddings[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end]
            )
            logger.info(f"  ✅ {end}/{len(documents)} سند اضافه شد")

        final_count = collection.count()
        logger.info(f"✅ مجموع {final_count} سند در کالکشن")

    except Exception as e:
        logger.error(f"❌ خطا در افزودن: {e}")
        return False

    # ذخیره config با top_k بالاتر
    config = {
        "collection_name": COLLECTION_NAME,
        "display_name": DISPLAY_NAME,
        "collection_type": COLLECTION_TYPE,
        "processing_mode": "rag_only",
        "description": DESCRIPTION,
        "system_prompt": SYSTEM_PROMPT,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "documents_count": final_count,
        "retrieval_config": {
            "top_k": 15,
            "use_reranking": True,
            "semantic_weight": 0.7,
            "keyword_weight": 0.3
        },
        "generation_config": {
            "temperature": 0.1,
            "max_tokens": 2048,
            "top_p": 0.9
        },
        "metadata": {
            "sources": list(source_stats.keys()),
            "total_documents": final_count,
            "source_stats": source_stats,
            "version": "2.0",
            "rebuild_reason": "improved document text structure for better retrieval accuracy"
        }
    }

    config_file = project_root / "collections_config" / f"{COLLECTION_NAME}.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ Config ذخیره شد (top_k=15)")

    logger.info("\n" + "=" * 70)
    logger.info("✅ بازسازی کالکشن با موفقیت انجام شد!")
    logger.info("=" * 70)
    return True


if __name__ == "__main__":
    success = asyncio.run(rebuild_collection())
    sys.exit(0 if success else 1)
