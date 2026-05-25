#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بازسازی Collection budget_financial
"""

import chromadb
import pandas as pd
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import sys

def rebuild_budget_financial():
    """بازسازی collection budget_financial با embedding dimension 384"""
    
    print("="*80)
    print("🔧 بازسازی Collection budget_financial")
    print("="*80)
    
    # 1. Initialize
    print("\n📦 Initializing...")
    client = chromadb.PersistentClient(path="chroma_db")
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
    print(f"   Model dimension: {model.get_sentence_embedding_dimension()}")
    
    # 2. Delete old collection
    print("\n🗑️  Deleting old collection...")
    try:
        client.delete_collection("budget_financial")
        print("   ✅ Old collection deleted")
    except Exception as e:
        print(f"   ⚠️  No old collection to delete: {e}")
    
    # 3. Create new collection
    print("\n🆕 Creating new collection...")
    collection = client.create_collection(
        name="budget_financial",
        metadata={"description": "Budget and Financial Data - Rebuilt with dimension 384"}
    )
    print("   ✅ Collection created")
    
    # 4. Process masaref2.xlsx
    print("\n📊 Processing masaref2.xlsx (مصارف - هزینه‌ها)...")
    try:
        df_masaref = pd.read_excel('archive/data_files/masaref2.xlsx')
        # Clean column names
        df_masaref.columns = df_masaref.columns.str.strip()
        print(f"   Loaded {len(df_masaref)} rows")
        
        doc_count = 0
        for idx, row in tqdm(df_masaref.iterrows(), total=len(df_masaref), desc="   Processing"):
            try:
                # ساخت متن
                text = f"""دستگاه اجرایی: {row['عنوان دستگاه اجرايي']}
دستگاه اصلی: {row['عنوان دستگاه اصلي']}
سال: {row['سال']}

اعتبارات هزینه‌ای:
- عمومی: {row['براورد اعتبارات هزینه ای - عمومی']} میلیون ریال
- متفرقه: {row['برآورد اعتبارات هزینه ای - متفرقه']} میلیون ریال
- اختصاصی: {row['براورد اعتبارات هزینه ای - اختصاصی']} میلیون ریال
- جمع: {row['جمع براورد اعتبارات هزینه ای']} میلیون ریال

تملک دارایی سرمایه‌ای:
- عمومی: {row['براورد تملك دارايي هاي سرمايه اي - عمومی']} میلیون ریال
- متفرقه: {row['براورد تملك دارايي هاي سرمايه اي - متفرقه']} میلیون ریال
- جمع: {row['جمع برآورد تملك دارايي هاي سرمايه اي']} میلیون ریال

جمع کل بودجه: {row['جمع كل']} میلیون ریال"""
                
                # ساخت metadata
                metadata = {
                    'دستگاه_اجرایی': str(row['عنوان دستگاه اجرايي']).strip(),
                    'دستگاه_اصلی': str(row['عنوان دستگاه اصلي']).strip(),
                    'سال': str(int(row['سال'])),
                    'جمع_کل': str(row['جمع كل']),
                    'type': 'masaref',
                    'source': 'masaref2.xlsx',
                    'table': 'مصارف'
                }
                
                # Generate embedding
                embedding = model.encode(text)
                
                # Add to collection
                collection.add(
                    documents=[text],
                    metadatas=[metadata],
                    embeddings=[embedding.tolist()],
                    ids=[f"masaref_{idx}"]
                )
                doc_count += 1
                
            except Exception as e:
                print(f"\n   ⚠️  Error processing row {idx}: {e}")
                continue
        
        print(f"   ✅ Added {doc_count} documents from masaref2.xlsx")
        
    except Exception as e:
        print(f"   ❌ Error loading masaref2.xlsx: {e}")
        return False
    
    # 5. Process manabe.xlsx
    print("\n📊 Processing manabe.xlsx (منابع - درآمدها)...")
    try:
        df_manabe = pd.read_excel('archive/data_files/manabe.xlsx')
        # Clean column names
        df_manabe.columns = df_manabe.columns.str.strip()
        print(f"   Loaded {len(df_manabe)} rows")
        
        doc_count = 0
        for idx, row in tqdm(df_manabe.iterrows(), total=len(df_manabe), desc="   Processing"):
            try:
                # ساخت متن
                text = f"""دستگاه اجرایی: {row['عنوان دستگاه اجرایی']}
دستگاه اصلی: {row['عنوان دستگاه اصلی']}
سال: {row['سال']}

قسمت: {row['عنوان قسمت']}
بخش: {row['عنوان بخش']}
بند: {row['عنوان بند']}
جزء: {row['عنوان جزء']}

درآمد عمومی:
- ملی: {row['در آمد عمومي ملي']} میلیون ریال
- استانی: {row['در آمد عمومي استاني']} میلیون ریال
- جمع: {row['جمع در آمد عمومي']} میلیون ریال

درآمد اختصاصی:
- ملی: {row['در آمد اختصاصي ملي']} میلیون ریال
- استانی: {row['در آمد اختصاصي استاني']} میلیون ریال
- جمع: {row['جمع در آمد اختصاصي']} میلیون ریال

جمع کل درآمد: {row['جمع کل']} میلیون ریال"""
                
                # ساخت metadata
                metadata = {
                    'دستگاه_اجرایی': str(row['عنوان دستگاه اجرایی']).strip(),
                    'دستگاه_اصلی': str(row['عنوان دستگاه اصلی']).strip(),
                    'سال': str(int(row['سال'])),
                    'جمع_کل': str(row['جمع کل']),
                    'type': 'manabe',
                    'source': 'manabe.xlsx',
                    'table': 'منابع',
                    'قسمت': str(row['عنوان قسمت']).strip(),
                    'بخش': str(row['عنوان بخش']).strip()
                }
                
                # Generate embedding
                embedding = model.encode(text)
                
                # Add to collection
                collection.add(
                    documents=[text],
                    metadatas=[metadata],
                    embeddings=[embedding.tolist()],
                    ids=[f"manabe_{idx}"]
                )
                doc_count += 1
                
            except Exception as e:
                print(f"\n   ⚠️  Error processing row {idx}: {e}")
                continue
        
        print(f"   ✅ Added {doc_count} documents from manabe.xlsx")
        
    except Exception as e:
        print(f"   ❌ Error loading manabe.xlsx: {e}")
        return False
    
    # 6. Verify
    print("\n✅ Collection rebuilt successfully!")
    print(f"   Total documents: {collection.count()}")
    
    # Test query
    print("\n🧪 Testing collection...")
    try:
        results = collection.query(
            query_texts=["بودجه نهاد ریاست جمهوری در سال 1403"],
            n_results=3
        )
        
        if results['ids'][0]:
            print(f"   ✅ Query successful! Found {len(results['ids'][0])} results")
            for i, (distance, metadata) in enumerate(zip(results['distances'][0], results['metadatas'][0])):
                score = 1 - distance
                print(f"      {i+1}. Score: {score:.3f}, دستگاه: {metadata.get('دستگاه_اجرایی', 'N/A')}")
        else:
            print("   ⚠️  No results found")
    except Exception as e:
        print(f"   ❌ Test query failed: {e}")
        return False
    
    print("\n" + "="*80)
    print("🎉 بازسازی با موفقیت انجام شد!")
    print("="*80)
    return True

if __name__ == "__main__":
    success = rebuild_budget_financial()
    sys.exit(0 if success else 1)

