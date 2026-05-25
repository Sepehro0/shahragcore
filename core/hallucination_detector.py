# -*- coding: utf-8 -*-
"""
Hallucination Detector
تشخیص hallucination در پاسخ‌های RAG با استفاده از LLM-based faithfulness check
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import re

logger = logging.getLogger(__name__)


class HallucinationDetector:
    """
    تشخیص hallucination در پاسخ‌های RAG
    """
    
    def __init__(self, qwen_client):
        """
        Args:
            qwen_client: Qwen client برای LLM-based checks
        """
        self.qwen_client = qwen_client
    
    async def detect_hallucination(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        collection_name: str = ""
    ) -> Dict[str, Any]:
        """
        تشخیص Hallucination با روش چند لایه (Multi-layer Detection)
        
        این متد از 5 روش مختلف برای تشخیص hallucination استفاده می‌کند:
        1. LLM-based Faithfulness Check (Primary)
        2. Self-Verification Check (New - LLM verifies itself)
        3. Entity Consistency Check
        4. Semantic Similarity Check
        5. Citation Mapping Check
        
        Args:
            query: سوال کاربر
            answer: پاسخ تولید شده
            contexts: متن‌های context از اسناد
            collection_name: نام collection
            
        Returns:
            Dict with hallucination detection results
        """
        if not contexts:
            logger.warning("⚠️ No contexts provided for hallucination detection")
            return {
                'is_hallucination': True,
                'confidence': 0.0,
                'faithfulness_score': 0.0,
                'breakdown': {},
                'issues': ['No contexts available']
            }
        
        # === 1. LLM-based Faithfulness Check (Primary) ===
        llm_faithfulness = await self._llm_faithfulness_check(query, answer, contexts)
        
        # === 2. Self-Verification Check (New) ===
        self_verification_score = await self._self_verification_check(query, answer, contexts)
        
        # === 3. Entity Consistency Check ===
        entity_score, entity_issues = self._entity_consistency_check(answer, contexts)
        
        # === 4. Semantic Similarity Check ===
        semantic_score = self._semantic_similarity_check(answer, contexts)
        
        # === 5. Citation Mapping Check ===
        citation_score, citation_issues = self._citation_mapping_check(answer, contexts)
        
        # === Weighted Confidence Score ===
        # وزن‌ها به گونه‌ای تنظیم شده که روی faithfulness و self-verification تمرکز بیشتری داشته باشیم
        if 'zabete' in collection_name.lower():
            # برای zabete_qa وزن بیشتری به LLM-based checks می‌دهیم
            faithfulness_score = (
                0.40 * llm_faithfulness +
                0.30 * self_verification_score +
                0.15 * entity_score +
                0.10 * semantic_score +
                0.05 * citation_score
            )
            # Threshold سخت‌گیرانه‌تر
            hallucination_threshold = 0.70
        else:
            faithfulness_score = (
                0.35 * llm_faithfulness +
                0.25 * self_verification_score +
                0.20 * entity_score +
                0.10 * semantic_score +
                0.10 * citation_score
            )
            hallucination_threshold = 0.60
        
        # === Additional Quality Checks ===
        # 1. Answer Length Check
        answer_length = len(answer.split())
        if answer_length < 15:
            faithfulness_score *= 0.90
            logger.info(f"⚠️ Short answer ({answer_length} words), reducing confidence by 10%")
        
        # 2. Uncertainty Keywords Check
        uncertainty_keywords = ['احتمالاً', 'ممکن است', 'شاید', 'به نظر می‌رسد', 'تقریباً', 'ظاهراً']
        uncertainty_count = sum(1 for kw in uncertainty_keywords if kw in answer)
        if uncertainty_count > 0:
            faithfulness_score *= (1.0 - min(uncertainty_count * 0.05, 0.15))
            logger.info(f"⚠️ {uncertainty_count} uncertainty keywords detected, reducing confidence")
        
        # === جمع‌آوری issues ===
        all_issues = entity_issues + citation_issues
        if faithfulness_score < hallucination_threshold:
            all_issues.append(f"Low faithfulness score: {faithfulness_score:.2f} < {hallucination_threshold}")
        
        # === تشخیص نهایی Hallucination ===
        is_hallucination = faithfulness_score < hallucination_threshold
        
        logger.info(
            f"🔍 Hallucination Detection: "
            f"faithfulness={faithfulness_score:.2f}, "
            f"threshold={hallucination_threshold:.2f}, "
            f"is_hallucination={is_hallucination}"
        )
        
        return {
            'is_hallucination': is_hallucination,
            'confidence': faithfulness_score,
            'faithfulness_score': faithfulness_score,
            'breakdown': {
                'llm_faithfulness': llm_faithfulness,
                'self_verification': self_verification_score,
                'entity_consistency': entity_score,
                'semantic_similarity': semantic_score,
                'citation_mapping': citation_score
            },
            'issues': all_issues
        }
    
    def _semantic_similarity_check(self, answer: str, contexts: List[str]) -> float:
        """بررسی semantic similarity بین answer و contexts"""
        if not contexts:
            return 0.0
        
        # ساده: بررسی وجود کلمات کلیدی answer در contexts
        answer_words = set(answer.lower().split())
        context_text = ' '.join(contexts).lower()
        context_words = set(context_text.split())
        
        # محاسبه overlap
        overlap = len(answer_words & context_words)
        total_answer_words = len(answer_words)
        
        if total_answer_words == 0:
            return 0.0
        
        similarity = overlap / total_answer_words
        return min(similarity, 1.0)
    
    def _entity_consistency_check(
        self,
        answer: str,
        contexts: List[str]
    ) -> Tuple[float, List[str]]:
        """بررسی consistency entities بین answer و contexts"""
        issues = []
        
        # استخراج اعداد از answer
        answer_numbers = re.findall(r'\d+', answer)
        
        # بررسی اینکه آیا این اعداد در contexts هستند
        context_text = ' '.join(contexts)
        context_numbers = set(re.findall(r'\d+', context_text))
        
        # اگر عددی در answer هست که در contexts نیست، مشکل داریم
        answer_numbers_set = set(answer_numbers)
        missing_numbers = answer_numbers_set - context_numbers
        
        if missing_numbers:
            issues.append(f"اعداد {missing_numbers} در contexts یافت نشد")
            return 0.5, issues
        
        return 1.0, issues
    
    def _citation_mapping_check(
        self,
        answer: str,
        contexts: List[str]
    ) -> Tuple[float, List[str]]:
        """بررسی mapping citations بین answer و contexts"""
        issues = []
        
        # استخراج عبارات خاص (مثل "ماده 46", "بند ج")
        citation_patterns = [
            r'ماده\s+\d+',
            r'بند\s+[الف-ی]',
            r'تبصره\s+\d+',
            r'جزء\s+\d+'
        ]
        
        answer_citations = []
        for pattern in citation_patterns:
            answer_citations.extend(re.findall(pattern, answer, re.IGNORECASE))
        
        if not answer_citations:
            return 1.0, issues  # اگر citation نداریم، مشکلی نیست
        
        # بررسی اینکه آیا citations در contexts هستند
        context_text = ' '.join(contexts)
        context_citations = []
        for pattern in citation_patterns:
            context_citations.extend(re.findall(pattern, context_text, re.IGNORECASE))
        
        context_citations_set = set([c.lower() for c in context_citations])
        answer_citations_set = set([c.lower() for c in answer_citations])
        
        missing_citations = answer_citations_set - context_citations_set
        
        if missing_citations:
            issues.append(f"Citations {missing_citations} در contexts یافت نشد")
            return 0.5, issues
        
        return 1.0, issues
    
    async def _llm_faithfulness_check(
        self,
        query: str,
        answer: str,
        contexts: List[str]
    ) -> float:
        """LLM-based faithfulness check"""
        try:
            context_text = '\n\n'.join(contexts[:3])  # فقط 3 context اول
            
            prompt = f"""شما یک ارزیاب پاسخ‌های RAG هستید. بررسی کنید که آیا پاسخ زیر بر اساس context ارائه شده است یا خیر.

