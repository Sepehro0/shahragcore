# -*- coding: utf-8 -*-
"""
Process Budget Financial Files (masaref2.xlsx and manabe.xlsx)
پردازش فایل‌های بودجه مالی و ایجاد Collection
"""

import sys
import asyncio
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any
import logging

# Add the current directory to Python path
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from core.refactored_rag_system import RefactoredRAGSystem
from config.budget_financial_prompt import (
    BUDGET_FINANCIAL_SYSTEM_PROMPT,
    normalize_year,
    format_number
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Collection name
COLLECTION_NAME = "budget_financial"

# File paths
MASAREF_FILE = "/home/user01/qwen-api/enhanced_rag_system_dev/archive/data_files/masaref2.xlsx"
MANABE_FILE = "/home/user01/qwen-api/enhanced_rag_system_dev/archive/data_files/manabe.xlsx"


def clean_value(value) -> str:
    """پاکسازی مقدار"""
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip()


def format_currency(value) -> str:
    """فرمت کردن مقادیر ارزی"""
    try:
        if pd.isna(value) or value is None or value == "":
            return "0"
        if isinstance(value, str):
            value = float(value.replace(',', ''))
        return f"{int(value):,}"
    except:
        return "0"


def process_masaref_row(row: pd.Series, row_index: int) -> Dict[str, Any]:
    """
    پردازش یک ردیف از فایل مصارف
    
    Returns:
        دیکشنری حاوی text، metadata
    """
    # استخراج اطلاعات
    main_org = clean_value(row.get('عنوان دستگاه اصلي', ''))
    exec_org = clean_value(row.get('عنوان دستگاه اجرايي ', ''))
    exec_code = clean_value(row.get('کد دستگاه اجرايي ', ''))
    year = clean_value(row.get('سال ', ''))
    
    # اعتبارات هزینه‌ای
    expense_general = row.get('براورد اعتبارات هزینه ای - عمومی', 0)
    expense_misc = row.get('برآورد اعتبارات هزینه ای - متفرقه', 0)
    expense_specific = row.get('براورد اعتبارات هزینه ای - اختصاصی', 0)
    expense_total = row.get('جمع براورد اعتبارات هزینه ای', 0)
    expense_subsidy = row.get('براورد اعتبارات هزینه ای - یارانه ها', 0)
    
    # تملک دارایی‌های سرمایه‌ای
    capital_general = row.get(' براورد تملك دارايي هاي سرمايه اي - عمومی', 0)
    capital_misc = row.get(' براورد تملك دارايي هاي سرمايه اي - متفرقه', 0)
    capital_specific = row.get(' براورد تملك دارايي هاي سرمايه اي - اختصاصی', 0)
    capital_total = row.get('جمع برآورد تملك دارايي هاي سرمايه اي', 0)
    capital_subsidy = row.get('براورد تملک دارایی های سرمایه ای - یارانه ها', 0)
    
    # جمع کل
    grand_total = row.get('جمع كل ', 0)
    
    # ساخت متن توصیفی
    text_parts = [
        f"دستگاه اصلی: {main_org}",
        f"دستگاه اجرایی: {exec_org}",
        f"کد دستگاه: {exec_code}",
        f"سال: {year}",
        "",
        "## اعتبارات هزینه‌ای (جاری):",
        f"- اعتبارات عمومی: {format_currency(expense_general)} میلیون ریال",
        f"- اعتبارات متفرقه: {format_currency(expense_misc)} میلیون ریال",
        f"- اعتبارات اختصاصی: {format_currency(expense_specific)} میلیون ریال",
        f"- جمع اعتبارات هزینه‌ای: {format_currency(expense_total)} میلیون ریال",
    ]
    
    # یارانه‌ها (اگر موجود باشد)
    if not pd.isna(expense_subsidy) and expense_subsidy != 0:
        text_parts.append(f"- یارانه‌های هزینه‌ای: {format_currency(expense_subsidy)} میلیون ریال")
    
    text_parts.extend([
        "",
        "## تملک دارایی‌های سرمایه‌ای (عمرانی):",
        f"- تملک عمومی: {format_currency(capital_general)} میلیون ریال",
        f"- تملک متفرقه: {format_currency(capital_misc)} میلیون ریال",
        f"- تملک اختصاصی: {format_currency(capital_specific)} میلیون ریال",
        f"- جمع تملک دارایی‌های سرمایه‌ای: {format_currency(capital_total)} میلیون ریال",
    ])
    
    # یارانه‌های سرمایه‌ای (اگر موجود باشد)
    if not pd.isna(capital_subsidy) and capital_subsidy != 0:
        text_parts.append(f"- یارانه‌های سرمایه‌ای: {format_currency(capital_subsidy)} میلیون ریال")
    
    text_parts.extend([
        "",
        f"## جمع کل مصارف: {format_currency(grand_total)} میلیون ریال"
    ])
    
    text = "\n".join(text_parts)
    
    # متادیتا
    metadata = {
        "source_file": "masaref2.xlsx",
        "table_type": "expenses",  # مصارف/هزینه‌ها
        "row_index": row_index,
        "main_organization": main_org,
        "executive_organization": exec_org,
        "executive_code": exec_code,
        "year": year,
        "organization_level": "executive" if exec_org != main_org else "main",
        
        # اعتبارات هزینه‌ای
        "expense_general": float(expense_general) if not pd.isna(expense_general) else 0.0,
        "expense_misc": float(expense_misc) if not pd.isna(expense_misc) else 0.0,
        "expense_specific": float(expense_specific) if not pd.isna(expense_specific) else 0.0,
        "expense_total": float(expense_total) if not pd.isna(expense_total) else 0.0,
        "expense_subsidy": float(expense_subsidy) if not pd.isna(expense_subsidy) else 0.0,
        
        # تملک دارایی‌های سرمایه‌ای
        "capital_general": float(capital_general) if not pd.isna(capital_general) else 0.0,
        "capital_misc": float(capital_misc) if not pd.isna(capital_misc) else 0.0,
        "capital_specific": float(capital_specific) if not pd.isna(capital_specific) else 0.0,
        "capital_total": float(capital_total) if not pd.isna(capital_total) else 0.0,
        "capital_subsidy": float(capital_subsidy) if not pd.isna(capital_subsidy) else 0.0,
        
        # جمع کل
        "grand_total": float(grand_total) if not pd.isna(grand_total) else 0.0,
        
        # برای جستجو
        "budget_type": "current_and_capital",  # هم جاری هم عمرانی
        "has_subsidy": not pd.isna(expense_subsidy) or not pd.isna(capital_subsidy)
    }
    
    return {
        "text": text,
        "metadata": metadata
    }


def process_manabe_row(row: pd.Series, row_index: int) -> Dict[str, Any]:
    """
    پردازش یک ردیف از فایل منابع/درآمدها
    
    Returns:
        دیکشنری حاوی text، metadata
    """
    # استخراج اطلاعات
    section_title = clean_value(row.get('عنوان قسمت ', ''))
    chapter_code = clean_value(row.get('کد بخش ', ''))
    chapter_title = clean_value(row.get('عنوان بخش', ''))
    clause_code = clean_value(row.get('کد بند', ''))
    clause_title = clean_value(row.get('عنوان بند', ''))
    item_code = clean_value(row.get('کد جزء ', ''))
    item_title = clean_value(row.get('عنوان جزء', ''))
    org_code = clean_value(row.get('کد دستگاه ', ''))
    exec_org = clean_value(row.get('عنوان دستگاه اجرایی', ''))
    main_org = clean_value(row.get('عنوان دستگاه اصلی', ''))
    year = clean_value(row.get('سال', ''))
    
    # درآمد عمومی
    income_general_national = row.get(' در آمد عمومي ملي', 0)
    income_general_regional = row.get(' در آمد عمومي استاني', 0)
    income_general_total = row.get(' جمع در آمد عمومي', 0)
    
    # درآمد اختصاصی
    income_specific_national = row.get(' در آمد اختصاصي ملي', 0)
    income_specific_regional = row.get(' در آمد اختصاصي استاني', 0)
    income_specific_total = row.get(' جمع در آمد اختصاصي', 0)
    
    # جمع کل
    total_national = row.get('جمع کل ملي', 0)
    total_regional = row.get(' جمع کل استاني', 0)
    grand_total = row.get('جمع کل ', 0)
    
    # ساخت متن توصیفی
    text_parts = [
        f"قسمت: {section_title}",
        f"بخش: {chapter_title} (کد: {chapter_code})",
        f"بند: {clause_title} (کد: {clause_code})",
        f"جزء: {item_title} (کد: {item_code})",
        f"دستگاه اصلی: {main_org}",
        f"دستگاه اجرایی: {exec_org}",
        f"کد دستگاه: {org_code}",
        f"سال: {year}",
        "",
        "## درآمد عمومی:",
        f"- درآمد عمومی ملی: {format_currency(income_general_national)} میلیون ریال",
        f"- درآمد عمومی استانی: {format_currency(income_general_regional)} میلیون ریال",
        f"- جمع درآمد عمومی: {format_currency(income_general_total)} میلیون ریال",
        "",
        "## درآمد اختصاصی:",
        f"- درآمد اختصاصی ملی: {format_currency(income_specific_national)} میلیون ریال",
        f"- درآمد اختصاصی استانی: {format_currency(income_specific_regional)} میلیون ریال",
        f"- جمع درآمد اختصاصی: {format_currency(income_specific_total)} میلیون ریال",
        "",
        "## جمع کل:",
        f"- جمع کل ملی: {format_currency(total_national)} میلیون ریال",
        f"- جمع کل استانی: {format_currency(total_regional)} میلیون ریال",
        f"- جمع کل درآمد: {format_currency(grand_total)} میلیون ریال"
    ]
    
    text = "\n".join(text_parts)
    
    # متادیتا
    metadata = {
        "source_file": "manabe.xlsx",
        "table_type": "income",  # درآمدها/منابع
        "row_index": row_index,
        "section_title": section_title,
        "chapter_code": chapter_code,
        "chapter_title": chapter_title,
        "clause_code": clause_code,
        "clause_title": clause_title,
        "item_code": item_code,
        "item_title": item_title,
        "main_organization": main_org,
        "executive_organization": exec_org,
        "organization_code": org_code,
        "year": year,
        "organization_level": "executive" if exec_org != main_org else "main",
        
        # درآمد عمومی
        "income_general_national": float(income_general_national) if not pd.isna(income_general_national) else 0.0,
        "income_general_regional": float(income_general_regional) if not pd.isna(income_general_regional) else 0.0,
        "income_general_total": float(income_general_total) if not pd.isna(income_general_total) else 0.0,
        
        # درآمد اختصاصی
        "income_specific_national": float(income_specific_national) if not pd.isna(income_specific_national) else 0.0,
        "income_specific_regional": float(income_specific_regional) if not pd.isna(income_specific_regional) else 0.0,
        "income_specific_total": float(income_specific_total) if not pd.isna(income_specific_total) else 0.0,
        
        # جمع کل
        "total_national": float(total_national) if not pd.isna(total_national) else 0.0,
        "total_regional": float(total_regional) if not pd.isna(total_regional) else 0.0,
        "grand_total": float(grand_total) if not pd.isna(grand_total) else 0.0,
        
        # برای جستجو
        "is_capital_transfer": "واگذاری" in section_title and "سرمایه" in section_title
    }
    
    return {
        "text": text,
        "metadata": metadata
    }


async def process_and_upload():
    """پردازش و آپلود فایل‌های بودجه"""
    
    logger.info("🚀 Starting budget files processing...")
    
    # Initialize RAG system
    rag = RefactoredRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    )
    
    # Check if collection exists
    collections = await rag.get_collections()
    if COLLECTION_NAME in collections:
        logger.warning(f"⚠️ Collection '{COLLECTION_NAME}' already exists. Deleting...")
        try:
            rag.chroma_client.delete_collection(name=COLLECTION_NAME)
            logger.info(f"✅ Deleted existing collection")
        except Exception as e:
            logger.error(f"❌ Error deleting collection: {e}")
    
    # Process masaref2.xlsx
    logger.info(f"📊 Processing {MASAREF_FILE}...")
    try:
        df_masaref = pd.read_excel(MASAREF_FILE)
        logger.info(f"   - Loaded {len(df_masaref)} rows from masaref2.xlsx")
        
        masaref_documents = []
        for idx, row in df_masaref.iterrows():
            try:
                doc = process_masaref_row(row, idx)
                masaref_documents.append(doc)
            except Exception as e:
                logger.error(f"   - Error processing row {idx}: {e}")
        
        logger.info(f"   - Processed {len(masaref_documents)} documents from masaref2")
        
    except Exception as e:
        logger.error(f"❌ Error loading masaref2.xlsx: {e}")
        return
    
    # Process manabe.xlsx
    logger.info(f"📊 Processing {MANABE_FILE}...")
    try:
        df_manabe = pd.read_excel(MANABE_FILE)
        logger.info(f"   - Loaded {len(df_manabe)} rows from manabe.xlsx")
        
        manabe_documents = []
        for idx, row in df_manabe.iterrows():
            try:
                doc = process_manabe_row(row, idx)
                manabe_documents.append(doc)
            except Exception as e:
                logger.error(f"   - Error processing row {idx}: {e}")
        
        logger.info(f"   - Processed {len(manabe_documents)} documents from manabe")
        
    except Exception as e:
        logger.error(f"❌ Error loading manabe.xlsx: {e}")
        return
    
    # Combine all documents
    all_documents = masaref_documents + manabe_documents
    logger.info(f"📦 Total documents to upload: {len(all_documents)}")
    
    # Upload to ChromaDB
    logger.info(f"⬆️ Uploading to collection '{COLLECTION_NAME}'...")
    
    try:
        # Get or create collection
        collection = rag.chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Budget Financial Data - Masaref and Manabe"}
        )
        
        # Prepare data for ChromaDB
        texts = [doc["text"] for doc in all_documents]
        metadatas = [doc["metadata"] for doc in all_documents]
        ids = [f"{doc['metadata']['source_file']}_{doc['metadata']['row_index']}" for doc in all_documents]
        
        # Upload documents to ChromaDB (ChromaDB will generate embeddings automatically)
        logger.info(f"   - Uploading {len(texts)} documents to ChromaDB...")
        logger.info(f"   - ChromaDB will generate embeddings automatically using default embedding function")
        
        # Upload in batches (500 per batch)
        batch_size = 500
        total_batches = (len(texts) + batch_size - 1) // batch_size
        
        for i in range(0, len(texts), batch_size):
            batch_num = i // batch_size + 1
            batch_texts = texts[i:i+batch_size]
            batch_metadatas = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            logger.info(f"   - Uploading batch {batch_num}/{total_batches} ({len(batch_texts)} documents)...")
            
            # Add to collection (ChromaDB will handle embeddings)
            collection.add(
                ids=batch_ids,
                documents=batch_texts,
                metadatas=batch_metadatas
                # No embeddings parameter - ChromaDB will use default embedding function
            )
            
            logger.info(f"   - Uploaded batch {batch_num}/{total_batches}")
        
        logger.info(f"✅ Successfully uploaded all documents to '{COLLECTION_NAME}'")
        
    except Exception as e:
        logger.error(f"❌ Error uploading documents: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Verify collection
    collections = await rag.get_collections()
    if COLLECTION_NAME in collections:
        logger.info(f"✅ Verification: Collection '{COLLECTION_NAME}' exists")
        
        # Get collection info
        try:
            collection = rag.chroma_client.get_collection(COLLECTION_NAME)
            count = collection.count()
            logger.info(f"   - Total documents in collection: {count}")
        except Exception as e:
            logger.warning(f"   - Could not get document count: {e}")
    else:
        logger.error(f"❌ Verification failed: Collection '{COLLECTION_NAME}' not found")
    
    logger.info("🎉 Processing complete!")


async def main():
    """تابع اصلی"""
    await process_and_upload()


if __name__ == "__main__":
    asyncio.run(main())

