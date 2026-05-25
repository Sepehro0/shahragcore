# -*- coding: utf-8 -*-
"""
Entity Disambiguation Service
سرویس تشخیص و تایید entity های مبهم
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EntityCandidate:
    """کاندید entity"""
    entity_name: str
    similarity_score: float
    word_overlap_score: float
    combined_score: float
    source: str  # 'exact_match', 'fuzzy_match', 'mapping'


class EntityDisambiguator:
    """
    سرویس تشخیص و تایید entity های مبهم
    
    این سرویس:
    1. چندین کاندید برای entity پیدا می‌کند
    2. آن‌ها را بر اساس similarity و word overlap امتیازدهی می‌کند
    3. اگر اطمینان کافی نباشد، از کاربر تایید می‌گیرد
    """
    
    # Thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.85  # اگر بالاتر از این باشد، مطمئن هستیم
    LOW_CONFIDENCE_THRESHOLD = 0.50   # اگر پایین‌تر از این باشد، رد می‌کنیم
    MIN_WORD_OVERLAP = 0.40           # حداقل word overlap
    
    def __init__(self, database_service=None):
        """
        Args:
            database_service: سرویس database برای جستجوی entity ها
        """
        self.database_service = database_service
        self._entity_cache = {}
    
    def normalize_text(self, text: str) -> str:
        """نرمال‌سازی متن برای مقایسه"""
        if not text:
            return ""
        
        # حذف فاصله‌های اضافی
        text = " ".join(text.split())
        
        # تبدیل به lowercase
        text = text.lower()
        
        # نرمال‌سازی کاراکترهای فارسی
        replacements = {
            'ي': 'ی',
            'ى': 'ی',
            'ك': 'ک',
            'ۀ': 'ه',
            'ة': 'ه',
            'أ': 'ا',
            'إ': 'ا',
            'ٱ': 'ا',
            'آ': 'ا'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def calculate_word_overlap(self, query: str, candidate: str) -> float:
        """محاسبه word overlap بین query و candidate"""
        query_words = set(self.normalize_text(query).split())
        candidate_words = set(self.normalize_text(candidate).split())
        
        # حذف stop words
        stop_words = {'و', 'در', 'به', 'از', 'با', 'که', 'این', 'آن', 'یک'}
        query_words = query_words - stop_words
        candidate_words = candidate_words - stop_words
        
        if len(query_words) == 0:
            return 0.0
        
        overlap = query_words & candidate_words
        return len(overlap) / len(query_words)
    
    def calculate_combined_score(
        self,
        similarity: float,
        word_overlap: float,
        query_length: int,
        candidate_length: int
    ) -> float:
        """
        محاسبه امتیاز ترکیبی
        
        Args:
            similarity: similarity ratio از SequenceMatcher
            word_overlap: نسبت کلمات مشترک
            query_length: طول query
            candidate_length: طول candidate
            
        Returns:
            امتیاز ترکیبی بین 0 و 1
        """
        # وزن‌ها
        similarity_weight = 0.5
        word_overlap_weight = 0.4
        length_penalty_weight = 0.1
        
        # محاسبه length penalty (اگر candidate خیلی طولانی‌تر باشد، penalty بدهیم)
        length_ratio = min(query_length, candidate_length) / max(query_length, candidate_length)
        length_score = length_ratio ** 0.5  # کاهش تاثیر با جذر
        
        # امتیاز نهایی
        combined = (
            similarity_weight * similarity +
            word_overlap_weight * word_overlap +
            length_penalty_weight * length_score
        )
        
        return combined
    
    def find_entity_candidates(
        self,
        query_entity: str,
        table_name: str = "masaref2_sheet1",
        max_candidates: int = 5
    ) -> List[EntityCandidate]:
        """
        پیدا کردن کاندیدهای entity
        
        Args:
            query_entity: entity که کاربر پرسیده
            table_name: نام جدول
            max_candidates: حداکثر تعداد کاندیدها
            
        Returns:
            لیست کاندیدها مرتب شده بر اساس امتیاز
        """
        if not self.database_service:
            logger.warning("⚠️ [DISAMBIGUATOR] No database service available")
            return []
        
        # بارگذاری entity ها از cache یا database
        if table_name not in self._entity_cache:
            try:
                entities = self.database_service.get_unique_entities(table_name)
                self._entity_cache[table_name] = entities
            except Exception as e:
                logger.error(f"❌ [DISAMBIGUATOR] Error loading entities: {e}")
                return []
        
        entities = self._entity_cache[table_name]
        
        # محاسبه امتیاز برای هر entity
        candidates = []
        normalized_query = self.normalize_text(query_entity)
        query_length = len(query_entity)
        
        for entity in entities:
            normalized_entity = self.normalize_text(entity)
            
            # محاسبه similarity
            similarity = SequenceMatcher(None, normalized_query, normalized_entity).ratio()
            
            # محاسبه word overlap
            word_overlap = self.calculate_word_overlap(query_entity, entity)
            
            # محاسبه امتیاز ترکیبی
            combined_score = self.calculate_combined_score(
                similarity, word_overlap, query_length, len(entity)
            )
            
            # اگر امتیاز بالاتر از threshold باشد، اضافه کن
            if combined_score >= self.LOW_CONFIDENCE_THRESHOLD:
                candidates.append(EntityCandidate(
                    entity_name=entity,
                    similarity_score=similarity,
                    word_overlap_score=word_overlap,
                    combined_score=combined_score,
                    source='fuzzy_match'
                ))
        
        # مرتب‌سازی بر اساس امتیاز ترکیبی
        candidates.sort(key=lambda x: x.combined_score, reverse=True)
        
        return candidates[:max_candidates]
    
    def needs_disambiguation(
        self,
        query_entity: str,
        best_candidate: EntityCandidate,
        second_best: Optional[EntityCandidate] = None
    ) -> bool:
        """
        تشخیص اینکه آیا نیاز به تایید از کاربر داریم
        
        Args:
            query_entity: entity که کاربر پرسیده
            best_candidate: بهترین کاندید
            second_best: دومین کاندید (اگر وجود دارد)
            
        Returns:
            True اگر نیاز به تایید باشد
        """
        # اگر امتیاز خیلی بالاست، نیازی به تایید نیست
        if best_candidate.combined_score >= self.HIGH_CONFIDENCE_THRESHOLD:
            logger.info(f"✅ [DISAMBIGUATOR] High confidence match: {best_candidate.entity_name} ({best_candidate.combined_score:.3f})")
            return False
        
        # اگر word overlap خیلی پایین است، نیاز به تایید داریم
        if best_candidate.word_overlap_score < self.MIN_WORD_OVERLAP:
            logger.warning(f"⚠️ [DISAMBIGUATOR] Low word overlap: {best_candidate.word_overlap_score:.3f}")
            return True
        
        # اگر دو کاندید نزدیک به هم داریم، نیاز به تایید داریم
        if second_best and (best_candidate.combined_score - second_best.combined_score) < 0.15:
            logger.warning(f"⚠️ [DISAMBIGUATOR] Close candidates: {best_candidate.combined_score:.3f} vs {second_best.combined_score:.3f}")
            return True
        
        # اگر امتیاز بین threshold ها باشد، نیاز به تایید داریم
        if self.LOW_CONFIDENCE_THRESHOLD <= best_candidate.combined_score < self.HIGH_CONFIDENCE_THRESHOLD:
            logger.warning(f"⚠️ [DISAMBIGUATOR] Medium confidence: {best_candidate.combined_score:.3f}")
            return True
        
        return False
    
    def build_disambiguation_message(
        self,
        query_entity: str,
        candidates: List[EntityCandidate],
        query: str
    ) -> str:
        """
        ساخت پیام تایید برای کاربر
        
        Args:
            query_entity: entity که کاربر پرسیده
            candidates: لیست کاندیدها
            query: سوال اصلی کاربر
            
        Returns:
            پیام تایید
        """
        message_parts = [
            f"⚠️ **نیاز به تایید:**",
            f"",
            f"شما پرسیدید: *\"{query}\"*",
            f"",
            f"Entity شما: **\"{query_entity}\"**",
            f"",
            f"چند گزینه مشابه پیدا شد. لطفاً مشخص کنید منظور شما کدام است:",
            f""
        ]
        
        for i, candidate in enumerate(candidates[:5], 1):
            confidence_emoji = "🟢" if candidate.combined_score >= 0.75 else "🟡" if candidate.combined_score >= 0.60 else "🔴"
            message_parts.append(
                f"{i}. {confidence_emoji} **{candidate.entity_name}** "
                f"(اطمینان: {candidate.combined_score:.0%})"
            )
        
        message_parts.extend([
            f"",
            f"لطفاً شماره گزینه مورد نظر خود را وارد کنید، یا اگر هیچ‌کدام درست نیست، 'خیر' بنویسید."
        ])
        
        return "\n".join(message_parts)
    
    def disambiguate_entity(
        self,
        query_entity: str,
        query: str,
        table_name: str = "masaref2_sheet1"
    ) -> Tuple[Optional[str], Optional[str], bool]:
        """
        تشخیص و تایید entity
        
        Args:
            query_entity: entity که کاربر پرسیده
            query: سوال کامل کاربر
            table_name: نام جدول
            
        Returns:
            Tuple of (matched_entity, disambiguation_message, needs_confirmation)
            - matched_entity: entity که match شده (یا None)
            - disambiguation_message: پیام تایید (اگر نیاز باشد)
            - needs_confirmation: آیا نیاز به تایید کاربر دارد
        """
        # پیدا کردن کاندیدها
        candidates = self.find_entity_candidates(query_entity, table_name)
        
        if not candidates:
            logger.warning(f"⚠️ [DISAMBIGUATOR] No candidates found for: {query_entity}")
            return None, None, False
        
        best_candidate = candidates[0]
        second_best = candidates[1] if len(candidates) > 1 else None
        
        # بررسی نیاز به تایید
        if self.needs_disambiguation(query_entity, best_candidate, second_best):
            # ساخت پیام تایید
            message = self.build_disambiguation_message(query_entity, candidates, query)
            
            logger.info(f"❓ [DISAMBIGUATOR] Disambiguation needed for: {query_entity}")
            logger.info(f"   Best: {best_candidate.entity_name} ({best_candidate.combined_score:.3f})")
            if second_best:
                logger.info(f"   Second: {second_best.entity_name} ({second_best.combined_score:.3f})")
            
            return best_candidate.entity_name, message, True
        else:
            # مطمئن هستیم، نیازی به تایید نیست
            logger.info(f"✅ [DISAMBIGUATOR] Confident match: {best_candidate.entity_name}")
            return best_candidate.entity_name, None, False

