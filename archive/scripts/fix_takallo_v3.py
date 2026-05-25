# -*- coding: utf-8 -*-
"""
پردازش بهبود یافته takallo.pdf - نسخه 3
با chunks بزرگتر و محتوای معنادار
"""

import asyncio
import pdfplumber
import re
import chromadb
import sys
sys.path.insert(0, '/home/user01/qwen-api/enhanced_rag_system')


def fix_rtl_text(text):
    """تبدیل متن visual-order به logical-order"""
    if not text:
        return ""
    
    lines = text.split('\n')
    fixed_lines = []
    
    for line in lines:
        if not line.strip():
            fixed_lines.append(line)
            continue
        
        reversed_line = line[::-1]
        
        def fix_english(match):
            return match.group(0)[::-1]
        
        def fix_numbers(match):
            return match.group(0)[::-1]
        
        fixed_line = re.sub(r'[A-Za-z]+', fix_english, reversed_line)
        fixed_line = re.sub(r'\d+', fix_numbers, fixed_line)
        
        fixed_lines.append(fixed_line)
    
    return '\n'.join(fixed_lines)


def clean_header_lines(text):
    """حذف خطوط header تکراری"""
    lines = text.split('\n')
    clean_lines = []
    
    skip_patterns = [
        r'^[\s]*\d+[\s]*صفحه',
        r'^[\s]*صفحه[\s]*\d+',
        r'برای کارهای صنعتی$',
        r'^C C P P E E$',
        r'^EPC$',
        r'^[\s]*ن[\s]*$',
        r'^[\s]*ب[\s]*$',
        r'^[\s]*سا[\s]*$',
        r'^[\s]*ص[\s]*$',
        r'^[\s]*م[\s]*$',
        r'^[\s]*ه[\s]*$',
        r'^[\s]*و[\s]*$',
        r'^[\s]*ا[\s]*$',
        r'^[\s]*ی[\s]*$',
        r'^[\s]*ت[\s]*$',
        r'^[\s]*پ[\s]*$',
        r'^[\s]*خ[\s]*$',
        r'^[\s]*عم[\s]*$',
        r'^[\s]*ز ا[\s]*$',
        r'^[\s]*ط[\s]*$',
        r'^[\s]*هی[\s]*$',
        r'^[\s]*ای[\s]*$',
        r'^[\s]*ج[\s]*$',
        r'^[\s]*شر[\s]*$',
    ]
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Skip very short lines
        if len(line_stripped) < 3:
            continue
        
        # Skip header patterns
        is_header = False
        for pattern in skip_patterns:
            if re.match(pattern, line_stripped):
                is_header = True
                break
        
        if not is_header:
            clean_lines.append(line)
    
    return '\n'.join(clean_lines)


def extract_meaningful_chunks(pdf_path):
    """استخراج chunks معنادار با حفظ ساختار ماده‌ها"""
    chunks = []
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"📄 Processing {len(pdf.pages)} pages...")
        
        full_text = ""
        page_markers = {}  # Track which page each character index belongs to
        
        # First pass: collect all text
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                fixed_text = fix_rtl_text(text)
                cleaned_text = clean_header_lines(fixed_text)
                
                # Track page for this text
                start_idx = len(full_text)
                full_text += cleaned_text + "\n\n"
                page_markers[start_idx] = page_num + 1
        
        # Second pass: split by فصل and ماده
        # Pattern for فصل
        fasls = re.split(r'(فصل\s*\d+\s*[:\s-])', full_text)
        
        current_page = 1
        for i, section in enumerate(fasls):
            if not section.strip():
                continue
            
            # Check if this is a فصل header
            if re.match(r'فصل\s*\d+', section):
                continue
            
            # Split by ماده
            maddehs = re.split(r'(ماده\s*\d+\s*[-–])', section)
            
            for j, maddeh_section in enumerate(maddehs):
                if not maddeh_section.strip():
                    continue
                
                # Skip ماده headers
                if re.match(r'ماده\s*\d+', maddeh_section) and len(maddeh_section) < 20:
                    continue
                
                # Combine ماده header with its content
                text_content = maddeh_section.strip()
                
                # Skip very short sections
                if len(text_content) < 100:
                    continue
                
                # Find page number
                for start_idx in sorted(page_markers.keys(), reverse=True):
                    if start_idx <= full_text.find(text_content[:50]):
                        current_page = page_markers[start_idx]
                        break
                
                # Extract ماده number if exists
                maddeh_match = re.search(r'ماده\s*(\d+)', text_content[:100])
                maddeh_num = maddeh_match.group(1) if maddeh_match else None
                
                # Extract فصل number if exists
                fasl_match = re.search(r'فصل\s*(\d+)', text_content[:100])
                fasl_num = fasl_match.group(1) if fasl_match else None
                
                # Create chunk with meaningful metadata (avoid None values)
                meta = {
                    'page': current_page,
                    'source': 'pdf_text',
                    'filename': 'takallo.pdf',
                    'type': 'contract_clause'
                }
                if maddeh_num:
                    meta['maddeh'] = maddeh_num
                if fasl_num:
                    meta['fasl'] = fasl_num
                
                chunks.append({
                    'text': text_content[:2000],
                    'metadata': meta
                })
        
        # If we got very few chunks, fall back to page-based chunking
        if len(chunks) < 50:
            print("   ⚠️ Few structured chunks found, using page-based chunking...")
            chunks = []
            
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    fixed_text = fix_rtl_text(text)
                    cleaned_text = clean_header_lines(fixed_text)
                    
                    if len(cleaned_text.strip()) > 100:
                        chunks.append({
                            'text': cleaned_text.strip()[:2000],
                            'metadata': {
                                'page': page_num + 1,
                                'source': 'pdf_text',
                                'filename': 'takallo.pdf',
                                'type': 'text_content'
                            }
                        })
    
    return chunks


