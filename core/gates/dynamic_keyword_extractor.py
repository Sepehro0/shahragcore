# -*- coding: utf-8 -*-
"""
Dynamic Keyword Extractor
استخراج داینامیک keywords از collection برای تشخیص domain
"""

import logging
from typing import Dict, List, Set, Optional, Tuple
from collections import Counter
import re
import chromadb
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ExtractedKeywords:
    """Keywords استخراج شده از collection"""
    keywords: List[str]
    domain_description: str
    confidence: float
    extraction_method: str
    timestamp: datetime


class DynamicKeywordExtractor:
    """
    استخراج داینامیک keywords از collection
    
    Methods:
    1. از collection metadata استفاده می‌کند
    2. از sample documents برای استخراج keywords استفاده می‌کند
    3. از TF-IDF برای پیدا کردن مهم‌ترین کلمات استفاده می‌کند
    4. Cache mechanism برای بهبود performance
    """
    
    # Cache برای keywords استخراج شده
    _keywords_cache: Dict[str, ExtractedKeywords] = {}
    CACHE_TTL_HOURS = 24  # Cache برای 24 ساعت معتبر است
    
    # Stop words فارسی (گسترش یافته)
    PERSIAN_STOP_WORDS = {
        'در', 'به', 'از', 'که', 'را', 'و', 'یا', 'این', 'آن', 'است', 'برای', 'با',
        'چرا', 'چطور', 'چگونه', 'چیست', 'کی', 'کجا', 'چه', 'چقدر', 'چند',
        'می', 'می‌شود', 'می‌شود', 'می‌شویم', 'می‌شوی', 'می‌شوند',
        'است', 'هست', 'هستند', 'بود', 'بودند', 'باشند', 'باشد',
        'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه', 'ده',
        'هم', 'نیز', 'همچنین', 'همین', 'همان', 'همین', 'همچنین',
        # کلمات عمومی که نباید keyword باشند
        'های', 'شود', 'کند', 'شوند', 'شوید', 'شویم', 'می‌تواند', 'می‌توانند',
        'می‌توان', 'می‌شود', 'می‌شوند', 'می‌شوید', 'می‌شویم',
        'دارد', 'دارند', 'داشته', 'دارای', 'دارا',
        'بوده', 'بودند', 'بوده‌اند', 'بوده‌ایم',
        'خواهد', 'خواهند', 'خواهیم', 'خواهید',
        'است', 'هست', 'هستند', 'هستیم', 'هستید',
        'باشد', 'باشند', 'باشیم', 'باشید',
        'شده', 'شده‌اند', 'شده‌ایم', 'شده‌اید',
        'کرده', 'کرده‌اند', 'کرده‌ایم', 'کرده‌اید',
        'گرفته', 'گرفته‌اند', 'گرفته‌ایم', 'گرفته‌اید',
        'داده', 'داده‌اند', 'داده‌ایم', 'داده‌اید',
        'کرد', 'کردند', 'کردیم', 'کردید',
        'شد', 'شدند', 'شدیم', 'شدید',
        'گرفت', 'گرفتند', 'گرفتیم', 'گرفتید',
        'داد', 'دادند', 'دادیم', 'دادید',
        'بود', 'بودند', 'بودیم', 'بودید',
        'شد', 'شدند', 'شدیم', 'شدید',
        'خواهد', 'خواهند', 'خواهیم', 'خواهید',
        'می‌توان', 'می‌تواند', 'می‌توانند',
        'می‌شود', 'می‌شوند', 'می‌شوید', 'می‌شویم',
        'می‌کند', 'می‌کنند', 'می‌کنید', 'می‌کنیم',
        'می‌دهد', 'می‌دهند', 'می‌دهید', 'می‌دهیم',
        'می‌گیرد', 'می‌گیرند', 'می‌گیرید', 'می‌گیریم',
        'می‌شود', 'می‌شوند', 'می‌شوید', 'می‌شویم',
        'می‌بود', 'می‌بودند', 'می‌بودید', 'می‌بودیم',
        'می‌شد', 'می‌شدند', 'می‌شدید', 'می‌شدیم',
        'می‌خواهد', 'می‌خواهند', 'می‌خواهید', 'می‌خواهیم',
        'می‌توان', 'می‌تواند', 'می‌توانند',
        'می‌شود', 'می‌شوند', 'می‌شوید', 'می‌شویم',
        'می‌کند', 'می‌کنند', 'می‌کنید', 'می‌کنیم',
        'می‌دهد', 'می‌دهند', 'می‌دهید', 'می‌دهیم',
        'می‌گیرد', 'می‌گیرند', 'می‌گیرید', 'می‌گیریم',
        'می‌شود', 'می‌شوند', 'می‌شوید', 'می‌شویم',
        'می‌بود', 'می‌بودند', 'می‌بودید', 'می‌بودیم',
        'می‌شد', 'می‌شدند', 'می‌شدید', 'می‌شدیم',
        'می‌خواهد', 'می‌خواهند', 'می‌خواهید', 'می‌خواهیم',
        # کلمات سوالی عمومی
        'چیست', 'چیست؟', 'چیست؟', 'چیست؟',
        'چگونه', 'چطور', 'چجوری',
        'چرا', 'چرا؟', 'چرا؟',
        'کی', 'کی؟', 'کی؟',
        'کجا', 'کجا؟', 'کجا؟',
        'چه', 'چه؟', 'چه؟',
        'چقدر', 'چقدر؟', 'چقدر؟',
        'چند', 'چند؟', 'چند؟',
        # کلمات ربطی
        'که', 'که', 'که',
        'اگر', 'اگر', 'اگر',
        'چون', 'چون', 'چون',
        'زیرا', 'زیرا', 'زیرا',
        'چرا', 'چرا', 'چرا',
        'چون', 'چون', 'چون',
        'زیرا', 'زیرا', 'زیرا',
        # کلمات اضافی
        'هم', 'هم', 'هم',
        'نیز', 'نیز', 'نیز',
        'همچنین', 'همچنین', 'همچنین',
        'همین', 'همین', 'همین',
        'همان', 'همان', 'همان',
        'همچنین', 'همچنین', 'همچنین',
        # کلمات عددی
        'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه', 'ده',
        'اول', 'دوم', 'سوم', 'چهارم', 'پنجم', 'ششم', 'هفتم', 'هشتم', 'نهم', 'دهم',
        # کلمات زمانی عمومی
        'امروز', 'دیروز', 'فردا', 'هفته', 'ماه', 'سال',
        'صبح', 'ظهر', 'عصر', 'شب',
        # کلمات مکانی عمومی
        'اینجا', 'آنجا', 'کجا', 'کجا',
        # کلمات اشاره
        'این', 'آن', 'اینها', 'آنها',
        # کلمات پرسشی
        'آیا', 'آیا', 'آیا',
        'چطور', 'چطور', 'چطور',
        'چگونه', 'چگونه', 'چگونه',
        'چرا', 'چرا', 'چرا',
        'کی', 'کی', 'کی',
        'کجا', 'کجا', 'کجا',
        'چه', 'چه', 'چه',
        'چقدر', 'چقدر', 'چقدر',
        'چند', 'چند', 'چند',
    }
    
    # Minimum keyword length
    MIN_KEYWORD_LENGTH = 3
    
    # Maximum keywords to extract
    MAX_KEYWORDS = 50
    
    def __init__(self, embedding_client=None):
        """
        Args:
            embedding_client: برای semantic analysis (اختیاری)
        """
        self.embedding_client = embedding_client
    
    def extract_keywords(
        self,
        collection_name: str,
        chroma_client: chromadb.Client,
        force_refresh: bool = False
    ) -> ExtractedKeywords:
        """
        استخراج keywords از collection
        
        Args:
            collection_name: نام collection
            chroma_client: ChromaDB client
            force_refresh: آیا cache را ignore کنیم؟
            
        Returns:
            ExtractedKeywords با keywords استخراج شده
        """
        # بررسی cache
        if not force_refresh and collection_name in self._keywords_cache:
            cached = self._keywords_cache[collection_name]
            if datetime.now() - cached.timestamp < timedelta(hours=self.CACHE_TTL_HOURS):
                logger.debug(f"📦 [KEYWORD_EXTRACTOR] Using cached keywords for {collection_name}")
                return cached
        
        try:
            collection = chroma_client.get_collection(collection_name)
            
            # Method 1: از metadata استفاده کن
            metadata_keywords = self._extract_from_metadata(collection)
            
            # Method 2: از sample documents استفاده کن
            document_keywords = self._extract_from_documents(collection)
            
            # ترکیب keywords
            combined_keywords = self._combine_keywords(metadata_keywords, document_keywords)
            
            # استخراج domain description
            domain_description = self._extract_domain_description(collection, combined_keywords)
            
            result = ExtractedKeywords(
                keywords=combined_keywords[:self.MAX_KEYWORDS],
                domain_description=domain_description,
                confidence=0.8 if combined_keywords else 0.5,
                extraction_method="dynamic_extraction",
                timestamp=datetime.now()
            )
            
            # ذخیره در cache
            self._keywords_cache[collection_name] = result
            
            logger.info(
                f"✅ [KEYWORD_EXTRACTOR] Extracted {len(combined_keywords)} keywords for {collection_name}"
            )
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ [KEYWORD_EXTRACTOR] Failed to extract keywords: {e}")
            # Fallback: return empty keywords
            return ExtractedKeywords(
                keywords=[],
                domain_description="",
                confidence=0.0,
                extraction_method="fallback",
                timestamp=datetime.now()
            )
    
    def _extract_from_metadata(self, collection) -> List[str]:
        """استخراج keywords از collection metadata"""
        keywords = []
        
        if collection.metadata:
            # از description استفاده کن
            description = collection.metadata.get('description', '')
            if description:
                keywords.extend(self._extract_keywords_from_text(description))
            
            # از keywords metadata استفاده کن
            metadata_keywords = collection.metadata.get('keywords', [])
            if isinstance(metadata_keywords, list):
                keywords.extend(metadata_keywords)
            elif isinstance(metadata_keywords, str):
                keywords.extend(metadata_keywords.split(','))
        
        return keywords
    
    def _extract_from_documents(self, collection, sample_size: int = 100) -> List[str]:
        """استخراج keywords از sample documents"""
        try:
            # دریافت sample documents
            sample_docs = collection.get(limit=sample_size)
            
            if not sample_docs or not sample_docs.get('documents'):
                return []
            
            # ترکیب همه documents
            all_text = ' '.join(sample_docs['documents'])
            
            # استخراج keywords با TF-IDF approach
            keywords = self._extract_keywords_from_text(all_text)
            
            # استفاده از metadata documents (question, answer, title)
            if sample_docs.get('metadatas'):
                for metadata in sample_docs['metadatas'][:50]:  # فقط 50 تا برای performance
                    if metadata:
                        # از question استفاده کن
                        question = metadata.get('question', '')
                        if question:
                            keywords.extend(self._extract_keywords_from_text(question))
                        
                        # از answer استفاده کن
                        answer = metadata.get('answer', '')
                        if answer:
                            keywords.extend(self._extract_keywords_from_text(answer))
                        
                        # از title استفاده کن
                        title = metadata.get('title', '')
                        if title:
                            keywords.extend(self._extract_keywords_from_text(title))
            
            return keywords
            
        except Exception as e:
            logger.warning(f"⚠️ [KEYWORD_EXTRACTOR] Failed to extract from documents: {e}")
            return []
    
    def _extract_keywords_from_text(self, text: str, top_n: int = 50) -> List[str]:
        """
        استخراج keywords از متن با استفاده از TF-IDF approach
        
        Improvements:
        - استخراج multi-word phrases (bigrams, trigrams)
        - فیلتر کردن stop words بهتر
        - اولویت‌دهی به کلمات مهم‌تر
        """
        if not text:
            return []
        
        # Normalize text
        text_lower = text.lower()
        
        # Tokenize (فقط حروف فارسی)
        tokens = re.findall(r'[\u0600-\u06FF]+', text_lower)
        
        # فیلتر کردن stop words و کلمات کوتاه
        filtered_tokens = [
            token for token in tokens
            if len(token) >= self.MIN_KEYWORD_LENGTH
            and token not in self.PERSIAN_STOP_WORDS
            and not token.isdigit()
        ]
        
        # === 1. Single-word keywords ===
        word_freq = Counter(filtered_tokens)
        single_keywords = [
            word for word, freq in word_freq.most_common(top_n)
            if freq >= 2  # حداقل 2 بار تکرار
        ]
        
        # === 2. Multi-word phrases (bigrams) ===
        bigrams = []
        for i in range(len(filtered_tokens) - 1):
            bigram = f"{filtered_tokens[i]} {filtered_tokens[i+1]}"
            bigrams.append(bigram)
        
        bigram_freq = Counter(bigrams)
        bigram_keywords = [
            bigram for bigram, freq in bigram_freq.most_common(top_n // 2)
            if freq >= 2  # حداقل 2 بار تکرار
        ]
        
        # === 3. Trigrams (اختیاری) ===
        trigrams = []
        for i in range(len(filtered_tokens) - 2):
            trigram = f"{filtered_tokens[i]} {filtered_tokens[i+1]} {filtered_tokens[i+2]}"
            trigrams.append(trigram)
        
        trigram_freq = Counter(trigrams)
        trigram_keywords = [
            trigram for trigram, freq in trigram_freq.most_common(top_n // 4)
            if freq >= 2  # حداقل 2 بار تکرار
        ]
        
        # === 4. ترکیب همه ===
        # اولویت: trigrams > bigrams > single words
        all_keywords = trigram_keywords + bigram_keywords + single_keywords
        
        # حذف duplicates و محدود کردن به top_n
        seen = set()
        unique_keywords = []
        for kw in all_keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
                if len(unique_keywords) >= top_n:
                    break
        
        return unique_keywords
    
    def _combine_keywords(
        self,
        metadata_keywords: List[str],
        document_keywords: List[str]
    ) -> List[str]:
        """ترکیب keywords از منابع مختلف"""
        # ترکیب و حذف duplicates
        all_keywords = metadata_keywords + document_keywords
        
        # حذف duplicates و مرتب‌سازی بر اساس frequency
        keyword_freq = Counter(all_keywords)
        
        # مرتب‌سازی بر اساس frequency
        sorted_keywords = [
            word for word, freq in keyword_freq.most_common()
        ]
        
        return sorted_keywords
    
    def _extract_domain_description(
        self,
        collection,
        keywords: List[str]
    ) -> str:
        """
        استخراج domain description
        
        Improved: از sample documents برای ساخت description استفاده می‌کند
        """
        # اول از metadata استفاده کن
        if collection.metadata and collection.metadata.get('description'):
            return collection.metadata.get('description')
        
        # === Method 1: از questions در metadata استفاده کن ===
        try:
            sample_docs = collection.get(limit=20)
            if sample_docs and sample_docs.get('metadatas'):
                questions = []
                answers = []
                for metadata in sample_docs['metadatas'][:20]:
                    if metadata:
                        if metadata.get('question'):
                            questions.append(metadata['question'])
                        if metadata.get('answer'):
                            answers.append(metadata['answer'])
                
                # ترکیب questions و answers برای description بهتر
                combined_text = ' '.join(questions[:5] + answers[:5])
                if combined_text:
                    # استخراج کلمات کلیدی از این متن
                    desc_keywords = self._extract_keywords_from_text(combined_text, top_n=15)
                    if desc_keywords:
                        return f"این مجموعه شامل اطلاعات درباره {', '.join(desc_keywords[:10])} است"
        except Exception as e:
            logger.debug(f"⚠️ Failed to extract description from documents: {e}")
        
        # === Method 2: Fallback - از keywords استفاده کن ===
        if keywords:
            top_keywords = keywords[:10]
            return f"موضوعات مرتبط با: {', '.join(top_keywords)}"
        
        return ""
    
    def clear_cache(self, collection_name: Optional[str] = None):
        """پاک کردن cache"""
        if collection_name:
            if collection_name in self._keywords_cache:
                del self._keywords_cache[collection_name]
                logger.info(f"🗑️ [KEYWORD_EXTRACTOR] Cleared cache for {collection_name}")
        else:
            self._keywords_cache.clear()
            logger.info("🗑️ [KEYWORD_EXTRACTOR] Cleared all cache")

