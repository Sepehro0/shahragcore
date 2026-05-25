# -*- coding: utf-8 -*-
"""
پردازش مجدد takallo.pdf با RTL Fix بهتر
"""

import asyncio
import sys
import os
import re
import unicodedata
from typing import List, Dict, Any

sys.path.insert(0, '/home/user01/qwen-api/enhanced_rag_system')

import fitz  # PyMuPDF
from ultimate_rag_system import UltimateRAGSystem
from processors.document_domain_classifier import DocumentDomain


def is_persian_char(char: str) -> bool:
    """Check if character is Persian/Arabic"""
    code = ord(char)
    # Arabic block: 0600-06FF
    # Arabic Supplement: 0750-077F
    # Arabic Extended-A: 08A0-08FF
    # Arabic Presentation Forms-A: FB50-FDFF
    # Arabic Presentation Forms-B: FE70-FEFF
    return (0x0600 <= code <= 0x06FF or
            0x0750 <= code <= 0x077F or
            0x08A0 <= code <= 0x08FF or
            0xFB50 <= code <= 0xFDFF or
            0xFE70 <= code <= 0xFEFF)


def reverse_persian_text(text: str) -> str:
    """
    Fix reversed Persian text from PDF
    
    در PDF های فارسی، متن اغلب به صورت visual-order ذخیره می‌شود
    که باعث می‌شود کلمات و حروف معکوس شوند.
    این تابع با reverse کردن هر خط، متن را به صورت صحیح برمی‌گرداند.
    """
    if not text:
        return ""
    
    # NFKC normalization
    text = unicodedata.normalize('NFKC', text)
    
    lines = text.split('\n')
    fixed_lines = []
    
    for line in lines:
        if not line.strip():
            fixed_lines.append(line)
            continue
        
        # بررسی تعداد کاراکترهای فارسی
        persian_chars = sum(1 for c in line if is_persian_char(c))
        total_chars = len([c for c in line if c.strip()])
        
        # اگر خط شامل کاراکترهای فارسی است، آن را reverse کن
        if total_chars > 0 and persian_chars / total_chars > 0.2:
            # Reverse کردن کل خط
            fixed_lines.append(line[::-1])
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def extract_text_with_rtl_fix(pdf_path: str) -> List[Dict[str, Any]]:
    """استخراج متن از PDF با RTL fix"""
    
    doc = fitz.open(pdf_path)
    chunks = []
    
    print(f"📄 Processing {len(doc)} pages...")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # استخراج متن
        text = page.get_text("text")
        
        if text and text.strip():
            # RTL Fix
            fixed_text = reverse_persian_text(text)
            
            # تقسیم به chunks
            page_chunks = split_into_chunks(fixed_text, chunk_size=500)
            
            for idx, chunk_text in enumerate(page_chunks):
                if chunk_text.strip() and len(chunk_text.strip()) > 30:
                    chunks.append({
                        'text': chunk_text.strip(),
                        'metadata': {
                            'page': page_num + 1,
                            'chunk_index': idx,
                            'source': 'pdf_text_fixed',
                            'filename': 'takallo.pdf',
                            'type': 'text_content',
                            'total_pages': len(doc)
                        }
                    })
        
        if (page_num + 1) % 20 == 0:
            print(f"   Processed {page_num + 1}/{len(doc)} pages...")
    
    doc.close()
    return chunks


def split_into_chunks(text: str, chunk_size: int = 500) -> List[str]:
    """تقسیم متن به chunks"""
    if not text:
        return []
    
    # تقسیم بر اساس پاراگراف
    paragraphs = text.split('\n\n')
    chunks = []
    current = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        if len(current) + len(para) > chunk_size and current:
            chunks.append(current.strip())
            current = para
        else:
            current += "\n\n" + para if current else para
    
    if current.strip():
        chunks.append(current.strip())
    
    return chunks


async def reprocess_takallo():
    """پردازش مجدد فایل takallo.pdf با RTL fix کامل"""
    
    pdf_path = "/home/user01/qwen-api/enhanced_rag_system/takallo.pdf"
    collection_name = "takallo"
    
    print("="*100)
    print("🔄 REPROCESSING TAKALLO.PDF WITH COMPLETE RTL FIX")
    print("="*100)
    
    # 1. استخراج متن با RTL fix
    print("\n📝 Step 1: Extracting text with RTL fix...")
    text_chunks = extract_text_with_rtl_fix(pdf_path)
    print(f"   ✅ Created {len(text_chunks)} text chunks")
    
    # 2. استخراج جداول
    print("\n📊 Step 2: Extracting tables...")
    from processors.advanced_pdf_table_processor import AdvancedPDFTableProcessor
    
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    table_processor = AdvancedPDFTableProcessor()
    table_chunks = []
    
    try:
        tables_data = table_processor.extract_tables_advanced(pdf_bytes)
        if tables_data:
            raw_table_chunks = table_processor.create_structured_chunks(tables_data)
            
            # RTL fix برای جداول
            for chunk in raw_table_chunks:
                fixed_text = reverse_persian_text(chunk['text'])
                chunk['text'] = fixed_text
                table_chunks.append(chunk)
            
            print(f"   ✅ Created {len(table_chunks)} table chunks (with RTL fix)")
    except Exception as e:
        print(f"   ⚠️ Table extraction failed: {e}")
    
    # 3. ترکیب همه chunks
    all_chunks = text_chunks + table_chunks
    print(f"\n📦 Total chunks: {len(all_chunks)}")
    
    # 4. نمایش نمونه
    if text_chunks and len(text_chunks) > 5:
        print(f"\n📖 Sample text chunk:")
        print("-"*60)
        print(text_chunks[5]['text'][:300])
        print("-"*60)
    
    # 5. ذخیره در ChromaDB
    print("\n💾 Step 3: Storing in ChromaDB...")
    
    rag = UltimateRAGSystem(
        enable_semantic_chunking=False,
        enable_query_understanding=False,
        enable_advanced_retrieval=False
    )
    
    domain_info = {
        'domain': DocumentDomain.TECHNICAL,
        'confidence': 0.9,
        'keywords': ['پیمان', 'EPC', 'کارفرما', 'پیمانکار', 'ساختمان', 'تجهیزات', 'ماده', 'بند'],
        'summary': 'سند شرایط عمومی و خصوصی پیمان EPC برای کارهای صنعتی - شامل موافقتنامه، شرایط عمومی، شرایط خصوصی و پیوست‌ها',
        'method': 'manual'
    }
    
    result = await rag._store_chunks(
        chunks=all_chunks,
        collection_name=collection_name,
        filename='takallo.pdf',
        domain_info=domain_info
    )
    
    if result.get('success'):
        print(f"   ✅ Stored {result.get('chunks_count')} chunks")
    else:
        print(f"   ❌ Failed: {result.get('error')}")
        return
    
    print("\n" + "="*100)
    print("✅ REPROCESSING COMPLETE!")
    print(f"   Collection: {collection_name}")
    print(f"   Text chunks: {len(text_chunks)}")
    print(f"   Table chunks: {len(table_chunks)}")
    print(f"   Total: {len(all_chunks)}")
    print("="*100)


if __name__ == "__main__":
    asyncio.run(reprocess_takallo())

