"""
Fix script for zavabet collection data quality issues:
1. Fix digit reversal: "19 (نودویک)" → "91 (نودویک)" in 12 chunks
2. Update article metadata for EPC/PC Article 65 suspension content chunks
3. Re-generate embeddings for modified chunks
"""

import chromadb
from sentence_transformers import SentenceTransformer
import re

# ===== Configuration =====
CHROMA_DB_PATH = '/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db'
EMBEDDING_MODEL = 'heydariAI/persian-embeddings'
COLLECTION_NAME = 'zavabet'

# Chunks that need article metadata update to "ماده 65"
# These contain Article 65 suspension limit content but are labeled "تبصره"
ARTICLE_65_CHUNKS = {
    'zavabet_314': ('epc', 'ماده 65 - تعلیق کارها (65-1)'),  # Contains: "زیربند 65-1-1 مدت تعلیق را درمجموع تا سقف 91 روز"
    'zavabet_316': ('epc', 'ماده 65 - تعلیق کارها (65-1)'),  # Contains: "مجموعًا حداکثر برای مدت 91 روز صادرکند"
    'zavabet_791': ('pc',  'ماده 65 - تعلیق کارها (65-1)'),  # PC equivalent of zavabet_314
    'zavabet_793': ('pc',  'ماده 65 - تعلیق کارها (65-1)'),  # PC equivalent of zavabet_316
}

def main():
    print("Loading ChromaDB...")
    client = chromadb.PersistentClient(CHROMA_DB_PATH)
    col = client.get_collection(COLLECTION_NAME)

    print(f"Loading embedding model: {EMBEDDING_MODEL}...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    
    # Get all documents
    all_docs = col.get(include=['documents', 'metadatas', 'embeddings'])
    total = len(all_docs['ids'])
    print(f"Total chunks: {total}")
    
    # ===== Step 1: Fix digit reversals =====
    print("\n" + "="*60)
    print("STEP 1: Fixing digit reversals '19 (نودویک)' → '91 (نودویک)'")
    print("="*60)
    
    fixed_ids = []
    fixed_texts = []
    fixed_metadatas = []
    
    for doc_id, doc, meta in zip(all_docs['ids'], all_docs['documents'], all_docs['metadatas']):
        if '19 (نودویک)' in doc:
            new_doc = doc.replace('19 (نودویک)', '91 (نودویک)')
            count = doc.count('19 (نودویک)')
            print(f"  Fixing [{doc_id}] - {count} occurrence(s)")
            print(f"    article={meta.get('article')} page={meta.get('page')} doc_type={meta.get('doc_type')}")
            
            # Show what changed
            for line in doc.split('\n'):
                if '19 (نودویک)' in line:
                    print(f"    BEFORE: {line.strip()}")
                    print(f"    AFTER:  {line.replace('19 (نودویک)', '91 (نودویک)').strip()}")
            
            # Collect for batch update
            new_meta = meta.copy() if meta else {}
            
            # Also fix article metadata if needed
            if doc_id in ARTICLE_65_CHUNKS:
                expected_doc_type, new_article = ARTICLE_65_CHUNKS[doc_id]
                new_meta['article'] = new_article
                print(f"    → Also updating article metadata: '{meta.get('article')}' → '{new_article}'")
            
            fixed_ids.append(doc_id)
            fixed_texts.append(new_doc)
            fixed_metadatas.append(new_meta)
    
    # ===== Step 2: Fix article metadata ONLY for chunks not already processed =====
    print("\n" + "="*60)
    print("STEP 2: Fixing article metadata for Article 65 chunks")
    print("="*60)
    
    for doc_id, (expected_doc_type, new_article) in ARTICLE_65_CHUNKS.items():
        if doc_id not in fixed_ids:  # Not already in the list
            # Find this chunk
            for orig_id, orig_doc, orig_meta in zip(all_docs['ids'], all_docs['documents'], all_docs['metadatas']):
                if orig_id == doc_id:
                    old_article = orig_meta.get('article', '')
                    if old_article != new_article:
                        new_meta = orig_meta.copy() if orig_meta else {}
                        new_meta['article'] = new_article
                        print(f"  Updating [{doc_id}]:")
                        print(f"    '{old_article}' → '{new_article}'")
                        fixed_ids.append(doc_id)
                        fixed_texts.append(orig_doc)
                        fixed_metadatas.append(new_meta)
                    break
    
    if not fixed_ids:
        print("No changes needed!")
        return
    
    print(f"\nTotal chunks to update: {len(fixed_ids)}")
    
    # ===== Step 3: Re-generate embeddings =====
    print("\n" + "="*60)
    print(f"STEP 3: Re-generating embeddings for {len(fixed_ids)} chunks")
    print("="*60)
    
    print("  Encoding texts...")
    new_embeddings = model.encode(fixed_texts, batch_size=16, show_progress_bar=True).tolist()
    print(f"  Generated {len(new_embeddings)} embeddings (dim={len(new_embeddings[0])})")
    
    # ===== Step 4: Update ChromaDB =====
    print("\n" + "="*60)
    print("STEP 4: Updating ChromaDB")
    print("="*60)
    
    col.update(
        ids=fixed_ids,
        documents=fixed_texts,
        metadatas=fixed_metadatas,
        embeddings=new_embeddings
    )
    
    print(f"  ✅ Updated {len(fixed_ids)} chunks successfully!")
    
    # ===== Verify =====
    print("\n" + "="*60)
    print("STEP 5: Verification")
    print("="*60)
    
    # Check if fixes applied
    verify = col.get(ids=fixed_ids, include=['documents', 'metadatas'])
    for v_id, v_doc, v_meta in zip(verify['ids'], verify['documents'], verify['metadatas']):
        has_old = '19 (نودویک)' in v_doc
        has_new = '91 (نودویک)' in v_doc
        article = v_meta.get('article', '')
        print(f"  [{v_id}] has_old={has_old}, has_new={has_new}, article='{article}'")
    
    print("\n✅ All fixes applied successfully!")

if __name__ == '__main__':
    main()
