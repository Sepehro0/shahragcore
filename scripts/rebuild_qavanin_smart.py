# -*- coding: utf-8 -*-
"""
اسکریپت بازسازی کامل کالکشن qavanin با chunking هوشمند
نسخه ۳ - جداسازی تبصره‌ها + حذف intro + تقسیم معنایی
"""

import asyncio
import logging
import sys
import chromadb
from chromadb.config import Settings as ChromaSettings
import hashlib
import re
from datetime import datetime

sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

# استفاده از heydaryAI/persian-embeddings (1024 dim) - بسیار بهتر از distiluse برای فارسی
EMBEDDING_MODEL = "heydariAI/persian-embeddings"
EMBEDDING_DIM = 1024

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clean_color_tags(text: str) -> str:
    """حذف تگ‌های رنگی از متن"""
    text = re.sub(r'\s*\[BLACK\]', '', text)
    text = re.sub(r'\s*\[GREEN\]', ' [الحاقی/اصلاحی]', text)
    text = re.sub(r'\s*\[RED\]', ' [منسوخه]', text)
    text = re.sub(r'\s*\[ORANGE\]', ' [تفسیر]', text)
    text = re.sub(r'\[مشکی/BLACK\]', 'معتبر', text)
    text = re.sub(r'\[سبز/GREEN\]', 'اصلاحی/الحاقی', text)
    text = re.sub(r'\[قرمز/RED\]', 'منسوخه', text)
    text = re.sub(r'\[نارنجی/ORANGE\]', 'تفسیر', text)
    return text


def extract_tabasere_chunks(article_text: str, article_num: int, base_meta: dict) -> list:
    """
    استخراج تبصره‌ها از متن ماده و ساخت chunk جداگانه برای هر کدام.
    هر تبصره به عنوان یک chunk مستقل ایندکس می‌شود تا retrieval بهتری داشته باشیم.
    """
    tabasere_chunks = []

    # الگوی تبصره: "تبصره - " یا "تبصره X - "
    # باید lines بین تبصره‌ها را جدا کنیم
    tab_pattern = r'(تبصره\s*(\d*)\s*[-–]\s*)'
    tab_matches = list(re.finditer(tab_pattern, article_text))

    if not tab_matches:
        return tabasere_chunks

    for k, tab_match in enumerate(tab_matches):
        tab_start = tab_match.start()
        tab_end = tab_matches[k + 1].start() if k + 1 < len(tab_matches) else len(article_text)
        tab_text = article_text[tab_start:tab_end].strip()
        tab_text = re.sub(r'\n={40,}.*', '', tab_text).strip()

        tab_num_str = tab_match.group(2).strip()
        tab_num = int(tab_num_str) if tab_num_str else (1 if len(tab_matches) == 1 else k + 1)

        clean_tab = clean_color_tags(tab_text)

        # ساخت متن غنی‌تر با ارجاع به ماده
        enriched_text = f"ماده {article_num} - تبصره {tab_num}\n{clean_tab}"

        meta = base_meta.copy()
        meta['type'] = 'tabasere'
        meta['tabasere_num'] = tab_num
        meta['parent_article'] = article_num

        # استخراج topic هوشمند از متن تبصره
        topic_keywords = []
        if 'محرمانه' in clean_tab or 'مستثنی' in clean_tab:
            topic_keywords.append('استثنای محرمانه')
        if 'بیمه' in clean_tab:
            topic_keywords.append('بیمه')
        if 'سراسری' in clean_tab or 'تشکل' in clean_tab:
            topic_keywords.append('تشکل')
        if 'اضطرار' in clean_tab or 'اضطراری' in clean_tab:
            topic_keywords.append('اضطراری')
        if 'نظر مشورتی' in clean_tab:
            topic_keywords.append('نظر مشورتی')
        if 'مصوبات' in clean_tab:
            topic_keywords.append('مصوبات')
        if meta.get('semantic_topic'):
            topic_keywords.append(meta['semantic_topic'])

        meta['semantic_topic'] = ' - '.join(topic_keywords) if topic_keywords else f'تبصره {tab_num} ماده {article_num}'

        tabasere_chunks.append({
            'text': enriched_text,
            'metadata': meta
        })

    return tabasere_chunks


