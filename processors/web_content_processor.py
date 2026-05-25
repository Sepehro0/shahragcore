# -*- coding: utf-8 -*-
"""
Web Content Processor
پردازش محتوای crawl شده → chunks → embeddings → ChromaDB

جریان:
1. هر صفحه به chunks تقسیم می‌شود (sentence-aware)
2. embeddings با مدل heydari تولید می‌شود
3. در ChromaDB ذخیره می‌شود
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CHROMA_DB_PATH = "/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"


# ──────────────────────────────────────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class WebChunk:
    text: str
    chunk_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)


# ──────────────────────────────────────────────────────────────────────────────
# Language detection
# ──────────────────────────────────────────────────────────────────────────────

def _detect_language(text: str) -> str:
    """تشخیص زبان متن (fa/en/mixed)"""
    if not text:
        return "en"
    persian_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    ratio = persian_chars / max(len(text), 1)
    if ratio > 0.3:
        return "fa"
    elif ratio > 0.05:
        return "mixed"
    return "en"


# ──────────────────────────────────────────────────────────────────────────────
# Sentence-aware chunker
# ──────────────────────────────────────────────────────────────────────────────

class SentenceAwareChunker:
    """
    chunker که مرزهای جمله را رعایت می‌کند.
    برای فارسی و انگلیسی هر دو مناسب است.
    """

    # جداکننده‌های جمله
    SENTENCE_DELIMITERS = re.compile(r"(?<=[.!?؟\n])\s+|(?<=\n)\n+")

    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 80) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _split_into_sentences(self, text: str) -> List[str]:
        """متن را به جملات تقسیم کن."""
        sentences: List[str] = []
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        for para in paragraphs:
            lines = [l.strip() for l in para.splitlines() if l.strip()]
            for line in lines:
                parts = re.split(r"(?<=[.!?؟])\s+", line)
                sentences.extend([p.strip() for p in parts if p.strip()])
        return sentences

    def chunk(self, text: str) -> List[str]:
        """متن را به chunks تقسیم کن."""
        if not text or len(text.strip()) < 30:
            return []

        sentences = self._split_into_sentences(text)
        if not sentences:
            return []

        chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for sent in sentences:
            sent_len = len(sent)
            if current_len + sent_len > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                if len(chunk_text.strip()) >= 50:
                    chunks.append(chunk_text)
                # Overlap: آخرین چند جمله را نگه دار
                overlap_text = ""
                overlap_sents: List[str] = []
                overlap_len = 0
                for s in reversed(current_chunk):
                    if overlap_len + len(s) < self.chunk_overlap:
                        overlap_sents.insert(0, s)
                        overlap_len += len(s)
                    else:
                        break
                current_chunk = overlap_sents
                current_len = sum(len(s) for s in current_chunk)

            current_chunk.append(sent)
            current_len += sent_len

        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text.strip()) >= 50:
                chunks.append(chunk_text)

        return chunks


# ──────────────────────────────────────────────────────────────────────────────
# Processor
# ──────────────────────────────────────────────────────────────────────────────

class WebContentProcessor:
    """
    پردازشگر محتوای وب.
    صفحات crawl‌شده را به chunks تبدیل می‌کند و در ChromaDB ذخیره می‌کند.
    """

    _embed_model = None  # singleton

    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 80) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunker = SentenceAwareChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def _get_embed_model(self):
        if WebContentProcessor._embed_model is None:
            logger.info("🔄 Loading embedding model...")
            from services.persian_embedding_service import get_heydari_model
            WebContentProcessor._embed_model = get_heydari_model()
            logger.info("✅ Embedding model loaded")
        return WebContentProcessor._embed_model

    def _get_chroma_client(self):
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        return chromadb.PersistentClient(
            path=CHROMA_DB_PATH,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        model = self._get_embed_model()
        batch_size = 32
        all_embs: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embs = model.encode(batch, show_progress_bar=False).tolist()
            all_embs.extend(embs)
        return all_embs

    def page_to_chunks(
        self,
        page_url: str,
        content: str,
        page_metadata: Dict[str, Any],
        base_chunk_index: int = 0,
    ) -> List[WebChunk]:
        """یک صفحه را به chunks تبدیل کن."""
        lang = _detect_language(content)
        raw_chunks = self.chunker.chunk(content)
        chunks: List[WebChunk] = []
        for i, chunk_text in enumerate(raw_chunks):
            meta = {
                **page_metadata,
                "chunk_index": base_chunk_index + i,
                "language": lang,
                "page_chunk_index": i,
                "total_page_chunks": len(raw_chunks),
                "char_count": len(chunk_text),
                "source": page_url,
            }
            chunks.append(WebChunk(
                text=chunk_text,
                chunk_index=base_chunk_index + i,
                metadata=meta,
            ))
        return chunks

    def _item_to_virtual_chunk(
        self,
        item: Dict[str, Any],
        page_url: str,
        page_metadata: Dict[str, Any],
        chunk_index: int,
    ) -> Optional[WebChunk]:
        """
        از یک آیتم ساختاریافته (محصول، مقاله، ...) یک chunk مجازی بساز
        که در جستجوی semantic قابل بازیابی باشد.
        متن chunk شامل نام، قیمت، توضیحات و لینک است.
        """
        title = (item.get("title") or "").strip()
        if not title or len(title) < 2:
            return None

        parts = [title]
        price = (item.get("price") or "").strip()
        if price:
            parts.append(f"قیمت: {price}")
        desc = (item.get("description") or "").strip()
        if desc and desc != title:
            parts.append(desc[:200])
        link = (item.get("link") or "").strip()
        if link:
            parts.append(f"لینک: {link}")
        image = (item.get("image") or "").strip()

        text = " — ".join(parts)
        if len(text) < 10:
            return None

        meta = {
            **page_metadata,
            "chunk_index": chunk_index,
            "language": _detect_language(text),
            "page_chunk_index": 0,
            "total_page_chunks": 1,
            "char_count": len(text),
            "source": page_url,
            "type": "structured_item",
            "item_title": title[:200],
            "item_price": price[:50] if price else "",
            "item_link": link[:500] if link else "",
            "item_image": image[:500] if image else "",
        }

        return WebChunk(text=text, chunk_index=chunk_index, metadata=meta)

    def process_and_index(
        self,
        pages: List[Dict[str, Any]],
        collection_name: str,
        overwrite: bool = True,
    ) -> Dict[str, Any]:
        """
        همه صفحات را پردازش کن و در ChromaDB ذخیره کن.

        Args:
            pages: لیست صفحات {url, content, metadata}
            collection_name: نام collection در ChromaDB
            overwrite: اگر True، collection قبلی را پاک کن

        Returns:
            {success, total_chunks, pages_processed}
        """
        t0 = time.time()
        logger.info(f"🔧 Processing {len(pages)} pages → collection '{collection_name}'")

        # مرحله ۱: تبدیل صفحات به chunks
        all_chunks: List[WebChunk] = []
        chunk_offset = 0
        for page in pages:
            page_chunks = self.page_to_chunks(
                page_url=page["url"],
                content=page["content"],
                page_metadata=page.get("metadata", {}),
                base_chunk_index=chunk_offset,
            )
            all_chunks.extend(page_chunks)
            chunk_offset += len(page_chunks)

            # ساخت virtual chunks برای آیتم‌های ساختاریافته (محصولات/قیمت‌ها)
            page_meta = page.get("metadata", {})
            raw_structured_items = (
                page.get("_structured_items")
                or page.get("metadata", {}).get("_structured_items")
                or []
            )
            # فیلتر کردن آیتم‌های navigation (بدون قیمت و با عنوان کوتاه)
            structured_items = [
                it for it in raw_structured_items
                if it.get("title") and (
                    it.get("price") or
                    it.get("description") or
                    len(it.get("title", "")) > 10
                )
            ]

            # همیشه از page_product_meta (با قیمت واقعی صفحه) virtual chunk بساز
            # این chunk مهم‌ترین است چون قیمت و عنوان واقعی محصول دارد
            if page_meta.get("page_product_title") and page_meta.get("page_product_price"):
                page_product = {
                    "title": page_meta["page_product_title"],
                    "price": page_meta["page_product_price"],
                    "description": page_meta.get("page_product_description", ""),
                    "link": page["url"],
                    "image": page_meta.get("page_product_image", ""),
                }
                # اضافه کردن به ابتدای لیست (اولویت بالا)
                structured_items = [page_product] + [
                    it for it in structured_items
                    if it.get("link") != page["url"]  # جلوگیری از تکرار
                ]

            if structured_items:
                for item in structured_items:
                    item_chunk = self._item_to_virtual_chunk(
                        item=item,
                        page_url=page["url"],
                        page_metadata=page.get("metadata", {}),
                        chunk_index=chunk_offset,
                    )
                    if item_chunk:
                        all_chunks.append(item_chunk)
                        chunk_offset += 1

        logger.info(f"  📄 {len(all_chunks)} chunks from {len(pages)} pages")

        if not all_chunks:
            return {"success": False, "error": "هیچ chunk‌ای تولید نشد", "total_chunks": 0}

        # مرحله ۲: تولید embeddings
        logger.info("  🔢 Generating embeddings...")
        texts = [c.text for c in all_chunks]
        embeddings = self._embed_texts(texts)
        logger.info(f"  ✅ {len(embeddings)} embeddings generated")

        # مرحله ۳: ذخیره در ChromaDB
        client = self._get_chroma_client()

        if overwrite:
            try:
                client.delete_collection(collection_name)
                logger.info(f"  🗑️ Deleted existing collection: {collection_name}")
            except Exception:
                pass

        # دریافت embedding dim
        try:
            from services.persian_embedding_service import HEYDARI_EMBEDDING_DIM
            emb_dim = HEYDARI_EMBEDDING_DIM
        except Exception:
            emb_dim = len(embeddings[0]) if embeddings else 1024

        try:
            collection = client.get_collection(collection_name)
        except Exception:
            collection = client.create_collection(
                name=collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "source_type": "web_crawl",
                    "embedding_dim": str(emb_dim),
                    "created_at": datetime.utcnow().isoformat(),
                },
            )
            logger.info(f"  ✅ Created collection: {collection_name}")

        # تعیین offset برای append mode
        existing_count = 0
        if not overwrite:
            try:
                existing_count = collection.count()
            except Exception:
                existing_count = 0

        ids, documents, meta_list, valid_embs = [], [], [], []
        for chunk, emb in zip(all_chunks, embeddings):
            text = chunk.text.strip()
            if not text or len(text) < 20:
                continue
            chunk_id = f"{collection_name}_web_{existing_count + chunk.chunk_index}"
            ids.append(chunk_id)
            documents.append(text)
            valid_embs.append(emb)
            # پاکسازی metadata برای ChromaDB (فقط str/int/float/bool)
            clean_meta = {}
            for k, v in chunk.metadata.items():
                if v is None:
                    continue
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)
            meta_list.append(clean_meta)

        # ذخیره batch به batch
        batch_size = 100
        saved = 0
        for i in range(0, len(ids), batch_size):
            end = min(i + batch_size, len(ids))
            collection.add(
                ids=ids[i:end],
                documents=documents[i:end],
                embeddings=valid_embs[i:end],
                metadatas=meta_list[i:end],
            )
            saved += end - i

        elapsed = time.time() - t0
        logger.info(
            f"  💾 Saved {saved} chunks to '{collection_name}' "
            f"in {elapsed:.1f}s"
        )

        return {
            "success": True,
            "total_chunks": saved,
            "pages_processed": len(pages),
            "elapsed_seconds": round(elapsed, 1),
        }
