# -*- coding: utf-8 -*-
"""
Smart Persian PDF Processor
پردازشگر هوشمند PDF فارسی

قابلیت‌ها:
- تشخیص خودکار نوع PDF (متنی / تصویری / ترکیبی)
- استخراج متن با ترتیب‌بندی RTL بر اساس موقعیت کاراکترها
- اصلاح اعداد معکوس شده ناشی از RTL
- استخراج جداول با AdvancedPDFTableProcessor
- Chunking هوشمند اسناد حقوقی/فنی
- Fallback به OCR برای صفحات تصویری
- Embedding با heydariAI/persian-embeddings (1024-dim)
- ذخیره در ChromaDB
"""

import io
import re
import unicodedata
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

from services.persian_embedding_service import HEYDARI_MODEL_LOCAL_PATH, HEYDARI_EMBEDDING_DIM, get_heydari_model
EMBEDDING_MODEL = HEYDARI_MODEL_LOCAL_PATH
EMBEDDING_DIM = HEYDARI_EMBEDDING_DIM
CHROMA_DB_PATH = "/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db"


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PDFTypeInfo:
    pdf_type: str          # "text" | "image" | "hybrid"
    text_extractable: bool
    text_ratio: float      # ratio of pages with extractable text
    total_pages: int
    avg_chars_per_page: float
    has_persian: bool = False


@dataclass
class ProcessedChunk:
    text: str
    chunk_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingStats:
    total_pages: int = 0
    text_pages: int = 0
    image_pages: int = 0
    total_chunks: int = 0
    text_chunks: int = 0
    table_chunks: int = 0
    ocr_chunks: int = 0
    total_chars: int = 0
    processing_time: float = 0.0
    errors: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Core text helpers
# ─────────────────────────────────────────────────────────────────────────────

def normalize_persian(text: str) -> str:
    """NFKC normalization + Arabic→Persian character mapping"""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    mapping = {"ي": "ی", "ك": "ک", "ة": "ه", "ى": "ی"}
    return "".join(mapping.get(c, c) for c in text)


def has_persian_chars(text: str) -> bool:
    return any("\u0600" <= c <= "\u06FF" for c in text)


def fix_rtl_numbers(text: str) -> str:
    """
    اصلاح اعداد دو/سه رقمی که به خاطر RTL معکوس ذخیره شده‌اند.
    شناسایی از روی متن توضیحی داخل پرانتز.
    مثال: '42 (چهلودو)' ← '24 (چهلودو)'
    """
    if not text:
        return text

    persian_num_map = {
        # معکوس → درست
        "24": ("چهلودو",  "42"),
        "52": ("بیستوپنج", "25"),
        "63": ("شصتوسه",  "36"),
        "17": ("هفتادویک","71"),
        "81": ("هجده",    "18"),
        "91": ("نودویک",  "19"),
        "12": ("بیستویک", "21"),
        "31": ("سیزده",   "13"),
        "41": ("چهارده",  "14"),
        "51": ("پانزده",  "15"),
        "61": ("شانزده",  "16"),
        "71": ("هفده",    "17"),
        "48": ("چهل",     "84"),
        "39": ("نودوسه",  "93"),
        "49": ("نودوچهار","94"),
        "59": ("نودوپنج", "95"),
        "69": ("نودوشش",  "96"),
        "79": ("نودوهفت", "97"),
    }

    def _replace(m: re.Match) -> str:
        num = m.group(1)
        desc = m.group(2)
        if num in persian_num_map:
            fa_keyword, correct_num = persian_num_map[num]
            if fa_keyword in desc:
                return f"{correct_num} ({desc})"
        return m.group(0)

    pattern = re.compile(r"\b(\d{2,3})\s*\(([^)]{3,40})\)")
    return pattern.sub(_replace, text)