def split_article30_semantic(article_text: str) -> list:
    """تقسیم معنایی ماده ۳۰ الحاقی"""
    chunks = []
    base = {
        'source': 'قانون بهبود مستمر محیط کسب‌وکار',
        'article_num': 30,
        'status': 'الحاقی',
        'chapter': 'فصل دهم',
        'chapter_title': 'مواد الحاقی',
    }

    parts = [
        {
            'topic': 'الزام اصلاح پایگاه اطلاعات',
            'text': 'ماده ۳۰ (الحاقی ۲۴/۱۲/۱۴۰۰) - الزام اصلاح پایگاه:\n'
                    'وزارت امور اقتصادی و دارایی مکلف است با همکاری معاونت ذی ربط رئیس جمهور '
                    'حداکثر شش ماه پس از لازم الاجراء شدن این قانون، با استفاده از ظرفیت‌های موجود '
                    'نسبت به اصلاح و ارتقاء «پایگاه اطلاعات قوانین و مقررات مرتبط با محیط کسب و کار» اقدام نماید.',
        },
        {
            'topic': 'انتشار پیش‌نویس بخشنامه یک هفته قبل از صدور',
            'text': 'ماده ۳۰ (الحاقی ۲۴/۱۲/۱۴۰۰) - الزام انتشار پیش‌نویس بخشنامه:\n'
                    'دستگاههای اجرائی موضوع ماده (۵) قانون مدیریت خدمات کشوری مصوب ۱۳۸۶/۷/۸ '
                    'مکلفند پیش‌نویس آیین‌نامه، دستورالعمل یا بخشنامه خود را یک هفته قبل از صدور، '
                    'در تارنمای (سایت) خود به اطلاع عموم و فعالان اقتصادی برسانند تا فرصت لازم '
                    'برای اعلام نظرات عموم یا فعالان اقتصادی و تشکل‌ها وجود داشته باشد.',
        },
        {
            'topic': 'الزام ثبت مقررات در پایگاه',
            'text': 'ماده ۳۰ (الحاقی ۲۴/۱۲/۱۴۰۰) - الزام ثبت مقررات در پایگاه:\n'
                    'دستگاههای اجرائی مکلفند هرگونه آیین‌نامه، دستورالعمل یا بخشنامه یا مقرره خود را '
                    'بلافاصله در پایگاه اطلاعات قوانین و مقررات مرتبط با محیط کسب و کار ثبت نمایند '
                    'و به اطلاع عموم برسانند.',
        },
        {
            'topic': 'نافذ نبودن مقررات ثبت‌نشده',
            'text': 'ماده ۳۰ (الحاقی ۲۴/۱۲/۱۴۰۰) - حکم مقررات ثبت‌نشده:\n'
                    'یک سال پس از لازم الاجراء شدن این قانون، مقررات تنها در صورت ثبت '
                    'در پایگاه موضوع این ماده نافذ می‌باشد. '
                    'به عبارت دیگر، مقررات ثبت‌نشده نافذ نیستند و فاقد اعتبار قانونی هستند.',
        },
    ]

    for p in parts:
        meta = base.copy()
        meta['type'] = 'article_semantic'
        meta['semantic_topic'] = p['topic']
        chunks.append({'text': p['text'], 'metadata': meta})

    return chunks


