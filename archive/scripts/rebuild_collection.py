#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت بازسازی Collection با فایل اکسل جدید
این اسکریپت collection موجود را حذف و با embedding model بهبود یافته دوباره می‌سازد
"""

import asyncio
import os
import sys
import shutil
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ultimate_rag_system import UltimateRAGSystem

# Configuration
EXCEL_FILE = "/home/user01/qwen-api/enhanced_rag_system_dev/archive/data_files/karbaran_omomi_latest.xlsx"
COLLECTION_NAME = "karbaran_omomi"
DB_PATH = "/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
BACKUP_PATH = f"/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

async def main():
    print("=" * 80)
    print("🔄 بازسازی Collection با فایل اکسل جدید")
    print("=" * 80)
    print()
    
    # بررسی وجود فایل
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ فایل اکسل پیدا نشد: {EXCEL_FILE}")
        return 1
    
    print(f"📁 فایل اکسل: {EXCEL_FILE}")
    print(f"🗄️  Collection: {COLLECTION_NAME}")
    print(f"💾 مسیر دیتابیس: {DB_PATH}")
    print()
    
    # 1. Backup دیتابیس موجود
    if os.path.exists(DB_PATH):
        print("📦 ایجاد نسخه پشتیبان...")
        try:
            shutil.copytree(DB_PATH, BACKUP_PATH)
            print(f"✅ نسخه پشتیبان: {BACKUP_PATH}")
        except Exception as e:
            print(f"⚠️  خطا در ایجاد backup: {e}")
    else:
        print("⚠️  دیتابیس موجود نیست، نسخه پشتیبان ایجاد نمی‌شود")
    
    print()
    
    # 2. Initialize RAG System
    print("🚀 راه‌اندازی سیستم RAG...")
    try:
        rag = UltimateRAGSystem(db_path=DB_PATH)
        print("✅ سیستم RAG آماده است")
        
        # بررسی embedding model
        if hasattr(rag, 'persian_embedding_client') and rag.persian_embedding_client:
            model_info = rag.persian_embedding_client.get_model_info()
            print(f"   📊 Embedding Model: {model_info['model_name']}")
            print(f"   📏 Dimension: {model_info['dimension']}")
            print(f"   💻 Device: {model_info['device']}")
        
    except Exception as e:
        print(f"❌ خطا در راه‌اندازی سیستم: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print()
    
    # 3. حذف collection قدیمی
    print(f"🗑️  حذف collection قدیمی: {COLLECTION_NAME}")
    try:
        rag.chroma_client.delete_collection(name=COLLECTION_NAME)
        print("✅ Collection قدیمی حذف شد")
    except Exception as e:
        print(f"⚠️  Collection وجود نداشت یا خطا: {e}")
    
    print()
    
    # 4. پردازش فایل اکسل
    print("📖 پردازش فایل اکسل...")
    try:
        with open(EXCEL_FILE, "rb") as f:
            file_bytes = f.read()
        
        print(f"   📦 حجم فایل: {len(file_bytes) / 1024:.2f} KB")
        
        # Process با force_recreate
        result = await rag.process_excel(
            file_bytes=file_bytes,
            filename=os.path.basename(EXCEL_FILE),
            collection_name=COLLECTION_NAME
        )
        
        if result.get("success"):
            print("✅ پردازش موفق!")
            print(f"   📊 تعداد سند: {result.get('documents_count', 'N/A')}")
            print(f"   🔢 تعداد chunk: {result.get('chunks_count', 'N/A')}")
            if 'sheets_processed' in result:
                print(f"   📋 Sheet های پردازش شده: {result['sheets_processed']}")
        else:
            print(f"❌ خطا در پردازش: {result.get('error', 'Unknown')}")
            return 1
            
    except Exception as e:
        print(f"❌ خطا در پردازش فایل: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print()
    
    # 5. تست جستجو
    print("=" * 80)
    print("🧪 تست جستجو")
    print("=" * 80)
    print()
    
    test_queries = [
        "اگر ایدم خیلی خام باشه میتونم بازم برا دانشمند ایدمو بفرستم؟",
        "ایمیل صندوق باور چیه؟",
        "چقدر سرمایه می‌تونم بگیرم؟",
        "ماموریت های موسسه دانشمند",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"تست {i}/{len(test_queries)}: {query}")
        try:
            results = await rag.semantic_search(
                query=query,
                collection_name=COLLECTION_NAME,
                top_k=3
            )
            
            if results:
                top_result = results[0]
                metadata = top_result.get('metadata', {})
                print(f"   ✅ نتیجه برتر:")
                print(f"      سوال: {metadata.get('question', 'N/A')[:100]}")
                print(f"      امتیاز: {top_result.get('score', 0.0):.4f}")
                if len(results) > 1:
                    print(f"   📋 نتایج بیشتر: {len(results)} نتیجه")
            else:
                print("   ❌ نتیجه‌ای پیدا نشد")
                
        except Exception as e:
            print(f"   ❌ خطا: {e}")
        
        print()
    
    # 6. Close
    await rag.close()
    
    print("=" * 80)
    print("✅ بازسازی کامل شد!")
    print("=" * 80)
    print()
    print("📊 خلاصه:")
    print(f"   - Collection: {COLLECTION_NAME}")
    print(f"   - Embedding Model: DistilUSE (512-dim)")
    print(f"   - Text Format: Clean (بدون noise)")
    print(f"   - Backup: {BACKUP_PATH}")
    print()
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


