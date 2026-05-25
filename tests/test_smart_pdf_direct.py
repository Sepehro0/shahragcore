#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست مستقل Smart PDF Upload
بدون نیاز به سرور API - تست مستقیم توابع
"""

import sys
import asyncio
from pathlib import Path

# اضافه کردن مسیر پروژه
sys.path.insert(0, str(Path(__file__).parent))

from api.v1.endpoints.smart_pdf_upload import (
    detect_pdf_type,
    process_text_based_pdf,
    process_image_based_pdf,
)


async def main():
    print("=" * 80)
    print("🧪 تست مستقل Smart PDF Upload")
    print("=" * 80)
    
    # فایل تست
    pdf_file = Path("archive/data_files/qovve-ketab-sample.pdf")
    if not pdf_file.exists():
        print(f"❌ Test PDF not found: {pdf_file}")
        return
    
    print(f"\n📄 Test PDF: {pdf_file.name} ({pdf_file.stat().st_size / 1024:.1f} KB)")
    
    # خواندن فایل
    with open(pdf_file, 'rb') as f:
        pdf_bytes = f.read()
    
    # تست 1: تشخیص نوع PDF
    print("\n" + "-" * 80)
    print("🔍 TEST 1: Detect PDF Type")
    print("-" * 80)
    
    try:
        pdf_info = detect_pdf_type(pdf_bytes)
        print(f"✅ PDF Type: {pdf_info.get('type')}")
        print(f"   Text Extractable: {pdf_info.get('text_extractable')}")
        print(f"   Text Ratio: {pdf_info.get('text_ratio', 0):.0%}")
        print(f"   Total Pages: {pdf_info.get('total_pages')}")
        print(f"   Avg Text Length: {pdf_info.get('avg_text_length', 0):.0f}")
        
        # تعیین روش پردازش
        if pdf_info['type'] == 'image':
            recommended = "OCR"
        elif pdf_info['type'] == 'text':
            recommended = "Standard Text Processing"
        else:
            recommended = "Hybrid (Text + OCR fallback)"
        
        print(f"   Recommended Method: {recommended}")
        
    except Exception as e:
        print(f"❌ Error detecting PDF type: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # تست 2: پردازش بر اساس نوع
    print("\n" + "-" * 80)
    print(f"🔄 TEST 2: Process PDF ({recommended})")
    print("-" * 80)
    
    collection_name = "qovve_smart_direct_test"
    
    try:
        if pdf_info['type'] == 'image' or pdf_info['type'] == 'hybrid':
            print("🖼️ Using OCR processing...")
            result = process_image_based_pdf(
                pdf_bytes,
                pdf_file.name,
                collection_name,
                dpi=300,
                chunk_size=500,
                chunk_overlap=50,
            )
        else:
            print("📄 Using standard text processing...")
            result = process_text_based_pdf(
                pdf_bytes,
                pdf_file.name,
                collection_name,
                chunk_size=500,
                chunk_overlap=50,
            )
        
        if result.get('success'):
            print(f"\n✅ Processing Successful!")
            print(f"   Collection: {collection_name}")
            print(f"   Total Chunks: {result.get('total_chunks', 0)}")
            print(f"   Total Tables: {result.get('total_tables', 0)}")
            print(f"   Total Pages: {result.get('total_pages', 0)}")
            if 'text_chunks' in result:
                print(f"   Text Chunks: {result.get('text_chunks', 0)}")
            if 'table_chunks' in result:
                print(f"   Table Chunks: {result.get('table_chunks', 0)}")
            if 'processing_time_seconds' in result:
                print(f"   Processing Time: {result.get('processing_time_seconds', 0):.1f}s")
        else:
            print(f"\n❌ Processing Failed!")
            print(f"   Error: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"❌ Error processing PDF: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # تست 3: جستجو در کالکشن
    if result.get('success'):
        print("\n" + "-" * 80)
        print("🔍 TEST 3: Search in Collection")
        print("-" * 80)
        
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
            
            client = chromadb.PersistentClient(path="./chroma_db")
            collection = client.get_collection(name=collection_name)
            
            # تست جستجو
            test_queries = [
                "اجاره نامه",
                "دادخواست",
                "قرض الحسنه"
            ]
            
            model = SentenceTransformer("heydariAI/persian-embeddings")
            
            for query in test_queries:
                query_embedding = model.encode([query], convert_to_numpy=False)
                query_embedding = [emb.tolist() if hasattr(emb, 'tolist') else emb for emb in query_embedding]
                
                results = collection.query(
                    query_embeddings=query_embedding,
                    n_results=3,
                    include=['documents', 'metadatas', 'distances']
                )
                
                if results and results['documents']:
                    top_doc = results['documents'][0][0] if results['documents'][0] else ""
                    top_dist = results['distances'][0][0] if results['distances'][0] else 1.0
                    score = 1 - top_dist  # تبدیل distance به score
                    
                    print(f"\n  Query: '{query}'")
                    print(f"  ✅ Found {len(results['documents'][0])} results")
                    print(f"     Top Score: {score:.3f}")
                    print(f"     Preview: {top_doc[:100]}...")
                else:
                    print(f"\n  Query: '{query}'")
                    print(f"  ⚠️ No results found")
        
        except Exception as e:
            print(f"❌ Error searching: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("✅ تمام تست‌ها انجام شد")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