def parse_ayin_nameh(content: str) -> list:
    """Parse آیین‌نامه لزوم ثبت و اطلاع‌رسانی مقررات"""
    chunks = []

    ayin_start = content.find('آیین‌نامه لزوم ثبت و اطلاع‌رسانی')
    if ayin_start < 0:
        logger.warning("⚠️ آیین‌نامه یافت نشد!")
        return chunks

    ayin_content = content[ayin_start:]
    logger.info("📜 Processing آیین‌نامه لزوم ثبت و اطلاع‌رسانی مقررات...")

    article_pattern = r'(ماده\s+(\d+)\s+\(آیین‌نامه\)\s+\[([A-Z]+)\])'
    article_matches = list(re.finditer(article_pattern, ayin_content))

    logger.info(f"  Found {len(article_matches)} articles in آیین‌نامه")

    for j, match in enumerate(article_matches):
        art_start = match.start()
        art_end = article_matches[j + 1].start() if j + 1 < len(article_matches) else len(ayin_content)
        article_text = ayin_content[art_start:art_end].strip()
        article_text = re.sub(r'={40,}.*', '', article_text).strip()

        article_num = int(match.group(2))
        article_color = match.group(3)

        clean_text = clean_color_tags(article_text)
        status_map = {'BLACK': 'معتبر', 'GREEN': 'اصلاحی/الحاقی', 'RED': 'منسوخه', 'ORANGE': 'تفسیر'}
        status = status_map.get(article_color, 'معتبر')

        base_meta = {
            'type': 'ayin_nameh_article',
            'source': 'آیین‌نامه لزوم ثبت و اطلاع‌رسانی مقررات در پایگاه ـ مصوب ۳۰/۱/۱۴۰۲',
            'article_num': article_num,
            'status': status,
            'chapter': 'آیین‌نامه',
            'chapter_title': 'لزوم ثبت و اطلاع‌رسانی مقررات',
        }

        # ماده کامل
        chunks.append({'text': clean_text, 'metadata': base_meta.copy()})

        # تبصره‌های ماده ۷
        if article_num == 7:
            t1_match = re.search(r'(تبصره 1 \(ماده 7 آیین‌نامه\)\s*-\s*.*?)(?=تبصره 2|$)', clean_text, re.DOTALL)
            if t1_match:
                meta_t1 = base_meta.copy()
                meta_t1['type'] = 'ayin_nameh_tabasere'
                meta_t1['tabasere_num'] = 1
                meta_t1['semantic_topic'] = 'مقررات داخلی از تاریخ ابلاغ لازم‌الاجرا'
                chunks.append({'text': t1_match.group(1).strip(), 'metadata': meta_t1})

            t2_match = re.search(r'(تبصره 2 \(ماده 7 آیین‌نامه\)\s*-\s*.*?)$', clean_text, re.DOTALL)
            if t2_match:
                meta_t2 = base_meta.copy()
                meta_t2['type'] = 'ayin_nameh_tabasere'
                meta_t2['tabasere_num'] = 2
                meta_t2['semantic_topic'] = 'ممنوعیت عطف به ماسبق و تسری به گذشته مقررات ناقض حقوق شهروندان'
                chunks.append({'text': t2_match.group(1).strip(), 'metadata': meta_t2})

    return chunks


