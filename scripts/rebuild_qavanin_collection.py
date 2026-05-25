# -*- coding: utf-8 -*-
"""
اسکریپت ساخت مجدد کالکشن قوانین
حذف کالکشن قبلی و ساخت مجدد با فایل کامل qavanin_complete.txt
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
import chromadb
from chromadb.config import Settings as ChromaSettings
import hashlib
import re

# Add project path
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from services.persian_embedding_service import PersianEmbeddingClient
from utils.text_utils import TextNormalizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QavaninCollectionBuilder:
    """سازنده کالکشن قوانین با ساختار هوشمند"""
    
    def __init__(
        self,
        db_path: str = "/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db",
        data_file: str = "/home/user01/qwen-api/enhanced_rag_system_dev/archive/data_files/qavanin_complete.txt"
    ):
        self.db_path = db_path
        self.data_file = data_file
        self.collection_name = "qavanin"
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding service
        logger.info("🔧 Initializing Persian Embedding Service...")
        self.embedding_service = PersianEmbeddingClient()
        
        # Initialize text normalizer
        self.text_normalizer = TextNormalizer()
        
        logger.info("✅ QavaninCollectionBuilder initialized")
    
    def _parse_qavanin_file(self) -> list:
        """
        پارس فایل قوانین با ساختار هوشمند
        
        Returns:
            لیست چانک‌ها با متادیتای کامل
        """
        logger.info(f"📖 Reading file: {self.data_file}")
        
        with open(self.data_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        chunks = []
        current_chapter = ""
        current_chapter_num = 0
        
        # Pattern for detecting chapters (فصل)
        chapter_pattern = re.compile(r'^(={80,})\s*\n(فصل\s+([\u0660-\u0669\u06F0-\u06F90-9]+|اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم)):(.+?)\n(={80,})', re.MULTILINE)
        
        # Pattern for detecting articles (ماده)
        article_pattern = re.compile(r'^(ماده\s+(\d+)(?:\s+\(([^)]+)\))?)?\s*(\[([A-Z]+)\])?', re.MULTILINE)
        
        # Split by chapters
        chapter_matches = list(chapter_pattern.finditer(content))
        
        if not chapter_matches:
            logger.warning("⚠️  No chapters found, processing as single document")
            chunks.append({
                'text': content,
                'metadata': {
                    'type': 'full_document',
                    'chapter': 'کل سند',
                    'chapter_num': 0
                }
            })
            return chunks
        
        # Process each chapter
        for i, chapter_match in enumerate(chapter_matches):
            chapter_start = chapter_match.start()
            chapter_end = chapter_matches[i + 1].start() if i + 1 < len(chapter_matches) else len(content)
            chapter_content = content[chapter_start:chapter_end]
            
            # Extract chapter info
            chapter_num_text = chapter_match.group(3)
            chapter_title = chapter_match.group(4).strip()
            current_chapter = f"فصل {chapter_num_text}: {chapter_title}"
            current_chapter_num = self._persian_to_number(chapter_num_text)
            
            logger.info(f"📑 Processing: {current_chapter}")
            
            # Split chapter into articles
            article_matches = list(article_pattern.finditer(chapter_content))
            
            if not article_matches:
                # No articles, save whole chapter as one chunk
                chunks.append({
                    'text': chapter_content.strip(),
                    'metadata': {
                        'type': 'chapter',
                        'chapter': current_chapter,
                        'chapter_num': current_chapter_num,
                        'chapter_title': chapter_title
                    }
                })
                continue
            
            # Process each article
            for j, article_match in enumerate(article_matches):
                article_start = article_match.start()
                article_end = article_matches[j + 1].start() if j + 1 < len(article_matches) else len(chapter_content)
                article_content = chapter_content[article_start:article_end].strip()
                
                # Extract article info
                article_num = article_match.group(2) if article_match.group(2) else "0"
                article_status = article_match.group(3) if article_match.group(3) else ""
                article_color = article_match.group(5) if article_match.group(5) else "BLACK"
                
                # Determine article status from color
                status_map = {
                    'BLACK': 'معتبر',
                    'GREEN': 'اصلاحی/الحاقی',
                    'RED': 'منسوخه',
                    'ORANGE': 'تفسیر'
                }
                status = status_map.get(article_color, 'معتبر')
                
                # Extract تبصره (notes)
                tabasere_pattern = re.compile(r'(تبصره\s*\d*\s*[-–])', re.MULTILINE)
                tabasere_matches = list(tabasere_pattern.finditer(article_content))
                has_tabasere = len(tabasere_matches) > 0
                
                # Create chunk metadata
                metadata = {
                    'type': 'article',
                    'chapter': current_chapter,
                    'chapter_num': current_chapter_num,
                    'chapter_title': chapter_title,
                    'article_num': int(article_num) if article_num.isdigit() else 0,
                    'article_status': article_status,
                    'status': status,
                    'color': article_color,
                    'has_tabasere': has_tabasere,
                    'tabasere_count': len(tabasere_matches)
                }
                
                chunks.append({
                    'text': article_content,
                    'metadata': metadata
                })
                
                logger.debug(f"  ✓ ماده {article_num} - {status} - تبصره: {len(tabasere_matches)}")
        
        logger.info(f"✅ Parsed {len(chunks)} chunks from file")
        return chunks
    
    def _persian_to_number(self, persian_text: str) -> int:
        """تبدیل اعداد فارسی به عدد"""
        persian_numbers = {
            'اول': 1, 'دوم': 2, 'سوم': 3, 'چهارم': 4, 'پنجم': 5,
            'ششم': 6, 'هفتم': 7, 'هشتم': 8, 'نهم': 9, 'دهم': 10
        }
        
        if persian_text in persian_numbers:
            return persian_numbers[persian_text]
        
        # Try to parse as digit
        try:
            return int(persian_text)
        except:
            return 0
    
    def _generate_chunk_id(self, text: str, index: int) -> str:
        """تولید ID یکتا برای چانک"""
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()[:8]
        return f"{self.collection_name}_{index}_{text_hash}"
    
    async def delete_existing_collection(self):
        """حذف کالکشن قبلی"""
        try:
            logger.info(f"🗑️  Checking for existing collection: {self.collection_name}")
            
            # Get all collections
            collections = self.chroma_client.list_collections()
            collection_names = [col.name for col in collections]
            
            if self.collection_name in collection_names:
                logger.info(f"⚠️  Found existing collection: {self.collection_name}")
                logger.info("🗑️  Deleting existing collection...")
                
                self.chroma_client.delete_collection(self.collection_name)
                
                logger.info(f"✅ Collection '{self.collection_name}' deleted successfully")
            else:
                logger.info(f"ℹ️  Collection '{self.collection_name}' does not exist")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting collection: {e}")
            return False
    
    async def create_collection(self):
        """ساخت کالکشن جدید با ساختار هوشمند"""
        try:
            logger.info(f"🏗️  Creating new collection: {self.collection_name}")
            
            # Parse file
            logger.info("📖 Parsing qavanin file...")
            chunks = self._parse_qavanin_file()
            
            if not chunks:
                logger.error("❌ No chunks extracted from file")
                return False
            
            # Create collection
            logger.info("🏗️  Creating ChromaDB collection...")
            collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={
                    "description": "قانون بهبود مستمر محیط کسب و کار - نسخه کامل با تگ‌گذاری",
                    "created_at": datetime.now().isoformat(),
                    "source_file": "qavanin_complete.txt",
                    "total_articles": 31,
                    "total_chapters": 10,
                    "includes_amendments": True,
                    "color_coded": True
                }
            )
            
            # Generate embeddings and add to collection
            logger.info("🔢 Generating embeddings...")
            
            batch_size = 50
            total_added = 0
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                
                # Extract texts and metadata
                texts = [chunk['text'] for chunk in batch]
                metadatas = [chunk['metadata'] for chunk in batch]
                
                # Generate embeddings
                embeddings = []
                for text in texts:
                    try:
                        embedding = await self.embedding_service.generate_embedding(text)
                        embeddings.append(embedding)
                    except Exception as e:
                        logger.error(f"❌ Error generating embedding: {e}")
                        # Use zero vector as fallback
                        embeddings.append([0.0] * 768)
                
                # Generate IDs
                ids = [self._generate_chunk_id(text, i + j) for j, text in enumerate(texts)]
                
                # Add to collection
                collection.add(
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas,
                    ids=ids
                )
                
                total_added += len(batch)
                logger.info(f"  ✓ Added {total_added}/{len(chunks)} chunks")
            
            # Verify collection
            final_count = collection.count()
            logger.info(f"✅ Collection created successfully with {final_count} documents")
            
            # Save collection info
            self._save_collection_info(chunks, final_count)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating collection: {e}", exc_info=True)
            return False
    
    def _save_collection_info(self, chunks: list, total_count: int):
        """ذخیره اطلاعات کالکشن"""
        try:
            # Count by type
            articles = [c for c in chunks if c['metadata'].get('type') == 'article']
            chapters = [c for c in chunks if c['metadata'].get('type') == 'chapter']
            
            # Count by status
            status_counts = {}
            for chunk in chunks:
                status = chunk['metadata'].get('status', 'نامشخص')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count articles with تبصره
            articles_with_tabasere = [c for c in chunks if c['metadata'].get('has_tabasere', False)]
            total_tabasere = sum(c['metadata'].get('tabasere_count', 0) for c in chunks)
            
            info = {
                "collection_name": self.collection_name,
                "created_at": datetime.now().isoformat(),
                "source_file": self.data_file,
                "statistics": {
                    "total_chunks": total_count,
                    "articles": len(articles),
                    "chapters": len(chapters),
                    "articles_with_tabasere": len(articles_with_tabasere),
                    "total_tabasere": total_tabasere,
                    "status_distribution": status_counts
                },
                "structure": {
                    "total_chapters": 10,
                    "total_articles": 31,
                    "main_articles": 29,
                    "amendment_articles": 2
                }
            }
            
            # Save to file
            config_dir = Path("/home/user01/qwen-api/enhanced_rag_system_dev/collections_config")
            config_dir.mkdir(exist_ok=True, parents=True)
            
            config_file = config_dir / f"{self.collection_name}_info.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(info, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Collection info saved to: {config_file}")
            
            # Print summary
            logger.info("\n" + "="*80)
            logger.info("📊 COLLECTION STATISTICS")
            logger.info("="*80)
            logger.info(f"Collection Name: {self.collection_name}")
            logger.info(f"Total Chunks: {total_count}")
            logger.info(f"Articles: {len(articles)}")
            logger.info(f"Chapters: {len(chapters)}")
            logger.info(f"Articles with تبصره: {len(articles_with_tabasere)}")
            logger.info(f"Total تبصره: {total_tabasere}")
            logger.info("\nStatus Distribution:")
            for status, count in status_counts.items():
                logger.info(f"  - {status}: {count}")
            logger.info("="*80 + "\n")
            
        except Exception as e:
            logger.error(f"❌ Error saving collection info: {e}")
    
    async def verify_collection(self):
        """بررسی صحت کالکشن"""
        try:
            logger.info(f"🔍 Verifying collection: {self.collection_name}")
            
            # Get collection
            collection = self.chroma_client.get_collection(self.collection_name)
            
            # Get sample
            results = collection.get(limit=5, include=['documents', 'metadatas'])
            
            logger.info("\n" + "="*80)
            logger.info("📋 SAMPLE DOCUMENTS")
            logger.info("="*80)
            
            for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
                logger.info(f"\nDocument {i+1}:")
                logger.info(f"Type: {meta.get('type', 'N/A')}")
                logger.info(f"Chapter: {meta.get('chapter', 'N/A')}")
                if meta.get('type') == 'article':
                    logger.info(f"Article: {meta.get('article_num', 'N/A')}")
                    logger.info(f"Status: {meta.get('status', 'N/A')}")
                    logger.info(f"Has تبصره: {meta.get('has_tabasere', False)}")
                logger.info(f"Text preview: {doc[:200]}...")
            
            logger.info("="*80 + "\n")
            
            # Test search
            logger.info("🔍 Testing search functionality...")
            
            test_query = "تعریف محیط کسب و کار چیست؟"
            query_embedding = await self.embedding_service.generate_embedding(test_query)
            
            search_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=3,
                include=['documents', 'metadatas', 'distances']
            )
            
            logger.info(f"\nTest Query: {test_query}")
            logger.info("Top 3 Results:")
            
            for i, (doc, meta, dist) in enumerate(zip(
                search_results['documents'][0],
                search_results['metadatas'][0],
                search_results['distances'][0]
            )):
                logger.info(f"\nResult {i+1}:")
                logger.info(f"Distance: {dist:.4f}")
                logger.info(f"Type: {meta.get('type', 'N/A')}")
                logger.info(f"Chapter: {meta.get('chapter', 'N/A')}")
                if meta.get('type') == 'article':
                    logger.info(f"Article: {meta.get('article_num', 'N/A')}")
                logger.info(f"Preview: {doc[:150]}...")
            
            logger.info("\n✅ Verification completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error verifying collection: {e}", exc_info=True)
            return False


async def main():
    """اجرای اصلی اسکریپت"""
    
    logger.info("="*80)
    logger.info("🚀 Qavanin Collection Rebuild Script")
    logger.info("="*80)
    logger.info("این اسکریپت کالکشن qavanin را به طور کامل بازسازی می‌کند")
    logger.info("با استفاده از فایل qavanin_complete.txt")
    logger.info("="*80 + "\n")
    
    # Create builder
    builder = QavaninCollectionBuilder()
    
    # Step 1: Delete existing collection
    logger.info("📍 Step 1: Delete existing collection")
    success = await builder.delete_existing_collection()
    if not success:
        logger.error("❌ Failed to delete existing collection")
        return
    
    logger.info("")
    
    # Step 2: Create new collection
    logger.info("📍 Step 2: Create new collection")
    success = await builder.create_collection()
    if not success:
        logger.error("❌ Failed to create collection")
        return
    
    logger.info("")
    
    # Step 3: Verify collection
    logger.info("📍 Step 3: Verify collection")
    success = await builder.verify_collection()
    if not success:
        logger.error("❌ Failed to verify collection")
        return
    
    logger.info("\n" + "="*80)
    logger.info("✅ QAVANIN COLLECTION REBUILD COMPLETED SUCCESSFULLY")
    logger.info("="*80)
    logger.info("\nNext Steps:")
    logger.info("1. Test the collection with sample queries")
    logger.info("2. Verify search results quality")
    logger.info("3. Check metadata accuracy")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())
