# -*- coding: utf-8 -*-
"""
بازسازی کامل کالکشن azizashna - نسخه ۳
اضافه شدن شناسایی زیرقانون‌ها برای کلیات.json (رفع مشکل مواد تکراری)
"""

import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

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
- مجموعه قوانین و مقررات وزارت علوم، تحقیقات و فناوری شامل:
  * نقشه جامع علمی کشور (مواد ۱ تا ۸)
  * آیین‌نامه ستاد راهبری نقشه جامع علمی کشور (مواد ۱ تا ۶ - اختصارات، ارکان، وظایف شورای ستاد، وظایف رئیس)
  * قانون برنامه پنجم توسعه (مواد ۱۵ تا ۲۹ و مواد ۱۱۲، ۱۵۰، ۱۶۹، ۲۲۴)
  * قانون اهداف، وظایف و تشکیلات وزارت علوم مصوب ۱۳۸۳ (مواد ۱ تا ۱۲)
  * ماده ۴۱ قانون برنامه پنجم توسعه - شاخص‌ها
  * قانون تشکیل هیأت‌های امنای دانشگاه‌ها (مواد ۱ تا ۱۱)
  * ماده ۱۰ و ماده ۲۰ قانون برنامه پنجم توسعه (بندهای تکمیلی)
  * قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳ (مواد ۱ تا ۲۱)

**اصول مهم پاسخگویی:**
- هر ماده را با ذکر دقیق شماره ماده، نام زیرقانون و نام مجموعه بیاورید
- وقتی چند ماده با شماره یکسان در زیرقوانین مختلف وجود دارد، همه را ذکر کنید
- اگر کاربر سوال مفهومی دارد (مثلاً وظایف شورای ستاد)، تمام اطلاعات مرتبط را کامل بیاورید
- فقط زمانی بگویید "موجود نیست" که واقعاً در هیچ‌کدام از اسناد نباشد
- متن کامل مواد را بیاورید، خلاصه نکنید مگر کاربر بخواهد

