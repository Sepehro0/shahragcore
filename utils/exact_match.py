# -*- coding: utf-8 -*-
"""
Exact Match Utility
جستجوی تطابق دقیق یا نزدیک سوالات در dataset
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


def normalize_query(text: str) -> str:
    """نرمال‌سازی متن برای مقایسه"""
    if not text:
        return ""
    
    # تبدیل به حروف کوچک
    text = text.lower()
    
    # حذف نشانه‌های خاص
    text = text.replace('؟', '').replace('?', '').replace('!', '')
    text = text.replace('،', '').replace(',', '').replace('.', '')
    
    # تبدیل نیم‌فاصله به فاصله
    text = text.replace('\u200c', ' ')
    
    # حذف فاصله‌های اضافی
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def find_exact_match(
    query: str,
    collection,
    similarity_threshold: float = 0.85
) -> Optional[Dict[str, Any]]:
    """
    یافتن تطابق دقیق یا نزدیک در collection
    
    Args:
        query: سوال کاربر
        collection: ChromaDB collection
        similarity_threshold: حداقل شباهت برای تطابق
        
    Returns:
        اگر تطابق پیدا شد، document را برمی‌گرداند
    """
    normalized_query = normalize_query(query)
    
    if not normalized_query:
        return None
    
    try:
        # دریافت همه documents
        all_docs = collection.get()
        
        if not all_docs or not all_docs.get('metadatas'):
            return None
        
        best_match = None
        best_score = 0.0
        
        for i, metadata in enumerate(all_docs['metadatas']):
            if not metadata:
                continue
                
            # بررسی فیلد question
            doc_question = metadata.get('question', '')
            if not doc_question:
                continue
            
            normalized_doc = normalize_query(doc_question)
            
            # محاسبه شباهت
            similarity = calculate_similarity(normalized_query, normalized_doc)
            
            if similarity > best_score:
                best_score = similarity
                best_match = {
                    'id': all_docs['ids'][i] if all_docs.get('ids') else f'doc_{i}',
                    'document': all_docs['documents'][i] if all_docs.get('documents') else '',
                    'metadata': metadata,
                    'similarity': similarity
                }
        
        if best_match and best_score >= similarity_threshold:
            logger.info(f"🎯 [Exact Match] Found match with similarity {best_score:.2f}: {best_match['metadata'].get('question', '')[:50]}...")
            return best_match
        
        logger.info(f"❌ [Exact Match] No match found for: {query[:50]}... (best_score={best_score:.2f})")
        return None
        
    except Exception as e:
        logger.error(f"Error in exact match: {e}")
        return None


def calculate_similarity(s1: str, s2: str) -> float:
    """
    محاسبه شباهت دو رشته با استفاده از Jaccard similarity
    """
    if not s1 or not s2:
        return 0.0
    
    # تبدیل به مجموعه کلمات
    words1 = set(s1.split())
    words2 = set(s2.split())
    
    if not words1 or not words2:
        return 0.0
    
    # Jaccard similarity
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    if union == 0:
        return 0.0
    
    return intersection / union


def boost_relevant_sources(
    query: str,
    sources: List[Dict[str, Any]],
    boost_factor: float = 2.0
) -> List[Dict[str, Any]]:
    """
    افزایش امتیاز sources که سوالشان شبیه query است
    
    Args:
        query: سوال کاربر
        sources: لیست sources
        boost_factor: ضریب افزایش امتیاز
        
    Returns:
        لیست sources با امتیازهای به‌روزشده
    """
    normalized_query = normalize_query(query)
    
    if not normalized_query or not sources:
        return sources
    
    boosted_sources = []
    
    for source in sources:
        boosted = dict(source)
        metadata = source.get('metadata', {})
        doc_question = metadata.get('question', '')
        
        if doc_question:
            normalized_doc = normalize_query(doc_question)
            similarity = calculate_similarity(normalized_query, normalized_doc)
            
            # اگر شباهت بالا بود، امتیاز را افزایش بده
            if similarity >= 0.6:
                original_score = boosted.get('score', 0)
                boosted['score'] = original_score + (similarity * boost_factor)
                boosted['exact_match_boost'] = similarity
                logger.info(f"⬆️ Boosted source '{doc_question[:40]}...' by {similarity:.2f}")
        
        boosted_sources.append(boosted)
    
    # مرتب‌سازی مجدد بر اساس score
    boosted_sources.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    return boosted_sources