**سوال کاربر:**
{query}

**Context (اسناد بازیابی شده):**
{context_text[:2000]}

**پاسخ تولید شده:**
{answer}

**دستورالعمل:**
1. بررسی کنید که آیا تمام اطلاعات موجود در پاسخ در context وجود دارد
2. بررسی کنید که آیا هیچ اطلاعاتی در پاسخ نیست که در context نباشد
3. بررسی کنید که آیا اعداد، تاریخ‌ها، و citations درست هستند

**پاسخ شما:**
فقط یک عدد بین 0 تا 1 بدهید که نشان‌دهنده faithfulness است:
- 1.0 = کاملاً بر اساس context
- 0.8 = عمدتاً بر اساس context (ممکن است استنتاج منطقی داشته باشد)
- 0.6 = تا حدی بر اساس context (برخی اطلاعات ممکن است استنتاج شده باشد)
- 0.4 = کم بر اساس context (اطلاعات زیادی استنتاج شده)
- 0.2 = خیلی کم بر اساس context
- 0.0 = اصلاً بر اساس context نیست

فقط عدد را بنویسید (مثلاً: 0.85):"""
            
            response = await self.qwen_client.generate_text(
                prompt=prompt,
                max_tokens=50,
                temperature=0.1
            )
            
            if response.success:
                text = response.text if hasattr(response, 'text') else str(response)
                # استخراج عدد از پاسخ
                numbers = re.findall(r'0?\.\d+|1\.0|0\.0', text)
                if numbers:
                    score = float(numbers[0])
                    return min(max(score, 0.0), 1.0)
            
            # Fallback
            return 0.7
            
        except Exception as e:
            logger.warning(f"⚠️ LLM faithfulness check failed: {e}")
            return 0.7  # Fallback
    
    async def _self_verification_check(self, query: str, answer: str, contexts: List[str]) -> float:
        """
        Self-Verification: از LLM می‌خواهیم که پاسخ خودش را verify کند
        
        این روش بسیار قوی است چون LLM خودش را بررسی می‌کند و می‌گوید
        آیا پاسخی که داده واقعاً از منابع است یا خیر
        """
        if not self.qwen_client or not contexts:
            return 0.5
        
        context_str = "\n".join([f"منبع {i+1}: {c[:400]}..." for i, c in enumerate(contexts[:3])])
        
        system_prompt = """شما یک ارزیاب دقیق و صادق هستید. وظیفه شما بررسی این است که آیا پاسخ داده شده **صرفاً** بر اساس منابع ارائه شده است یا خیر.

اگر حتی بخش کوچکی از پاسخ در منابع نباشد، باید بگویید "نادرست".

فقط یکی از این 3 گزینه را بنویس:
- "کاملاً صحیح" → اگر 100% اطلاعات پاسخ در منابع موجود است
- "نسبتاً صحیح" → اگر بیشتر اطلاعات در منابع است ولی جزئیات کمی ممکن است استنباط باشد
- "نادرست" → اگر اطلاعات پاسخ در منابع موجود نیست یا تناقض دارد"""
        
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
                logger.info(f"🔍 Self-verification response: {response_text}")
                
                # Parse response
                if 'کاملاً صحیح' in response_text or 'کاملا صحیح' in response_text:
                    return 1.0
                elif 'نسبتاً صحیح' in response_text or 'نسبتا صحیح' in response_text:
                    return 0.7
                elif 'نادرست' in response_text:
                    return 0.0
                else:
                    # Fallback parsing
                    if 'صحیح' in response_text and 'نادرست' not in response_text:
                        return 0.8
                    elif 'نادرست' in response_text or 'اشتباه' in response_text:
                        return 0.1
            
            return 0.5  # Default if unclear
            
        except Exception as e:
            logger.warning(f"⚠️ Self-verification check failed: {e}")
            return 0.5

