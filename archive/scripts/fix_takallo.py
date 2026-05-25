# -*- coding: utf-8 -*-
"""
پردازش صحیح takallo.pdf با RTL Fix بهبود یافته
"""

import asyncio
import fitz  # PyMuPDF
import re
import chromadb
import sys
sys.path.insert(0, '/home/user01/qwen-api/enhanced_rag_system')


def is_english_word(word):
    """بررسی اینکه آیا کلمه انگلیسی است"""
    return bool(re.match(r'^[A-Za-z0-9]+$', word))


def smart_rtl_fix(text):
    """
    RTL Fix هوشمند که:
    1. خطوط فارسی را معکوس می‌کند
    2. کلمات انگلیسی را دوباره معکوس می‌کند (تا درست بمانند)
    """
    if not text:
        return ""
    
    lines = text.split('\n')
    fixed_lines = []
    
    for line in lines:
        if not line.strip():
            fixed_lines.append(line)
            continue
        
        # معکوس کردن کل خط
        reversed_line = line[::-1]
        
        # پیدا کردن و اصلاح کلمات انگلیسی (که الان معکوس شده‌اند)
        # مثلاً CPE باید EPC بشود
        def fix_english(match):
            word = match.group(0)
            return word[::-1]  # معکوس کردن مجدد برای بازگشت به حالت اصلی
        
        # الگو برای کلمات انگلیسی معکوس شده
        fixed_line = re.sub(r'[A-Za-z][A-Za-z0-9]+', fix_english, reversed_line)
        
        fixed_lines.append(fixed_line)
    
    return '\n'.join(fixed_lines)


def extract_pdf_with_smart_fix(pdf_path):
    """استخراج متن با RTL fix هوشمند"""
    doc = fitz.open(pdf_path)
    chunks = []
    
    print(f"📄 Processing {len(doc)} pages...")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        
        if text and text.strip():
            # اعمال RTL fix هوشمند
            fixed_text = smart_rtl_fix(text)
            
            # تقسیم به chunks
            paragraphs = fixed_text.split('\n\n')
            current_chunk = ""
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                
                if len(current_chunk) + len(para) > 500 and current_chunk:
                    if len(current_chunk.strip()) > 30:
                        chunks.append({
                            'text': current_chunk.strip(),
                            'metadata': {
                                'page': page_num + 1,
                                'source': 'pdf_text_fixed',
                                'filename': 'takallo.pdf',
                                'type': 'text_content'
                            }
                        })
                    current_chunk = para
                else:
                    current_chunk += "\n\n" + para if current_chunk else para
            
            if current_chunk.strip() and len(current_chunk.strip()) > 30:
                chunks.append({
                    'text': current_chunk.strip(),
                    'metadata': {
                        'page': page_num + 1,
                        'source': 'pdf_text_fixed',
                        'filename': 'takallo.pdf',
                        'type': 'text_content'
                    }
                })
        
        if (page_num + 1) % 20 == 0:
            print(f"   Processed {page_num + 1}/{len(doc)} pages...")
    
    doc.close()
    return chunks


async def reprocess_takallo():
    """پردازش مجدد takallo با RTL fix هوشمند"""
    from services.persian_embedding_service import PersianEmbeddingClient
    
    print("="*100)
    print("🔄 REPROCESSING TAKALLO.PDF WITH SMART RTL FIX")
    print("="*100)
    
    # 1. استخراج متن با RTL fix هوشمند
    print("\n📝 Step 1: Extracting text with smart RTL fix...")
    chunks = extract_pdf_with_smart_fix("takallo.pdf")
    print(f"   ✅ Created {len(chunks)} chunks")
    
    # نمایش نمونه
    if len(chunks) > 20:
        print(f"\n📖 Sample chunk (page {chunks[20]['metadata']['page']}):")
        print("-"*60)
        print(chunks[20]['text'][:400])
        print("-"*60)
    
    # 2. Generate embeddings
    print("\n🔢 Step 2: Generating embeddings...")
    embedding_client = PersianEmbeddingClient()
    
    documents = [c['text'] for c in chunks]
    embeddings = await embedding_client.generate_embeddings(documents)
    print(f"   ✅ Generated {len(embeddings)} embeddings")
    
    # 3. Store in ChromaDB
    print("\n💾 Step 3: Storing in ChromaDB...")
    
    client = chromadb.PersistentClient(path="./chroma_db_ultimate")
    
    # حذف collection قبلی
    try:
        client.delete_collection("takallo")
        print("   ⚠️ Deleted old collection")
    except:
        pass
    
    # ایجاد collection جدید با domain info
    collection = client.create_collection(
        name="takallo",
        metadata={
            "hnsw:space": "cosine",
            "domain_type": "technical",
            "domain_confidence": "0.9",
            "domain_method": "manual",
            "document_summary": "سند شرایط عمومی و خصوصی پیمان EPC برای کارهای صنعتی - شامل موافقتنامه، شرایط عمومی، شرایط خصوصی و پیوست‌ها. این سند قرارداد پیمانکاری است که شامل وظایف کارفرما، پیمانکار، شرایط پرداخت، ضمانت‌نامه‌ها، تحویل موقت و قطعی، و سایر شرایط قانونی است.",
            "domain_keywords": '["پیمان", "EPC", "کارفرما", "پیمانکار", "مهندسی", "طراحی", "ساختمان", "نصب", "تجهیزات", "مصالح", "ماده", "بند", "ضمانت", "تحویل", "پرداخت"]'
        }
    )
    
    # ذخیره chunks
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
    print("✅ REPROCESSING COMPLETE!")
    print(f"   Collection: takallo")
    print(f"   Chunks: {len(chunks)}")
    print("="*100)


if __name__ == "__main__":
    asyncio.run(reprocess_takallo())

