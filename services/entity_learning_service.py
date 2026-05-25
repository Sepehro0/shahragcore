# -*- coding: utf-8 -*-
"""
Entity Learning Service
سیستم یادگیری از اصلاحات کاربر برای بهبود Entity Matching

این سیستم:
1. ذخیره اصلاحات کاربر
2. یادگیری از patterns
3. بهبود تدریجی دقت matching
4. پیشنهاد entity ها بر اساس history
"""

import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
import threading
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class EntityCorrection:
    """اصلاح entity توسط کاربر"""
    id: str
    timestamp: str
    query: str
    user_entity: str  # entity که کاربر پرسیده
    suggested_entity: str  # entity که سیستم پیشنهاد داده
    correct_entity: str  # entity صحیح (انتخاب کاربر)
    collection_name: str
    table_name: str
    was_correct: bool  # آیا پیشنهاد سیستم درست بود؟
    confidence: float  # confidence سیستم در زمان پیشنهاد


@dataclass
class DisambiguationRequest:
    """درخواست disambiguation از کاربر"""
    request_id: str
    timestamp: str
    query: str
    user_entity: str
    candidates: List[Dict[str, Any]]
    selected_index: Optional[int]  # انتخاب کاربر (None = هنوز انتخاب نشده)
    is_resolved: bool
    collection_name: str


