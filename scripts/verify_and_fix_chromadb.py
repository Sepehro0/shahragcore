#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت بررسی و بهبود ChromaDB
بررسی اینکه آیا داده‌های Excel به درستی در ChromaDB index شده‌اند یا نه
"""

import sys
import asyncio
import pandas as pd
import chromadb
from chromadb.config import Settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_chromadb_indexing():
    """بررسی اینکه آیا داده‌ها در ChromaDB index شده‌اند"""
    
    print("\n" + "="*90)
    print("بررسی ChromaDB Indexing")
    print("="*90 + "\n")
    
    # Initialize ChromaDB
    db_path = "/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    client = chromadb.PersistentClient(path=db_path, settings=Settings(anonymized_telemetry=False))
    
    collection_name = 'budget_financial'
    
    try:
        collection = client.get_collection(name=collection_name)
        logger.info(f"✅ Collection '{collection_name}' found")
    except Exception as e:
        logger.error(f"❌ Collection '{collection_name}' not found: {e}")
        return False
    
    # بررسی تعداد documents
    total_count = collection.count()
    print(f"📊 تعداد کل documents در ChromaDB: {total_count}")
    
    # بررسی داده‌های مربوط به وزارت نفت
    print("\n🔍 بررسی داده‌های \"وزارت نفت\" در ChromaDB:")
    try:
        # جستجو در documents
        all_docs = collection.get(limit=min(5000, total_count))
        
        naft_docs = []
        for idx, (doc_id, content) in enumerate(zip(all_docs['ids'], all_docs['documents'])):
            if 'نفت' in content or (all_docs.get('metadatas') and all_docs['metadatas'][idx] and 
                                     any('نفت' in str(v) for v in all_docs['metadatas'][idx].values())):
                naft_docs.append((doc_id, content[:200]))
        
        print(f"  ✅ {len(naft_docs)} document با \"نفت\" پیدا شد")
        if len(naft_docs) > 0:
            print(f"  نمونه:")
            for doc_id, content in naft_docs[:3]:
                print(f"    - {content}...")
        else:
            print(f"  ❌ هیچ document با \"نفت\" پیدا نشد")
    except Exception as e:
        logger.error(f"  ❌ خطا در جستجو: {e}")
    
    # بررسی داده‌های مربوط به دانشگاه تبریز
    print("\n🔍 بررسی داده‌های \"دانشگاه تبریز\" در ChromaDB:")
    try:
        tabriz_docs = []
        for idx, (doc_id, content) in enumerate(zip(all_docs['ids'], all_docs['documents'])):
            if 'تبریز' in content or (all_docs.get('metadatas') and all_docs['metadatas'][idx] and 
                                      any('تبریز' in str(v) for v in all_docs['metadatas'][idx].values())):
                tabriz_docs.append((doc_id, content[:200]))
        
        print(f"  ✅ {len(tabriz_docs)} document با \"تبریز\" پیدا شد")
        if len(tabriz_docs) > 0:
            print(f"  نمونه:")
            for doc_id, content in tabriz_docs[:3]:
                print(f"    - {content}...")
        else:
            print(f"  ❌ هیچ document با \"تبریز\" پیدا نشد")
    except Exception as e:
        logger.error(f"  ❌ خطا در جستجو: {e}")
    
    # بررسی سال 1403
    print("\n🔍 بررسی داده‌های سال 1403 در ChromaDB:")
    try:
        year_1403_docs = []
        for idx, (doc_id, content) in enumerate(zip(all_docs['ids'], all_docs['documents'])):
            if '1403' in content or (all_docs.get('metadatas') and all_docs['metadatas'][idx] and 
                                     all_docs['metadatas'][idx].get('year') == '1403'):
                year_1403_docs.append((doc_id, content[:200]))
        
        print(f"  ✅ {len(year_1403_docs)} document با سال 1403 پیدا شد")
    except Exception as e:
        logger.error(f"  ❌ خطا در جستجو: {e}")
    
    return len(naft_docs) > 0 or len(tabriz_docs) > 0


async def check_excel_data():
    """بررسی داده‌های موجود در فایل‌های Excel"""
    
    print("\n" + "="*90)
    print("بررسی داده‌های Excel")
    print("="*90 + "\n")
    
    # بررسی manabe.xlsx
    print("📄 بررسی manabe.xlsx (درآمدها):")
    try:
        df = pd.read_excel('archive/data_files/manabe.xlsx', sheet_name='Sheet1')
        
        # بررسی سال 1403
        df_1403 = df[df['سال'] == 1403]
        print(f"  ✅ تعداد ردیف‌های سال 1403: {len(df_1403)}")
        
        # بررسی وزارت نفت در سال 1403
        naft_1403 = df_1403[df_1403['عنوان دستگاه اصلی'].astype(str).str.contains('نفت', na=False, case=False)]
        print(f"  ✅ تعداد ردیف‌های \"نفت\" در سال 1403: {len(naft_1403)}")
        
        # بررسی دانشگاه تبریز در سال 1403
        tabriz_1403 = df_1403[df_1403['عنوان دستگاه اجرایی'].astype(str).str.contains('تبریز', na=False, case=False)]
        print(f"  ✅ تعداد ردیف‌های \"تبریز\" در سال 1403: {len(tabriz_1403)}")
        
        if len(naft_1403) > 0:
            print(f"\n  نمونه داده‌های وزارت نفت در سال 1403:")
            sample = naft_1403.head(1).iloc[0]
            print(f"    - عنوان دستگاه: {sample['عنوان دستگاه اصلی']}")
            print(f"    - عنوان جزء: {sample['عنوان جزء']}")
            print(f"    - درآمد استانی اختصاصی: {sample.get(' در آمد اختصاصي استاني', 'N/A')}")
            print(f"    - درآمد ملی اختصاصی: {sample.get(' در آمد اختصاصي ملي', 'N/A')}")
        
        return len(naft_1403) > 0, len(tabriz_1403) > 0
        
    except Exception as e:
        logger.error(f"❌ خطا در بررسی Excel: {e}")
        import traceback
        traceback.print_exc()
        return False, False


async def main():
    """تابع اصلی"""
    
    # بررسی داده‌های Excel
    has_naft, has_tabriz = await check_excel_data()
    
    # بررسی ChromaDB
    has_indexed = await check_chromadb_indexing()
    
    # نتیجه‌گیری
    print("\n" + "="*90)
    print("نتیجه‌گیری")
    print("="*90 + "\n")
    
    print(f"📊 داده‌های Excel:")
    print(f"  - وزارت نفت در سال 1403: {'✅ موجود' if has_naft else '❌ موجود نیست'}")
    print(f"  - دانشگاه تبریز در سال 1403: {'✅ موجود' if has_tabriz else '❌ موجود نیست'}")
    
    print(f"\n🗄️ ChromaDB Indexing:")
    print(f"  - داده‌ها index شده‌اند: {'✅ بله' if has_indexed else '❌ خیر'}")
    
    if has_naft and not has_indexed:
        print("\n⚠️ هشدار: داده‌ها در Excel موجود هستند اما در ChromaDB index نشده‌اند!")
        print("   نیاز به re-index کردن داده‌ها داریم.")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)