async def rebuild_qavanin_smart():
    """ساخت مجدد کالکشن qavanin v3"""

    logger.info("=" * 80)
    logger.info("🚀 Smart Rebuilding Qavanin Collection (v3)")
    logger.info("=" * 80)

    db_path = "/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    data_file = "/home/user01/qwen-api/enhanced_rag_system_dev/archive/data_files/qavanin_complete.txt"
    collection_name = "qavanin"

    logger.info("🔧 Initializing ChromaDB...")
    client = chromadb.PersistentClient(
        path=db_path,
        settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True)
    )

    logger.info(f"🗑️  Deleting existing collection: {collection_name}")
    try:
        client.delete_collection(collection_name)
        logger.info("✅ Collection deleted")
    except Exception as e:
        logger.info(f"ℹ️  {e}")

    logger.info(f"📖 Reading file: {data_file}")
    with open(data_file, 'r', encoding='utf-8') as f:
        content = f.read()

    chunks = []

    # ============================================================
    # ❌ حذف intro chunk - بی‌فایده و همیشه اولین نتیجه بود
    # ============================================================

    # ============================================================
    # بخش ۱: Parse قانون اصلی
    # ============================================================
    chapter_pattern = r'={80,}\n(فصل\s+(اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم)):\s*(.+?)\n={80,}'
    chapter_matches = list(re.finditer(chapter_pattern, content))

    persian_to_num = {
        'اول': 1, 'دوم': 2, 'سوم': 3, 'چهارم': 4, 'پنجم': 5,
        'ششم': 6, 'هفتم': 7, 'هشتم': 8, 'نهم': 9, 'دهم': 10
    }

    for i, chapter_match in enumerate(chapter_matches):
        chapter_start = chapter_match.end()
        chapter_end = chapter_matches[i + 1].start() if i + 1 < len(chapter_matches) else content.find('بخش پایانی', chapter_start)
        if chapter_end < 0:
            chapter_end = len(content)
        chapter_content = content[chapter_start:chapter_end]

        chapter_full = chapter_match.group(1)
        chapter_num_text = chapter_match.group(2)
        chapter_title = chapter_match.group(3).strip()
        chapter_num = persian_to_num.get(chapter_num_text, i + 1)

        logger.info(f"📑 Processing: {chapter_full}: {chapter_title}")

        article_pattern = r'(ماده\s+(\d+)(?:\s+\(([^)]+)\))?\s+\[([A-Z]+)\])'
        article_matches_list = list(re.finditer(article_pattern, chapter_content))

        if not article_matches_list:
            continue

        for j, article_match in enumerate(article_matches_list):
            art_start = article_match.start()
            art_end = article_matches_list[j + 1].start() if j + 1 < len(article_matches_list) else len(chapter_content)
            article_text = chapter_content[art_start:art_end].strip()
            article_text = re.sub(r'\n={40,}.*', '', article_text).strip()

            article_num = int(article_match.group(2))
            article_status_text = article_match.group(3) or ""
            article_color = article_match.group(4)

            status_map = {'BLACK': 'معتبر', 'GREEN': 'الحاقی', 'RED': 'منسوخه', 'ORANGE': 'تفسیر'}
            status = status_map.get(article_color, 'معتبر')

            tabasere_matches = re.findall(r'تبصره\s*\d*\s*[-–]', article_text)
            clean_text = clean_color_tags(article_text)

            base_meta = {
                'source': 'قانون بهبود مستمر محیط کسب‌وکار',
                'chapter': chapter_full,
                'chapter_num': chapter_num,
                'chapter_title': chapter_title,
                'article_num': article_num,
                'article_status': article_status_text,
                'status': status,
                'has_tabasere': len(tabasere_matches) > 0,
                'tabasere_count': len(tabasere_matches),
            }

            # ماده ۱ - تعاریف
            if article_num == 1 and chapter_num == 1:
                def_pattern = r'(الف|ب|پ|ت|ث|ج|چ|ح|خ)\s*[-–]\s*([^:]+):\s*([^\n]+(?:\n(?![الف-ی]\s*[-–])[^\n]+)*)'
                definitions = re.findall(def_pattern, article_text)
                logger.info(f"  ✓ Found {len(definitions)} definitions in ماده 1")

                for def_letter, def_term, def_text in definitions:
                    full_def = f"{def_letter} - {def_term}: {def_text}".strip()
                    meta_def = base_meta.copy()
                    meta_def['type'] = 'definition'
                    meta_def['definition_letter'] = def_letter
                    meta_def['definition_term'] = def_term.strip()
                    chunks.append({
                        'text': f"ماده ۱ (تعاریف) - قانون بهبود مستمر محیط کسب‌وکار\n\n{full_def}",
                        'metadata': meta_def
                    })

                # ماده کامل
                meta_full = base_meta.copy()
                meta_full['type'] = 'article_full'
                meta_full['has_definitions'] = True
                chunks.append({'text': clean_text, 'metadata': meta_full})

            # ماده ۳۰ الحاقی: تقسیم معنایی
            elif article_num == 30:
                logger.info("  ✓ Semantic splitting ماده ۳۰")
                chunks.extend(split_article30_semantic(article_text))
                meta_full = base_meta.copy()
                meta_full['type'] = 'article_full'
                chunks.append({'text': clean_text, 'metadata': meta_full})

            else:
                # ماده عادی - ذخیره ماده کامل
                meta_art = base_meta.copy()
                meta_art['type'] = 'article'
                chunks.append({'text': clean_text, 'metadata': meta_art})

                # ✨ NEW: تبصره‌ها به صورت جداگانه
                if len(tabasere_matches) > 0:
                    tab_chunks = extract_tabasere_chunks(article_text, article_num, base_meta)
                    if tab_chunks:
                        logger.info(f"  ✓ Extracted {len(tab_chunks)} tabasere from ماده {article_num}")
                        chunks.extend(tab_chunks)

    # ============================================================
    # بخش ۲: Parse آیین‌نامه
    # ============================================================
    ayin_chunks = parse_ayin_nameh(content)
    chunks.extend(ayin_chunks)
    logger.info(f"📜 Added {len(ayin_chunks)} chunks from آیین‌نامه")

    # ============================================================
    # آمار
    # ============================================================
    type_counts = {}
    for c in chunks:
        t = c['metadata'].get('type', 'unknown')
        type_counts[t] = type_counts.get(t, 0) + 1

    logger.info(f"\n📊 Total chunks: {len(chunks)}")
    for t, count in sorted(type_counts.items()):
        logger.info(f"   {t}: {count}")

    # ============================================================
    # ساخت کالکشن
    # ============================================================
    logger.info(f"\n🏗️  Creating collection: {collection_name}")
    collection = client.create_collection(
        name=collection_name,
        metadata={
            "hnsw:space": "cosine",
            "description": "قانون بهبود مستمر محیط کسب‌وکار + آیین‌نامه ۱۴۰۲ - chunking v3 with separate tabasere",
            "created_at": datetime.now().isoformat(),
            "source_file": "qavanin_complete.txt",
            "total_chunks": len(chunks),
            "smart_chunking": True,
            "version": "3"
        }
    )

    logger.info(f"🔢 Loading embedding model: {EMBEDDING_MODEL} ({EMBEDDING_DIM}d)...")
    from sentence_transformers import SentenceTransformer
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    logger.info("✅ Embedding model loaded")

    logger.info("📥 Adding chunks to collection...")
    batch_size = 20
    total_added = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c['text'] for c in batch]
        metadatas = [c['metadata'] for c in batch]

        embeddings = [embedding_model.encode(text).tolist() for text in texts]

        ids = [
            f"{collection_name}_{i + j}_{hashlib.md5(text.encode()).hexdigest()[:8]}"
            for j, text in enumerate(texts)
        ]

        collection.add(embeddings=embeddings, documents=texts, metadatas=metadatas, ids=ids)
        total_added += len(batch)
        logger.info(f"  ✓ Added {total_added}/{len(chunks)} chunks")

    final_count = collection.count()
    logger.info(f"\n✅ Collection created with {final_count} documents")

    # ============================================================
    # تست‌ها
    # ============================================================
    test_queries = [
        "تعریف محیط کسب و کار چیست؟",
        "آیا لازم‌الاجرا شدن مقررات منوط به ثبت در پایگاه است؟",
        "مقررات ثبت‌نشده چه حکمی دارند؟",
        "آیا موارد محرمانه از شمول تکلیف اطلاع‌رسانی ماده ۲۴ خارج می‌شوند؟",
        "در صورت نیاز به مهلتی بیش از ۱۵ روز برای اجرای مقرره، چه حکمی جاری است؟",
        "آیا دستگاه‌ها می‌توانند مقررات موجد تکلیف را پیش از انتشار در پایگاه لازم‌الاجرا کنند؟",
        "ثبت مقررات ناقض حقوق شهروندان به گذشته امکان‌پذیر است؟",
    ]

    logger.info("\n🔍 Running test queries...")
    for query in test_queries:
        q_emb = embedding_model.encode(query).tolist()
        results = collection.query(query_embeddings=[q_emb], n_results=5, include=['documents', 'metadatas', 'distances'])

        logger.info(f"\n  Q: {query}")
        for k, (doc, meta, dist) in enumerate(zip(results['documents'][0], results['metadatas'][0], results['distances'][0])):
            tp = meta.get('type', '')
            art = meta.get('article_num', '?')
            topic = meta.get('semantic_topic', '')
            tab = meta.get('tabasere_num', '')
            tab_str = f" tab={tab}" if tab else ""
            logger.info(f"    {k+1}. dist={dist:.4f} | art={art}{tab_str} | type={tp} | {topic}")
            logger.info(f"       {doc[:120]}...")

    logger.info("\n" + "=" * 80)
    logger.info("✅ SMART REBUILD v3 COMPLETED SUCCESSFULLY")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(rebuild_qavanin_smart())
