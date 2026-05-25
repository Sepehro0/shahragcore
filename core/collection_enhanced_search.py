# -*- coding: utf-8 -*-
"""
Collection Enhanced Search — Generic IDF-based keyword scoring for ANY collection.

رویکرد:
- واژگان به صورت داینامیک از خود داده‌های collection ساخته می‌شوند (TF-IDF)
- فیلدهای metadata به صورت خودکار شناسایی و وزن‌دهی می‌شوند
- هیچ لیست کلمات کلیدی استاتیکی وجود ندارد
- هر collection (zabete_qa, col_xxx, ...) می‌تواند از این سیستم بهره ببرد
"""

import re
import math
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class CollectionEnhancedSearch:
    """
    سیستم IDF-based keyword scoring عمومی.

    - واژگان و وزن فیلدها به صورت خودکار از collection استخراج می‌شوند
    - cache سطح class: هر collection فقط یک‌بار vocab ساخته می‌شود
    - قابل استفاده برای هر collection (نه فقط zabete_qa)
    """

    # ── Class-level caches ──
    _vocab_cache: Dict[str, Dict[str, float]] = {}
    _field_weights_cache: Dict[str, Dict[str, float]] = {}

    BOKSHNAME_PATTERNS = [
        r'\d+/\d+',
        r'\d+-\d+',
        r'\d{4,}',
    ]

    PERSIAN_STOPWORDS = {
        'و', 'در', 'به', 'از', 'که', 'این', 'را', 'با', 'برای', 'آن',
        'یک', 'هم', 'تا', 'بر', 'هر', 'نیز', 'یا', 'آیا', 'چه', 'هیچ',
        'است', 'بود', 'شد', 'شده', 'باشد', 'می', 'های', 'ها', 'شود',
        'کند', 'دارد', 'بوده', 'نمی', 'آنها', 'خود', 'دیگر', 'اگر',
        'هنگام', 'همه', 'ولی', 'اما', 'پس', 'زیرا', 'بین', 'روی',
        'چگونه', 'چیست', 'چیست؟', 'کجاست', 'کجاست؟', 'چطور',
        'نحوه', 'خصوص', 'خاص', 'دقیق', 'حدود', 'نظر',
        'است؟', 'شود؟', 'گردد', 'گردد؟', 'باشد؟', 'کجاست؟',
        'صورت', 'مورد', 'طریق', 'عنوان', 'قالب',
    }

    # فیلدهای metadata که خیلی بزرگ یا غیرمفید هستند و باید skip شوند
    _SKIP_FIELDS = {
        'source_file', 'row_number', 'row_index', 'chunk_index',
        'page_number', 'page_numbers', 'file_name', 'filename',
        'total_pages', 'processing_date', 'timestamp',
        'embedding_model', 'embedding_dim', 'hnsw:space',
        'question_number', 'type', 'source',
    }

    def __init__(self, collection):
        self.collection = collection
        self._all_docs_cache = None

    # ─────────────────────────────────────────────
    # Core helpers
    # ─────────────────────────────────────────────

    def _get_all_docs(self) -> Dict[str, Any]:
        if self._all_docs_cache is None:
            self._all_docs_cache = self.collection.get(
                include=['metadatas', 'documents']
            )
        return self._all_docs_cache

    @staticmethod
    def normalize_text(text: str) -> str:
        if not text:
            return ""
        text = text.replace('ي', 'ی').replace('ى', 'ی')
        text = text.replace('ك', 'ک')
        for p, e in zip('۰۱۲۳۴۵۶۷۸۹', '0123456789'):
            text = text.replace(p, e)
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('\u200c', ' ')
        text = text.replace('\u00ad', '')
        return text.strip().lower()

    def _col_name(self) -> str:
        return getattr(self.collection, 'name', str(id(self.collection)))

    # ─────────────────────────────────────────────
    # Auto-discover field weights
    # ─────────────────────────────────────────────

    def _get_field_weights(self) -> Dict[str, float]:
        """
        فیلدهای metadata و وزنشان را به صورت خودکار تشخیص بده.

        استراتژی وزن‌دهی:
        - فیلدهای «سوالی» (question, query, ...) → وزن بالا (3.0)
        - فیلدهای «جوابی» (answer, content, text, ...) → وزن خوب (2.5)
        - فیلدهای «عنوانی» (title, name, ...) → وزن خوب (2.5)
        - فیلدهای «دسته‌بندی» (category, tag, section, ...) → وزن متوسط (2.0)
        - بقیه فیلدهای متنی → وزن پایه (1.0)
        """
        cn = self._col_name()
        if cn in self.__class__._field_weights_cache:
            return self.__class__._field_weights_cache[cn]

        all_docs = self._get_all_docs()
        metadatas = all_docs.get('metadatas', [])
        if not metadatas:
            return {}

        # شمارش فیلدها و بررسی محتوا
        field_stats: Dict[str, int] = {}
        for meta in metadatas[:100]:  # نمونه 100 doc اول
            if not meta:
                continue
            for key, val in meta.items():
                if key in self._SKIP_FIELDS:
                    continue
                s = str(val).strip()
                if not s or len(s) < 2:
                    continue
                field_stats[key] = field_stats.get(key, 0) + 1

        # حذف فیلدهایی که در کمتر از 10% docs هستند
        threshold = max(len(metadatas[:100]) * 0.1, 1)
        active_fields = {k for k, v in field_stats.items() if v >= threshold}

        # وزن‌دهی خودکار بر اساس نام فیلد
        question_patterns = {'question', 'query', 'سوال', 'پرسش'}
        answer_patterns = {'answer', 'content', 'text', 'جواب', 'پاسخ', 'متن'}
        title_patterns = {'title', 'name', 'عنوان', 'نام', 'zabete_title', 'madde_title'}
        category_patterns = {'category', 'subcategory', 'section', 'tag', 'topic',
                             'دسته', 'بخش', 'موضوع', 'تگ', 'code', 'کد'}

        weights: Dict[str, float] = {}
        for field in active_fields:
            fl = field.lower()
            if fl in question_patterns or any(p in fl for p in question_patterns):
                weights[field] = 3.0
            elif fl in answer_patterns or any(p in fl for p in answer_patterns):
                weights[field] = 2.5
            elif fl in title_patterns or any(p in fl for p in title_patterns):
                weights[field] = 2.5
            elif fl in category_patterns or any(p in fl for p in category_patterns):
                weights[field] = 2.0
            else:
                avg_len = 0
                sample_count = 0
                for meta in metadatas[:50]:
                    if meta and field in meta:
                        avg_len += len(str(meta[field]))
                        sample_count += 1
                avg_len = avg_len / max(sample_count, 1)
                weights[field] = 1.5 if avg_len > 20 else 1.0

        self.__class__._field_weights_cache[cn] = weights
        logger.info(f"🏗️ [FIELDS] Auto-discovered {len(weights)} fields for '{cn}': {list(weights.keys())}")
        return weights

    # ─────────────────────────────────────────────
    # Dynamic Vocabulary (IDF-based)
    # ─────────────────────────────────────────────

    def _get_vocab(self) -> Dict[str, float]:
        cn = self._col_name()
        if cn not in self.__class__._vocab_cache:
            self.__class__._vocab_cache[cn] = self._build_vocab()
            logger.info(
                f"📚 [VOCAB] Built vocabulary for '{cn}': "
                f"{len(self.__class__._vocab_cache[cn])} terms"
            )
        return self.__class__._vocab_cache[cn]

    def _build_vocab(self) -> Dict[str, float]:
        """
        ساخت واژگان IDF از محتوای collection.
        فیلدها به صورت خودکار تشخیص داده می‌شوند.
        """
        all_docs = self._get_all_docs()
        metadatas = all_docs.get('metadatas', [])
        documents = all_docs.get('documents', [])
        if not metadatas and not documents:
            return {}

        total_docs = max(len(metadatas), len(documents))
        term_doc_count: Dict[str, int] = {}
        field_weights = self._get_field_weights()
        searchable_fields = list(field_weights.keys()) if field_weights else []

        for idx in range(total_docs):
            parts = []
            if idx < len(metadatas) and metadatas[idx]:
                for f in searchable_fields:
                    val = str(metadatas[idx].get(f, ''))
                    if val and len(val) > 1:
                        parts.append(val)
            if idx < len(documents) and documents[idx]:
                parts.append(documents[idx])

            combined = ' '.join(parts)
            normalized = self.normalize_text(combined)
            words = [w for w in normalized.split()
                     if len(w) > 1 and w not in self.PERSIAN_STOPWORDS]
            words = [re.sub(r'^[«»()\[\]{}،,.؟!:;]+|[«»()\[\]{}،,.؟!:;]+$', '', w)
                     for w in words]
            words = [w for w in words if len(w) > 1]

            doc_terms: set = set()
            for w in words:
                doc_terms.add(w)
            for i in range(len(words) - 1):
                doc_terms.add(f"{words[i]} {words[i+1]}")

            for term in doc_terms:
                term_doc_count[term] = term_doc_count.get(term, 0) + 1

        vocab: Dict[str, float] = {}
        for term, df in term_doc_count.items():
            vocab[term] = math.log(total_docs / max(df, 1)) + 1.0
        return vocab

    @classmethod
    def prebuild_vocab(cls, collection) -> int:
        """
        Pre-build vocab at collection creation time.
        Returns number of terms in vocabulary.
        """
        searcher = cls(collection)
        vocab = searcher._get_vocab()
        return len(vocab)

    @classmethod
    def invalidate_cache(cls, collection_name: str):
        """حذف cache یک collection (مثلاً بعد از اضافه شدن docs جدید)"""
        cls._vocab_cache.pop(collection_name, None)
        cls._field_weights_cache.pop(collection_name, None)

    # ─────────────────────────────────────────────
    # Keyword extraction
    # ─────────────────────────────────────────────

    def _extract_keywords(self, query: str) -> List[str]:
        """
        استخراج کلمات کلیدی از query.
        فقط term هایی که در collection vocab وجود دارند استخراج می‌شوند.
        """
        vocab = self._get_vocab()
        query_normalized = self.normalize_text(query)
        keywords: List[str] = []
        seen: set = set()

        for pattern in self.BOKSHNAME_PATTERNS:
            for m in re.findall(pattern, query):
                if m not in seen:
                    keywords.append(m)
                    seen.add(m)

        query_words = query_normalized.split()
        meaningful = [w for w in query_words
                      if len(w) > 2 and w not in self.PERSIAN_STOPWORDS
                      and not re.match(r'^[«»()\[\]{}؟!,،.]+$', w)]
        meaningful = [re.sub(r'^[«»()\[\]{}،,.؟!:;]+|[«»()\[\]{}،,.؟!:;]+$', '', w)
                      for w in meaningful]
        meaningful = [w for w in meaningful if len(w) > 2]

        for word in meaningful:
            wn = self.normalize_text(word)
            if wn not in seen and wn in vocab:
                keywords.append(word)
                seen.add(wn)

        for i in range(len(meaningful) - 1):
            bigram = f"{meaningful[i]} {meaningful[i+1]}"
            bn = self.normalize_text(bigram)
            if bn in query_normalized and bn not in seen and bn in vocab:
                keywords.append(bigram)
                seen.add(bn)

        for i in range(len(meaningful) - 2):
            trigram = f"{meaningful[i]} {meaningful[i+1]} {meaningful[i+2]}"
            tn = self.normalize_text(trigram)
            if tn in query_normalized and tn not in seen:
                keywords.append(trigram)
                seen.add(tn)

        return keywords

    # ─────────────────────────────────────────────
    # Keyword scoring
    # ─────────────────────────────────────────────

    def calculate_keyword_score(
        self,
        query: str,
        metadata: Dict[str, Any],
        text: str = ""
    ) -> Tuple[float, List[str]]:
        """
        محاسبه امتیاز IDF-weighted keyword matching.
        متعادل روی همه فیلدهای metadata + document text.

        Args:
            query: سوال کاربر
            metadata: metadata سند
            text: متن اصلی سند (document text)

        Returns:
            (score, matched_keywords)
        """
        vocab = self._get_vocab()
        field_weights = self._get_field_weights()
        query_normalized = self.normalize_text(query)
        query_keywords = self._extract_keywords(query)

        total_score = 0.0
        matched_keywords: List[str] = []

        # ── فیلدهای metadata ──
        for field, weight in field_weights.items():
            field_value = str(metadata.get(field, ''))
            field_normalized = self.normalize_text(field_value)
            if not field_normalized:
                continue
            for kw in query_keywords:
                kw_norm = self.normalize_text(kw)
                if kw_norm in field_normalized:
                    ngram_bonus = len(kw_norm.split())
                    idf = vocab.get(kw_norm, 2.0)
                    total_score += weight * idf * ngram_bonus
                    if kw not in matched_keywords:
                        matched_keywords.append(kw)

        # ── Document text (وزن 1.5 — مکمل metadata) ──
        if text:
            text_normalized = self.normalize_text(text)
            for kw in query_keywords:
                kw_norm = self.normalize_text(kw)
                if kw_norm in text_normalized:
                    ngram_bonus = len(kw_norm.split())
                    idf = vocab.get(kw_norm, 2.0)
                    total_score += 1.5 * idf * ngram_bonus
                    if kw not in matched_keywords:
                        matched_keywords.append(kw)

        # ── Coverage bonus ──
        if query_keywords:
            coverage = len(matched_keywords) / len(query_keywords)
            if coverage >= 0.7:
                total_score += 12.0 * coverage
            elif coverage >= 0.4:
                total_score += 6.0 * coverage

        # ── Diversity bonus ──
        matched_fields: set = set()
        for kw in matched_keywords:
            kw_norm = self.normalize_text(kw)
            for field in field_weights:
                if kw_norm in self.normalize_text(str(metadata.get(field, ''))):
                    matched_fields.add(field)
            if text and kw_norm in self.normalize_text(text):
                matched_fields.add('_document')
        if len(matched_fields) >= 3:
            total_score += 5.0
        elif len(matched_fields) >= 2:
            total_score += 2.0

        # ── Question/query similarity bonus ──
        for qf in ('question', 'query', 'سوال'):
            q_norm = self.normalize_text(str(metadata.get(qf, '')))
            if q_norm and len(q_norm) > 5:
                sim = SequenceMatcher(None, query_normalized, q_norm).ratio()
                total_score += sim * 5.0
                break

        return total_score, matched_keywords

    def has_meaningful_match(self, matched_keywords: List[str]) -> bool:
        """آیا matched keywords واقعاً معنادار هستند (IDF بالا)؟"""
        vocab = self._get_vocab()
        idf_threshold = 2.0
        for kw in matched_keywords:
            kw_norm = self.normalize_text(kw)
            if vocab.get(kw_norm, 0) >= idf_threshold:
                return True
        return False

    # ─────────────────────────────────────────────
    # Search methods
    # ─────────────────────────────────────────────

    def enhanced_search(
        self,
        query: str,
        semantic_results: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        if not semantic_results:
            return []

        query_keywords = self._extract_keywords(query)
        cn = self._col_name()
        logger.info(f"🔍 [EnhancedSearch:{cn}] Query: {query[:50]}... | Keywords: {query_keywords}")

        scored_results = []
        for result in semantic_results:
            metadata = result.get('metadata', {})
            text = result.get('text', '')
            semantic_score = result.get('score', 0.5)
            keyword_score, matched_kws = self.calculate_keyword_score(query, metadata, text)

            hybrid_score = (semantic_score * 0.4) + (keyword_score * 0.1)
            if query_keywords and len(matched_kws) == len(query_keywords):
                hybrid_score += 1.0

            scored_results.append({
                **result,
                'keyword_score': keyword_score,
                'matched_keywords': matched_kws,
                'hybrid_score': hybrid_score,
                'original_semantic_score': semantic_score,
            })

        scored_results.sort(key=lambda x: x['hybrid_score'], reverse=True)
        return scored_results[:top_k]

    def keyword_only_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        all_docs = self._get_all_docs()
        if not all_docs or not all_docs.get('metadatas'):
            return []

        scored = []
        docs = all_docs.get('documents', [])
        for idx, metadata in enumerate(all_docs['metadatas']):
            text = docs[idx] if idx < len(docs) else ''
            score, matched = self.calculate_keyword_score(query, metadata, text)
            if score > 0:
                scored.append({
                    'id': all_docs['ids'][idx],
                    'text': text,
                    'metadata': metadata,
                    'keyword_score': score,
                    'matched_keywords': matched,
                    'score': min(score / 10, 1.0),
                })
        scored.sort(key=lambda x: x['keyword_score'], reverse=True)
        return scored[:top_k]
