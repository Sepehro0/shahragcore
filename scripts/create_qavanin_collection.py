# -*- coding: utf-8 -*-
"""
Script to create and populate the 'qavanin' collection
قانون بهبود مستمر محیط کسب و کار
"""

import sys
import os
import logging
import re
from pathlib import Path
from typing import List, Dict, Any
import uuid
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from docx import Document
import chromadb
from chromadb.config import Settings as ChromaSettings

# Import project modules
from config.settings import Settings
from services.persian_embedding_service import PersianEmbeddingService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_text_from_docx(docx_path: str) -> str:
    """استخراج متن از فایل Word"""
    try:
        doc = Document(docx_path)
        text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return text
    except Exception as e:
        logger.error(f"خطا در استخراج متن از {docx_path}: {e}")
        return ""


def parse_law_document(text: str) -> List[Dict[str, Any]]:
    """
    پارس کردن متن قانون و تقسیم به مواد و تبصره‌ها
    
    Returns:
        لیستی از دیکشنری‌ها شامل اطلاعات هر ماده/تبصره
    """
    chunks = []
    
    # الگوی شناسایی مواد
    article_pattern = r'ماده\s*(\d+|\d+[الف-ی]*)\s*[ـ\-]?\s*(.*?)(?=ماده\s*\d+|$)'
    
    # پیدا کردن تمام مواد
    articles = re.finditer(article_pattern, text, re.DOTALL)
    
    for match in articles:
        article_num = match.group(1).strip()
        article_text = match.group(2).strip()
        
        # بررسی اینکه آیا ماده اصلاحی یا الحاقی است
        is_amended = "اصلاحی" in article_text[:50] or "اصلاحي" in article_text[:50]
        is_added = "الحاقی" in article_text[:50] or "الحاقي" in article_text[:50]
        
        # استخراج تاریخ اصلاح یا الحاق
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', article_text[:100])
        modification_date = date_match.group(1) if date_match else None
        
        # تقسیم به تبصره‌ها
        notes_pattern = r'تبصره\s*(\d*)\s*[ـ\-]?\s*(.*?)(?=تبصره\s*\d+|ماده\s*\d+|$)'
        notes = list(re.finditer(notes_pattern, article_text, re.DOTALL))
        
        if notes:
            # ماده دارای تبصره است
            main_text = article_text[:notes[0].start()].strip()
            
            # اضافه کردن متن اصلی ماده
            if main_text:
                chunks.append({
                    'type': 'article',
                    'article_number': article_num,
                    'note_number': None,
                    'content': main_text,
                    'full_text': f"ماده {article_num}:\n{main_text}",
                    'is_amended': is_amended,
                    'is_added': is_added,
                    'modification_date': modification_date,
                    'has_notes': True
                })
            
            # اضافه کردن تبصره‌ها
            for note_match in notes:
                note_num = note_match.group(1).strip() if note_match.group(1) else "۱"
                note_text = note_match.group(2).strip()
                
                chunks.append({
                    'type': 'note',
                    'article_number': article_num,
                    'note_number': note_num,
                    'content': note_text,
                    'full_text': f"ماده {article_num} - تبصره {note_num}:\n{note_text}",
                    'is_amended': is_amended,
                    'is_added': is_added,
                    'modification_date': modification_date,
                    'has_notes': False
                })
        else:
            # ماده بدون تبصره
            chunks.append({
                'type': 'article',
                'article_number': article_num,
                'note_number': None,
                'content': article_text,
                'full_text': f"ماده {article_num}:\n{article_text}",
                'is_amended': is_amended,
                'is_added': is_added,
                'modification_date': modification_date,
                'has_notes': False
            })
    
    return chunks


