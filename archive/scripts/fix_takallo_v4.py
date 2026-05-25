# -*- coding: utf-8 -*-
"""
پردازش نهایی takallo.pdf با cleaning بهتر
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
            continue
        
        reversed_line = line[::-1]
        
        # Fix English words
        def fix_english(match):
            return match.group(0)[::-1]
        
        # Fix numbers
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
        '\u064A': '\u06CC',
        '\u0643': '\u06A9',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text


def is_noise_line(line):
    """تشخیص خطوط نویز (header/footer)"""
    line = line.strip()
    
    # Empty or very short
    if not line or len(line) < 5:
        return True
    
    # Page numbers
    if re.match(r'^صفحه\s*\d+', line) or re.match(r'^\d+\s*صفحه', line):
        return True
    
    # Headers like "برای کارهای صنعتی صفحه X"
    if 'برای کارهای صنعتی صفحه' in line:
        return True
    
    # Fragmented letters (like "م C س ا P ن E")
    if re.match(r'^[A-Za-z\s\u0600-\u06FF]{1,3}(\s+[A-Za-z\s\u0600-\u06FF]{1,3})+$', line):
        return True
    
    # Single letters with spaces
    if len(line) < 10 and len(line.split()) > 3:
        return True
    
    # Lines that are just dots
    if re.match(r'^[\.\s]+$', line):
        return True
    
    # Table of contents pattern (ماده X - موضوع ...)
    if re.match(r'^ماده\s*\d+\s*-\s*\w+\s*\.{5,}', line):
        return True
    
    # Header pattern with page number
    if re.match(r'.*صفحه\s*\d+\s*$', line):
        return True
    
    return False


def is_toc_page(text):
    """تشخیص صفحات فهرست مطالب"""
    lines = text.split('\n')
    dot_lines = sum(1 for line in lines if '.....' in line)
    return dot_lines > 5  # If more than 5 lines have dots, it's probably TOC


def clean_text(text):
    """تمیز کردن متن از نویز"""
    lines = text.split('\n')
    clean_lines = []
    
    for line in lines:
        if not is_noise_line(line):
            clean_lines.append(line)
    
    return '\n'.join(clean_lines)


def extract_chunks(pdf_path):
    """استخراج chunks با متن تمیز"""
    chunks = []
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"📄 Processing {len(pdf.pages)} pages...")
        
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            
            # Skip TOC pages
            if is_toc_page(text):
                print(f"   Skipping page {page_num + 1} (TOC)")
                continue
            
            # Fix RTL
            fixed_text = fix_rtl_text(text)
            
            # Normalize Persian
            normalized_text = normalize_persian_text(fixed_text)
            
            # Clean noise
            cleaned_text = clean_text(normalized_text)
            
            # Skip if too short after cleaning
            if len(cleaned_text.strip()) < 100:
                continue
            
            # Create chunk
            chunks.append({
                'text': cleaned_text.strip(),
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
    print("🔄 REPROCESSING TAKALLO.PDF - Version 4 with Better Cleaning")
    print("="*80)
    
    # 1. Extract chunks
    print("\n📝 Step 1: Extracting and cleaning text...")
    chunks = extract_chunks("takallo.pdf")
    print(f"   ✅ Created {len(chunks)} chunks")
    
    # Show samples
    print("\n📖 Sample chunks:")
    for i in [0, len(chunks)//2, len(chunks)-1]:
        if i < len(chunks):
            c = chunks[i]
            print(f"\n--- Chunk {i} (Page {c['metadata'].get('page')}) ---")
            print(c['text'][:300])
    
    # 2. Generate embeddings
    print("\n🔢 Step 2: Generating embeddings...")
    embedding_client = PersianEmbeddingClient()
    documents = [c['text'] for c in chunks]
    
    batch_size = 50
    all_embeddings = []
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]
        print(f"   Processing batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}...")
        batch_embeddings = await embedding_client.generate_embeddings(batch)
        all_embeddings.extend(batch_embeddings)
    
    print(f"   ✅ Generated {len(all_embeddings)} embeddings")
    
    # 3. Store in ChromaDB
    print("\n💾 Step 3: Storing in ChromaDB...")
    client = chromadb.PersistentClient(
        path="/home/user01/qwen-api/enhanced_rag_system/chroma_db_ultimate",
        settings=Settings(anonymized_telemetry=False)
    )
    
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

این سند شامل موارد زیر است:
- تعریف‌ها و اصطلاحات (ماده 1)
- موضوع پیمان و اسناد (ماده 2-4)
- تاریخ شروع و مدت پیمان (ماده 5)
- تعهدات پیمانکار و کارفرما
- پرداخت‌ها و تضمین‌ها
- تغییرات کار و تمدید مدت
- تحویل موقت و قطعی
- فسخ و خاتمه پیمان
- حل اختلاف""",
            "domain_keywords": '["پیمان", "EPC", "کارفرما", "پیمانکار", "ماده", "تعهدات", "پرداخت", "تحویل", "فسخ", "مدت"]'
        }
    )
    
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
    test_queries = [
        "مدت پیمان چقدر است؟",
        "EPC چیست؟",
        "تعهدات کارفرما چیست؟"
    ]
    
    for query in test_queries:
        query_embedding = await embedding_client.generate_embedding(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=2,
            include=["documents", "distances"]
        )
        
        print(f"\n📌 Query: {query}")
        for i, (doc, dist) in enumerate(zip(results['documents'][0], results['distances'][0])):
            sim = 1 - dist
            print(f"   Result {i+1} (sim: {sim:.4f}): {doc[:100]}...")
    
    print("\n" + "="*80)
    print("✅ COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())

