# -*- coding: utf-8 -*-
"""
اسکریپت پروسس کامل کالکشن budget_financial
شامل: پروسس Excel + ساخت دیتابیس + ساخت کالکشن
"""

import asyncio
import logging
import sys
import pandas as pd
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.refactored_rag_system import RefactoredRAGSystem
from services.database_service import DatabaseService
from processors.excel_to_database import ExcelToDatabaseProcessor


async def process_budget_financial():
    """پروسس کامل کالکشن budget_financial"""
    
    collection_name = "budget_financial"
    
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("🚀 شروع پروسس کامل کالکشن budget_financial")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    try:
        # ═══════════════════════════════════════════════════════════════════════════════
        # مرحله 1: حذف کالکشن قبلی (اگر وجود دارد)
        # ═══════════════════════════════════════════════════════════════════════════════
        logger.info("\n📋 مرحله 1: حذف کالکشن قبلی (اگر وجود دارد)")
        
        rag_system = RefactoredRAGSystem()
        
        try:
            rag_system.chroma_client.delete_collection(collection_name)
            logger.info(f"✅ کالکشن قبلی {collection_name} حذف شد")
        except Exception as e:
            logger.info(f"ℹ️ کالکشن قبلی وجود نداشت یا حذف نشد: {e}")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # مرحله 2: پروسس فایل‌های Excel و ساخت دیتابیس
        # ═══════════════════════════════════════════════════════════════════════════════
        logger.info("\n📊 مرحله 2: پروسس فایل‌های Excel و ساخت دیتابیس")
        
        database_service = DatabaseService()
        excel_processor = ExcelToDatabaseProcessor(database_service)
        
        # فایل‌های Excel
        excel_files = [
            "archive/data_files/masaref2.xlsx",  # مصارف
            "archive/data_files/manabe.xlsx"      # منابع
        ]
        
        all_tables = []
        
        for excel_file in excel_files:
            logger.info(f"\n  📄 پروسس فایل: {excel_file}")
            
            # خواندن فایل
            with open(excel_file, 'rb') as f:
                file_bytes = f.read()
            
            filename = Path(excel_file).name
            
            # پروسس Excel
            result = await excel_processor.process_excel_file(
                file_bytes=file_bytes,
                filename=filename,
                collection_name=collection_name
            )
            
            if result.get("success"):
                tables = result.get("tables", [])
                all_tables.extend(tables)
                logger.info(f"  ✅ {len(tables)} جدول ایجاد شد")
                for table in tables:
                    logger.info(f"     - {table['table_name']}: {table['row_count']} rows, {table['column_count']} columns")
            else:
                logger.error(f"  ❌ خطا در پروسس {filename}: {result.get('error')}")
        
        logger.info(f"\n✅ مجموع {len(all_tables)} جدول در دیتابیس ایجاد شد")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # مرحله 3: ساخت کالکشن ChromaDB
        # ═══════════════════════════════════════════════════════════════════════════════
        logger.info("\n🗂️ مرحله 3: ساخت کالکشن ChromaDB")
        
        # ساخت کالکشن با metadata
        collection = rag_system.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={
                "description": "بودجه مالی کشور - منابع و مصارف",
                "domain": "financial",
                "type": "database",
                "tables": ", ".join([t["table_name"] for t in all_tables]),
                "total_tables": str(len(all_tables))
            }
        )
        
        logger.info(f"✅ کالکشن {collection_name} ایجاد شد")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # مرحله 4: ایجاد metadata documents برای هر جدول
        # ═══════════════════════════════════════════════════════════════════════════════
        logger.info("\n📝 مرحله 4: ایجاد metadata documents")
        
        documents = []
        metadatas = []
        ids = []
        
        for idx, table in enumerate(all_tables):
            table_name = table["table_name"]
            
            # ساخت document برای metadata
            doc_text = f"""جدول: {table_name}
نام sheet: {table.get('sheet_name', 'N/A')}
تعداد سطرها: {table['row_count']}
تعداد ستون‌ها: {table['column_count']}

این جدول شامل اطلاعات بودجه مالی کشور است.
"""
            
            documents.append(doc_text)
            metadatas.append({
                "type": "table_metadata",
                "table_name": table_name,
                "sheet_name": table.get('sheet_name', ''),
                "row_count": str(table['row_count']),
                "column_count": str(table['column_count']),
                "source": "database"
            })
            ids.append(f"table_meta_{idx}")
        
        # اضافه کردن به کالکشن
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"✅ {len(documents)} metadata document به کالکشن اضافه شد")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # مرحله 5: خلاصه نهایی
        # ═══════════════════════════════════════════════════════════════════════════════
        logger.info("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("✅ پروسس کامل budget_financial با موفقیت انجام شد!")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"\n📊 خلاصه:")
        logger.info(f"   - کالکشن: {collection_name}")
        logger.info(f"   - تعداد جداول: {len(all_tables)}")
        logger.info(f"   - تعداد documents: {len(documents)}")
        logger.info(f"\n📋 جداول ایجاد شده:")
        for table in all_tables:
            logger.info(f"   ✅ {table['table_name']}: {table['row_count']} rows")
        
        logger.info("\n🚀 سیستم آماده پاسخگویی به سوالات مالی است!")
        
        return {
            "success": True,
            "collection_name": collection_name,
            "tables": all_tables,
            "documents_count": len(documents)
        }
        
    except Exception as e:
        logger.error(f"\n❌ خطا در پروسس: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    result = asyncio.run(process_budget_financial())
    
    if result.get("success"):
        print("\n✅ پروسس با موفقیت کامل شد!")
        sys.exit(0)
    else:
        print(f"\n❌ پروسس با خطا مواجه شد: {result.get('error')}")
        sys.exit(1)