def create_qavanin_collection():
    """ایجاد و پرکردن کالکشن qavanin"""
    
    logger.info("شروع فرآیند ایجاد کالکشن qavanin...")
    
    # 1. بارگذاری تنظیمات
    settings = Settings()
    
    # 2. مسیر فایل قانون
    docx_path = project_root / "archive" / "data_files" / "قانون بهبود مستمر محيط كسب و كار.docx"
    
    if not docx_path.exists():
        logger.error(f"فایل قانون یافت نشد: {docx_path}")
        return False
    
    # 3. استخراج متن
    logger.info(f"استخراج متن از {docx_path.name}...")
    law_text = extract_text_from_docx(str(docx_path))
    
    if not law_text:
        logger.error("متن قانون استخراج نشد")
        return False
    
    logger.info(f"طول متن استخراج شده: {len(law_text)} کاراکتر")
    
    # 4. پارس کردن قانون
    logger.info("پارس کردن قانون...")
    chunks = parse_law_document(law_text)
    logger.info(f"تعداد بخش‌های استخراج شده: {len(chunks)}")
    
    # 5. اتصال به ChromaDB
    logger.info("اتصال به ChromaDB...")
    chroma_settings = ChromaSettings(
        persist_directory=settings.database.chroma_db_path,
        anonymized_telemetry=False
    )
    
    chroma_client = chromadb.PersistentClient(
        path=settings.database.chroma_db_path,
        settings=chroma_settings
    )
    
    # 6. حذف کالکشن قدیمی (اگر وجود دارد)
    try:
        chroma_client.delete_collection("qavanin")
        logger.info("کالکشن قدیمی حذف شد")
    except:
        logger.info("کالکشن قبلی وجود نداشت")
    
    # 7. ایجاد کالکشن جدید
    logger.info("ایجاد کالکشن جدید...")
    collection = chroma_client.create_collection(
        name="qavanin",
        metadata={"hnsw:space": "cosine"}
    )
    
    # 8. آماده‌سازی داده‌ها برای indexing
    logger.info("آماده‌سازی داده‌ها...")
    documents = []
    metadatas = []
    ids = []
    
    for i, chunk in enumerate(chunks):
        # متن برای embedding
        embed_text = chunk['full_text']
        
        # metadata
        metadata = {
            'type': chunk['type'],
            'article_number': chunk['article_number'],
            'note_number': chunk['note_number'] if chunk['note_number'] else '',
            'is_amended': chunk['is_amended'],
            'is_added': chunk['is_added'],
            'modification_date': chunk['modification_date'] if chunk['modification_date'] else '',
            'has_notes': chunk['has_notes'],
            'content_length': len(chunk['content']),
            'law_name': 'قانون بهبود مستمر محیط کسب و کار',
            'law_date': '۱۶/۱۱/۱۳۹۰',
            'created_at': datetime.now().isoformat()
        }
        
        documents.append(embed_text)
        metadatas.append(metadata)
        ids.append(f"qavanin_{i}_{uuid.uuid4().hex[:8]}")
    
    # 9. ایجاد embeddings با استفاده از Persian Embedding Service
    logger.info("محاسبه embeddings...")
    embedding_service = PersianEmbeddingService()
    embeddings = embedding_service.generate_embeddings(documents)
    
    if not embeddings or len(embeddings) != len(documents):
        logger.error(f"خطا در ایجاد embeddings. تعداد: {len(embeddings)}/{len(documents)}")
        return False
    
    logger.info(f"✅ embeddings ایجاد شد: {len(embeddings)} عدد")
    
    # 10. اضافه کردن به collection
    logger.info("افزودن به collection...")
    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )
    
    # 11. تأیید
    count = collection.count()
    logger.info(f"✅ کالکشن qavanin با موفقیت ایجاد شد")
    logger.info(f"تعداد chunks: {count}")
    logger.info(f"تعداد مواد: {len([c for c in chunks if c['type'] == 'article'])}")
    logger.info(f"تعداد تبصره‌ها: {len([c for c in chunks if c['type'] == 'note'])}")
    
    return True


if __name__ == "__main__":
    try:
        success = create_qavanin_collection()
        if success:
            logger.info("=" * 60)
            logger.info("فرآیند ایجاد کالکشن با موفقیت تکمیل شد")
            logger.info("=" * 60)
            sys.exit(0)
        else:
            logger.error("فرآیند ایجاد کالکشن با خطا مواجه شد")
            sys.exit(1)
    except Exception as e:
        logger.error(f"خطای غیرمنتظره: {e}", exc_info=True)
        sys.exit(1)
