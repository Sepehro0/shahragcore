# -*- coding: utf-8 -*-
"""
اسکریپت ساخت مجدد کالکشن قوانین - نسخه ساده
"""

import asyncio
import logging
import sys
import chromadb
from chromadb.config import Settings as ChromaSettings
import hashlib
import re
from datetime import datetime

sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")
from services.persian_embedding_service import PersianEmbeddingClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def rebuild_qavanin():
    """ساخت مجدد کالکشن qavanin با روش ساده"""
    
    logger.info("="*80)
    logger.info("🚀 Rebuilding Qavanin Collection")
    logger.info("="*80)
    
    # Paths
    db_path = "/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
    data_file = "/home/user01/qwen-api/enhanced_rag_system_dev/archive/data_files/qavanin_complete.txt"
    collection_name = "qavanin"
    
    # Initialize ChromaDB
    logger.info("🔧 Initializing ChromaDB...")
    client = chromadb.PersistentClient(
        path=db_path,
        settings=ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    
    # Delete existing collection
    logger.info(f"🗑️  Deleting existing collection: {collection_name}")
    try:
        client.delete_collection(collection_name)
        logger.info(f"✅ Collection deleted")
    except Exception as e:
        logger.info(f"ℹ️  Collection doesn't exist or error: {e}")
    
    # Read file
    logger.info(f"📖 Reading file: {data_file}")
    with open(data_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by articles (ماده)
    # Pattern: "ماده" followed by number and optional status
    article_pattern = r'(?:^|\n)(ماده\s+\d+(?:\s*\([^)]+\))?\s*\[[A-Z]+\])'
    
    parts = re.split(article_pattern, content, flags=re.MULTILINE)
    
    chunks = []
    current_chapter = "مقدمه"
    current_chapter_num = 0
    
    # Track chapters
    chapter_pattern = r'فصل\s+(اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم|[\u0660-\u0669\u06F0-\u06F90-9]+):\s*(.+?)(?=\n===|\Z)'
    
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        
        if not part:
            i += 1
            continue
        
        # Check if this is an article header
        if part.startswith('ماده'):
            # Extract article info
            article_header = part
            article_body = parts[i + 1] if i + 1 < len(parts) else ""
            full_article = article_header + "\n" + article_body
            
            # Extract article number
            article_num_match = re.search(r'ماده\s+(\d+)', article_header)
            article_num = int(article_num_match.group(1)) if article_num_match else 0
            
            # Extract status/color
            color_match = re.search(r'\[([A-Z]+)\]', article_header)
            color = color_match.group(1) if color_match else 'BLACK'
            
            # Map color to status
            status_map = {
                'BLACK': 'معتبر',
                'GREEN': 'اصلاحی/الحاقی',
                'RED': 'منسوخه',
                'ORANGE': 'تفسیر'
            }
            status = status_map.get(color, 'معتبر')
            
            # Extract status text (e.g., "اصلاحی ...")
            status_text_match = re.search(r'ماده\s+\d+\s*\(([^)]+)\)', article_header)
            article_status = status_text_match.group(1) if status_text_match else ""
            
            # Check for chapter in body
            chapter_match = re.search(chapter_pattern, article_body)
            if chapter_match:
                chapter_num_text = chapter_match.group(1)
                chapter_title = chapter_match.group(2).strip()
                current_chapter = f"فصل {chapter_num_text}: {chapter_title}"
                current_chapter_num = _persian_to_number(chapter_num_text)
            
            # Check for تبصره
            tabasere_pattern = r'تبصره\s*\d*\s*[-–]'
            tabasere_matches = re.findall(tabasere_pattern, full_article)
            has_tabasere = len(tabasere_matches) > 0
            
            # Create chunk
            chunks.append({
                'text': full_article.strip(),
                'metadata': {
                    'type': 'article',
                    'chapter': current_chapter,
                    'chapter_num': current_chapter_num,
                    'article_num': article_num,
                    'article_status': article_status,
                    'status': status,
                    'color': color,
                    'has_tabasere': has_tabasere,
                    'tabasere_count': len(tabasere_matches)
                }
            })
            
            i += 2  # Skip article header and body
        else:
            # This is intro/outro text
            # Check for chapter
            chapter_match = re.search(chapter_pattern, part)
            if chapter_match:
                chapter_num_text = chapter_match.group(1)
                chapter_title = chapter_match.group(2).strip()
                current_chapter = f"فصل {chapter_num_text}: {chapter_title}"
                current_chapter_num = _persian_to_number(chapter_num_text)
            
            # Only add if substantial content
            if len(part) > 50:
                chunks.append({
                    'text': part,
                    'metadata': {
                        'type': 'intro',
                        'chapter': current_chapter,
                        'chapter_num': current_chapter_num
                    }
                })
            
            i += 1
    
    logger.info(f"✅ Extracted {len(chunks)} chunks")
    
    # Count articles
    articles = [c for c in chunks if c['metadata']['type'] == 'article']
    logger.info(f"📊 Articles: {len(articles)}")
    
    # Create collection
    logger.info(f"🏗️  Creating collection: {collection_name}")
    collection = client.create_collection(
        name=collection_name,
        metadata={
            "description": "قانون بهبود مستمر محیط کسب و کار - نسخه کامل",
            "created_at": datetime.now().isoformat(),
            "source_file": "qavanin_complete.txt",
            "total_articles": len(articles),
            "total_chunks": len(chunks)
        }
    )
    
    # Initialize embedding service
    logger.info("🔢 Initializing embedding service...")
    embedding_service = PersianEmbeddingClient()
    
    # Add chunks in batches
    logger.info("📥 Adding chunks to collection...")
    batch_size = 20
    total_added = 0
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        
        texts = [c['text'] for c in batch]
        metadatas = [c['metadata'] for c in batch]
        
        # Generate embeddings
        embeddings = []
        for text in texts:
            embedding = await embedding_service.generate_embedding(text)
            embeddings.append(embedding)
        
        # Generate IDs
        ids = [
            f"{collection_name}_{i+j}_{hashlib.md5(text.encode()).hexdigest()[:8]}"
            for j, text in enumerate(texts)
        ]
        
        # Add to collection
        collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        total_added += len(batch)
        logger.info(f"  ✓ Added {total_added}/{len(chunks)} chunks")
    
    # Verify
    final_count = collection.count()
    logger.info(f"✅ Collection created with {final_count} documents")
    
    # Test search
    logger.info("\n🔍 Testing search...")
    test_query = "تعریف محیط کسب و کار چیست؟"
    query_embedding = await embedding_service.generate_embedding(test_query)
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3,
        include=['documents', 'metadatas', 'distances']
    )
    
    logger.info(f"\nQuery: {test_query}")
    logger.info("Top 3 Results:")
    
    for i, (doc, meta, dist) in enumerate(zip(
        results['documents'][0],
        results['metadatas'][0],
        results['distances'][0]
    )):
        logger.info(f"\n  Result {i+1}:")
        logger.info(f"  Distance: {dist:.4f}")
        logger.info(f"  Type: {meta.get('type')}")
        logger.info(f"  Chapter: {meta.get('chapter')}")
        logger.info(f"  Article: {meta.get('article_num', 'N/A')}")
        logger.info(f"  Status: {meta.get('status')}")
        logger.info(f"  Preview: {doc[:150]}...")
    
    logger.info("\n" + "="*80)
    logger.info("✅ REBUILD COMPLETED SUCCESSFULLY")
    logger.info("="*80)


def _persian_to_number(text):
    """تبدیل اعداد فارسی به عدد"""
    persian_numbers = {
        'اول': 1, 'دوم': 2, 'سوم': 3, 'چهارم': 4, 'پنجم': 5,
        'ششم': 6, 'هفتم': 7, 'هشتم': 8, 'نهم': 9, 'دهم': 10
    }
    return persian_numbers.get(text, 0)


if __name__ == "__main__":
    asyncio.run(rebuild_qavanin())
