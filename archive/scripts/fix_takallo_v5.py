# -*- coding: utf-8 -*-
"""
پردازش نهایی takallo.pdf با chunks کوچکتر و بدون noise
"""

import sys
sys.path.insert(0, '/home/user01/qwen-api/enhanced_rag_system')
import asyncio
import pdfplumber
import re
import chromadb
from chromadb.config import Settings


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
        fixed_line = re.sub(r'[A-Za-z]+', lambda m: m.group(0)[::-1], reversed_line)
        fixed_line = re.sub(r'\d+', lambda m: m.group(0)[::-1], fixed_line)
        fixed_lines.append(fixed_line)
    return '\n'.join(fixed_lines)


def is_noise_line(line):
    """تشخیص خطوط نویز"""
    line = line.strip()
    if not line or len(line) < 5:
        return True
    
    # Page number patterns
    if re.match(r'.*صفحه\s*\d+', line):
        return True
    if re.match(r'^\d+\s*صفحه', line):
        return True
    
    # Header patterns
    if 'برای کارهای صنعتی' in line and len(line) < 50:
        return True
    
    # Fragmented letters like "C C P P E E" or "م C س ا P ن E"
    if re.match(r'^[A-Za-z\s]+$', line):
        return True
    if re.match(r'^[A-Za-z\s\u0600-\u06FF]{1,3}(\s+[A-Za-z\s\u0600-\u06FF]{1,3})+$', line):
        return True
    
    # Common header
    if line.startswith('شرایط عمومی پیمان طراحی') and len(line) < 60:
        return True
    if line.startswith('موافقتنامه پیمان طراحی') and len(line) < 60:
        return True
    if line.startswith('پیوستهای پیمان طراحی') and len(line) < 60:
        return True
    
    # Single/double letter lines
    if len(line) < 4:
        return True
    
    # Lines that are just dots
    if re.match(r'^[\.\s…]+$', line):
        return True
    
    return False


def is_toc_page(text):
    """تشخیص صفحات فهرست مطالب"""
    lines = text.split('\n')
    dot_lines = sum(1 for line in lines if '.....' in line or '...' in line)
    return dot_lines > 5


def split_into_paragraphs(text, max_chars=500, min_chars=100):
    """تقسیم متن به پاراگراف‌های کوچکتر"""
    paragraphs = []
    
    # Split by ماده or فصل
    sections = re.split(r'((?:ماده|فصل)\s*\d+\s*[-–:]\s*)', text)
    
    current = ""
    for section in sections:
        if re.match(r'(?:ماده|فصل)\s*\d+', section):
            if current.strip() and len(current.strip()) >= min_chars:
                paragraphs.append(current.strip())
            current = section
        else:
            current += section
            
            # If too long, split
            while len(current) > max_chars:
                # Find a good break point
                break_point = current.rfind('.\n', 0, max_chars)
                if break_point == -1:
                    break_point = current.rfind('\n', 0, max_chars)
                if break_point == -1:
                    break_point = max_chars
                
                chunk = current[:break_point].strip()
                if len(chunk) >= min_chars:
                    paragraphs.append(chunk)
                current = current[break_point:].strip()
    
    if current.strip() and len(current.strip()) >= min_chars:
        paragraphs.append(current.strip())
    
    return paragraphs


def extract_chunks(pdf_path):
    """استخراج chunks کوچک و تمیز"""
    chunks = []
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"📄 Processing {len(pdf.pages)} pages...")
        
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            
            # Skip TOC pages
            if is_toc_page(text):
                continue
            
            # Fix RTL
            fixed_text = fix_rtl_text(text)
            
            # Remove noise lines
            clean_lines = [l for l in fixed_text.split('\n') if not is_noise_line(l)]
            clean_text = '\n'.join(clean_lines)
            
            # Split into paragraphs
            paragraphs = split_into_paragraphs(clean_text)
            
            for para in paragraphs:
                if len(para) >= 100:
                    chunks.append({
                        'text': para,
                        'page': page_num + 1
                    })
    
    return chunks


async def main():
    from services.persian_embedding_service import PersianEmbeddingClient
    
    print("="*80)
    print("🔄 REPROCESSING TAKALLO.PDF - V5 with Small Chunks")
    print("="*80)
    
    # 1. Extract
    print("\n📝 Step 1: Extracting text...")
    chunks = extract_chunks("takallo.pdf")
    print(f"   ✅ Created {len(chunks)} chunks")
    
    # Show samples
    print("\n📖 Sample chunks:")
    for i, c in enumerate(chunks[:5]):
        print(f"\n--- Chunk {i} (Page {c['page']}) ---")
        print(c['text'][:200])
    
    # 2. Generate embeddings
    print("\n🔢 Step 2: Generating embeddings...")
    embed_client = PersianEmbeddingClient()
    documents = [c['text'] for c in chunks]
    
    batch_size = 50
    all_embeddings = []
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]
        print(f"   Batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}...")
        batch_embeddings = await embed_client.generate_embeddings(batch)
        all_embeddings.extend(batch_embeddings)
    
    print(f"   ✅ Generated {len(all_embeddings)} embeddings")
    
    # 3. Store
    print("\n💾 Step 3: Storing in ChromaDB...")
    client = chromadb.PersistentClient(
        path="/home/user01/qwen-api/enhanced_rag_system/chroma_db_ultimate",
        settings=Settings(anonymized_telemetry=False)
    )
    
    try:
        client.delete_collection("takallo")
    except:
        pass
    
    collection = client.create_collection(
        name="takallo",
        metadata={
            "hnsw:space": "cosine",
            "domain_type": "technical",
            "domain_confidence": "0.95",
            "document_summary": "سند شرایط عمومی پیمان EPC برای کارهای صنعتی"
        }
    )
    
    metadatas = [{'page': c['page'], 'source': 'pdf'} for c in chunks]
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    
    collection.add(
        documents=documents,
        embeddings=all_embeddings,
        metadatas=metadatas,
        ids=ids
    )
    
    print(f"   ✅ Stored {len(chunks)} chunks")
    
    # 4. Test
    print("\n🧪 Step 4: Testing retrieval...")
    test_queries = [
        "مدت پیمان چقدر است؟",
        "EPC چیست؟",
        "تعهدات کارفرما چیست؟",
        "نحوه فسخ پیمان چگونه است؟"
    ]
    
    for query in test_queries:
        query_embedding = await embed_client.generate_embedding(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
            include=["documents", "distances"]
        )
        
        print(f"\n📌 Query: {query}")
        for i, (doc, dist) in enumerate(zip(results['documents'][0][:2], results['distances'][0][:2])):
            sim = 1 - dist
            print(f"   {i+1}. (sim: {sim:.3f}) {doc[:80]}...")
    
    print("\n" + "="*80)
    print("✅ COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())

