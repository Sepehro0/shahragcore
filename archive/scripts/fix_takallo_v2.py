# -*- coding: utf-8 -*-
"""
پردازش صحیح takallo.pdf با RTL Fix بهبود یافته - نسخه 2
"""

import asyncio
import pdfplumber
import re
import chromadb
import sys
sys.path.insert(0, '/home/user01/qwen-api/enhanced_rag_system')


def fix_rtl_text(text):
    """
    تبدیل متن visual-order به logical-order
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
        
        # اصلاح کلمات انگلیسی
        def fix_english(match):
            return match.group(0)[::-1]
        
        # اصلاح اعداد
        def fix_numbers(match):
            return match.group(0)[::-1]
        
        fixed_line = re.sub(r'[A-Za-z]+', fix_english, reversed_line)
        fixed_line = re.sub(r'\d+', fix_numbers, fixed_line)
        
        fixed_lines.append(fixed_line)
    
    return '\n'.join(fixed_lines)


def extract_pdf_with_rtl_fix(pdf_path):
    """استخراج متن با RTL fix"""
    chunks = []
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"📄 Processing {len(pdf.pages)} pages...")
        
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            
            if text and text.strip():
                # اعمال RTL fix
                fixed_text = fix_rtl_text(text)
                
                # تقسیم به chunks بر اساس پاراگراف
                paragraphs = fixed_text.split('\n\n')
                current_chunk = ""
                
                for para in paragraphs:
                    para = para.strip()
                    if not para or len(para) < 20:
                        continue
                    
                    # حذف خطوط header تکراری
                    if 'برای کارهای صنعتی' in para and len(para) < 100:
                        continue
                    
                    if len(current_chunk) + len(para) > 600 and current_chunk:
                        if len(current_chunk.strip()) > 50:
                            chunks.append({
                                'text': current_chunk.strip(),
                                'metadata': {
                                    'page': page_num + 1,
                                    'source': 'pdf_text',
                                    'filename': 'takallo.pdf',
                                    'type': 'text_content'
                                }
                            })
                        current_chunk = para
                    else:
                        current_chunk += "\n\n" + para if current_chunk else para
                
                if current_chunk.strip() and len(current_chunk.strip()) > 50:
                    chunks.append({
                        'text': current_chunk.strip(),
                        'metadata': {
                            'page': page_num + 1,
                            'source': 'pdf_text',
                            'filename': 'takallo.pdf',
                            'type': 'text_content'
                        }
                    })
            
            if (page_num + 1) % 20 == 0:
                print(f"   Processed {page_num + 1}/{len(pdf.pages)} pages...")
    
    return chunks


async def reprocess_takallo():
    """پردازش مجدد takallo با RTL fix صحیح"""
    from services.persian_embedding_service import PersianEmbeddingClient
    
    print("="*100)
    print("🔄 REPROCESSING TAKALLO.PDF WITH CORRECT RTL FIX (V2)")
    print("="*100)
    
    # 1. استخراج متن
    print("\n📝 Step 1: Extracting text with RTL fix...")
    chunks = extract_pdf_with_rtl_fix("takallo.pdf")
    print(f"   ✅ Created {len(chunks)} chunks")
    
    # نمایش نمونه
    print("\n📖 Sample chunks:")
    for i in [0, 20, 40, 60]:
        if i < len(chunks):
            print(f"\n--- Chunk {i} (Page {chunks[i]['metadata']['page']}) ---")
            print(chunks[i]['text'][:300])
    
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
            "domain_confidence": "0.95",
            "domain_method": "manual",
            "document_summary": """سند شرایط عمومی پیمان EPC (مهندسی، طراحی، تأمین مصالح و تجهیزات، ساختمان و نصب) برای کارهای صنعتی.

این سند شامل موارد زیر است:
- فصل 1: تعریف‌ها و تفسیرها (ماده 1-3)
- فصل 2: تعهدات کارفرما (ماده 4-16)
- فصل 3: اسناد پیمان (ماده 4)
- فصل 4: تعهدات مشترک (ماده 17-23)
- فصل 5: تعهدات پیمانکار (ماده 24-39)
- فصل 6: تضمین‌ها (ماده 40-45)
- فصل 7: پرداخت‌ها (ماده 46-55)
- فصل 8: تغییرات (ماده 56-60)
- فصل 9: تحویل موقت و قطعی (ماده 61-66)
- فصل 10: تعلیق، خاتمه و فسخ (ماده 67-75)
- فصل 11: حل اختلاف (ماده 76-80)""",
            "domain_keywords": '["پیمان", "EPC", "کارفرما", "پیمانکار", "مهندسی", "طراحی", "ساختمان", "نصب", "تجهیزات", "مصالح", "ماده", "بند", "ضمانت", "تحویل", "پرداخت", "تعهدات", "مسئولیت", "فسخ", "خاتمه", "تعلیق"]'
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