**فرمت پاسخ:**
1. پاسخ مستقیم با ذکر نام قانون/زیرقانون و شماره ماده
2. متن کامل ماده با تمام بندها و تبصره‌ها
3. توضیحات تکمیلی در صورت نیاز"""


# ═══════════════════════════════════════════════════════════════════
# نگاشت زیرقانون‌های کلیات.json
# بر اساس تحلیل ساختار فایل (record index → sub-law name)
# ═══════════════════════════════════════════════════════════════════
KLIYAT_SUB_LAW_MAP = {
    "law-article-1": "نقشه جامع علمی کشور",
    "law-article-2": "نقشه جامع علمی کشور",
    "law-article-3": "نقشه جامع علمی کشور",
    "law-article-4": "نقشه جامع علمی کشور",
    "law-article-5": "نقشه جامع علمی کشور",
    "law-article-6": "نقشه جامع علمی کشور",
    "law-article-7": "نقشه جامع علمی کشور",
    "law-article-8-subsection-3_11": "نقشه جامع علمی کشور",

    "law-article-9": "آیین‌نامه ستاد راهبری نقشه جامع علمی کشور",
    "law-article-10": "آیین‌نامه ستاد راهبری نقشه جامع علمی کشور",
    "law-article-11": "آیین‌نامه ستاد راهبری نقشه جامع علمی کشور",
    "law-article-12": "آیین‌نامه ستاد راهبری نقشه جامع علمی کشور",
    "law-article-13": "آیین‌نامه ستاد راهبری نقشه جامع علمی کشور",
    "law-article-14": "آیین‌نامه ستاد راهبری نقشه جامع علمی کشور",

    "law-article-15": "قانون برنامه پنجم توسعه",
    "law-article-16": "قانون برنامه پنجم توسعه",
    "law-article-17": "قانون برنامه پنجم توسعه",
    "law-article-18": "قانون برنامه پنجم توسعه",
    "law-article-19": "قانون برنامه پنجم توسعه",
    "law-article-20": "قانون برنامه پنجم توسعه",
    "law-article-21": "قانون برنامه پنجم توسعه",
    "law-article-22": "قانون برنامه پنجم توسعه",
    "law-article-23": "قانون برنامه پنجم توسعه",
    "law-article-24": "قانون برنامه پنجم توسعه",
    "law-article-25": "قانون برنامه پنجم توسعه",
    "law-article-26": "قانون برنامه پنجم توسعه",
    "law-article-27": "قانون برنامه پنجم توسعه",
    "law-article-28": "قانون برنامه پنجم توسعه",
    "law-article-29": "قانون برنامه پنجم توسعه",

    "law-article-30": "قانون اهداف، وظایف و تشکیلات وزارت علوم مصوب ۱۳۸۳",
    "law-article-31": "قانون اهداف، وظایف و تشکیلات وزارت علوم مصوب ۱۳۸۳",
    "law-article-32": "قانون اهداف، وظایف و تشکیلات وزارت علوم مصوب ۱۳۸۳",
    "law-article-33": "قانون اهداف، وظایف و تشکیلات وزارت علوم مصوب ۱۳۸۳",
    "law-article-34": "قانون اهداف، وظایف و تشکیلات وزارت علوم مصوب ۱۳۸۳",
    "law-article-35": "قانون اهداف، وظایف و تشکیلات وزارت علوم مصوب ۱۳۸۳",
    "law-article-36": "قانون اهداف، وظایف و تشکیلات وزارت علوم مصوب ۱۳۸۳",
    "law-article-37": "قانون اهداف، وظایف و تشکیلات وزارت علوم مصوب ۱۳۸۳",
    "law-article-38": "قانون اهداف، وظایف و تشکیلات وزارت علوم مصوب ۱۳۸۳",
    "law-article-39": "قانون اهداف، وظایف و تشکیلات وزارت علوم مصوب ۱۳۸۳",
    "law-article-40": "قانون اهداف، وظایف و تشکیلات وزارت علوم مصوب ۱۳۸۳",

    "law-article-41-subsection-1_1": "شاخص‌های ماده ۴۱ قانون برنامه پنجم توسعه",
    "law-article-41-subsection-1_17": "شاخص‌های ماده ۴۱ قانون برنامه پنجم توسعه",
    "law-article-41-subsection-3_7": "شاخص‌های ماده ۴۱ قانون برنامه پنجم توسعه",
    "law-article-41-subsection-5_9": "شاخص‌های ماده ۴۱ قانون برنامه پنجم توسعه",
    "law-article-41-subsection-6_17": "شاخص‌های ماده ۴۱ قانون برنامه پنجم توسعه",
    "law-article-41-subsection-1_25": "شاخص‌های ماده ۴۱ قانون برنامه پنجم توسعه",
    "law-article-41-subsection-3_18": "شاخص‌های ماده ۴۱ قانون برنامه پنجم توسعه",
    "law-article-41-subsection-4_28": "شاخص‌های ماده ۴۱ قانون برنامه پنجم توسعه",
    "law-article-41-subsection-6_1": "شاخص‌های ماده ۴۱ قانون برنامه پنجم توسعه",

    "law-article-42": "قانون تشکیل هیأت‌های امنای دانشگاه‌ها",
    "law-article-43": "قانون تشکیل هیأت‌های امنای دانشگاه‌ها",
    "law-article-44": "قانون تشکیل هیأت‌های امنای دانشگاه‌ها",
    "law-article-45": "قانون تشکیل هیأت‌های امنای دانشگاه‌ها",
    "law-article-46": "قانون تشکیل هیأت‌های امنای دانشگاه‌ها",
    "law-article-47": "قانون تشکیل هیأت‌های امنای دانشگاه‌ها",
    "law-article-48": "قانون تشکیل هیأت‌های امنای دانشگاه‌ها",
    "law-article-49": "قانون برنامه پنجم توسعه",
    "law-article-50": "قانون تشکیل هیأت‌های امنای دانشگاه‌ها",
    "law-article-51": "قانون تشکیل هیأت‌های امنای دانشگاه‌ها",
    "law-article-52": "قانون تشکیل هیأت‌های امنای دانشگاه‌ها",
    "law-article-53": "قانون اهداف، وظایف و تشکیلات وزارت علوم مصوب ۱۳۸۳",

    "law-article-54": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-55": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-56": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-57": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-58": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-59": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-60": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-61": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-62": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-63": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-64": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-65": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-66": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-67": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-68": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-69": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-70": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-71": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-72": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-73": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-74": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-75": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-76": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
    "law-article-77": "قانون تأسیس دانشگاه تهران مصوب ۱۳۱۳",
}


def to_str(val) -> str:
    if val is None:
        return ""
    if isinstance(val, list):
        return "|".join(str(v) for v in val)
    return str(val)


def normalize_persian(text: str) -> str:
    """نرمال‌سازی کاراکترهای عربی به فارسی برای بهبود embedding"""
    replacements = {
        'ي': 'ی',
        'ك': 'ک',
        'ة': 'ه',
        '\u200c': ' ',  # ZWNJ to space
        'ؤ': 'و',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def num_to_persian(n: str) -> str:
    mapping = {'0':'۰','1':'۱','2':'۲','3':'۳','4':'۴','5':'۵','6':'۶','7':'۷','8':'۸','9':'۹'}
    return ''.join(mapping.get(c, c) for c in str(n))


def prepare_document_v3(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    نسخه ۳: embedding از متن کوتاه (header+summary+keywords+اول متن)
    ولی ذخیره متن کامل در ChromaDB
    + نرمال‌سازی فارسی
    """
    payload = record.get("payload", {})
    text = normalize_persian(payload.get("text", ""))
    metadata = payload.get("metadata", {})
    source = payload.get("source", {})
    record_id = record.get("id", "")

    book_title = normalize_persian(to_str(metadata.get("book_title")))
    section_type = normalize_persian(to_str(metadata.get("section_type")))
    section_number = to_str(metadata.get("section_number"))
    section_title = normalize_persian(to_str(metadata.get("section_title")))
    semantic_summary = normalize_persian(to_str(metadata.get("semantic_summary")))
    approval_body = normalize_persian(to_str(metadata.get("approval_body")))
    major_div_type = normalize_persian(to_str(metadata.get("major_division_type")))
    major_div_title = normalize_persian(to_str(metadata.get("major_division_title")))

    keywords_raw = metadata.get("keywords", [])
    if isinstance(keywords_raw, str):
        keywords_list = [normalize_persian(k.strip()) for k in keywords_raw.replace('|', ',').split(',') if k.strip()]
    elif isinstance(keywords_raw, list):
        keywords_list = [normalize_persian(str(k)) for k in keywords_raw]
    else:
        keywords_list = []

    sec_num_persian = num_to_persian(section_number) if section_number.isdigit() else section_number

    # فقط برای رکوردهای کلیات.json از sub_law map استفاده کن
    is_kliyat = record.get("_is_kliyat", False)
    sub_law = KLIYAT_SUB_LAW_MAP.get(record_id, "") if is_kliyat else ""

    # === Header (مشترک بین embedding text و stored text) ===
    header = f"مجموعه: {book_title}"
    if sub_law:
        header += f"\nزیرقانون: {sub_law}"
    if section_type and section_number:
        article_line = f"{section_type} {section_number}"
        if sec_num_persian != section_number:
            article_line += f" ({section_type} {sec_num_persian})"
        if section_title:
            article_line += f" - {section_title}"
        header += f"\n{article_line}"

    location_parts = []
    if major_div_type:
        location_parts.append(major_div_type)
    if major_div_title:
        location_parts.append(major_div_title)
    if approval_body:
        location_parts.append(f"مصوب {approval_body}")
    location = " | ".join(location_parts) if location_parts else ""

    # === Full text (ذخیره در ChromaDB) ===
    full_parts = [header]
    if location:
        full_parts.append(f"بخش: {location}")
    full_parts.append("")
    full_parts.append(text)
    if semantic_summary:
        full_parts.append(f"\nخلاصه: {semantic_summary}")
    if keywords_list:
        full_parts.append(f"کلمات کلیدی: {' | '.join(keywords_list)}")
    full_text = "\n".join(full_parts).strip()

    # === Embedding text (header + اول متن + خلاصه + کلمات کلیدی) ===
    text_first = text[:400]
    embed_parts = [header]
    if location:
        embed_parts.append(f"بخش: {location}")
    embed_parts.append("")
    embed_parts.append(text_first)
    if semantic_summary:
        embed_parts.append(f"\nخلاصه: {semantic_summary}")
    if keywords_list:
        embed_parts.append(f"کلمات کلیدی: {' | '.join(keywords_list)}")
    embed_text = "\n".join(embed_parts).strip()

    # metadata
    chroma_metadata = {
        "id": to_str(record_id),
        "book_title": book_title,
        "book_type": to_str(metadata.get("book_type")),
        "sub_law": sub_law,
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
        "approval_body": approval_body,
        "created_at": datetime.now().isoformat()
    }

    for field in ["subsection_number", "parent_section", "approval_date"]:
        val = metadata.get(field)
        if val:
            chroma_metadata[field] = to_str(val)

    return {
        "text": full_text,
        "embed_text": embed_text,
        "metadata": chroma_metadata,
    }


