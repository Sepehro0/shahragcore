# -*- coding: utf-8 -*-
"""
Context Contradiction Detector
تشخیص تناقضات بین contexts مختلف
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import re

logger = logging.getLogger(__name__)


class ContextContradictionDetector:
    """
    تشخیص contradictions بین contexts مختلف
    
    این کلاس:
    - استخراج claims از هر context
    - مقایسه claims با یکدیگر
    - تشخیص contradictory statements
    - انتخاب authoritative context در صورت تناقض
    """
    
    # ========== Contradiction Indicators ==========
    NEGATION_PATTERNS = [
        r'نمی\s*[\w]+',  # نمی‌کند، نمی‌شود
        r'غیر\s*[\w]+',  # غیر مجاز، غیر قانونی
        r'بدون',  # بدون
        r'نه\s+',  # نه
        r'نیست',  # نیست
        r'ندارد',  # ندارد
    ]
    
    AFFIRMATION_PATTERNS = [
        r'می\s*[\w]+',  # می‌کند، می‌شود
        r'مجاز',  # مجاز
        r'قانونی',  # قانونی
        r'با\s+',  # با
        r'بله',  # بله
        r'است',  # است
        r'دارد',  # دارد
    ]
    
    # Opposite pairs (برای تشخیص تناقض)
    OPPOSITE_PAIRS = [
        ('مجاز', 'غیر مجاز'),
        ('مجاز', 'ممنوع'),
        ('قانونی', 'غیر قانونی'),
        ('می‌تواند', 'نمی‌تواند'),
        ('باید', 'نباید'),
        ('است', 'نیست'),
        ('دارد', 'ندارد'),
        ('با', 'بدون'),
    ]
    
    def __init__(self, qwen_client=None):
        """
        Initialize Context Contradiction Detector
        
        Args:
            qwen_client: Qwen client برای LLM-based contradiction detection (اختیاری)
        """
        self.qwen_client = qwen_client
    
    def detect_contradictions(
        self,
        contexts: List[str],
        retrieval_results: Optional[List[Dict[str, Any]]] = None,
        use_llm: bool = False
    ) -> Dict[str, Any]:
        """
        تشخیص contradictions بین contexts
        
        Args:
            contexts: لیست context ها
            retrieval_results: نتایج retrieval (برای scores)
            use_llm: استفاده از LLM برای تشخیص دقیق‌تر
            
        Returns:
            Dict حاوی:
            - has_contradiction: bool
            - contradiction_score: float (0-1, بالاتر = تناقض بیشتر)
            - contradictory_pairs: List[Tuple[int, int]]
            - authoritative_context_idx: int (context با score بالاتر)
            - details: Dict
        """
        if not contexts or len(contexts) < 2:
            return {
                'has_contradiction': False,
                'contradiction_score': 0.0,
                'contradictory_pairs': [],
                'authoritative_context_idx': 0 if contexts else None,
                'details': {'reason': 'not_enough_contexts'}
            }
        
        # === 1. Rule-based Contradiction Detection ===
        contradictory_pairs = []
        contradiction_scores = []
        
        for i in range(len(contexts)):
            for j in range(i + 1, len(contexts)):
                score, is_contradictory = self._check_pair_contradiction(
                    contexts[i], contexts[j]
                )
                
                if is_contradictory:
                    contradictory_pairs.append((i, j))
                    contradiction_scores.append(score)
        
        # === 2. LLM-based Detection (اختیاری) ===
        if use_llm and self.qwen_client and len(contradictory_pairs) > 0:
            # برای هر pair contradictory، از LLM بپرس
            llm_confirmed_pairs = []
            for i, j in contradictory_pairs:
                if self._llm_confirm_contradiction(contexts[i], contexts[j]):
                    llm_confirmed_pairs.append((i, j))
            
            contradictory_pairs = llm_confirmed_pairs
        
        # === 3. Calculate Overall Contradiction Score ===
        if contradiction_scores:
            contradiction_score = max(contradiction_scores)
        else:
            contradiction_score = 0.0
        
        has_contradiction = len(contradictory_pairs) > 0
        
        # === 4. Select Authoritative Context ===
        authoritative_idx = self._select_authoritative_context(
            contexts, retrieval_results, contradictory_pairs
        )
        
        logger.info(
            f"🔍 [CONTRADICTION_DETECTOR] has_contradiction={has_contradiction}, "
            f"score={contradiction_score:.2f}, pairs={len(contradictory_pairs)}, "
            f"authoritative_idx={authoritative_idx}"
        )
        
        return {
            'has_contradiction': has_contradiction,
            'contradiction_score': contradiction_score,
            'contradictory_pairs': contradictory_pairs,
            'authoritative_context_idx': authoritative_idx,
            'details': {
                'num_contexts': len(contexts),
                'num_contradictory_pairs': len(contradictory_pairs),
                'contradiction_scores': contradiction_scores
            }
        }
    
    def _check_pair_contradiction(
        self,
        context1: str,
        context2: str
    ) -> Tuple[float, bool]:
        """
        بررسی تناقض بین دو context
        
        Returns:
            Tuple of (contradiction_score, is_contradictory)
        """
        context1_lower = context1.lower()
        context2_lower = context2.lower()
        
        contradiction_indicators = 0
        total_checks = 0
        
        # === Check 1: Opposite Pairs ===
        for word1, word2 in self.OPPOSITE_PAIRS:
            total_checks += 1
            
            # اگر context1 دارای word1 و context2 دارای word2 باشد
            if word1 in context1_lower and word2 in context2_lower:
                # بررسی کن که آیا در مورد یک موضوع مشترک صحبت می‌کنند
                # (ساده: اگر 2+ کلمه مشترک داشته باشند)
                common_words = set(context1_lower.split()) & set(context2_lower.split())
                if len(common_words) >= 2:
                    contradiction_indicators += 1
                    logger.debug(f"⚠️ [CONTRADICTION] Found opposite pair: '{word1}' vs '{word2}'")
            
            # معکوس
            if word2 in context1_lower and word1 in context2_lower:
                common_words = set(context1_lower.split()) & set(context2_lower.split())
                if len(common_words) >= 2:
                    contradiction_indicators += 1
                    logger.debug(f"⚠️ [CONTRADICTION] Found opposite pair: '{word2}' vs '{word1}'")
        
        # === Check 2: Negation vs Affirmation ===
        # اگر یکی negation دارد و دیگری affirmation
        context1_has_negation = any(
            re.search(pattern, context1_lower) for pattern in self.NEGATION_PATTERNS
        )
        context1_has_affirmation = any(
            re.search(pattern, context1_lower) for pattern in self.AFFIRMATION_PATTERNS
        )
        
        context2_has_negation = any(
            re.search(pattern, context2_lower) for pattern in self.NEGATION_PATTERNS
        )
        context2_has_affirmation = any(
            re.search(pattern, context2_lower) for pattern in self.AFFIRMATION_PATTERNS
        )
        
        # اگر یکی فقط negation و دیگری فقط affirmation دارد
        if (context1_has_negation and not context1_has_affirmation and
            context2_has_affirmation and not context2_has_negation):
            # بررسی موضوع مشترک
            common_words = set(context1_lower.split()) & set(context2_lower.split())
            if len(common_words) >= 3:
                contradiction_indicators += 1
                logger.debug(f"⚠️ [CONTRADICTION] Negation vs Affirmation detected")
        
        # === Calculate Score ===
        if total_checks > 0:
            contradiction_score = contradiction_indicators / total_checks
        else:
            contradiction_score = 0.0
        
        # Threshold: 0.3
        is_contradictory = contradiction_score >= 0.3
        
        return contradiction_score, is_contradictory
    
    def _llm_confirm_contradiction(
        self,
        context1: str,
        context2: str
    ) -> bool:
        """
        استفاده از LLM برای تأیید تناقض
        
        Returns:
            True اگر LLM تناقض را تأیید کند
        """
        if not self.qwen_client:
            return False
        
        try:
            prompt = f"""آیا این دو متن با یکدیگر تناقض دارند؟ فقط با "بله" یا "خیر" پاسخ دهید.

