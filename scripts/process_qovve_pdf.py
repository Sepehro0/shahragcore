#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
پردازش کامل فایل PDF قوه قضاییه با استفاده از تمام ویژگی‌های پیشرفته

این اسکریپت:
1. کالکشن qovve را می‌سازد
2. فایل PDF را با تمام ویژگی‌ها پردازش می‌کند
3. جداول را استخراج می‌کند
4. هدر و فوتر را حذف می‌کند
5. Embedding انجام می‌دهد
6. تست می‌کند
"""

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, List
import json

# اضافه کردن مسیر پروژه
sys.path.insert(0, str(Path(__file__).parent))

# تنظیم logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('process_qovve.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import ها
try:
    from processors.advanced_pdf_table_processor import AdvancedPDFTableProcessor
    from processors.improved_persian_pdf_processor import ImprovedPersianPDFProcessor
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except ImportError as e:
    logger.error(f"❌ Import failed: {e}")
    sys.exit(1)


class QovvePDFProcessor:
    """پردازشگر کامل PDF قوه قضاییه"""
    
    def __init__(self):
        """Initialize processors"""
        logger.info("🔧 Initializing processors...")
        
        # PDF processors
        self.advanced_table_processor = AdvancedPDFTableProcessor()
        self.persian_pdf_processor = ImprovedPersianPDFProcessor()
        
        # Database path
        db_path = "/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"
        
        # Embedding service - استفاده از JinaClient
        try:
            from services.jina_client import JinaClient
            self.embedding_service = JinaClient()
            logger.info("✅ Embedding service (Jina) initialized")
        except Exception as e:
            logger.warning(f"⚠️ Embedding service not available: {e}")
            self.embedding_service = None
        
        # ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=False
            )
        )
        
        self.collection_name = "qovve"
        logger.info("✅ QovvePDFProcessor initialized")
    
    def remove_header_footer(self, text: str, page_num: int = None) -> str:
        """
        حذف هدر و فوتر از متن
        
        الگوهای رایج:
        - شماره صفحه
        - هدرهای تکراری
        - فوترهای تکراری
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # حذف خطوط خالی
            if not line:
                continue
            
            # حذف شماره صفحه (فقط عدد)
            if line.isdigit() and len(line) <= 3:
                continue
            
            # حذف هدرهای تکراری (خطوط کوتاه که در ابتدای صفحات تکرار می‌شوند)
            if len(line) < 30 and line.count(' ') < 5:
                # اگر این خط در ابتدای متن است و کوتاه است، احتمالاً هدر است
                if len(cleaned_lines) < 3:
                    continue
            
            # حذف فوترهای رایج
            footer_keywords = [
                'صفحه',
                'page',
                'تاریخ',
                'نسخه',
                'version'
            ]
            if any(keyword in line.lower() for keyword in footer_keywords) and len(line) < 50:
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def process_pdf_complete(self, pdf_path: str) -> Dict[str, Any]:
        """
        پردازش کامل PDF با تمام ویژگی‌ها
        
        Returns:
            Dict with:
            - text_chunks: متن‌های chunk شده
            - tables: جداول استخراج شده
            - metadata: متادیتای پردازش
        """
        logger.info(f"📄 Processing PDF: {pdf_path}")
        
        # خواندن فایل
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        logger.info(f"📊 File size: {len(pdf_bytes) / 1024:.2f} KB")
        
        # 1. استخراج جداول با Advanced Table Processor
        logger.info("🔍 Step 1: Extracting tables with advanced processor...")
        tables_data = self.advanced_table_processor.extract_tables_advanced(pdf_bytes)
        logger.info(f"✅ Extracted {len(tables_data)} tables")
        
        # 2. استخراج متن با pdfplumber و PyMuPDF (fallback)
        logger.info("📝 Step 2: Extracting text...")
        import pdfplumber
        import io
        text_data = []
        
        # روش 1: pdfplumber
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                logger.info(f"📄 PDF has {len(pdf.pages)} pages")
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text and text.strip():
                        # استفاده از Persian PDF Processor برای رفع مشکل reversed text
                        try:
                            cleaned_text = self.persian_pdf_processor.fix_reversed_text(text)
                        except:
                            cleaned_text = text
                        
                        text_data.append({
                            "page": page_num,
                            "text": cleaned_text
                        })
            
            if text_data:
                logger.info(f"✅ Extracted text from {len(text_data)} pages using pdfplumber")
        except Exception as e:
            logger.warning(f"⚠️ pdfplumber extraction failed: {e}")
        
        # روش 2: PyMuPDF (fallback اگر pdfplumber متن نداشت)
        if not text_data:
            logger.info("🔄 Trying PyMuPDF as fallback...")
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(stream=pdf_bytes, filetype='pdf')
                logger.info(f"📄 PDF has {doc.page_count} pages (PyMuPDF)")
                
                for page_num in range(doc.page_count):
                    page = doc[page_num]
                    text = page.get_text()
                    
                    if text and text.strip():
                        # استفاده از Persian PDF Processor
                        try:
                            cleaned_text = self.persian_pdf_processor.fix_reversed_text(text)
                        except:
                            cleaned_text = text
                        
                        text_data.append({
                            "page": page_num + 1,
                            "text": cleaned_text
                        })
                
                doc.close()
                
                if text_data:
                    logger.info(f"✅ Extracted text from {len(text_data)} pages using PyMuPDF")
            except Exception as e:
                logger.error(f"❌ PyMuPDF extraction also failed: {e}")
        
        if not text_data:
            logger.error("❌ No text extracted from PDF. PDF might be image-based or corrupted.")
            logger.info("💡 Tip: This PDF appears to be image-based. Consider using OCR.")
            return {
                "error": "No text extracted from PDF",
                "text_chunks": [],
                "table_chunks": [],
                "all_chunks": [],
                "tables_data": [],
                "metadata": {
                    "total_pages": 0,
                    "total_tables": 0,
                    "total_text_chunks": 0,
                    "total_table_chunks": 0,
                    "total_chunks": 0,
                    "error": "PDF is image-based, no text extracted"
                }
            }
        
        # 3. پردازش و تمیز کردن متن
        logger.info("🧹 Step 3: Cleaning text (removing headers/footers)...")
        cleaned_texts = []
        for page_data in text_data:
            page_num = page_data.get("page", 0)
            text = page_data.get("text", "")
            
            # حذف هدر و فوتر
            cleaned_text = self.remove_header_footer(text, page_num)
            
            if cleaned_text.strip():
                cleaned_texts.append({
                    "page": page_num,
                    "text": cleaned_text,
                    "original_length": len(text),
                    "cleaned_length": len(cleaned_text)
                })
        
        logger.info(f"✅ Cleaned {len(cleaned_texts)} pages")
        
        # 4. Chunking متن
        logger.info("✂️ Step 4: Chunking text...")
        
        def simple_text_splitter(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
            """Text splitter ساده"""
            if not text:
                return []
            
            chunks = []
            start = 0
            text_length = len(text)
            
            while start < text_length:
                end = start + chunk_size
                
                # اگر به انتهای متن نرسیده‌ایم، سعی کن روی separator ببر
                if end < text_length:
                    # جستجوی separator مناسب
                    for sep in ["\n\n", "\n", " ", ""]:
                        sep_pos = text.rfind(sep, start, end)
                        if sep_pos != -1:
                            end = sep_pos + len(sep)
                            break
                
                chunk = text[start:end].strip()
                if chunk:
                    chunks.append(chunk)
                
                start = end - chunk_overlap
                if start < 0:
                    start = 0
            
            return chunks
        
        all_chunks = []
        for page_data in cleaned_texts:
            text = page_data["text"]
            chunks = simple_text_splitter(text, chunk_size=500, chunk_overlap=50)
            
            for chunk_idx, chunk in enumerate(chunks):
                all_chunks.append({
                    "text": chunk,
                    "page": page_data["page"],
                    "chunk_index": chunk_idx,
                    "source": "text",
                    "metadata": {
                        "page": page_data["page"],
                        "chunk_index": chunk_idx,
                        "source_type": "text"
                    }
                })
        
        logger.info(f"✅ Created {len(all_chunks)} text chunks")
        
        # 5. پردازش جداول و تبدیل به chunks
        logger.info("📊 Step 5: Processing tables into chunks...")
        table_chunks = []
        
        for table in tables_data:
            page = table.get("page", 0)
            table_idx = table.get("table_index", 0)
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            
            # ساخت متن از جدول با header paths
            table_text_parts = []
            
            # اضافه کردن header paths
            header_paths = [h.get("full_path", "") for h in headers]
            if header_paths:
                table_text_parts.append("ستون‌ها: " + " | ".join(header_paths))
            
            # اضافه کردن rows
            for row in rows[:50]:  # حداکثر 50 ردیف برای جلوگیری از chunk های خیلی بزرگ
                cells_with_headers = row.get("cells_with_headers", [])
                row_text_parts = []
                
                for cell_data in cells_with_headers:
                    value = cell_data.get("value", "").strip()
                    header_path = cell_data.get("header_path", "").strip()
                    
                    if value:
                        if header_path:
                            row_text_parts.append(f"{header_path}: {value}")
                        else:
                            row_text_parts.append(value)
                
                if row_text_parts:
                    table_text_parts.append(" | ".join(row_text_parts))
            
            table_text = "\n".join(table_text_parts)
            
            if table_text.strip():
                table_chunks.append({
                    "text": table_text,
                    "page": page,
                    "table_index": table_idx,
                    "source": "table",
                    "metadata": {
                        "page": page,
                        "table_index": table_idx,
                        "source_type": "table",
                        "num_header_rows": table.get("num_header_rows", 0),
                        "num_data_rows": len(rows)
                    }
                })
        
        logger.info(f"✅ Created {len(table_chunks)} table chunks")
        
        # 6. ترکیب همه chunks
        all_final_chunks = all_chunks + table_chunks
        logger.info(f"✅ Total chunks: {len(all_final_chunks)} (text: {len(all_chunks)}, table: {len(table_chunks)})")
        
        return {
            "text_chunks": all_chunks,
            "table_chunks": table_chunks,
            "all_chunks": all_final_chunks,
            "tables_data": tables_data,
            "metadata": {
                "total_pages": len(text_data),
                "total_tables": len(tables_data),
                "total_text_chunks": len(all_chunks),
                "total_table_chunks": len(table_chunks),
                "total_chunks": len(all_final_chunks)
            }
        }
    
    def create_collection(self) -> bool:
        """ساخت کالکشن qovve"""
        logger.info(f"📦 Creating collection: {self.collection_name}")
        
        try:
            # بررسی وجود کالکشن
            try:
                existing = self.chroma_client.get_collection(self.collection_name)
                logger.warning(f"⚠️ Collection {self.collection_name} already exists")
                logger.info("🗑️ Deleting existing collection...")
                self.chroma_client.delete_collection(self.collection_name)
                logger.info("✅ Deleted existing collection")
            except:
                pass
            
            # ساخت کالکشن جدید
            collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={
                    "description": "کالکشن قوه قضاییه - پردازش شده با Advanced PDF Processor",
                    "source": "qovve-ketab-sample.pdf",
                    "processing_type": "advanced_with_tables"
                }
            )
            
            logger.info(f"✅ Collection {self.collection_name} created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create collection: {e}")
            return False
    
    def add_chunks_to_collection(self, chunks: List[Dict[str, Any]]) -> bool:
        """اضافه کردن chunks به کالکشن"""
        logger.info(f"📤 Adding {len(chunks)} chunks to collection...")
        
        if not self.embedding_service:
            logger.warning("⚠️ Embedding service not available, using ChromaDB default")
            # استفاده از ChromaDB default embedding
            use_default_embedding = True
        else:
            use_default_embedding = False
        
        try:
            collection = self.chroma_client.get_collection(self.collection_name)
            
            # آماده‌سازی داده‌ها
            texts = []
            metadatas = []
            ids = []
            
            for idx, chunk in enumerate(chunks):
                text = chunk.get("text", "")
                metadata = chunk.get("metadata", {})
                
                if not text.strip():
                    continue
                
                texts.append(text)
                metadatas.append(metadata)
                ids.append(f"{self.collection_name}_chunk_{idx}")
            
            if use_default_embedding:
                # استفاده از ChromaDB default embedding
                logger.info("💾 Saving to ChromaDB (using default embedding)...")
                collection.add(
                    documents=texts,
                    metadatas=metadatas,
                    ids=ids
                )
            else:
                # تولید embeddings
                logger.info("🔄 Generating embeddings...")
                embeddings = []
                batch_size = 20  # کوچکتر برای جلوگیری از timeout
                
                import asyncio
                
                async def generate_batch_embeddings(batch_texts):
                    """تولید embeddings برای یک batch"""
                    try:
                        response = await self.embedding_service.generate_embeddings(
                            batch_texts,
                            task="retrieval.document"
                        )
                        if response.success and response.embeddings:
                            return response.embeddings
                        else:
                            logger.warning(f"  ⚠️ Embedding generation failed: {response.error}")
                            return None
                    except Exception as e:
                        logger.warning(f"  ⚠️ Embedding batch failed: {e}")
                        return None
                
                # تولید embeddings به صورت batch
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i+batch_size]
                    batch_embeddings = asyncio.run(generate_batch_embeddings(batch_texts))
                    
                    if batch_embeddings:
                        embeddings.extend(batch_embeddings)
                    else:
                        # Fallback: استفاده از default
                        logger.warning(f"  ⚠️ Using default embedding for batch {i//batch_size + 1}")
                        embeddings.extend([[0.0] * 1024] * len(batch_texts))
                    
                    if (i // batch_size + 1) % 10 == 0:
                        logger.info(f"  Processed {i + len(batch_texts)}/{len(texts)} chunks")
                
                logger.info(f"✅ Generated {len(embeddings)} embeddings")
                
                # اضافه کردن به ChromaDB
                logger.info("💾 Saving to ChromaDB...")
                collection.add(
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas,
                    ids=ids
                )
            
            logger.info(f"✅ Added {len(texts)} chunks to collection")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add chunks: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_collection(self, test_queries: List[str] = None) -> Dict[str, Any]:
        """تست کالکشن با query های مختلف"""
        logger.info("🧪 Testing collection...")
        
        if test_queries is None:
            test_queries = [
                "این سند درباره چیست؟",
                "چه جداولی در این سند وجود دارد؟",
                "اطلاعات مالی موجود در سند را بده",
                "خلاصه محتوای سند"
            ]
        
        results = []
        
        try:
            collection = self.chroma_client.get_collection(self.collection_name)
            
            for query in test_queries:
                logger.info(f"🔍 Query: {query}")
                
                # جستجو
                if self.embedding_service:
                    # تولید embedding برای query
                    import asyncio
                    try:
                        response = asyncio.run(
                            self.embedding_service.generate_embedding(query, "retrieval.query")
                        )
                        if not response.success or not response.embeddings:
                            logger.warning(f"  ⚠️ Query embedding failed: {response.error}")
                            continue
                        query_embedding = response.embeddings[0]
                        
                        # جستجو با embedding
                        search_results = collection.query(
                            query_embeddings=[query_embedding],
                            n_results=5
                        )
                    except Exception as e:
                        logger.error(f"  ❌ Query embedding failed: {e}")
                        continue
                else:
                    # استفاده از query_texts (ChromaDB خودش embed می‌کند)
                    search_results = collection.query(
                        query_texts=[query],
                        n_results=5
                    )
                
                if search_results['documents'] and search_results['documents'][0]:
                    top_result = search_results['documents'][0][0]
                    top_metadata = search_results['metadatas'][0][0] if search_results['metadatas'] else {}
                    
                    results.append({
                        "query": query,
                        "top_result": top_result[:200] + "..." if len(top_result) > 200 else top_result,
                        "metadata": top_metadata,
                        "num_results": len(search_results['documents'][0])
                    })
                    
                    logger.info(f"  ✅ Found {len(search_results['documents'][0])} results")
                    logger.info(f"  📄 Top result (first 100 chars): {top_result[:100]}...")
                else:
                    results.append({
                        "query": query,
                        "top_result": None,
                        "error": "No results found"
                    })
                    logger.warning(f"  ⚠️ No results found")
        
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
        
        return {"test_results": results}


def main():
    """تابع اصلی"""
    logger.info("=" * 70)
    logger.info("🚀 Starting Qovve PDF Processing")
    logger.info("=" * 70)
    
    # مسیر فایل PDF
    pdf_path = "/home/user01/qwen-api/enhanced_rag_system_dev/archive/data_files/qovve-ketab-sample.pdf"
    
    if not os.path.exists(pdf_path):
        logger.error(f"❌ PDF file not found: {pdf_path}")
        sys.exit(1)
    
    # ایجاد processor
    processor = QovvePDFProcessor()
    
    # 1. ساخت کالکشن
    logger.info("\n" + "=" * 70)
    logger.info("Step 1: Creating Collection")
    logger.info("=" * 70)
    if not processor.create_collection():
        logger.error("❌ Failed to create collection")
        sys.exit(1)
    
    # 2. پردازش PDF
    logger.info("\n" + "=" * 70)
    logger.info("Step 2: Processing PDF")
    logger.info("=" * 70)
    processing_result = processor.process_pdf_complete(pdf_path)
    
    # نمایش آمار
    logger.info("\n📊 Processing Statistics:")
    logger.info(f"  - Total pages: {processing_result['metadata']['total_pages']}")
    logger.info(f"  - Total tables: {processing_result['metadata']['total_tables']}")
    logger.info(f"  - Text chunks: {processing_result['metadata']['total_text_chunks']}")
    logger.info(f"  - Table chunks: {processing_result['metadata']['total_table_chunks']}")
    logger.info(f"  - Total chunks: {processing_result['metadata']['total_chunks']}")
    
    # ذخیره نتایج پردازش
    output_file = "qovve_processing_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "metadata": processing_result['metadata'],
            "sample_chunks": {
                "text_sample": processing_result['text_chunks'][:2] if processing_result['text_chunks'] else [],
                "table_sample": processing_result['table_chunks'][:2] if processing_result['table_chunks'] else []
            }
        }, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ Processing results saved to: {output_file}")
    
    # 3. اضافه کردن به کالکشن
    logger.info("\n" + "=" * 70)
    logger.info("Step 3: Adding Chunks to Collection")
    logger.info("=" * 70)
    if not processor.add_chunks_to_collection(processing_result['all_chunks']):
        logger.error("❌ Failed to add chunks to collection")
        sys.exit(1)
    
    # 4. تست
    logger.info("\n" + "=" * 70)
    logger.info("Step 4: Testing Collection")
    logger.info("=" * 70)
    test_results = processor.test_collection()
    
    # ذخیره نتایج تست
    test_output_file = "qovve_test_results.json"
    with open(test_output_file, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ Test results saved to: {test_output_file}")
    
    # خلاصه نهایی
    logger.info("\n" + "=" * 70)
    logger.info("✅ Processing Complete!")
    logger.info("=" * 70)
    logger.info(f"📦 Collection: {processor.collection_name}")
    logger.info(f"📄 PDF: {pdf_path}")
    logger.info(f"📊 Total chunks: {processing_result['metadata']['total_chunks']}")
    logger.info(f"📁 Results: {output_file}, {test_output_file}")
    logger.info("\n🎉 Ready to use!")


if __name__ == "__main__":
    main()