def extract_page_text_rtl(page) -> str:
    """
    استخراج متن صفحه با ترتیب‌بندی RTL مبتنی بر موقعیت کاراکترها.
    این روش دقیق‌ترین نتیجه را برای PDFهای فارسی می‌دهد.
    """
    chars = page.chars
    if not chars:
        return ""

    y_tolerance = 3.0
    lines: Dict[float, list] = defaultdict(list)
    for char in chars:
        y_key = round(char["y0"] / y_tolerance) * y_tolerance
        lines[y_key].append(char)

    result_lines = []
    for y in sorted(lines.keys()):
        line_chars = sorted(lines[y], key=lambda c: c["x0"], reverse=True)
        line_text = "".join(normalize_persian(c["text"]) for c in line_chars).strip()
        if line_text:
            result_lines.append(line_text)

    return "\n".join(result_lines)


def clean_page_text(text: str) -> str:
    """پاکسازی متن صفحه از header/footer و خطوط ناخواسته"""
    if not text:
        return ""
    text = fix_rtl_numbers(text)
    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if re.match(r"^\d{1,3}$", stripped):
            continue
        if len(stripped) < 2:
            continue
        lines.append(stripped)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Chunking
# ─────────────────────────────────────────────────────────────────────────────

def smart_chunk_text(
    text: str,
    base_metadata: Dict[str, Any],
    chunk_size: int = 700,
    overlap: int = 100,
) -> List[ProcessedChunk]:
    """
    Chunking هوشمند:
    - ابتدا تلاش می‌کند بر اساس مواد/بندهای حقوقی chunk کند
    - در صورت کمبود مواد، از sliding window استفاده می‌کند
    """
    chunks = []
    chunk_idx = 0

    article_pattern = re.compile(
        r"(?:^|\n)\s*(ماده\s+\d+|ماده\s+[۰-۹]+|بند\s+\d+[-.]?\d*|تبصره\s*\d*|فصل\s+\d+)",
        re.MULTILINE,
    )
    article_matches = list(article_pattern.finditer(text))

    if len(article_matches) >= 3:
        for j, match in enumerate(article_matches):
            start = match.start()
            end = (
                article_matches[j + 1].start()
                if j + 1 < len(article_matches)
                else len(text)
            )
            article_text = text[start:end].strip()
            if not article_text or len(article_text) < 20:
                continue

            article_header = match.group(1).strip()

            if len(article_text) > chunk_size * 2:
                sub_chunks = _sliding_window(article_text, chunk_size, overlap)
                for k, sub in enumerate(sub_chunks):
                    chunks.append(
                        ProcessedChunk(
                            text=sub,
                            chunk_index=chunk_idx,
                            metadata={
                                **base_metadata,
                                "article": article_header,
                                "sub_chunk": k,
                                "chunk_type": "article_part",
                            },
                        )
                    )
                    chunk_idx += 1
            else:
                chunks.append(
                    ProcessedChunk(
                        text=article_text,
                        chunk_index=chunk_idx,
                        metadata={
                            **base_metadata,
                            "article": article_header,
                            "sub_chunk": 0,
                            "chunk_type": "article",
                        },
                    )
                )
                chunk_idx += 1
    else:
        for k, sub in enumerate(_sliding_window(text, chunk_size, overlap)):
            chunks.append(
                ProcessedChunk(
                    text=sub,
                    chunk_index=chunk_idx,
                    metadata={
                        **base_metadata,
                        "sub_chunk": k,
                        "chunk_type": "sliding_window",
                    },
                )
            )
            chunk_idx += 1

    return chunks