متن 1: {context1[:200]}

متن 2: {context2[:200]}

پاسخ:"""
            
            response = self.qwen_client.generate(
                prompt=prompt,
                max_tokens=10,
                temperature=0.0
            )
            
            response_lower = response.lower().strip()
            
            return 'بله' in response_lower or 'yes' in response_lower
        
        except Exception as e:
            logger.warning(f"⚠️ [CONTRADICTION_DETECTOR] LLM confirmation failed: {e}")
            return False
    
    def _select_authoritative_context(
        self,
        contexts: List[str],
        retrieval_results: Optional[List[Dict[str, Any]]],
        contradictory_pairs: List[Tuple[int, int]]
    ) -> int:
        """
        انتخاب authoritative context (با score بالاتر)
        
        Returns:
            Index of authoritative context
        """
        if not retrieval_results:
            # اگر retrieval_results نداریم، اولین context را انتخاب کن
            return 0
        
        # اگر تناقضی نیست، اولین context (با بالاترین score)
        if not contradictory_pairs:
            return 0
        
        # اگر تناقض هست، context با بالاترین score را انتخاب کن
        scores = []
        for i, result in enumerate(retrieval_results[:len(contexts)]):
            score = result.get('final_score') or result.get('rerank_score') or result.get('score', 0.0)
            scores.append((i, score))
        
        # Sort by score (descending)
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return index با بالاترین score
        return scores[0][0] if scores else 0
    
    def filter_contradictory_contexts(
        self,
        contexts: List[str],
        retrieval_results: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[List[str], List[int]]:
        """
        فیلتر کردن contexts متناقض و نگه‌داری فقط authoritative ones
        
        Returns:
            Tuple of (filtered_contexts, kept_indices)
        """
        if len(contexts) < 2:
            return contexts, list(range(len(contexts)))
        
        # تشخیص تناقضات
        contradiction_result = self.detect_contradictions(contexts, retrieval_results)
        
        if not contradiction_result['has_contradiction']:
            # اگر تناقضی نیست، همه را نگه دار
            return contexts, list(range(len(contexts)))
        
        # اگر تناقض هست، فقط authoritative context را نگه دار
        authoritative_idx = contradiction_result['authoritative_context_idx']
        
        logger.info(
            f"🔍 [CONTRADICTION_DETECTOR] Filtering contexts: "
            f"keeping only context {authoritative_idx} (authoritative)"
        )
        
        return [contexts[authoritative_idx]], [authoritative_idx]