class EntityLearningService:
    """
    سیستم یادگیری entity ها از اصلاحات کاربر
    
    Features:
    - ذخیره و بازیابی corrections
    - تحلیل patterns
    - پیشنهاد بر اساس history
    - Feedback loop برای بهبود
    """
    
    DATA_DIR = Path("/home/user01/qwen-api/enhanced_rag_system_dev/.entity_learning")
    CORRECTIONS_FILE = "corrections.json"
    PATTERNS_FILE = "patterns.json"
    PENDING_REQUESTS_FILE = "pending_requests.json"
    
    def __init__(self):
        """مقداردهی اولیه"""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        self.corrections: List[EntityCorrection] = []
        self.patterns: Dict[str, str] = {}  # user_entity -> correct_entity
        self.pending_requests: Dict[str, DisambiguationRequest] = {}
        self.entity_aliases: Dict[str, List[str]] = defaultdict(list)  # correct_entity -> [aliases]
        
        self._lock = threading.Lock()
        
        # بارگذاری داده‌ها
        self._load_data()
        
        # آمار
        self.stats = {
            'total_corrections': 0,
            'correct_suggestions': 0,
            'incorrect_suggestions': 0,
            'patterns_learned': 0,
            'pending_requests': 0
        }
        
        self._update_stats()
        
        logger.info(f"✅ EntityLearningService initialized with {len(self.corrections)} corrections")
    
    def _load_data(self):
        """بارگذاری داده‌ها از فایل"""
        try:
            # بارگذاری corrections
            corrections_path = self.DATA_DIR / self.CORRECTIONS_FILE
            if corrections_path.exists():
                with open(corrections_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.corrections = [EntityCorrection(**c) for c in data]
            
            # بارگذاری patterns
            patterns_path = self.DATA_DIR / self.PATTERNS_FILE
            if patterns_path.exists():
                with open(patterns_path, 'r', encoding='utf-8') as f:
                    self.patterns = json.load(f)
            
            # بارگذاری pending requests
            pending_path = self.DATA_DIR / self.PENDING_REQUESTS_FILE
            if pending_path.exists():
                with open(pending_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.pending_requests = {
                        k: DisambiguationRequest(**v) for k, v in data.items()
                    }
            
            # ساخت entity aliases از corrections
            self._build_aliases()
            
        except Exception as e:
            logger.error(f"❌ Error loading learning data: {e}")
    
    def _save_data(self):
        """ذخیره داده‌ها در فایل"""
        try:
            with self._lock:
                # ذخیره corrections
                corrections_path = self.DATA_DIR / self.CORRECTIONS_FILE
                with open(corrections_path, 'w', encoding='utf-8') as f:
                    json.dump([asdict(c) for c in self.corrections], f, ensure_ascii=False, indent=2)
                
                # ذخیره patterns
                patterns_path = self.DATA_DIR / self.PATTERNS_FILE
                with open(patterns_path, 'w', encoding='utf-8') as f:
                    json.dump(self.patterns, f, ensure_ascii=False, indent=2)
                
                # ذخیره pending requests
                pending_path = self.DATA_DIR / self.PENDING_REQUESTS_FILE
                with open(pending_path, 'w', encoding='utf-8') as f:
                    json.dump(
                        {k: asdict(v) for k, v in self.pending_requests.items()},
                        f, ensure_ascii=False, indent=2
                    )
                    
        except Exception as e:
            logger.error(f"❌ Error saving learning data: {e}")
    
    def _build_aliases(self):
        """ساخت alias map از corrections"""
        self.entity_aliases.clear()
        
        for correction in self.corrections:
            if not correction.was_correct and correction.correct_entity:
                # اگر پیشنهاد سیستم اشتباه بود، user_entity یک alias برای correct_entity است
                if correction.user_entity not in self.entity_aliases[correction.correct_entity]:
                    self.entity_aliases[correction.correct_entity].append(correction.user_entity)
    
    def _update_stats(self):
        """بروزرسانی آمار"""
        self.stats['total_corrections'] = len(self.corrections)
        self.stats['correct_suggestions'] = sum(1 for c in self.corrections if c.was_correct)
        self.stats['incorrect_suggestions'] = sum(1 for c in self.corrections if not c.was_correct)
        self.stats['patterns_learned'] = len(self.patterns)
        self.stats['pending_requests'] = len([r for r in self.pending_requests.values() if not r.is_resolved])
    
    def _normalize_entity(self, entity: str) -> str:
        """نرمال‌سازی entity برای مقایسه"""
        if not entity:
            return ""
        # حذف فاصله‌های اضافی و نرمال‌سازی
        entity = " ".join(entity.split()).strip().lower()
        # نرمال‌سازی کاراکترها
        replacements = {
            'ي': 'ی', 'ى': 'ی', 'ك': 'ک',
            'ۀ': 'ه', 'ة': 'ه',
            'أ': 'ا', 'إ': 'ا', 'ٱ': 'ا', 'آ': 'ا'
        }
        for old, new in replacements.items():
            entity = entity.replace(old, new)
        return entity
    
    def check_learned_pattern(self, user_entity: str) -> Optional[str]:
        """
        بررسی آیا برای این entity pattern یاد گرفته شده وجود دارد
        
        Args:
            user_entity: entity که کاربر پرسیده
            
        Returns:
            entity صحیح اگر pattern وجود دارد، None در غیر این صورت
        """
        normalized = self._normalize_entity(user_entity)
        
        # بررسی در patterns
        if normalized in self.patterns:
            logger.info(f"📚 [LEARNING] Found learned pattern: '{user_entity}' -> '{self.patterns[normalized]}'")
            return self.patterns[normalized]
        
        # بررسی در aliases
        for correct_entity, aliases in self.entity_aliases.items():
            if normalized in [self._normalize_entity(a) for a in aliases]:
                logger.info(f"📚 [LEARNING] Found alias: '{user_entity}' -> '{correct_entity}'")
                return correct_entity
        
        return None
    
    def record_correction(
        self,
        query: str,
        user_entity: str,
        suggested_entity: str,
        correct_entity: str,
        collection_name: str,
        table_name: str = "",
        confidence: float = 0.0
    ) -> EntityCorrection:
        """
        ثبت یک اصلاح از کاربر
        
        Args:
            query: سوال کاربر
            user_entity: entity که کاربر پرسیده
            suggested_entity: entity که سیستم پیشنهاد داده
            correct_entity: entity صحیح (انتخاب کاربر)
            collection_name: نام collection
            table_name: نام جدول
            confidence: confidence سیستم
            
        Returns:
            EntityCorrection ایجاد شده
        """
        import uuid
        
        was_correct = self._normalize_entity(suggested_entity) == self._normalize_entity(correct_entity)
        
        correction = EntityCorrection(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(),
            query=query,
            user_entity=user_entity,
            suggested_entity=suggested_entity,
            correct_entity=correct_entity,
            collection_name=collection_name,
            table_name=table_name,
            was_correct=was_correct,
            confidence=confidence
        )
        
        with self._lock:
            self.corrections.append(correction)
            
            # یادگیری pattern جدید
            if not was_correct:
                normalized = self._normalize_entity(user_entity)
                self.patterns[normalized] = correct_entity
                logger.info(f"📚 [LEARNING] Learned new pattern: '{user_entity}' -> '{correct_entity}'")
            
            self._update_stats()
        
        # ذخیره
        self._save_data()
        
        logger.info(
            f"✅ [LEARNING] Recorded correction: was_correct={was_correct}, "
            f"user='{user_entity}', suggested='{suggested_entity}', correct='{correct_entity}'"
        )
        
        return correction
    
    def create_disambiguation_request(
        self,
        query: str,
        user_entity: str,
        candidates: List[Dict[str, Any]],
        collection_name: str
    ) -> DisambiguationRequest:
        """
        ایجاد یک درخواست disambiguation برای نمایش به کاربر
        
        Args:
            query: سوال کاربر
            user_entity: entity که کاربر پرسیده
            candidates: لیست کاندیدها
            collection_name: نام collection
            
        Returns:
            DisambiguationRequest ایجاد شده
        """
        import uuid
        
        request = DisambiguationRequest(
            request_id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(),
            query=query,
            user_entity=user_entity,
            candidates=candidates,
            selected_index=None,
            is_resolved=False,
            collection_name=collection_name
        )
        
        with self._lock:
            self.pending_requests[request.request_id] = request
            self._update_stats()
        
        self._save_data()
        
        logger.info(f"❓ [LEARNING] Created disambiguation request: {request.request_id}")
        
        return request
    
    def resolve_disambiguation(
        self,
        request_id: str,
        selected_index: int
    ) -> Optional[str]:
        """
        حل disambiguation با انتخاب کاربر
        
        Args:
            request_id: ID درخواست
            selected_index: index انتخاب شده (0-based)
            
        Returns:
            entity انتخاب شده یا None
        """
        if request_id not in self.pending_requests:
            logger.warning(f"⚠️ [LEARNING] Request not found: {request_id}")
            return None
        
        request = self.pending_requests[request_id]
        
        if selected_index < 0 or selected_index >= len(request.candidates):
            logger.warning(f"⚠️ [LEARNING] Invalid selection index: {selected_index}")
            return None
        
        selected_entity = request.candidates[selected_index].get('entity', '')
        
        with self._lock:
            request.selected_index = selected_index
            request.is_resolved = True
            
            # ثبت به عنوان correction
            if request.candidates:
                suggested = request.candidates[0].get('entity', '')
                self.record_correction(
                    query=request.query,
                    user_entity=request.user_entity,
                    suggested_entity=suggested,
                    correct_entity=selected_entity,
                    collection_name=request.collection_name,
                    confidence=request.candidates[0].get('score', 0.0)
                )
            
            self._update_stats()
        
        self._save_data()
        
        logger.info(f"✅ [LEARNING] Resolved disambiguation: {request_id} -> '{selected_entity}'")
        
        return selected_entity
    
    def get_pending_requests(self, collection_name: Optional[str] = None) -> List[DisambiguationRequest]:
        """دریافت درخواست‌های pending"""
        requests = [r for r in self.pending_requests.values() if not r.is_resolved]
        
        if collection_name:
            requests = [r for r in requests if r.collection_name == collection_name]
        
        return requests
    
    def get_stats(self) -> Dict[str, Any]:
        """دریافت آمار"""
        self._update_stats()
        
        accuracy = 0.0
        if self.stats['total_corrections'] > 0:
            accuracy = self.stats['correct_suggestions'] / self.stats['total_corrections']
        
        return {
            **self.stats,
            'accuracy': accuracy,
            'entity_aliases_count': sum(len(v) for v in self.entity_aliases.values())
        }
    
    def export_patterns(self) -> Dict[str, str]:
        """خروجی patterns یاد گرفته شده"""
        return dict(self.patterns)
    
    def import_patterns(self, patterns: Dict[str, str]):
        """وارد کردن patterns"""
        with self._lock:
            self.patterns.update(patterns)
            self._update_stats()
        self._save_data()
        logger.info(f"📥 [LEARNING] Imported {len(patterns)} patterns")


# Singleton instance
_learning_service: Optional[EntityLearningService] = None

def get_learning_service() -> EntityLearningService:
    """دریافت instance از EntityLearningService"""
    global _learning_service
    if _learning_service is None:
        _learning_service = EntityLearningService()
    return _learning_service

