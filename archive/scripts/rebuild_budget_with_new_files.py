# -*- coding: utf-8 -*-
"""
Rebuild budget_financial collection with new files (manabe3.xlsx and masaref3.xlsx)
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
from services.smart_column_extractor import get_smart_column_extractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Collection name
COLLECTION_NAME = "budget_financial"

# New file paths
MASAREF_FILE = "/home/user01/qwen-api/enhanced_rag_system_dev/archive/data_files/masaref3.xlsx"
MANABE_FILE = "/home/user01/qwen-api/enhanced_rag_system_dev/archive/data_files/manabe3.xlsx"


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


def get_column_value(row, possible_names: List[str], default=""):
    """Get column value trying multiple possible names"""
    for name in possible_names:
        if name in row.index:
            val = row.get(name)
            if not pd.isna(val):
                return val
    return default


def process_masaref_row(row: pd.Series, row_index: int) -> Dict[str, Any]:
    """پردازش یک ردیف از فایل مصارف"""
    
    # استخراج اطلاعات با handle کردن نام‌های مختلف ستون
    main_org = clean_value(get_column_value(row, ['عنوان دستگاه اصلي', 'عنوان_دستگاه_اصلي', 'عنوان دستگاه اصلی']))
    exec_org = clean_value(get_column_value(row, ['عنوان دستگاه اجرايي ', 'عنوان_دستگاه_اجرايي', 'عنوان دستگاه اجرایی']))
    exec_code = clean_value(get_column_value(row, ['کد دستگاه اجرايي ', 'کد_دستگاه_اجرايي', 'کد دستگاه اجرایی']))
    year = clean_value(get_column_value(row, ['سال ', 'سال', 'سال']))
    
    # اعتبارات هزینه‌ای
    expense_general = get_column_value(row, ['براورد اعتبارات هزینه ای - عمومی', 'براورد_اعتبارات_هزینه_ای_عمومی'], 0)
    expense_misc = get_column_value(row, ['برآورد اعتبارات هزینه ای - متفرقه', 'برآورد_اعتبارات_هزینه_ای_متفرقه'], 0)
    expense_specific = get_column_value(row, ['براورد اعتبارات هزینه ای - اختصاصی', 'براورد_اعتبارات_هزینه_ای_اختصاصی'], 0)
    expense_total = get_column_value(row, ['جمع براورد اعتبارات هزینه ای', 'جمع_براورد_اعتبارات_هزینه_ای'], 0)
    
    # تملک دارایی‌های سرمایه‌ای
    capital_general = get_column_value(row, [' براورد تملك دارايي هاي سرمايه اي - عمومی', 'براورد_تملك_دارايي_هاي_سرمايه_اي_عمومی'], 0)
    capital_misc = get_column_value(row, [' براورد تملك دارايي هاي سرمايه اي - متفرقه', 'براورد_تملك_دارايي_هاي_سرمايه_اي_متفرقه'], 0)
    capital_specific = get_column_value(row, [' براورد تملك دارايي هاي سرمايه اي - اختصاصی', 'براورد_تملك_دارايي_هاي_سرمايه_اي_اختصاصی'], 0)
    capital_total = get_column_value(row, ['جمع برآورد تملك دارايي هاي سرمايه اي', 'جمع_برآورد_تملك_دارايي_هاي_سرمايه_اي'], 0)
    
    # جمع کل
    grand_total = get_column_value(row, ['جمع كل ', 'جمع_كل', 'جمع کل'], 0)
    
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
        "",
        "## تملک دارایی‌های سرمایه‌ای (عمرانی):",
        f"- تملک عمومی: {format_currency(capital_general)} میلیون ریال",
        f"- تملک متفرقه: {format_currency(capital_misc)} میلیون ریال",
        f"- تملک اختصاصی: {format_currency(capital_specific)} میلیون ریال",
        f"- جمع تملک دارایی: {format_currency(capital_total)} میلیون ریال",
        "",
        f"## جمع کل بودجه: {format_currency(grand_total)} میلیون ریال"
    ]
    
    text = "\n".join(text_parts)
    
    # Metadata
    metadata = {
        "source": "masaref3.xlsx",
        "row_index": row_index,
        "doc_type": "masaref",
        "main_organization": main_org,
        "executive_organization": exec_org,
        "organization_code": exec_code,
        "year": year,
        "expense_general": float(expense_general) if not pd.isna(expense_general) else 0.0,
        "expense_specific": float(expense_specific) if not pd.isna(expense_specific) else 0.0,
        "expense_total": float(expense_total) if not pd.isna(expense_total) else 0.0,
        "capital_general": float(capital_general) if not pd.isna(capital_general) else 0.0,
        "capital_specific": float(capital_specific) if not pd.isna(capital_specific) else 0.0,
        "capital_total": float(capital_total) if not pd.isna(capital_total) else 0.0,
        "grand_total": float(grand_total) if not pd.isna(grand_total) else 0.0
    }
    
    return {
        "text": text,
        "metadata": metadata
    }


def process_manabe_row(row: pd.Series, row_index: int) -> Dict[str, Any]:
    """پردازش یک ردیف از فایل منابع"""
    
    # استخراج اطلاعات
    section_title = clean_value(get_column_value(row, ['عنوان قسمت ', 'عنوان_قسمت', 'عنوان قسمت']))
    part_code = clean_value(get_column_value(row, ['کد بخش ', 'کد_بخش', 'کد بخش']))
    part_title = clean_value(get_column_value(row, ['عنوان بخش ', 'عنوان_بخش', 'عنوان بخش']))
    item_code = clean_value(get_column_value(row, ['کد بند ', 'کد_بند', 'کد بند']))
    item_title = clean_value(get_column_value(row, ['عنوان بند', 'عنوان_بند']))
    sub_code = clean_value(get_column_value(row, ['کد جزء ', 'کد_جزء', 'کد جزء']))
    sub_title = clean_value(get_column_value(row, ['عنوان جزء ', 'عنوان_جزء', 'عنوان جزء']))
    org_code = clean_value(get_column_value(row, ['کد دستگاه اجرایی', 'کد_دستگاه_اجرایی', 'کد دستگاه']))
    exec_org = clean_value(get_column_value(row, ['عنوان دستگاه اجرایی', 'عنوان_دستگاه_اجرایی', 'عنوان دستگاه']))
    main_org = clean_value(get_column_value(row, ['عنوان دستگاه اصلی', 'عنوان_دستگاه_اصلی']))
    
    # درآمد عمومی
    income_general_national = get_column_value(row, ['در آمد عمومی - ملی', 'در_آمد_عمومي_ملي', 'درآمد عمومی ملی'], 0)
    income_general_regional = get_column_value(row, ['در آمد عمومی - استانی', 'در_آمد_عمومي_استاني', 'درآمد عمومی استانی'], 0)
    income_general_total = get_column_value(row, ['جمع در آمد عمومی', 'جمع_در_آمد_عمومي', 'جمع درآمد عمومی'], 0)
    
    # درآمد اختصاصی
    income_specific_national = get_column_value(row, ['در آمد اختصاصی - ملی', 'در_آمد_اختصاصي_ملي', 'درآمد اختصاصی ملی'], 0)
    income_specific_regional = get_column_value(row, ['در آمد اختصاصی - استانی', 'در_آمد_اختصاصي_استاني', 'درآمد اختصاصی استانی'], 0)
    income_specific_total = get_column_value(row, ['جمع در آمد اختصاصی', 'جمع_در_آمد_اختصاصي', 'جمع درآمد اختصاصی'], 0)
    
    # جمع کل
    total_national = get_column_value(row, ['جمع کل - ملی', 'جمع_کل_ملي', 'جمع کل ملی'], 0)
    total_regional = get_column_value(row, ['جمع کل - استانی', 'جمع_کل_استاني', 'جمع کل استانی'], 0)
    grand_total = get_column_value(row, ['جمع کل', 'جمع_کل'], 0)
    
    year = clean_value(get_column_value(row, ['سال', 'سال ']))
    
    # ساخت متن توصیفی
    text_parts = [
        f"قسمت: {section_title}",
        f"بخش: {part_title} (کد: {part_code})",
        f"بند: {item_title} (کد: {item_code})",
        f"جزء: {sub_title} (کد: {sub_code})",
        f"دستگاه اجرایی: {exec_org} (کد: {org_code})",
        f"دستگاه اصلی: {main_org}",
        f"سال: {year}",
        "",
        "## درآمد عمومی:",
        f"- ملی: {format_currency(income_general_national)} میلیون ریال",
        f"- استانی: {format_currency(income_general_regional)} میلیون ریال",
        f"- جمع: {format_currency(income_general_total)} میلیون ریال",
        "",
        "## درآمد اختصاصی:",
        f"- ملی: {format_currency(income_specific_national)} میلیون ریال",
        f"- استانی: {format_currency(income_specific_regional)} میلیون ریال",
        f"- جمع: {format_currency(income_specific_total)} میلیون ریال",
        "",
        "## جمع کل:",
        f"- ملی: {format_currency(total_national)} میلیون ریال",
        f"- استانی: {format_currency(total_regional)} میلیون ریال",
        f"- جمع کل: {format_currency(grand_total)} میلیون ریال"
    ]
    
    text = "\n".join(text_parts)
    
    # Metadata
    metadata = {
        "source": "manabe3.xlsx",
        "row_index": row_index,
        "doc_type": "manabe",
        "section_title": section_title,
        "part_code": part_code,
        "part_title": part_title,
        "item_code": item_code,
        "item_title": item_title,
        "sub_code": sub_code,
        "sub_title": sub_title,
        "organization_code": org_code,
        "executive_organization": exec_org,
        "main_organization": main_org,
        "year": year,
        "income_general_national": float(income_general_national) if not pd.isna(income_general_national) else 0.0,
        "income_general_regional": float(income_general_regional) if not pd.isna(income_general_regional) else 0.0,
        "income_general_total": float(income_general_total) if not pd.isna(income_general_total) else 0.0,
        "income_specific_national": float(income_specific_national) if not pd.isna(income_specific_national) else 0.0,
        "income_specific_regional": float(income_specific_regional) if not pd.isna(income_specific_regional) else 0.0,
        "income_specific_total": float(income_specific_total) if not pd.isna(income_specific_total) else 0.0,
        "total_national": float(total_national) if not pd.isna(total_national) else 0.0,
        "total_regional": float(total_regional) if not pd.isna(total_regional) else 0.0,
        "grand_total": float(grand_total) if not pd.isna(grand_total) else 0.0
    }
    
    return {
        "text": text,
        "metadata": metadata
    }


async def process_and_upload():
    """پردازش و آپلود فایل‌های بودجه"""
    
    logger.info("🚀 Starting budget files processing with NEW files...")
    logger.info(f"   - MASAREF: {MASAREF_FILE}")
    logger.info(f"   - MANABE: {MANABE_FILE}")
    
    # Initialize RAG system
    rag = RefactoredRAGSystem(
        db_path="/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    )
    
    # Check if collection exists and delete if needed
    collections = rag.get_collections()  # Not async
    collection_names = [c.name if hasattr(c, 'name') else c for c in collections]
    if COLLECTION_NAME in collection_names:
        logger.warning(f"⚠️ Collection '{COLLECTION_NAME}' already exists. Deleting...")
        try:
            rag.chroma_client.delete_collection(name=COLLECTION_NAME)
            logger.info(f"✅ Deleted existing collection")
        except Exception as e:
            logger.error(f"❌ Error deleting collection: {e}")
    
    # Process masaref3.xlsx
    logger.info(f"📊 Processing {MASAREF_FILE}...")
    try:
        df_masaref = pd.read_excel(MASAREF_FILE)
        logger.info(f"   - Loaded {len(df_masaref)} rows from masaref3.xlsx")
        logger.info(f"   - Columns: {list(df_masaref.columns)[:5]}...")
        
        masaref_documents = []
        for idx, row in df_masaref.iterrows():
            try:
                doc = process_masaref_row(row, idx)
                masaref_documents.append(doc)
            except Exception as e:
                if idx < 5:  # Only log first few errors
                    logger.error(f"   - Error processing row {idx}: {e}")
        
        logger.info(f"   - Processed {len(masaref_documents)} documents from masaref3")
        
    except Exception as e:
        logger.error(f"❌ Error loading masaref3.xlsx: {e}")
        return
    
    # Process manabe3.xlsx
    logger.info(f"📊 Processing {MANABE_FILE}...")
    try:
        df_manabe = pd.read_excel(MANABE_FILE)
        logger.info(f"   - Loaded {len(df_manabe)} rows from manabe3.xlsx")
        logger.info(f"   - Columns: {list(df_manabe.columns)[:5]}...")
        
        manabe_documents = []
        for idx, row in df_manabe.iterrows():
            try:
                doc = process_manabe_row(row, idx)
                manabe_documents.append(doc)
            except Exception as e:
                if idx < 5:  # Only log first few errors
                    logger.error(f"   - Error processing row {idx}: {e}")
        
        logger.info(f"   - Processed {len(manabe_documents)} documents from manabe3")
        
    except Exception as e:
        logger.error(f"❌ Error loading manabe3.xlsx: {e}")
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
            metadata={"description": "Budget Financial Data - Masaref3 and Manabe3"}
        )
        
        # Prepare data for ChromaDB
        texts = [doc["text"] for doc in all_documents]
        metadatas = [doc["metadata"] for doc in all_documents]
        ids = [f"budget_{i}" for i in range(len(all_documents))]
        
        # Upload in batches
        batch_size = 500
        total_uploaded = 0
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            batch_metadatas = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            collection.add(
                documents=batch_texts,
                metadatas=batch_metadatas,
                ids=batch_ids
            )
            
            total_uploaded += len(batch_texts)
            logger.info(f"   - Uploaded {total_uploaded}/{len(texts)} documents...")
        
        logger.info(f"✅ Successfully uploaded {total_uploaded} documents to '{COLLECTION_NAME}'")
        
        # Verify
        count = collection.count()
        logger.info(f"📊 Collection now has {count} documents")
        
    except Exception as e:
        logger.error(f"❌ Error uploading to ChromaDB: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Now process the Excel files for database tables
    logger.info("📊 Processing Excel files for database tables...")
    
    try:
        smart_extractor = get_smart_column_extractor()
        
        # Process masaref3.xlsx for database
        logger.info(f"   - Processing masaref3.xlsx for database...")
        masaref_result = await smart_extractor.process_excel_file(
            file_path=MASAREF_FILE,
            collection_name=COLLECTION_NAME,
            table_name="masaref_sheet1"
        )
        logger.info(f"   - Masaref result: {masaref_result}")
        
        # Process manabe3.xlsx for database
        logger.info(f"   - Processing manabe3.xlsx for database...")
        manabe_result = await smart_extractor.process_excel_file(
            file_path=MANABE_FILE,
            collection_name=COLLECTION_NAME,
            table_name="manabe_sheet1"
        )
        logger.info(f"   - Manabe result: {manabe_result}")
        
    except Exception as e:
        logger.error(f"❌ Error processing Excel files for database: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("🎉 Processing complete!")


if __name__ == "__main__":
    asyncio.run(process_and_upload())

