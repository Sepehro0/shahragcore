# -*- coding: utf-8 -*-
"""
پردازش نهایی takallo.pdf با embedding های صحیح
"""

import asyncio
import pdfplumber
import re
import chromadb
from chromadb.config import Settings
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


def normalize_persian_text(text):
    """نرمال‌سازی کاراکترهای فارسی/عربی"""
    if not text:
        return ""
    
    # Replace Arabic characters with Persian equivalents
    replacements = {
        'ك': 'ک',
        'ي': 'ی',
        'ﮐ': 'ک',
        'ﯾ': 'ی',
        'ﯽ': 'ی',
        '\u064A': '\u06CC',  # Arabic YEH to Persian YEH
        '\u0643': '\u06A9',  # Arabic KAF to Persian KAF
        'ﺗ': 'ت',
        'ﺴ': 'س',
        'ﺖ': 'ت',
        'ﺲ': 'س',
        'ﻨ': 'ن',
        'ﻪ': 'ه',
        'ﻪ': 'ه',
        'ﯽ': 'ی',
        'ﺪ': 'د',
        'ﺮ': 'ر',
        'ﺲ': 'س',
        'ﺎ': 'ا',
        'ﺴ': 'س',
        'ﻻ': 'لا',
        'ﻮ': 'و',
        'ﻟ': 'ل',
        'ﻊ': 'ع',
        'ﺑ': 'ب',
        'ﻬ': 'ه',
        'ﺺ': 'ص',
        'ﻼ': 'لا',
        'ﻢ': 'م',
        'ﻌ': 'ع',
        'ﺐ': 'ب',
        'ﻘ': 'ق',
        'ﺗ': 'ت',
        'ﺜ': 'ث',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text


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
    ]
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Skip very short lines (single chars)
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


def extract_chunks(pdf_path):
    """استخراج chunks با متن نرمال‌سازی شده"""
    chunks = []
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"📄 Processing {len(pdf.pages)} pages...")
        
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                # Fix RTL
                fixed_text = fix_rtl_text(text)
                # Normalize Persian characters
                normalized_text = normalize_persian_text(fixed_text)
                # Clean headers
                cleaned_text = clean_header_lines(normalized_text)
                
                if len(cleaned_text.strip()) > 50:
                    # Split into smaller chunks for better retrieval
                    paragraphs = cleaned_text.split('\n\n')
                    
                    current_chunk = ""
                    for para in paragraphs:
                        if len(current_chunk) + len(para) < 1000:
                            current_chunk += para + "\n\n"
                        else:
                            if current_chunk.strip():
                                chunks.append({
                                    'text': current_chunk.strip(),
                                    'metadata': {
                                        'page': page_num + 1,
                                        'source': 'pdf_text',
                                        'filename': 'takallo.pdf',
                                        'type': 'contract_clause'
                                    }
                                })
                            current_chunk = para + "\n\n"
                    
                    # Add remaining text
                    if current_chunk.strip():
                        chunks.append({
                            'text': current_chunk.strip(),
                            'metadata': {
                                'page': page_num + 1,
                                'source': 'pdf_text',
                                'filename': 'takallo.pdf',
                                'type': 'contract_clause'
                            }
                        })
    
    return chunks


async def main():
    """پردازش اصلی"""
    from services.persian_embedding_service import PersianEmbeddingClient
    
    print("="*80)
    print("🔄 REPROCESSING TAKALLO.PDF - Final Version with Correct Embeddings")
    print("="*80)
    
    # 1. Extract chunks
    print("\n📝 Step 1: Extracting and normalizing text...")
    chunks = extract_chunks("takallo.pdf")
    print(f"   ✅ Created {len(chunks)} chunks")
    
    # Show samples
    print("\n📖 Sample chunks:")
    for i in [0, len(chunks)//2, len(chunks)-1]:
        if i < len(chunks):
            c = chunks[i]
            print(f"\n--- Chunk {i} (Page {c['metadata'].get('page')}) ---")
            print(c['text'][:200])
    
    # 2. Generate embeddings with Persian Embedding Service
    print("\n🔢 Step 2: Generating embeddings with PersianEmbeddingClient...")
    embedding_client = PersianEmbeddingClient()
    documents = [c['text'] for c in chunks]
    
    # Generate embeddings in batches
    batch_size = 50
    all_embeddings = []
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]
        print(f"   Processing batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}...")
        batch_embeddings = await embedding_client.generate_embeddings(batch)
        all_embeddings.extend(batch_embeddings)
    
    print(f"   ✅ Generated {len(all_embeddings)} embeddings (dim: {len(all_embeddings[0])})")
    
    # 3. Store in ChromaDB
    print("\n💾 Step 3: Storing in ChromaDB...")
    client = chromadb.PersistentClient(
        path="/home/user01/qwen-api/enhanced_rag_system/chroma_db_ultimate",
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Delete old collection
    try:
        client.delete_collection("takallo")
        print("   ⚠️ Deleted old collection")
    except:
        pass
    
    # Create new collection
    collection = client.create_collection(
        name="takallo",
        metadata={
            "hnsw:space": "cosine",
            "domain_type": "technical",
            "domain_confidence": "0.95",
            "domain_method": "manual",
            "document_summary": """سند شرایط عمومی پیمان EPC برای کارهای صنعتی.

موضوعات اصلی:
- تعریف‌ها و تفسیرها
- تعهدات کارفرما و پیمانکار
- مبلغ پیمان و پرداخت‌ها
- تاریخ شروع، مدت پیمان و تحویل
- تضمین‌ها و بیمه‌نامه‌ها
- تغییرات و اصلاحیه‌ها
- تعلیق، فسخ و خاتمه پیمان
- حل اختلاف""",
            "domain_keywords": '["پیمان", "EPC", "کارفرما", "پیمانکار", "ماده", "تعهدات", "پرداخت", "تحویل", "فسخ", "مدت"]'
        }
    )
    
    # Store chunks with embeddings
    metadatas = [c['metadata'] for c in chunks]
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    
    collection.add(
        documents=documents,
        embeddings=all_embeddings,
        metadatas=metadatas,
        ids=ids
    )
    
    print(f"   ✅ Stored {len(chunks)} chunks")
    
    # 4. Test retrieval
    print("\n🧪 Step 4: Testing retrieval...")
    test_query = "مدت پیمان چقدر است؟"
    query_embedding = await embedding_client.generate_embedding(test_query)
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3,
        include=["documents", "metadatas", "distances"]
    )
    
    print(f"\nQuery: {test_query}")
    print("Top results:")
    for i, (doc, meta, dist) in enumerate(zip(results['documents'][0], results['metadatas'][0], results['distances'][0])):
        sim = 1 - dist  # Convert distance to similarity
        print(f"\n--- Result {i+1} (similarity: {sim:.4f}) ---")
        print(f"Page: {meta.get('page')}")
        print(f"Text: {doc[:200]}...")
    
    print("\n" + "="*80)
    print("✅ COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())