async def reprocess_takallo():
    """پردازش مجدد با chunks بهتر"""
    from services.persian_embedding_service import PersianEmbeddingClient
    
    print("="*100)
    print("🔄 REPROCESSING TAKALLO.PDF V3 - Better Chunking")
    print("="*100)
    
    # 1. استخراج
    print("\n📝 Step 1: Extracting meaningful chunks...")
    chunks = extract_meaningful_chunks("takallo.pdf")
    print(f"   ✅ Created {len(chunks)} chunks")
    
    # نمایش نمونه
    print("\n📖 Sample chunks:")
    for i in [0, len(chunks)//2, len(chunks)-1]:
        if i < len(chunks):
            c = chunks[i]
            print(f"\n--- Chunk {i} (Page {c['metadata'].get('page')}) ---")
            print(f"Maddeh: {c['metadata'].get('maddeh')}, Fasl: {c['metadata'].get('fasl')}")
            print(c['text'][:200])
    
    # 2. Embeddings
    print("\n🔢 Step 2: Generating embeddings...")
    embedding_client = PersianEmbeddingClient()
    documents = [c['text'] for c in chunks]
    embeddings = await embedding_client.generate_embeddings(documents)
    print(f"   ✅ Generated {len(embeddings)} embeddings")
    
    # 3. Store
    print("\n💾 Step 3: Storing in ChromaDB...")
    client = chromadb.PersistentClient(path="./chroma_db_ultimate")
    
    try:
        client.delete_collection("takallo")
        print("   ⚠️ Deleted old collection")
    except:
        pass
    
    collection = client.create_collection(
        name="takallo",
        metadata={
            "hnsw:space": "cosine",
            "domain_type": "technical",
            "domain_confidence": "0.95",
            "domain_method": "manual",
            "document_summary": """سند شرایط عمومی پیمان EPC برای کارهای صنعتی.

فصل 1: تعریف‌ها و تفسیرها (ماده 1-3)
فصل 2: تعهدات کارفرما  
فصل 3: اسناد پیمان (ماده 4)
فصل 4: تعهدات مشترک
فصل 5: تعهدات پیمانکار (ماده 24-39)
فصل 6: هماهنگی با سایر پیمانکاران (ماده 38)
فصل 7: پرداخت‌ها
فصل 8: تغییرات
فصل 9: تحویل موقت و قطعی (ماده 61-66)
فصل 10: تعلیق، خاتمه و فسخ
فصل 11: حل اختلاف""",
            "domain_keywords": '["پیمان", "EPC", "کارفرما", "پیمانکار", "ماده", "فصل", "تعهدات", "پرداخت", "تحویل", "فسخ"]'
        }
    )
    
    metadatas = [c['metadata'] for c in chunks]
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    
    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )
    
    print(f"   ✅ Stored {len(chunks)} chunks")
    
    print("\n" + "="*100)
    print("✅ COMPLETE!")
    print("="*100)


if __name__ == "__main__":
    asyncio.run(reprocess_takallo())

