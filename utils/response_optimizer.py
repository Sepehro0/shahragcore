# -*- coding: utf-8 -*-
"""
Response Optimizer - بهینه‌سازی حجم response برای جلوگیری از crash
"""

import logging
import sys
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# حداکثر حجم response به مگابایت
MAX_RESPONSE_SIZE_MB = 5.0


def optimize_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    بهینه‌سازی response برای کاهش حجم
    
    Args:
        response: Response dictionary
        
    Returns:
        بهینه‌شده response
    """
    optimized = response.copy()
    
    # 1. حذف فیلدهای تکراری
    # اگر full_answer و answer یکی هستند، یکی را حذف کن
    if optimized.get('answer') == optimized.get('full_answer'):
        logger.info("🔧 Removing duplicate full_answer (identical to answer)")
        optimized.pop('full_answer', None)
    
    # اگر full_text و full_answer یکی هستند، full_text را حذف کن
    if optimized.get('full_text') == optimized.get('full_answer'):
        logger.info("🔧 Removing duplicate full_text (identical to full_answer)")
        optimized.pop('full_text', None)
    
    # 2. بهینه‌سازی sources
    if 'sources' in optimized and isinstance(optimized['sources'], list):
        optimized['sources'] = optimize_sources(optimized['sources'])
    
    # 3. بررسی حجم و truncate اگر لازم است
    response_size_mb = estimate_size_mb(optimized)
    if response_size_mb > MAX_RESPONSE_SIZE_MB:
        logger.warning(f"⚠️ Response size {response_size_mb:.2f}MB > {MAX_RESPONSE_SIZE_MB}MB, truncating...")
        optimized = truncate_response(optimized, MAX_RESPONSE_SIZE_MB)
        optimized['_truncated'] = True
        optimized['_original_size_mb'] = response_size_mb
    
    return optimized


def optimize_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    بهینه‌سازی sources برای کاهش حجم
    
    Args:
        sources: لیست source ها
        
    Returns:
        بهینه‌شده sources
    """
    optimized_sources = []
    
    # فیلدهای مهم metadata که باید حفظ شوند
    important_metadata_fields = [
        'question', 'answer', 'subcategory', 'category',
        # zabete_qa specific fields
        'code', 'zabete_title', 'madde_title', 'maddeh_id', 
        'creation_date', 'modification_date', 'type', 'row_index',
        # karbaran_omomi specific fields
        'fund_name', 'fund_type', 'topic', 'subtopic', 'dataset_type',
        # general fields
        'source', 'page', 'chunk_index', 'hierarchy_code', 'hierarchy_title'
    ]
    
    for source in sources:
        original_metadata = source.get('metadata', {}) or {}
        
        # حفظ تمام فیلدهای مهم metadata
        optimized_metadata = {}
        for field in important_metadata_fields:
            if field in original_metadata and original_metadata[field] is not None:
                value = original_metadata[field]
                # truncate answer if too long
                if field == 'answer' and isinstance(value, str):
                    value = truncate_text(value, max_length=500)
                optimized_metadata[field] = value
        
        optimized_source = {
            'id': source.get('id'),
            'content': truncate_text(source.get('content', ''), max_length=500),
            'metadata': optimized_metadata,
            'score': source.get('score'),
            'semantic_score': source.get('semantic_score'),
        }
        
        # حذف فیلدهای None از سطح اول
        optimized_source = {k: v for k, v in optimized_source.items() if v is not None}
        
        optimized_sources.append(optimized_source)
    
    return optimized_sources


def truncate_text(text: str, max_length: int = 1000) -> str:
    """
    خلاصه کردن متن اگر از حد مجاز بیشتر باشد
    
    Args:
        text: متن اصلی
        max_length: حداکثر طول
        
    Returns:
        متن خلاصه شده
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length] + "..."


def truncate_response(response: Dict[str, Any], max_size_mb: float) -> Dict[str, Any]:
    """
    Truncate response تا به حجم مجاز برسد
    
    Args:
        response: Response dictionary
        max_size_mb: حداکثر حجم به مگابایت
        
    Returns:
        Truncated response
    """
    # استراتژی truncation:
    # 1. محدود کردن answer و full_answer
    # 2. کاهش تعداد sources
    # 3. حذف full_text
    
    truncated = response.copy()
    
    # 1. محدود کردن answer
    if 'answer' in truncated:
        truncated['answer'] = truncate_text(truncated['answer'], max_length=3000)
    
    if 'full_answer' in truncated:
        truncated['full_answer'] = truncate_text(truncated['full_answer'], max_length=3000)
    
    # 2. حذف full_text
    truncated.pop('full_text', None)
    
    # 3. کاهش تعداد sources
    if 'sources' in truncated and isinstance(truncated['sources'], list):
        truncated['sources'] = truncated['sources'][:5]  # فقط 5 تای اول
    
    # بررسی مجدد حجم
    new_size = estimate_size_mb(truncated)
    if new_size > max_size_mb:
        # اگر هنوز بزرگ است، sources را بیشتر کاهش بده
        if 'sources' in truncated:
            truncated['sources'] = truncated['sources'][:3]
    
    return truncated


def estimate_size_mb(obj: Any) -> float:
    """
    تخمین حجم object به مگابایت
    
    Args:
        obj: Python object
        
    Returns:
        حجم تقریبی به مگابایت
    """
    try:
        import json
        size_bytes = len(json.dumps(obj, ensure_ascii=False).encode('utf-8'))
        return size_bytes / (1024 * 1024)
    except Exception as e:
        logger.warning(f"⚠️ Could not estimate size: {e}")
        return 0.0


