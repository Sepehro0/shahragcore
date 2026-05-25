# -*- coding: utf-8 -*-
"""
Entity Cache - کش هوشمند entities از database
این ماژول برای بهبود عملکرد و پوشش کامل entities استفاده می‌شود
"""

from typing import List, Tuple, Optional, Dict
import logging
from difflib import SequenceMatcher
import time

logger = logging.getLogger(__name__)


class EntityCache:
    """
    کش هوشمند entities از database
    
    Features:
    - Cache تمام entities منحصر به فرد از database
    - Similarity matching با scoring
    - Refresh دوره‌ای برای به‌روز ماندن
    - Normalization برای handling تنوع املایی
    """
    
    def __init__(self, db_service, refresh_interval: int = 3600):
        """
        Args:
            db_service: سرویس database برای query
            refresh_interval: فاصله زمانی refresh (ثانیه) - default: 1 hour
        """
        self.db = db_service
        self.refresh_interval = refresh_interval
        self.cache: Dict[str, List[str]] = {}
        self.similarity_cache: Dict[str, List[Tuple[str, float]]] = {}
        self.last_refresh: Dict[str, float] = {}
        
        logger.info("✅ EntityCache initialized")
    
    def normalize(self, text: str) -> str:
        """
        نرمال‌سازی متن برای مقایسه
        
        Normalizations:
        - تبدیل به lowercase
        - حذف فاصله‌های اضافی
        - تبدیل ی عربی به فارسی
        - تبدیل ک عربی به فارسی
        - حذف نیم‌فاصله
        """
        if not text:
            return ""
        
        # تبدیل به lowercase
        text = text.lower()
        
        # نرمال‌سازی کاراکترهای فارسی/عربی
        text = text.replace('ي', 'ی').replace('ك', 'ک')
        text = text.replace('ة', 'ه').replace('ۀ', 'ه')
        text = text.replace('أ', 'ا').replace('إ', 'ا').replace('ٱ', 'ا').replace('آ', 'ا')
        
        # حذف نیم‌فاصله و تبدیل به فاصله
        text = text.replace('\u200c', ' ').replace('‌', ' ')
        
        # حذف فاصله‌های اضافی
        text = ' '.join(text.split())
        
        return text
    
    def should_refresh(self, cache_key: str) -> bool:
        """بررسی نیاز به refresh کش"""
        if cache_key not in self.last_refresh:
            return True
        
        elapsed = time.time() - self.last_refresh[cache_key]
        return elapsed > self.refresh_interval
    
    def get_all_entities(self, table_name: str, column_name: str, force_refresh: bool = False) -> List[str]:
        """
        دریافت تمام entities منحصر به فرد از یک ستون
        
        Args:
            table_name: نام جدول (e.g., "masaref2_sheet1")
            column_name: نام ستون (e.g., "عنوان_دستگاه_اجرایی")
            force_refresh: اجبار به refresh حتی اگر cache fresh باشد
        
        Returns:
            لیست تمام entities منحصر به فرد
        """
        cache_key = f"{table_name}:{column_name}"
        
        # Check if cache is valid and fresh
        if not force_refresh and cache_key in self.cache and not self.should_refresh(cache_key):
            logger.debug(f"✅ Using cached entities for {cache_key} ({len(self.cache[cache_key])} entities)")
            return self.cache[cache_key]
        
        # Fetch from database
        try:
            query = f'SELECT DISTINCT "{column_name}" FROM {table_name} WHERE "{column_name}" IS NOT NULL ORDER BY "{column_name}"'
            result = self.db.execute_query(query)
            
            if result and 'rows' in result:
                entities = [row[0] for row in result['rows']]
            elif isinstance(result, list):
                entities = [row[0] if isinstance(row, (list, tuple)) else row for row in result]
            else:
                logger.warning(f"⚠️  Unexpected result format from database: {type(result)}")
                entities = []
            
            # Update cache
            self.cache[cache_key] = entities
            self.last_refresh[cache_key] = time.time()
            
            logger.info(f"✅ Cached {len(entities)} entities from {table_name}.{column_name}")
            return entities
            
        except Exception as e:
            logger.error(f"❌ Error fetching entities from {table_name}.{column_name}: {e}")
            
            # Return cached data if available (graceful degradation)
            if cache_key in self.cache:
                logger.warning(f"⚠️  Using stale cache for {cache_key}")
                return self.cache[cache_key]
            
            return []
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """
        محاسبه similarity بین دو string با SequenceMatcher
        
        Returns:
            float بین 0 و 1 (1 = identical)
        """
        return SequenceMatcher(None, str1, str2).ratio()
    
    def find_similar_entities(
        self, 
        query_entity: str, 
        table_name: str, 
        column_name: str, 
        threshold: float = 0.7,
        max_results: int = 10
    ) -> List[Tuple[str, float]]:
        """
        پیدا کردن entities مشابه با scoring
        
        Matching strategies (in order of priority):
        1. Exact match (score = 1.0)
        2. Substring match (score = 0.9)
        3. Word-level Jaccard similarity (score = 0.8 * jaccard)
        4. Fuzzy string similarity (score = 0.7 * similarity)
        
        Args:
            query_entity: entity مورد جستجو
            table_name: نام جدول
            column_name: نام ستون
            threshold: حداقل امتیاز برای match (0-1)
            max_results: حداکثر تعداد نتایج
        
        Returns:
            لیست tuples (entity, score) مرتب شده بر اساس score
        """
        # Check similarity cache first
        cache_key = f"{query_entity}:{table_name}:{column_name}:{threshold}"
        if cache_key in self.similarity_cache:
            logger.debug(f"✅ Using cached similarity results for '{query_entity}'")
            return self.similarity_cache[cache_key]
        
        # Get all entities
        all_entities = self.get_all_entities(table_name, column_name)
        if not all_entities:
            logger.warning(f"⚠️  No entities found in {table_name}.{column_name}")
            return []
        
        normalized_query = self.normalize(query_entity)
        matches = []
        
        for entity in all_entities:
            normalized_entity = self.normalize(entity)
            
            # Strategy 1: Exact match (highest priority)
            if normalized_query == normalized_entity:
                matches.append((entity, 1.0))
                continue
            
            # Strategy 2: Substring match
            if normalized_query in normalized_entity:
                # Calculate how much of the entity is matched
                match_ratio = len(normalized_query) / len(normalized_entity)
                score = 0.85 + (0.1 * match_ratio)  # 0.85 to 0.95
                matches.append((entity, score))
                continue
            
            if normalized_entity in normalized_query:
                match_ratio = len(normalized_entity) / len(normalized_query)
                score = 0.80 + (0.1 * match_ratio)  # 0.80 to 0.90
                matches.append((entity, score))
                continue
            
            # Strategy 3: Word-level Jaccard similarity
            query_words = set(normalized_query.split())
            entity_words = set(normalized_entity.split())
            
            if query_words and entity_words:
                intersection = query_words & entity_words
                union = query_words | entity_words
                jaccard_score = len(intersection) / len(union) if union else 0
                
                if jaccard_score >= threshold:
                    # Scale: 0.7-0.85 based on jaccard score
                    score = 0.70 + (jaccard_score * 0.15)
                    matches.append((entity, score))
                    continue
            
            # Strategy 4: Fuzzy string similarity (most expensive, last resort)
            similarity = self.calculate_similarity(normalized_query, normalized_entity)
            if similarity >= threshold:
                # Scale: 0.60-0.75 based on similarity
                score = 0.60 + (similarity * 0.15)
                matches.append((entity, score))
        
        # Sort by score (descending) and limit results
        matches.sort(key=lambda x: x[1], reverse=True)
        matches = matches[:max_results]
        
        # Cache results
        self.similarity_cache[cache_key] = matches
        
        logger.debug(f"✅ Found {len(matches)} similar entities for '{query_entity}' (threshold={threshold})")
        if matches:
            logger.debug(f"   Top match: '{matches[0][0]}' (score={matches[0][1]:.3f})")
        
        return matches
    
    def find_entity_in_db(
        self,
        query_entity: str,
        table_names: List[str] = None,
        search_columns: List[str] = None,
        threshold: float = 0.65,
        max_results: int = 5
    ) -> List[Tuple[str, float, str]]:
        """
        🆕 Dynamic entity resolution - جستجوی هوشمند entity در دیتابیس
        
        این متد مستقیماً در دیتابیس جستجو می‌کند و نیاز به mapping استاتیک ندارد.
        
        Args:
            query_entity: entity استخراج شده از سوال
            table_names: لیست جداول برای جستجو (default: همه جداول رایج)
            search_columns: لیست ستون‌ها برای جستجو
            threshold: حداقل امتیاز similarity
            max_results: حداکثر تعداد نتایج
            
        Returns:
            لیست tuples (entity, score, column_name) مرتب بر اساس score
        """
        if not table_names:
            table_names = ['masaref2_sheet1', 'manabe_sheet1']
        
        if not search_columns:
            search_columns = ['عنوان_دستگاه_اجرایی', 'عنوان_دستگاه_اجرايي', 
                            'عنوان_دستگاه_اصلی', 'عنوان_دستگاه_اصلي']
        
        all_matches = []
        
        for table_name in table_names:
            for column_name in search_columns:
                try:
                    matches = self.find_similar_entities(
                        query_entity=query_entity,
                        table_name=table_name,
                        column_name=column_name,
                        threshold=threshold,
                        max_results=max_results
                    )
                    for entity, score in matches:
                        all_matches.append((entity, score, f"{table_name}.{column_name}"))
                except Exception as e:
                    logger.debug(f"Search in {table_name}.{column_name} failed: {e}")
                    continue
        
        # حذف تکراری‌ها و مرتب‌سازی بر اساس score
        seen_entities = set()
        unique_matches = []
        for entity, score, source in sorted(all_matches, key=lambda x: x[1], reverse=True):
            normalized = self.normalize(entity)
            if normalized not in seen_entities:
                seen_entities.add(normalized)
                unique_matches.append((entity, score, source))
        
        return unique_matches[:max_results]

    def clear_cache(self, table_name: Optional[str] = None):
        """
        پاک کردن کش
        
        Args:
            table_name: اگر مشخص شود، فقط کش آن جدول پاک می‌شود
        """
        if table_name:
            # Clear specific table cache
            keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{table_name}:")]
            for key in keys_to_remove:
                del self.cache[key]
                if key in self.last_refresh:
                    del self.last_refresh[key]
            logger.info(f"✅ Cleared cache for {table_name} ({len(keys_to_remove)} entries)")
        else:
            # Clear all cache
            self.cache.clear()
            self.similarity_cache.clear()
            self.last_refresh.clear()
            logger.info("✅ Cleared all cache")
    
    def get_cache_stats(self) -> Dict[str, any]:
        """دریافت آمار کش"""
        return {
            "entity_cache_size": len(self.cache),
            "similarity_cache_size": len(self.similarity_cache),
            "total_entities": sum(len(entities) for entities in self.cache.values()),
            "cache_keys": list(self.cache.keys())
        }