def _sliding_window(text: str, chunk_size: int, overlap: int) -> List[str]:
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        break_point = end
        for sep in ["\n", ".", "،", " "]:
            pos = text.rfind(sep, start + chunk_size // 2, end)
            if pos > start:
                break_point = pos + 1
                break

        chunk = text[start:break_point].strip()
        if chunk:
            chunks.append(chunk)
        start = break_point - overlap
        if start < 0:
            start = 0

    return chunks


def table_to_text(table: Dict[str, Any], source_label: str = "") -> str:
    """تبدیل داده جدول به متن ساختاریافته"""
    lines = []
    if source_label:
        lines.append(f"[جدول - {source_label} - صفحه {table.get('page', '?')}]")
    headers = table.get("headers", [])
    if headers:
        header_paths = [h.get("full_path", "") for h in headers if h.get("full_path")]
        if header_paths:
            lines.append("ستون‌ها: " + " | ".join(header_paths))
    for row in table.get("rows", [])[:40]:
        cells = [str(c) for c in row.get("cells", []) if c and str(c).strip()]
        if cells:
            lines.append(" | ".join(cells))
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Main processor class
# ─────────────────────────────────────────────────────────────────────────────

class SmartPersianPDFProcessor:
    """
    پردازشگر هوشمند PDF فارسی
    
    این کلاس تمام منطق پردازش PDF فارسی را در خود دارد:
    1. تشخیص نوع PDF
    2. استخراج متن (RTL-aware)
    3. استخراج جداول
    4. اصلاح اعداد معکوس
    5. Chunking هوشمند
    6. Embedding با heydariAI
    7. ذخیره در ChromaDB
    """

    _embed_model = None  # singleton

    def __init__(
        self,
        chroma_db_path: str = CHROMA_DB_PATH,
        embedding_model: str = EMBEDDING_MODEL,
        chunk_size: int = 700,
        chunk_overlap: int = 100,
        ocr_dpi: int = 200,
    ):
        self.chroma_db_path = chroma_db_path
        self.embedding_model_name = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.ocr_dpi = ocr_dpi
        self._table_processor = None

    # ── lazy loaders ──────────────────────────────────────────────────────────

    def _get_embed_model(self):
        if SmartPersianPDFProcessor._embed_model is None:
            logger.info("🔄 Loading heydariAI embedding model from local cache...")
            SmartPersianPDFProcessor._embed_model = get_heydari_model()
            logger.info("✅ Embedding model loaded")
        return SmartPersianPDFProcessor._embed_model

    def _get_table_processor(self):
        if self._table_processor is None:
            from processors.advanced_pdf_table_processor import AdvancedPDFTableProcessor
            self._table_processor = AdvancedPDFTableProcessor()
        return self._table_processor

    def _get_chroma_client(self):
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        # استفاده از همان Settings که ultimate_rag_system استفاده می‌کند
        # تا از خطای "different settings" جلوگیری شود
        return chromadb.PersistentClient(
            path=self.chroma_db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=False,
            )
        )

    # ── public API ────────────────────────────────────────────────────────────

    def detect_pdf_type(self, pdf_bytes: bytes) -> PDFTypeInfo:
        """تشخیص نوع PDF: متنی / تصویری / ترکیبی"""
        try:
            import pdfplumber

            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                total_pages = len(pdf.pages)
                sample = min(5, total_pages)
                pages_with_text = 0
                total_chars = 0
                has_persian = False

                for i in range(sample):
                    page = pdf.pages[i]
                    text = page.extract_text() or ""
                    if len(text.strip()) > 50:
                        pages_with_text += 1
                        total_chars += len(text.strip())
                    if has_persian_chars(text):
                        has_persian = True

            text_ratio = pages_with_text / sample if sample else 0
            avg_chars = total_chars / sample if sample else 0

            if text_ratio >= 0.7 and avg_chars > 100:
                pdf_type = "text"
            elif text_ratio <= 0.2 or avg_chars < 50:
                pdf_type = "image"
            else:
                pdf_type = "hybrid"

            return PDFTypeInfo(
                pdf_type=pdf_type,
                text_extractable=(pdf_type in ("text", "hybrid")),
                text_ratio=text_ratio,
                total_pages=total_pages,
                avg_chars_per_page=avg_chars,
                has_persian=has_persian,
            )

        except Exception as e:
            logger.warning(f"PDF type detection failed: {e}")
            return PDFTypeInfo("unknown", False, 0.0, 0, 0.0)

    def extract_text_from_pdf(self, pdf_bytes: bytes) -> Tuple[str, int]:
        """
        استخراج متن کامل PDF با روش RTL char-position.
        Returns (full_text, page_count)
        """
        import pdfplumber

        page_texts = []
        page_count = 0

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            page_count = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                # روش اول: char-position (بهترین برای فارسی RTL)
                text = extract_page_text_rtl(page)

                # fallback: extract_text استاندارد
                if not text or len(text) < 30:
                    raw = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                    if raw:
                        text = normalize_persian(raw)

                text = clean_page_text(text)
                if text:
                    page_texts.append(f"\n--- صفحه {i+1} ---\n{text}")

        return "\n".join(page_texts), page_count

    def extract_tables_from_pdf(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """استخراج جداول با AdvancedPDFTableProcessor"""
        try:
            processor = self._get_table_processor()
            tables = processor.extract_tables_advanced(pdf_bytes)
            logger.info(f"  📊 Extracted {len(tables)} tables")
            return tables
        except Exception as e:
            logger.warning(f"Table extraction failed: {e}")
            return []

    def process_image_pages_with_ocr(
        self, pdf_bytes: bytes, page_indices: List[int]
    ) -> str:
        """OCR برای صفحات تصویری"""
        try:
            import fitz
            from PIL import Image
            import easyocr

            reader = easyocr.Reader(["fa", "en"], gpu=False, verbose=False)
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            texts = []

            for idx in page_indices:
                if idx >= len(doc):
                    continue
                page = doc[idx]
                mat = fitz.Matrix(self.ocr_dpi / 72, self.ocr_dpi / 72)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                results = reader.readtext(
                    img, detail=0, paragraph=True, text_threshold=0.5
                )
                page_text = " ".join(results)
                if page_text.strip():
                    texts.append(f"\n--- صفحه {idx+1} (OCR) ---\n{page_text}")

            doc.close()
            return "\n".join(texts)

        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return ""

    def create_chunks(
        self,
        full_text: str,
        tables: List[Dict[str, Any]],
        base_metadata: Dict[str, Any],
    ) -> List[ProcessedChunk]:
        """ایجاد chunks از متن و جداول"""
        chunks = smart_chunk_text(
            full_text, base_metadata, self.chunk_size, self.chunk_overlap
        )
        text_count = len(chunks)

        for t_idx, table in enumerate(tables):
            t_text = table_to_text(table, base_metadata.get("short_name", ""))
            if t_text and len(t_text) > 30:
                chunks.append(
                    ProcessedChunk(
                        text=t_text,
                        chunk_index=text_count + t_idx,
                        metadata={
                            **base_metadata,
                            "page": table.get("page", 0),
                            "chunk_type": "table",
                            "table_index": t_idx,
                        },
                    )
                )

        return chunks

    def embed_chunks(self, chunks: List[ProcessedChunk]) -> List[List[float]]:
        """تولید embeddings برای تمام chunks"""
        model = self._get_embed_model()
        texts = [c.text for c in chunks]
        batch_size = 32
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embs = model.encode(batch, show_progress_bar=False).tolist()
            all_embeddings.extend(embs)
        return all_embeddings

    def save_to_collection(
        self,
        collection_name: str,
        chunks: List[ProcessedChunk],
        embeddings: List[List[float]],
        collection_metadata: Dict[str, Any],
        overwrite: bool = True,
        append: bool = False,
    ) -> Dict[str, Any]:
        """
        ذخیره chunks در ChromaDB.
        
        overwrite=True: کالکشن قبلی را حذف و دوباره می‌سازد
        append=True: به کالکشن موجود اضافه می‌کند
        """
        client = self._get_chroma_client()

        if overwrite and not append:
            try:
                client.delete_collection(collection_name)
                logger.info(f"  🗑️ Deleted existing collection: {collection_name}")
            except Exception:
                pass

        try:
            collection = client.get_collection(collection_name)
            logger.info(
                f"  📚 Using existing collection: {collection_name} "
                f"({collection.count()} docs)"
            )
        except Exception:
            collection = client.create_collection(
                name=collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "embedding_model": self.embedding_model_name,
                    "embedding_dim": str(EMBEDDING_DIM),
                    **{k: str(v) for k, v in collection_metadata.items()},
                },
            )
            logger.info(f"  ✅ Created new collection: {collection_name}")

        # تعیین offset برای append mode
        offset = 0
        if append:
            try:
                existing = client.get_collection(collection_name)
                offset = existing.count()
            except Exception:
                offset = 0

        ids, documents, meta_list, valid_embs = [], [], [], []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            text = chunk.text.strip()
            if not text or len(text) < 10:
                continue
            ids.append(f"{collection_name}_{offset + chunk.chunk_index}")
            documents.append(text)
            valid_embs.append(emb)
            meta = {
                k: (str(v) if not isinstance(v, (str, int, float, bool)) else v)
                for k, v in chunk.metadata.items()
                if v is not None
            }
            meta_list.append(meta)

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

        logger.info(f"  💾 Saved {saved} chunks to {collection_name}")

        # Pre-build dynamic vocabulary for IDF-based keyword scoring
        try:
            from core.collection_enhanced_search import CollectionEnhancedSearch
            CollectionEnhancedSearch.invalidate_cache(collection_name)
            vocab_size = CollectionEnhancedSearch.prebuild_vocab(collection)
            logger.info(f"  📚 [VOCAB] Pre-built vocabulary for '{collection_name}': {vocab_size} terms")
        except Exception as e:
            logger.warning(f"  ⚠️ [VOCAB] Failed to pre-build vocabulary: {e}")

        return {"success": True, "saved": saved, "total": len(ids)}

    # ── full pipeline ─────────────────────────────────────────────────────────

    def process_single_pdf(
        self,
        pdf_bytes: bytes,
        filename: str,
        collection_name: str,
        extra_metadata: Optional[Dict[str, Any]] = None,
        chunk_offset: int = 0,
    ) -> Tuple[List[ProcessedChunk], ProcessingStats]:
        """
        پردازش کامل یک فایل PDF.
        مناسب برای multi-file pipeline که chunks را جمع می‌کند.
        """
        stats = ProcessingStats()
        t0 = time.time()

        # تشخیص نوع
        pdf_info = self.detect_pdf_type(pdf_bytes)
        stats.total_pages = pdf_info.total_pages
        logger.info(
            f"  🔍 PDF type: {pdf_info.pdf_type} "
            f"(pages={pdf_info.total_pages}, text_ratio={pdf_info.text_ratio:.0%})"
        )

        base_metadata = {
            "source_file": filename,
            "collection": collection_name,
            "pdf_type": pdf_info.pdf_type,
            **(extra_metadata or {}),
        }

        full_text = ""
        tables = []

        # استخراج متن
        if pdf_info.text_extractable:
            logger.info("  📄 Extracting text (RTL char-position)...")
            full_text, _ = self.extract_text_from_pdf(pdf_bytes)
            stats.text_pages = int(pdf_info.text_ratio * pdf_info.total_pages)
            stats.total_chars = len(full_text)
            logger.info(f"  ✅ Text extracted: {len(full_text):,} chars")

        # OCR fallback برای صفحات بدون متن
        if pdf_info.pdf_type in ("image", "hybrid") or (
            pdf_info.pdf_type == "text" and len(full_text) < 500
        ):
            logger.info("  🖼️ Running OCR fallback for image pages...")
            try:
                import pdfplumber

                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    image_pages = [
                        i
                        for i, p in enumerate(pdf.pages)
                        if not p.extract_text()
                        or len((p.extract_text() or "").strip()) < 50
                    ]

                if image_pages:
                    ocr_text = self.process_image_pages_with_ocr(pdf_bytes, image_pages)
                    if ocr_text:
                        full_text = full_text + "\n" + ocr_text
                        stats.image_pages = len(image_pages)
                        logger.info(
                            f"  ✅ OCR added {len(ocr_text):,} chars from {len(image_pages)} pages"
                        )
            except Exception as e:
                logger.warning(f"  ⚠️ OCR fallback error: {e}")

        if not full_text.strip():
            logger.error(f"  ❌ No text extracted from {filename}")
            stats.errors.append(f"No text extracted from {filename}")
            return [], stats

        # استخراج جداول
        logger.info("  📊 Extracting tables...")
        tables = self.extract_tables_from_pdf(pdf_bytes)
        stats.table_chunks = len(tables)

        # Chunking
        logger.info("  ✂️ Chunking text...")
        chunks = self.create_chunks(full_text, tables, base_metadata)

        # تنظیم global offset
        for c in chunks:
            c.chunk_index += chunk_offset

        stats.total_chunks = len(chunks)
        stats.text_chunks = len(chunks) - len(tables)
        stats.processing_time = time.time() - t0

        logger.info(
            f"  ✅ {len(chunks)} chunks "
            f"(text={stats.text_chunks}, tables={stats.table_chunks}) "
            f"in {stats.processing_time:.1f}s"
        )
        return chunks, stats

    def build_collection_from_files(
        self,
        pdf_files: List[Dict[str, Any]],
        collection_name: str,
        collection_metadata: Optional[Dict[str, Any]] = None,
        overwrite: bool = True,
        append: bool = False,
    ) -> Dict[str, Any]:
        """
        ساخت کالکشن از چند فایل PDF.
        
        Args:
            pdf_files: لیست دیکشنری‌ها با کلیدهای:
                - bytes: محتوای PDF
                - filename: نام فایل
                - metadata: متادیتای اضافی (اختیاری)
            collection_name: نام کالکشن
            collection_metadata: متادیتای کالکشن
            overwrite: حذف کالکشن قبلی
            append: افزودن به کالکشن موجود
        
        Returns:
            dict با کلیدهای success, chunks_count, stats_per_file, ...
        """
        t_start = time.time()
        all_chunks: List[ProcessedChunk] = []
        stats_per_file = []
        global_offset = 0

        logger.info(f"🚀 Building collection '{collection_name}' from {len(pdf_files)} files")

        for file_info in pdf_files:
            pdf_bytes = file_info["bytes"]
            filename = file_info.get("filename", "unknown.pdf")
            extra_meta = file_info.get("metadata", {})

            logger.info(f"\n{'='*50}\n📄 {filename}\n{'='*50}")

            chunks, stats = self.process_single_pdf(
                pdf_bytes=pdf_bytes,
                filename=filename,
                collection_name=collection_name,
                extra_metadata=extra_meta,
                chunk_offset=global_offset,
            )

            all_chunks.extend(chunks)
            global_offset += len(chunks)
            stats_per_file.append(
                {
                    "filename": filename,
                    "chunks": stats.total_chunks,
                    "text_chunks": stats.text_chunks,
                    "table_chunks": stats.table_chunks,
                    "ocr_chunks": stats.ocr_chunks,
                    "pages": stats.total_pages,
                    "time": round(stats.processing_time, 1),
                    "errors": stats.errors,
                }
            )

        if not all_chunks:
            return {
                "success": False,
                "error": "No chunks extracted from any file",
                "stats_per_file": stats_per_file,
            }

        # Embedding
        logger.info(f"\n🔄 Generating embeddings for {len(all_chunks)} chunks...")
        t_emb = time.time()
        embeddings = self.embed_chunks(all_chunks)
        logger.info(f"  ✅ Embeddings done in {time.time() - t_emb:.1f}s")

        # Save
        coll_meta = {
            "sources": ", ".join(f["filename"] for f in pdf_files),
            "processing_type": "smart_persian_pdf",
            "embedding_model": self.embedding_model_name,
            "embedding_dim": str(EMBEDDING_DIM),
            **(collection_metadata or {}),
        }
        save_result = self.save_to_collection(
            collection_name=collection_name,
            chunks=all_chunks,
            embeddings=embeddings,
            collection_metadata=coll_meta,
            overwrite=overwrite,
            append=append,
        )

        total_time = time.time() - t_start
        logger.info(
            f"\n✅ Collection '{collection_name}' built: "
            f"{save_result['saved']} chunks in {total_time:.1f}s"
        )

        return {
            "success": True,
            "collection_name": collection_name,
            "total_chunks": save_result["saved"],
            "total_files": len(pdf_files),
            "total_time": round(total_time, 1),
            "stats_per_file": stats_per_file,
        }
