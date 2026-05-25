# -*- coding: utf-8 -*-
"""
Enhanced Hallucination Detector with Multi-layer Detection
تشخیص Hallucination با روش چند لایه (ReDeEP-inspired)
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
import re

logger = logging.getLogger(__name__)


class EnhancedHallucinationDetector:
    """
    تشخیص Hallucination با 5 روش مختلف:
    1. LLM-based Faithfulness Check
    2. Entity Consistency Check  
    3. Citation Mapping Check
    4. Semantic Similarity Check
    5. Self-Verification Check
    """
    
    def __init__(self, qwen_client=None):
        self.qwen_client = qwen_client

    async def detect_hallucination(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        تشخیص Hallucination با روش چند لایه
        """
        if not self.qwen_client:
            logger.warning("⚠️ Qwen client not initialized, returning default scores.")
            return {
                'confidence': 0.5,
                'is_hallucination': False,
                'faithfulness_score': 0.5,
                'breakdown': {}
            }

        # === 1. LLM-based Faithfulness Check (Primary) ===
        faithfulness_score = await self._llm_based_faithfulness_check(query, answer, contexts)

        # === 2. Entity Consistency Check (Secondary) ===
        entity_consistency_score = self._entity_consistency_check(answer, contexts)

        # === 3. Citation Mapping Check ===
        citation_score = self._citation_mapping_check(answer, contexts)
        
        # === 4. Semantic Similarity Check (New) ===
        semantic_similarity_score = self._semantic_similarity_check(answer, contexts)
        
        # === 5. Self-Verification Check (New) ===
        self_verification_score = await self._self_verification_check(query, answer, contexts)

        # === Weighted Confidence Score ===
        confidence = (
            0.35 * faithfulness_score +
            0.25 * self_verification_score +
            0.20 * entity_consistency_score +
            0.10 * semantic_similarity_score +
            0.10 * citation_score
        )

        # === Strict Threshold for zabete_qa ===
        if 'zabete' in (collection_name or '').lower():
            hallucination_threshold = 0.70  # افزایش threshold
        else:
            hallucination_threshold = 0.60

        is_hallucination = confidence < hallucination_threshold
        
        # === Additional Quality Checks ===
        answer_length = len(answer.split())
        if answer_length < 15:
            confidence *= 0.9
        
        uncertainty_keywords = ['احتمالاً', 'ممکن است', 'شاید', 'به نظر می‌رسد', 'تقریباً']
        if any(keyword in answer for keyword in uncertainty_keywords):
            confidence *= 0.85
            logger.info("⚠️ Uncertainty keywords detected, reducing confidence")

        logger.info(
            f"🔍 Hallucination Detection: confidence={confidence:.2f}, "
            f"threshold={hallucination_threshold:.2f}, "
            f"is_hallucination={confidence < hallucination_threshold}"
        )

        return {
            'confidence': confidence,
            'is_hallucination': is_hallucination,
            'faithfulness_score': faithfulness_score,
            'breakdown': {
                'llm_faithfulness': faithfulness_score,
                'entity_consistency': entity_consistency_score,
                'citation_mapping': citation_score,
                'semantic_similarity': semantic_similarity_score,
                'self_verification': self_verification_score
            }
        }

    async def _llm_based_faithfulness_check(self, query: str, answer: str, contexts: List[str]) -> float:
        """LLM-based faithfulness check"""
        if not contexts:
            return 0.0

        context_str = "\n".join([f"Source {i+1}: {c}" for i, c in enumerate(contexts)])

        system_prompt = """شما یک ارزیاب هستید که صحت یک پاسخ را بر اساس منابع ارائه شده بررسی می‌کنید.
فقط با 'بله' یا 'خیر' پاسخ دهید و سپس توضیح دهید."""

        user_prompt = f"""سوال: {query}
پاسخ: {answer}
منابع:
{context_str}

آیا پاسخ داده شده، **فقط و فقط** بر اساس اطلاعات موجود در منابع ارائه شده است؟"""

        try:
            response = await self.qwen_client.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.0,
                max_tokens=100
            )
            if response.success and response.text:
                response_text = response.text.lower().strip()
                if 'بله' in response_text:
                    return 1.0
                elif 'خیر' in response_text:
                    return 0.0
            return 0.5
        except Exception as e:
            logger.warning(f"⚠️ LLM faithfulness check failed: {e}")
            return 0.5

    def _entity_consistency_check(self, answer: str, contexts: List[str]) -> float:
        """Entity consistency check"""
        answer_words = set(self._tokenize_persian(answer))
        context_words = set()
        for context in contexts:
            context_words.update(self._tokenize_persian(context))

        common_words = answer_words.intersection(context_words)
        if not answer_words:
            return 0.5
        return len(common_words) / len(answer_words)

    def _citation_mapping_check(self, answer: str, contexts: List[str]) -> float:
        """Citation mapping check"""
        score = 0.5
        if "طبق" in answer or "بر اساس" in answer:
            score += 0.2
        if any(f"سند {i+1}" in answer or f"منبع {i+1}" in answer for i in range(len(contexts))):
            score += 0.3
        return min(score, 1.0)
    
    def _semantic_similarity_check(self, answer: str, contexts: List[str]) -> float:
        """Semantic similarity check"""
        if not contexts or not answer:
            return 0.0
        
        answer_tokens = set(self._tokenize_persian(answer))
        context_tokens = set()
        for ctx in contexts:
            context_tokens.update(self._tokenize_persian(ctx))
        
        if not answer_tokens:
            return 0.5
        
        common_tokens = answer_tokens.intersection(context_tokens)
        overlap_ratio = len(common_tokens) / len(answer_tokens)
        
        return min(overlap_ratio, 1.0)
    
    async def _self_verification_check(self, query: str, answer: str, contexts: List[str]) -> float:
        """Self-Verification: LLM verifies itself"""
        if not self.qwen_client or not contexts:
            return 0.5
        
        context_str = "\n".join([f"منبع {i+1}: {c[:400]}..." for i, c in enumerate(contexts[:3])])
        
        system_prompt = """شما یک ارزیاب دقیق هستید که باید تشخیص دهید آیا پاسخ داده شده از منابع ارائه شده استخراج شده یا خیر.

فقط یکی از این 3 گزینه را بنویس:
- "کاملاً صحیح" اگر تمام اطلاعات پاسخ در منابع موجود است
- "نسبتاً صحیح" اگر بیشتر اطلاعات در منابع موجود است ولی برخی جزئیات ممکن است استنباط شده باشد
- "نادرست" اگر اطلاعات پاسخ در منابع موجود نیست یا تناقض دارد"""
        
        user_prompt = f"""سوال: {query}

پاسخ داده شده:
{answer}

منابع موجود:
{context_str}

آیا این پاسخ **فقط و فقط** بر اساس منابع موجود است؟ 
لطفاً یکی از 3 گزینه را انتخاب کنید: "کاملاً صحیح"، "نسبتاً صحیح"، یا "نادرست"
"""
        
        try:
            response = await self.qwen_client.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.0,
                max_tokens=50
            )
            
            if response.success and response.text:
                response_text = response.text.strip()
                
                if 'کاملاً صحیح' in response_text or 'کاملا صحیح' in response_text:
                    return 1.0
                elif 'نسبتاً صحیح' in response_text or 'نسبتا صحیح' in response_text:
                    return 0.7
                elif 'نادرست' in response_text:
                    return 0.0
                else:
                    if 'صحیح' in response_text and 'نادرست' not in response_text:
                        return 0.8
                    elif 'نادرست' in response_text or 'اشتباه' in response_text:
                        return 0.1
            
            return 0.5
            
        except Exception as e:
            logger.warning(f"⚠️ Self-verification check failed: {e}")
            return 0.5

    def _tokenize_persian(self, text: str) -> List[str]:
        """Simple Persian tokenizer"""
        text = text.replace('ی', 'ی').replace('ك', 'ک')
        text = text.replace('\u200c', ' ')
        tokens = re.findall(r'\b[\u0600-\u06FF\w]+\b', text.lower())
        return tokens

