# -*- coding: utf-8 -*-
"""
Semantic Entity Matcher
سیستم هوشمند تطبیق entity ها با استفاده از Embedding و Semantic Similarity

این سیستم:
1. از Embedding برای درک معنایی entity ها استفاده می‌کند
2. Cache هوشمند برای entity embeddings دارد
3. از ترکیب fuzzy matching و semantic similarity استفاده می‌کند
4. در صورت عدم اطمینان، کاندیدها را با confidence نمایش می‌دهد
"""

import asyncio
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from difflib import SequenceMatcher
import time
import json
import os
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class EntityMatch:
    """نتیجه matching یک entity"""
    matched_entity: str
    confidence: float
    similarity_score: float
    semantic_score: float
    fuzzy_score: float
    word_overlap: float
    method: str  # 'exact', 'semantic', 'fuzzy', 'combined'
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    needs_confirmation: bool = False
    confirmation_message: Optional[str] = None


class SemanticEntityMatcher:
    """
    سیستم هوشمند تطبیق entity ها با Semantic Understanding
    
    Features:
    - Embedding-based semantic matching
    - Fuzzy string matching
    - Word overlap analysis
    - Combined scoring with tunable weights
    - Intelligent caching
    - User confirmation for uncertain matches
    """
    
    # Thresholds
    HIGH_CONFIDENCE = 0.85
    MEDIUM_CONFIDENCE = 0.65
    LOW_CONFIDENCE = 0.45
    
    # Weights for combined scoring
    SEMANTIC_WEIGHT = 0.50  # وزن امتیاز معنایی
    FUZZY_WEIGHT = 0.25    # وزن امتیاز fuzzy
    WORD_OVERLAP_WEIGHT = 0.25  # وزن word overlap
    
    # Cache settings
    CACHE_DIR = Path("/home/user01/qwen-api/enhanced_rag_system_dev/.entity_cache")
    CACHE_TTL = 3600 * 24  # 24 hours
    
    def __init__(
        self,
        embedding_client=None,
        database_service=None,
        use_cache: bool = True
    ):
        """
        Args:
            embedding_client: کلاینت embedding (JinaClient یا مشابه)
            database_service: سرویس database
            use_cache: استفاده از cache برای embeddings
        """
        self.embedding_client = embedding_client
        self.database_service = database_service
        self.use_cache = use_cache
        
        # Entity cache: {table_name: {entity: embedding}}
        self._entity_embeddings: Dict[str, Dict[str, List[float]]] = {}
        self._entity_list: Dict[str, List[str]] = {}
        self._cache_loaded = False
        
        # Statistics
        self.stats = {
            'total_matches': 0,
            'exact_matches': 0,
            'semantic_matches': 0,
            'fuzzy_matches': 0,
            'confirmations_needed': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Ensure cache directory exists
        if use_cache:
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ SemanticEntityMatcher initialized")
    
    def normalize_text(self, text: str) -> str:
        """نرمال‌سازی متن برای مقایسه"""
        if not text:
            return ""
        
        # حذف فاصله‌های اضافی
        text = " ".join(text.split())
        
        # نرمال‌سازی کاراکترهای فارسی
        replacements = {
            'ي': 'ی', 'ى': 'ی', 'ك': 'ک',
            'ۀ': 'ه', 'ة': 'ه',
            'أ': 'ا', 'إ': 'ا', 'ٱ': 'ا', 'آ': 'ا'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text.lower().strip()
    
    # کلمات کلیدی نوع entity
    ENTITY_TYPE_WORDS = {
        'معاونت', 'سازمان', 'وزارت', 'دانشگاه', 'بانک', 'بانك', 'شرکت', 
        'موسسه', 'ستاد', 'نهاد', 'بنیاد', 'فرهنگستان', 'شورا', 'هیات',
        'پارک', 'پارك', 'مرکز', 'اداره', 'کمیته', 'صندوق'
    }
    
    def get_primary_keywords(self, text: str) -> set:
        """استخراج کلمات کلیدی اصلی (نوع entity)"""
        words = set(self.normalize_text(text).split())
        return words & self.ENTITY_TYPE_WORDS
    
    def check_primary_keyword_match(self, query: str, candidate: str) -> bool:
        """بررسی اینکه کلمات کلیدی اصلی match شده‌اند"""
        query_primary = self.get_primary_keywords(query)
        candidate_primary = self.get_primary_keywords(candidate)
        
        # اگر query کلمه کلیدی اصلی داشته باشد، candidate هم باید داشته باشد
        if query_primary:
            return bool(query_primary & candidate_primary)
        
        return True  # اگر query کلمه کلیدی اصلی نداشت، همه چیز OK است
    
    def calculate_word_overlap(self, query: str, candidate: str) -> float:
        """محاسبه word overlap"""
        stop_words = {'و', 'در', 'به', 'از', 'با', 'که', 'این', 'آن', 'یک', 'را', 'های', 'هایی'}
        
        query_words = set(self.normalize_text(query).split()) - stop_words
        candidate_words = set(self.normalize_text(candidate).split()) - stop_words
        
        if not query_words:
            return 0.0
        
        overlap = query_words & candidate_words
        return len(overlap) / len(query_words)
    
    def calculate_fuzzy_score(self, query: str, candidate: str) -> float:
        """محاسبه fuzzy similarity"""
        norm_query = self.normalize_text(query)
        norm_candidate = self.normalize_text(candidate)
        return SequenceMatcher(None, norm_query, norm_candidate).ratio()
    
    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """دریافت embedding برای یک متن"""
        if not self.embedding_client:
            return None
        
        try:
            response = await self.embedding_client.generate_embedding(text)
            if response.success and response.embeddings:
                return response.embeddings[0]
        except Exception as e:
            logger.warning(f"⚠️ Embedding generation failed: {e}")
        
        return None
    
    async def _get_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """دریافت embeddings برای چندین متن به صورت batch"""
        if not self.embedding_client or not texts:
            return [None] * len(texts)
        
        try:
            # Split into batches of 50
            batch_size = 50
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = await self.embedding_client.generate_embeddings(batch)
                
                if response.success:
                    all_embeddings.extend(response.embeddings)
                else:
                    all_embeddings.extend([None] * len(batch))
            
            return all_embeddings
            
        except Exception as e:
            logger.warning(f"⚠️ Batch embedding generation failed: {e}")
            return [None] * len(texts)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """محاسبه cosine similarity"""
        if not vec1 or not vec2:
            return 0.0
        
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _get_cache_path(self, table_name: str) -> Path:
        """مسیر فایل cache برای یک جدول"""
        return self.CACHE_DIR / f"{table_name}_embeddings.pkl"
    
    def _save_cache(self, table_name: str):
        """ذخیره cache در فایل"""
        if not self.use_cache:
            return
        
        try:
            cache_path = self._get_cache_path(table_name)
            cache_data = {
                'embeddings': self._entity_embeddings.get(table_name, {}),
                'entities': self._entity_list.get(table_name, []),
                'timestamp': time.time()
            }
            
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            logger.info(f"✅ Saved cache for {table_name} ({len(cache_data['entities'])} entities)")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to save cache: {e}")
    
    def _load_cache(self, table_name: str) -> bool:
        """بارگذاری cache از فایل"""
        if not self.use_cache:
            return False
        
        try:
            cache_path = self._get_cache_path(table_name)
            
            if not cache_path.exists():
                return False
            
            # Check if cache is expired
            cache_age = time.time() - cache_path.stat().st_mtime
            if cache_age > self.CACHE_TTL:
                logger.info(f"⏰ Cache expired for {table_name}")
                return False
            
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)
            
            self._entity_embeddings[table_name] = cache_data.get('embeddings', {})
            self._entity_list[table_name] = cache_data.get('entities', [])
            
            self.stats['cache_hits'] += 1
            logger.info(f"✅ Loaded cache for {table_name} ({len(self._entity_list[table_name])} entities)")
            
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to load cache: {e}")
            return False
    
    async def load_entity_embeddings(
        self,
        table_name: str = "masaref2_sheet1",
        force_reload: bool = False
    ):
        """
        بارگذاری و embedding همه entity های یک جدول
        
        Args:
            table_name: نام جدول
            force_reload: آیا cache را نادیده بگیریم
        """
        # اگر قبلاً load شده و force نیست، skip کن
        if table_name in self._entity_embeddings and not force_reload:
            logger.info(f"📌 Entities already loaded for {table_name}")
            return
        
        # تلاش برای load از cache
        if not force_reload and self._load_cache(table_name):
            return
        
        self.stats['cache_misses'] += 1
        
        # دریافت entity ها از database
        if not self.database_service:
            logger.warning("⚠️ No database service available")
            return
        
        try:
            entities = self.database_service.get_unique_entities(table_name)
            
            if not entities:
                logger.warning(f"⚠️ No entities found in {table_name}")
                return
            
            logger.info(f"📊 Loading {len(entities)} entities from {table_name}...")
            self._entity_list[table_name] = entities
            
            # اگر embedding client نداریم، فقط لیست را ذخیره کن
            if not self.embedding_client:
                logger.warning("⚠️ No embedding client - using fuzzy matching only")
                self._entity_embeddings[table_name] = {}
                return
            
            # تولید embeddings به صورت batch
            logger.info(f"🔄 Generating embeddings for {len(entities)} entities...")
            
            embeddings = await self._get_embeddings_batch(entities)
            
            # ذخیره در cache
            self._entity_embeddings[table_name] = {}
            successful_count = 0
            
            for entity, embedding in zip(entities, embeddings):
                if embedding:
                    self._entity_embeddings[table_name][entity] = embedding
                    successful_count += 1
            
            logger.info(f"✅ Generated embeddings for {successful_count}/{len(entities)} entities")
            
            # ذخیره در فایل cache
            self._save_cache(table_name)
            
        except Exception as e:
            logger.error(f"❌ Failed to load entities: {e}")
    
    async def find_best_match(
        self,
        query_entity: str,
        query: str = None,
        table_name: str = "masaref2_sheet1",
        top_k: int = 5
    ) -> EntityMatch:
        """
        پیدا کردن بهترین entity match
        
        Args:
            query_entity: entity استخراج شده از سوال
            query: سوال کامل کاربر (برای context)
            table_name: نام جدول
            top_k: تعداد کاندیدهای برتر
            
        Returns:
            EntityMatch با بهترین نتیجه
        """
        self.stats['total_matches'] += 1
        
        # بارگذاری entity ها اگر لازم است
        if table_name not in self._entity_list:
            await self.load_entity_embeddings(table_name)
        
        entities = self._entity_list.get(table_name, [])
        entity_embeddings = self._entity_embeddings.get(table_name, {})
        
        if not entities:
            return EntityMatch(
                matched_entity=query_entity,
                confidence=0.0,
                similarity_score=0.0,
                semantic_score=0.0,
                fuzzy_score=0.0,
                word_overlap=0.0,
                method='none',
                needs_confirmation=True,
                confirmation_message=f"❌ هیچ entity ای در جدول {table_name} یافت نشد"
            )
        
        # بررسی exact match
        normalized_query = self.normalize_text(query_entity)
        for entity in entities:
            if self.normalize_text(entity) == normalized_query:
                self.stats['exact_matches'] += 1
                logger.info(f"✅ [EXACT MATCH] '{query_entity}' = '{entity}'")
                return EntityMatch(
                    matched_entity=entity,
                    confidence=1.0,
                    similarity_score=1.0,
                    semantic_score=1.0,
                    fuzzy_score=1.0,
                    word_overlap=1.0,
                    method='exact'
                )
        
        # محاسبه امتیاز برای هر entity
        candidates = []
        
        # دریافت embedding برای query entity
        query_embedding = None
        if self.embedding_client and entity_embeddings:
            query_embedding = await self._get_embedding(query_entity)
        
        for entity in entities:
            # ⭐ شرط جدید: بررسی کلمات کلیدی اصلی
            if not self.check_primary_keyword_match(query_entity, entity):
                continue  # Skip این entity چون کلمه کلیدی اصلی match نشده
            
            # محاسبه fuzzy score
            fuzzy_score = self.calculate_fuzzy_score(query_entity, entity)
            
            # محاسبه word overlap
            word_overlap = self.calculate_word_overlap(query_entity, entity)
            
            # محاسبه semantic score
            semantic_score = 0.0
            if query_embedding and entity in entity_embeddings:
                semantic_score = self._cosine_similarity(
                    query_embedding, 
                    entity_embeddings[entity]
                )
                # Normalize to 0-1 range
                semantic_score = (semantic_score + 1) / 2
            
            # Combined score
            if semantic_score > 0:
                combined_score = (
                    self.SEMANTIC_WEIGHT * semantic_score +
                    self.FUZZY_WEIGHT * fuzzy_score +
                    self.WORD_OVERLAP_WEIGHT * word_overlap
                )
            else:
                # اگر semantic نداریم، وزن‌ها را redistribute کن
                combined_score = (
                    0.6 * fuzzy_score +
                    0.4 * word_overlap
                )
            
            candidates.append({
                'entity': entity,
                'combined_score': combined_score,
                'semantic_score': semantic_score,
                'fuzzy_score': fuzzy_score,
                'word_overlap': word_overlap
            })
        
        # Sort by combined score
        candidates.sort(key=lambda x: x['combined_score'], reverse=True)
        top_candidates = candidates[:top_k]
        
        if not top_candidates:
            return EntityMatch(
                matched_entity=query_entity,
                confidence=0.0,
                similarity_score=0.0,
                semantic_score=0.0,
                fuzzy_score=0.0,
                word_overlap=0.0,
                method='none',
                needs_confirmation=True,
                confirmation_message=f"❌ هیچ match مناسبی برای '{query_entity}' یافت نشد"
            )
        
        best = top_candidates[0]
        
        # تعیین سطح اطمینان
        confidence = best['combined_score']
        needs_confirmation = False
        confirmation_message = None
        method = 'combined'
        
        if best['semantic_score'] > 0.8:
            method = 'semantic'
            self.stats['semantic_matches'] += 1
        elif best['fuzzy_score'] > 0.8:
            method = 'fuzzy'
            self.stats['fuzzy_matches'] += 1
        
        # بررسی شرایط نیاز به تایید
        if confidence < self.HIGH_CONFIDENCE:
            # اگر best و second خیلی نزدیک هستند
            if len(top_candidates) > 1:
                score_diff = best['combined_score'] - top_candidates[1]['combined_score']
                if score_diff < 0.10:
                    needs_confirmation = True
                    self.stats['confirmations_needed'] += 1
            
            # اگر word overlap پایین است
            if best['word_overlap'] < 0.40:
                needs_confirmation = True
                self.stats['confirmations_needed'] += 1
        
        if needs_confirmation:
            confirmation_message = self._build_confirmation_message(
                query_entity, query, top_candidates[:3]
            )
        
        # Log result
        log_level = "✅" if confidence >= self.HIGH_CONFIDENCE else "⚠️" if confidence >= self.MEDIUM_CONFIDENCE else "❌"
        logger.info(
            f"{log_level} [MATCH] '{query_entity}' -> '{best['entity']}' "
            f"(confidence: {confidence:.3f}, semantic: {best['semantic_score']:.3f}, "
            f"fuzzy: {best['fuzzy_score']:.3f}, overlap: {best['word_overlap']:.3f})"
        )
        
        return EntityMatch(
            matched_entity=best['entity'],
            confidence=confidence,
            similarity_score=best['combined_score'],
            semantic_score=best['semantic_score'],
            fuzzy_score=best['fuzzy_score'],
            word_overlap=best['word_overlap'],
            method=method,
            alternatives=[
                {
                    'entity': c['entity'],
                    'score': c['combined_score']
                }
                for c in top_candidates[1:4]
            ],
            needs_confirmation=needs_confirmation,
            confirmation_message=confirmation_message
        )
    
    def _build_confirmation_message(
        self,
        query_entity: str,
        query: Optional[str],
        candidates: List[Dict[str, Any]]
    ) -> str:
        """ساخت پیام تایید برای کاربر"""
        lines = [
            "⚠️ **نیاز به تایید:**",
            "",
            f"Entity شما: **\"{query_entity}\"**",
            "",
            "گزینه‌های مشابه:",
            ""
        ]
        
        for i, c in enumerate(candidates, 1):
            confidence_pct = c['combined_score'] * 100
            emoji = "🟢" if confidence_pct >= 75 else "🟡" if confidence_pct >= 50 else "🔴"
            lines.append(f"{i}. {emoji} **{c['entity']}** ({confidence_pct:.0f}%)")
        
        lines.extend([
            "",
            "کدام گزینه درست است؟ (شماره را وارد کنید یا 'خیر' بنویسید)"
        ])
        
        return "\n".join(lines)
    
    async def match_entity(
        self,
        query_entity: str,
        query: str = None,
        table_name: str = "masaref2_sheet1"
    ) -> Tuple[Optional[str], float, bool]:
        """
        Simple interface برای entity matching
        
        Returns:
            Tuple of (matched_entity, confidence, needs_confirmation)
        """
        result = await self.find_best_match(query_entity, query, table_name)
        
        # اگر confidence خیلی پایین است، None برگردان
        if result.confidence < self.LOW_CONFIDENCE:
            return None, result.confidence, True
        
        return result.matched_entity, result.confidence, result.needs_confirmation
    
    def get_stats(self) -> Dict[str, Any]:
        """دریافت آمار عملکرد"""
        return {
            **self.stats,
            'cached_tables': list(self._entity_embeddings.keys()),
            'total_cached_entities': sum(
                len(entities) for entities in self._entity_list.values()
            )
        }