async def rebuild_collection():
    """بازسازی کامل کالکشن azizashna نسخه ۳"""
    logger.info("=" * 70)
    logger.info("🔄 بازسازی کالکشن azizashna (نسخه ۳)")
    logger.info("=" * 70)

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
            # فقط فایل کلیات.json از sub_law map استفاده کند
            is_kliyat = (json_file == "کلیات.json")
            for r in records:
                r["_source_file"] = json_file
                r["_is_kliyat"] = is_kliyat
            all_records.extend(records)
            logger.info(f"  ✅ {json_file}: {len(records)} رکورد")

    logger.info(f"\n📊 مجموع: {len(all_records)} رکورد")

    documents = []        # متن کامل (ذخیره در ChromaDB)
    embed_texts = []       # متن خلاصه‌شده (برای embedding)
    metadatas = []
    for rec in all_records:
        doc = prepare_document_v3(rec)
        if doc["text"].strip():
            documents.append(doc["text"])
            embed_texts.append(doc["embed_text"])
            metadatas.append(doc["metadata"])

    source_stats = {}
    sub_law_stats = {}
    for m in metadatas:
        b = m.get("book_title", "?")
        source_stats[b] = source_stats.get(b, 0) + 1
        sl = m.get("sub_law", "")
        if sl:
            sub_law_stats[sl] = sub_law_stats.get(sl, 0) + 1

    logger.info("\n📋 آمار منابع:")
    for book, cnt in source_stats.items():
        logger.info(f"   {book}: {cnt}")

    if sub_law_stats:
        logger.info("\n📋 آمار زیرقوانین:")
        for sl, cnt in sub_law_stats.items():
            logger.info(f"   {sl}: {cnt}")

    # نمونه سند: وظایف شورای ستاد
    for doc, etxt, meta in zip(documents, embed_texts, metadatas):
        if meta.get('section_title') and 'ستاد' in meta.get('section_title', ''):
            logger.info(f"\n🔍 نمونه embed_text (وظایف شورای ستاد):")
            logger.info(etxt[:600])
            logger.info(f"\nDoc length: {len(doc)} / Embed text length: {len(etxt)}")
            break

    # ChromaDB
    try:
        from ultimate_rag_system import UltimateRAGSystem
        from services.persian_embedding_service import HeydariEmbeddingClient

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
                "hnsw:space": "cosine",
                "embedding_dimension": "1024",
                "embedding_model": "heydariAI/persian-embeddings",
                "created_at": datetime.now().isoformat()
            }
        )
        logger.info(f"✅ کالکشن جدید ایجاد شد")
    except Exception as e:
        logger.error(f"❌ خطا در ایجاد: {e}")
        return False

    # Embeddings با مدل heydariAI/persian-embeddings (1024 بعدی)
    logger.info("\n🧠 تولید Embeddings با مدل heydariAI (1024-dim)...")
    try:
        embed_svc = HeydariEmbeddingClient()
        logger.info(f"   مدل: {embed_svc.model_name} (dim={embed_svc.embedding_dimension})")
        BATCH = 50
        all_embeddings = []

        for i in range(0, len(embed_texts), BATCH):
            batch = embed_texts[i:i+BATCH]
            batch_num = i // BATCH + 1
            total_batches = (len(embed_texts) - 1) // BATCH + 1
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

    # Add to ChromaDB
    logger.info("\n📤 افزودن اسناد...")
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
            logger.info(f"  ✅ {end}/{len(documents)} سند")

        final_count = collection.count()
        logger.info(f"✅ مجموع {final_count} سند")
    except Exception as e:
        logger.error(f"❌ خطا: {e}")
        return False

    # Config
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
            "max_tokens": 4096,
            "top_p": 0.9
        },
        "metadata": {
            "sources": list(source_stats.keys()),
            "total_documents": final_count,
            "source_stats": source_stats,
            "sub_law_stats": sub_law_stats,
            "version": "3.1",
            "embedding_model": "heydariAI/persian-embeddings",
            "embedding_dim": 1024,
            "distance_metric": "cosine",
            "rebuild_reason": "heydariAI model + sub-law identification + cosine distance"
        }
    }

    config_file = project_root / "collections_config" / f"{COLLECTION_NAME}.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ Config ذخیره شد")

    logger.info("\n" + "=" * 70)
    logger.info("✅ بازسازی نسخه ۳ انجام شد!")
    logger.info("=" * 70)
    return True


if __name__ == "__main__":
    success = asyncio.run(rebuild_collection())
    sys.exit(0 if success else 1)
