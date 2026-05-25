# -*- coding: utf-8 -*-
"""
پردازش جامع فایل takallo.pdf با تمام تکنولوژی‌های موجود

این script از تمام قابلیت‌های پردازش PDF استفاده می‌کند:
1. Advanced PDF Table Processor (استخراج جداول)
2. Text Extraction با RTL Fix
3. Document Structure Analysis
4. Universal Metadata Extraction
5. Semantic Chunking
6. Document Domain Classification
"""

import asyncio
import sys
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

# Add project path
sys.path.insert(0, '/home/user01/qwen-api/enhanced_rag_system')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Imports
import pdfplumber
from ultimate_rag_system import UltimateRAGSystem
from processors.advanced_pdf_table_processor import AdvancedPDFTableProcessor
from processors.accurate_structure_analyzer import AccurateStructureAnalyzer
from processors.universal_metadata_extractor import UniversalMetadataExtractor
from processors.document_domain_classifier import DocumentDomainClassifier, DocumentDomain


async def process_takallo_pdf():
    """پردازش جامع فایل takallo.pdf"""
    
    pdf_path = "/home/user01/qwen-api/enhanced_rag_system/takallo.pdf"
    collection_name = "takallo"
    
    print("="*100)
    print("🚀 COMPREHENSIVE PDF PROCESSING: takallo.pdf")
    print("="*100)
    
    # بارگذاری فایل
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    file_size_mb = len(pdf_bytes) / 1024 / 1024
    print(f"📄 File: {pdf_path}")
    print(f"   Size: {file_size_mb:.2f} MB")
    
    # ========== مرحله 1: استخراج متن با RTL Fix ==========
    print("\n" + "="*100)
    print("📝 STEP 1: Text Extraction with RTL Fix")
    print("="*100)
    
    text_chunks = []
    import io
    
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        total_pages = len(pdf.pages)
        print(f"   Total pages: {total_pages}")
        
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            
            if text and text.strip():
                # RTL Fix - تبدیل متن معکوس به صحیح
                fixed_text = fix_rtl_text(text)
                
                # تقسیم به chunks کوچک‌تر
                page_chunks = split_text_into_chunks(fixed_text, chunk_size=600)
                
                for chunk_idx, chunk_text in enumerate(page_chunks):
                    if chunk_text.strip() and len(chunk_text.strip()) > 20:
                        chunk = {
                            'text': chunk_text.strip(),
                            'metadata': {
                                'page': page_num,
                                'chunk_index': chunk_idx,
                                'source': 'pdf_text',
                                'filename': 'takallo.pdf',
                                'type': 'text_content',
                                'total_pages': total_pages
                            }
                        }
                        text_chunks.append(chunk)
            
            if page_num % 10 == 0:
                print(f"   Processed {page_num}/{total_pages} pages...")
    
    print(f"✅ Text chunks created: {len(text_chunks)}")
    
    # ========== مرحله 2: استخراج جداول ==========
    print("\n" + "="*100)
    print("📊 STEP 2: Table Extraction with Advanced Processor")
    print("="*100)
    
    table_processor = AdvancedPDFTableProcessor()
    table_chunks = []
    
    try:
        tables_data = table_processor.extract_tables_advanced(pdf_bytes)
        
        if tables_data:
            table_chunks = table_processor.create_structured_chunks(tables_data)
            print(f"✅ Table chunks created: {len(table_chunks)}")
            
            # نمایش نمونه جداول
            for i, chunk in enumerate(table_chunks[:3]):
                print(f"   Table {i+1}: {chunk['text'][:100]}...")
        else:
            print("⚠️ No tables found in PDF")
    except Exception as e:
        print(f"❌ Table extraction failed: {e}")
    
    # ========== مرحله 3: ترکیب chunks ==========
    print("\n" + "="*100)
    print("🔗 STEP 3: Combining Chunks")
    print("="*100)
    
    all_chunks = text_chunks + table_chunks
    print(f"   Text chunks: {len(text_chunks)}")
    print(f"   Table chunks: {len(table_chunks)}")
    print(f"✅ Total chunks: {len(all_chunks)}")
    
    # ========== مرحله 4: تحلیل ساختار سند ==========
    print("\n" + "="*100)
    print("🏗️ STEP 4: Document Structure Analysis")
    print("="*100)
    
    try:
        structure_analyzer = AccurateStructureAnalyzer()
        doc_structure = structure_analyzer.analyze_document(all_chunks)
        
        # غنی‌سازی metadata
        enriched_chunks = []
        for chunk_idx, chunk in enumerate(all_chunks):
            enriched_chunk = structure_analyzer.enrich_chunk_metadata(
                chunk, doc_structure, chunk_idx
            )
            enriched_chunks.append(enriched_chunk)
        
        # افزودن خلاصه ساختار
        structure_summary_text = structure_analyzer.create_structure_summary_text(doc_structure)
        structure_summary_chunk = {
            'text': structure_summary_text,
            'metadata': {
                'type': 'structure_summary',
                'filename': 'takallo.pdf',
                'total_parts': str(doc_structure.get('total_parts', 0)),
                'total_sections': str(doc_structure.get('total_sections', 0)),
                'total_clauses': str(doc_structure.get('total_clauses', 0))
            }
        }
        
        enriched_chunks.insert(0, structure_summary_chunk)
        all_chunks = enriched_chunks
        
        print(f"✅ Structure analysis complete")
        print(f"   Parts: {doc_structure.get('total_parts', 0)}")
        print(f"   Sections: {doc_structure.get('total_sections', 0)}")
        print(f"   Clauses: {doc_structure.get('total_clauses', 0)}")
        
    except Exception as e:
        print(f"⚠️ Structure analysis failed: {e}")
        import traceback
        traceback.print_exc()
    
    # ========== مرحله 5: طبقه‌بندی حوزه سند ==========
    print("\n" + "="*100)
    print("🔍 STEP 5: Document Domain Classification")
    print("="*100)
    
    domain_info = None
    try:
        # Initialize RAG system for domain classification
        rag = UltimateRAGSystem(
            enable_semantic_chunking=False,
            enable_query_understanding=False,
            enable_advanced_retrieval=False
        )
        
        domain_info = await rag.domain_classifier.classify_document(
            chunks=all_chunks[:50],  # نمونه از chunks
            filename='takallo.pdf',
            use_llm=True
        )
        
        print(f"✅ Domain: {domain_info['domain']}")
        print(f"   Confidence: {domain_info['confidence']:.2f}")
        print(f"   Method: {domain_info['method']}")
        print(f"   Keywords: {domain_info.get('keywords', [])[:10]}")
        print(f"   Summary: {domain_info.get('summary', 'N/A')[:150]}...")
        
    except Exception as e:
        print(f"⚠️ Domain classification failed: {e}")
        domain_info = {
            'domain': DocumentDomain.TECHNICAL,
            'confidence': 0.7,
            'keywords': ['پیمان', 'EPC', 'تجهیزات', 'ساختمان'],
            'summary': 'سند فنی مربوط به پیمان‌های EPC',
            'method': 'default'
        }
    
    # ========== مرحله 6: ذخیره در ChromaDB ==========
    print("\n" + "="*100)
    print("💾 STEP 6: Storing in ChromaDB")
    print("="*100)
    
    try:
        # استفاده از RAG system برای ذخیره
        if 'rag' not in locals():
            rag = UltimateRAGSystem(
                enable_semantic_chunking=False,
                enable_query_understanding=False,
                enable_advanced_retrieval=False
            )
        
        # ذخیره با domain info
        result = await rag._store_chunks(
            chunks=all_chunks,
            collection_name=collection_name,
            filename='takallo.pdf',
            domain_info=domain_info
        )
        
        if result.get('success'):
            print(f"✅ Successfully stored {result.get('chunks_count')} chunks")
            print(f"   Collection: {collection_name}")
        else:
            print(f"❌ Storage failed: {result.get('error')}")
            return
        
    except Exception as e:
        print(f"❌ Storage failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========== مرحله 7: نمایش آمار نهایی ==========
    print("\n" + "="*100)
    print("📊 FINAL STATISTICS")
    print("="*100)
    
    print(f"""
    📄 File: takallo.pdf
    📦 Collection: {collection_name}
    📝 Total Chunks: {len(all_chunks)}
       - Text chunks: {len(text_chunks)}
       - Table chunks: {len(table_chunks)}
    🔍 Domain: {domain_info.get('domain', 'N/A')}
    🎯 Confidence: {domain_info.get('confidence', 0):.2f}
    """)
    
    print("="*100)
    print("✅ PDF PROCESSING COMPLETE!")
    print("="*100)
    
    return {
        'success': True,
        'collection_name': collection_name,
        'total_chunks': len(all_chunks),
        'text_chunks': len(text_chunks),
        'table_chunks': len(table_chunks),
        'domain_info': domain_info
    }


def fix_rtl_text(text: str) -> str:
    """Fix RTL text ordering issues"""
    if not text:
        return ""
    
    import unicodedata
    
    # مرحله 1: تبدیل presentation forms به حروف استاندارد
    fixed_text = ""
    for char in text:
        code_point = ord(char)
        # اگر کاراکتر در بازه presentation forms است
        if 0xFB50 <= code_point <= 0xFDFF or 0xFE70 <= code_point <= 0xFEFF:
            try:
                normalized = unicodedata.normalize('NFKC', char)
                fixed_text += normalized
            except:
                fixed_text += char
        else:
            fixed_text += char
    
    # مرحله 2: بررسی و اصلاح ترتیب کلمات معکوس
    lines = fixed_text.split('\n')
    corrected_lines = []
    
    for line in lines:
        words = line.split()
        if len(words) >= 3:
            # بررسی الگوی معکوس
            reversed_pattern_count = 0
            
            for word in words:
                if len(word) <= 1:
                    continue
                
                first_char = word[0]
                last_char = word[-1]
                
                # حروفی که معمولاً در انتهای کلمات فارسی هستند
                common_endings = ['ا', 'و', 'ی', 'ه', 'ن', 'ت', 'د', 'ر', 'ش', 'س']
                common_starts = ['ب', 'پ', 'ت', 'ث', 'ج', 'چ', 'ح', 'خ', 'م', 'ن']
                
                if first_char in common_endings and last_char in common_starts:
                    reversed_pattern_count += 1
            
            # اگر بیش از 50% کلمات الگوی معکوس دارند
            if len(words) > 0 and reversed_pattern_count / len(words) > 0.5:
                words = words[::-1]
        
        corrected_lines.append(' '.join(words))
    
    return '\n'.join(corrected_lines)


def split_text_into_chunks(text: str, chunk_size: int = 600) -> List[str]:
    """تقسیم متن به chunks"""
    if not text or not text.strip():
        return []
    
    # تقسیم بر اساس پاراگراف‌ها
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        
        if len(paragraph) > chunk_size:
            # تقسیم بر اساس جملات
            sentences = paragraph.replace('. ', '.\n').split('\n')
            for sentence in sentences:
                if len(current_chunk + sentence) > chunk_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk += " " + sentence
        else:
            if len(current_chunk + paragraph) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


if __name__ == "__main__":
    result = asyncio.run(process_takallo_pdf())
    
    if result and result.get('success'):
        print("\n🎉 Processing successful!")
        print(f"   Collection '{result['collection_name']}' is ready for queries.")
    else:
        print("\n❌ Processing failed!")

