# -*- coding: utf-8 -*-
"""
Pre-Generation Guard
محافظ قبل از generation برای جلوگیری از hallucination
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class GateStatus(Enum):
    """وضعیت هر gate"""
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class GuardResult:
    """
    نتیجه Pre-Generation Guard
    """
    should_generate: bool  # آیا باید generation انجام شود؟
    reason: str  # دلیل تصمیم
    quality_score: float  # نمره کیفیت کلی (0-1)
    issues: List[str]  # لیست مشکلات یافت شده
    gate_results: Dict[str, str]  # نتیجه هر gate
    details: Dict[str, Any]  # جزئیات اضافی


class PreGenerationGuard:
    """
    Pre-Generation Guard: بررسی کیفیت context قبل از LLM generation
    
    این guard چک‌های زیر را انجام می‌دهد:
    1. Retrieval Quality Check: آیا scores کافی هستند؟
    2. Semantic Alignment Check: آیا query و context مرتبط هستند؟
    3. Keyword Coverage Check: آیا keywords مهم در context هستند؟
    4. Context Sufficiency Check: آیا context کافی است؟
    
    اگر هر یک از این checks fail شود، generation متوقف می‌شود.
    """
    
    # ========== Thresholds ==========
    MIN_AVG_SCORE = 0.35  # حداقل میانگین score top-3 (کاهش یافت)
    MIN_MAX_SCORE = 0.40  # حداقل بیشترین score (کاهش یافت)
    MIN_SEMANTIC_SIMILARITY = 0.30  # حداقل similarity query-context (کاهش یافت)
    MIN_KEYWORD_COVERAGE = 0.40  # حداقل coverage keywords (کاهش یافت از 0.60)
    MIN_CONTEXT_LENGTH = 30  # حداقل طول context (کاراکتر) (کاهش یافت)
    
    def __init__(
        self,
        semantic_alignment_checker=None,
        embedding_client=None
    ):
        """
        Initialize Pre-Generation Guard
        
        Args:
            semantic_alignment_checker: SemanticAlignmentChecker instance
            embedding_client: Embedding client برای similarity checks
        """
        self.semantic_alignment_checker = semantic_alignment_checker
        self.embedding_client = embedding_client
    
    def evaluate_context_quality(
        self,
        query: str,
        contexts: List[str],
        retrieval_results: List[Dict[str, Any]],
        collection_name: str,
        query_complexity: Optional[Dict[str, Any]] = None
    ) -> GuardResult:
        """
        ارزیابی کیفیت context قبل از generation
        
        Args:
            query: سوال کاربر
            contexts: لیست context ها
            retrieval_results: نتایج retrieval
            collection_name: نام collection
            query_complexity: اطلاعات پیچیدگی query
            
        Returns:
            GuardResult با تصمیم نهایی
        """
        issues = []
        gate_results = {}
        details = {}
        
        # === Gate 1: Retrieval Quality Check ===
        retrieval_gate = self._check_retrieval_quality(retrieval_results)
        gate_results['retrieval_quality'] = retrieval_gate['status'].value
        details['retrieval_quality'] = retrieval_gate
        
        if retrieval_gate['status'] == GateStatus.FAIL:
            issues.append(retrieval_gate['reason'])
        
        # === Gate 2: Semantic Alignment Check ===
        if self.semantic_alignment_checker and self.embedding_client:
            semantic_gate = self._check_semantic_alignment(
                query, contexts, retrieval_results
            )
            gate_results['semantic_alignment'] = semantic_gate['status'].value
            details['semantic_alignment'] = semantic_gate
            
            if semantic_gate['status'] == GateStatus.FAIL:
                issues.append(semantic_gate['reason'])
        else:
            gate_results['semantic_alignment'] = GateStatus.SKIP.value
        
        # === Gate 3: Keyword Coverage Check ===
        keyword_gate = self._check_keyword_coverage(query, contexts, collection_name)
        gate_results['keyword_coverage'] = keyword_gate['status'].value
        details['keyword_coverage'] = keyword_gate
        
        if keyword_gate['status'] == GateStatus.FAIL:
            issues.append(keyword_gate['reason'])
        
        # === Gate 4: Context Sufficiency Check ===
        sufficiency_gate = self._check_context_sufficiency(contexts, query_complexity)
        gate_results['context_sufficiency'] = sufficiency_gate['status'].value
        details['context_sufficiency'] = sufficiency_gate
        
        if sufficiency_gate['status'] == GateStatus.FAIL:
            issues.append(sufficiency_gate['reason'])
        
        # === Final Decision ===
        # محاسبه quality score کلی
        quality_scores = []
        if retrieval_gate.get('score') is not None:
            quality_scores.append(retrieval_gate['score'])
        if 'semantic_alignment' in details and details['semantic_alignment'].get('score') is not None:
            quality_scores.append(details['semantic_alignment']['score'])
        if keyword_gate.get('score') is not None:
            quality_scores.append(keyword_gate['score'])
        if sufficiency_gate.get('score') is not None:
            quality_scores.append(sufficiency_gate['score'])
        
        quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        # === Special handling for karbaran_omomi (Dynamic Approach) ===
        # برای karbaran_omomi، از semantic alignment به عنوان fallback استفاده می‌کنیم
        # این روش داینامیک است و به keywords استاتیک وابسته نیست
        # zabete_qa هم نیاز به fallback دارد برای سوالات کلی
        failed_gates = [k for k, v in gate_results.items() if v == GateStatus.FAIL.value]
        
        semantic_alignment_gate = details.get('semantic_alignment', {})
        semantic_alignment_score = semantic_alignment_gate.get('score', 0.0)

        only_keyword_failed = (
            'keyword_coverage' in failed_gates and
            gate_results.get('retrieval_quality') != GateStatus.FAIL.value and
            gate_results.get('context_sufficiency') != GateStatus.FAIL.value
        )

        if collection_name in ("karbaran_omomi", "zabete_qa"):
            if collection_name == "zabete_qa":
                good_semantic = semantic_alignment_score >= 0.22
                high_quality = quality_score >= 0.50
            else:
                good_semantic = semantic_alignment_score >= 0.25
                high_quality = quality_score >= 0.55
        else:
            good_semantic = semantic_alignment_score >= 0.20
            high_quality = quality_score >= 0.45

        if only_keyword_failed and (good_semantic or high_quality):
            logger.info(
                f"✅ [PRE_GENERATION_GUARD][{collection_name}] Allowing generation despite keyword_coverage fail: "
                f"quality_score={quality_score:.2f}, keyword_coverage={keyword_gate.get('coverage', 0.0):.2f}, "
                f"semantic_alignment={semantic_alignment_score:.2f}"
            )
            should_generate = True
            reason = "all_gates_passed_with_semantic_fallback" if good_semantic else "all_gates_passed_with_high_quality"
        elif failed_gates:
            should_generate = False
            reason = f"gates_failed: {', '.join(failed_gates)}"
        else:
            should_generate = True
            reason = "all_gates_passed"
        
        logger.info(
            f"🛡️ [PRE_GENERATION_GUARD] should_generate={should_generate}, "
            f"quality_score={quality_score:.2f}, failed_gates={failed_gates}"
        )
        
        return GuardResult(
            should_generate=should_generate,
            reason=reason,
            quality_score=quality_score,
            issues=issues,
            gate_results=gate_results,
            details=details
        )
    
    def _check_retrieval_quality(
        self,
        retrieval_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        بررسی کیفیت retrieval بر اساس scores
        
        Returns:
            Dict با status, reason, score
        """
        if not retrieval_results:
            return {
                'status': GateStatus.FAIL,
                'reason': 'no_retrieval_results',
                'score': 0.0
            }
        
        # محاسبه scores
        scores = []
        for r in retrieval_results[:3]:
            score = r.get('final_score') or r.get('rerank_score') or r.get('score', 0.0)
            # Normalize if > 1.0
            if score > 1.0:
                score = min(score / 1.5, 1.0)
            scores.append(score)
        
        avg_score = sum(scores) / len(scores) if scores else 0.0
        max_score = max(scores) if scores else 0.0
        
        # Check thresholds
        if avg_score < self.MIN_AVG_SCORE or max_score < self.MIN_MAX_SCORE:
            return {
                'status': GateStatus.FAIL,
                'reason': f'low_retrieval_quality (avg={avg_score:.2f}, max={max_score:.2f})',
                'score': avg_score,
                'avg_score': avg_score,
                'max_score': max_score
            }
        
        return {
            'status': GateStatus.PASS,
            'reason': 'retrieval_quality_sufficient',
            'score': avg_score,
            'avg_score': avg_score,
            'max_score': max_score
        }
    
    def _check_semantic_alignment(
        self,
        query: str,
        contexts: List[str],
        retrieval_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        بررسی semantic alignment بین query و contexts
        
        Returns:
            Dict با status, reason, score
        """
        if not self.semantic_alignment_checker:
            return {
                'status': GateStatus.SKIP,
                'reason': 'semantic_checker_not_available',
                'score': None
            }
        
        try:
            # استفاده از SemanticAlignmentChecker
            alignment_result = self.semantic_alignment_checker.check_alignment(
                query=query,
                contexts=contexts,
                retrieval_results=retrieval_results
            )
            
            if alignment_result['is_aligned']:
                return {
                    'status': GateStatus.PASS,
                    'reason': 'semantic_alignment_sufficient',
                    'score': alignment_result['alignment_score'],
                    'max_similarity': alignment_result['max_similarity']
                }
            else:
                return {
                    'status': GateStatus.FAIL,
                    'reason': f"low_semantic_alignment (score={alignment_result['alignment_score']:.2f})",
                    'score': alignment_result['alignment_score'],
                    'max_similarity': alignment_result['max_similarity']
                }
        except Exception as e:
            logger.warning(f"⚠️ [PRE_GENERATION_GUARD] Semantic alignment check failed: {e}")
            return {
                'status': GateStatus.SKIP,
                'reason': f'semantic_check_error: {str(e)}',
                'score': None
            }
    
    def _check_keyword_coverage(
        self,
        query: str,
        contexts: List[str],
        collection_name: str = "default"
    ) -> Dict[str, Any]:
        """
        بررسی coverage keywords در contexts
        
        Returns:
            Dict با status, reason, score
        """
        if not contexts:
            return {
                'status': GateStatus.FAIL,
                'reason': 'no_contexts',
                'score': 0.0
            }
        
        # برای queryهای analytical (چرا، چطور) که به دنبال توضیح هستند،
        # keyword coverage کمتر اهمیت دارد
        analytical_keywords = ['چرا', 'چطور', 'چگونه', 'علت', 'دلیل']
        is_analytical = any(kw in query for kw in analytical_keywords)
        
        # استخراج keywords از query (ساده - فقط کلمات مهم)
        # فیلتر کردن stop words
        stop_words = {'در', 'به', 'از', 'که', 'را', 'و', 'یا', 'این', 'آن', 'است', 'برای', 'با', 'چرا', 'چطور', 'چگونه'}
        
        query_words = query.split()
        keywords = [w for w in query_words if len(w) > 2 and w not in stop_words]
        
        if not keywords:
            # اگر keyword نداریم، pass می‌دهیم
            return {
                'status': GateStatus.PASS,
                'reason': 'no_keywords_to_check',
                'score': 1.0
            }
        
        # بررسی coverage در contexts
        combined_context = ' '.join(contexts).lower()
        matched_keywords = [kw for kw in keywords if kw.lower() in combined_context]
        
        coverage = len(matched_keywords) / len(keywords) if keywords else 0.0
        
        # برای analytical queries، threshold را کاهش می‌دهیم
        # برای karbaran_omomi و zinaf_dakheli، threshold را کاهش می‌دهیم
        # چون این collection ها محتوای عمومی و متنوع دارند
        # zabete_qa هم نیاز به threshold پایین‌تر دارد برای سوالات کلی
        if collection_name == "karbaran_omomi":
            threshold = 0.10
        elif collection_name == "zinaf_dakheli":
            threshold = 0.10
        elif collection_name == "zabete_qa":
            threshold = 0.12
        elif collection_name and collection_name.startswith("col_"):
            threshold = 0.15
        elif is_analytical:
            threshold = 0.25
        else:
            threshold = self.MIN_KEYWORD_COVERAGE
        
        if coverage < threshold:
            missing = [kw for kw in keywords if kw.lower() not in combined_context]
            return {
                'status': GateStatus.FAIL,
                'reason': f'low_keyword_coverage ({coverage:.0%})',
                'score': coverage,
                'coverage': coverage,
                'matched': matched_keywords,
                'missing': missing
            }
        
        return {
            'status': GateStatus.PASS,
            'reason': 'keyword_coverage_sufficient',
            'score': coverage,
            'coverage': coverage,
            'matched': matched_keywords
        }
    
    def _check_context_sufficiency(
        self,
        contexts: List[str],
        query_complexity: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        بررسی کفایت context برای پاسخ دادن
        
        Returns:
            Dict با status, reason, score
        """
        if not contexts:
            return {
                'status': GateStatus.FAIL,
                'reason': 'no_contexts',
                'score': 0.0
            }
        
        # محاسبه طول کل contexts
        total_length = sum(len(c) for c in contexts)
        
        # اگر query پیچیده است، context بیشتری نیاز است
        min_length = self.MIN_CONTEXT_LENGTH
        if query_complexity:
            complexity_score = query_complexity.get('complexity_score', 0.5)
            if complexity_score > 0.6:
                min_length = int(self.MIN_CONTEXT_LENGTH * 1.5)  # 75 کاراکتر
        
        if total_length < min_length:
            return {
                'status': GateStatus.FAIL,
                'reason': f'insufficient_context_length ({total_length} < {min_length})',
                'score': min(total_length / min_length, 1.0),
                'total_length': total_length,
                'min_length': min_length
            }
        
        # بررسی truncation (آیا context ها کامل هستند؟)
        truncated_count = sum(1 for c in contexts if c.endswith('...') or len(c) < 20)
        if truncated_count > len(contexts) / 2:
            return {
                'status': GateStatus.FAIL,
                'reason': f'too_many_truncated_contexts ({truncated_count}/{len(contexts)})',
                'score': 0.5,
                'truncated_count': truncated_count
            }
        
        # Score بر اساس طول و تعداد contexts
        length_score = min(total_length / (min_length * 2), 1.0)
        count_score = min(len(contexts) / 3, 1.0)
        score = (length_score + count_score) / 2
        
        return {
            'status': GateStatus.PASS,
            'reason': 'context_sufficiency_ok',
            'score': score,
            'total_length': total_length,
            'num_contexts': len(contexts)
        }

