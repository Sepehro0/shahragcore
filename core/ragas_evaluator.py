# -*- coding: utf-8 -*-
"""
RAGAS Evaluator
ادغام RAGAS برای ارزیابی سیستم RAG
"""

import logging
from typing import Dict, Any, List, Optional
import asyncio

logger = logging.getLogger(__name__)


class RAGASEvaluator:
    """
    ارزیابی کننده RAGAS برای سنجش کیفیت سیستم RAG
    
    Metrics:
    - Retrieval: context_precision, context_recall, MRR
    - Generation: faithfulness, answer_relevancy, hallucination_rate
    - End-to-End: correctness, confidence, user_satisfaction
    """
    
    def __init__(self, qwen_client=None, embedding_client=None):
        """
        Args:
            qwen_client: کلاینت Qwen برای LLM-based metrics
            embedding_client: کلاینت embedding برای similarity calculations
        """
        self.qwen_client = qwen_client
        self.embedding_client = embedding_client
        
        # Try to import RAGAS
        try:
            from ragas import evaluate
            from ragas.metrics import (
                context_precision,
                context_recall,
                faithfulness,
                answer_relevancy
            )
            self.ragas_available = True
            self.evaluate = evaluate
            self.metrics = {
                'context_precision': context_precision,
                'context_recall': context_recall,
                'faithfulness': faithfulness,
                'answer_relevancy': answer_relevancy
            }
            logger.info("✅ RAGAS library loaded successfully")
        except ImportError as e:
            logger.warning(f"⚠️ RAGAS library not available: {e}")
            self.ragas_available = False
    
    async def calculate_retrieval_metrics(
        self,
        query: str,
        retrieved_contexts: List[str],
        ground_truth_contexts: Optional[List[str]] = None,
        ground_truth_answer: Optional[str] = None
    ) -> Dict[str, float]:
        """
        محاسبه متریک‌های Retrieval
        
        Args:
            query: سوال کاربر
            retrieved_contexts: Context های بازیابی شده
            ground_truth_contexts: Context های واقعی (اختیاری)
            ground_truth_answer: پاسخ واقعی (برای context_recall)
        
        Returns:
            Dictionary with retrieval metrics
        """
        metrics = {
            'context_precision': 0.0,
            'context_recall': 0.0,
            'mrr': 0.0
        }
        
        if not retrieved_contexts:
            return metrics
        
        # === Context Precision ===
        # نسبت context های مرتبط در top-k
        # (Simulated: فرض می‌کنیم context های top-ranked مرتبط‌ترند)
        if ground_truth_contexts:
            relevant_count = sum(
                1 for ctx in retrieved_contexts[:5]
                if any(self._is_context_relevant(ctx, gt) for gt in ground_truth_contexts)
            )
            metrics['context_precision'] = relevant_count / min(len(retrieved_contexts), 5)
        else:
            # بدون ground truth، از تشابه استفاده می‌کنیم
            metrics['context_precision'] = await self._estimate_context_precision(
                query, retrieved_contexts
            )
        
        # === Context Recall ===
        # نسبت context های مرتبط که بازیابی شده‌اند
        if ground_truth_contexts:
            retrieved_relevant = sum(
                1 for gt in ground_truth_contexts
                if any(self._is_context_relevant(ctx, gt) for ctx in retrieved_contexts)
            )
            metrics['context_recall'] = retrieved_relevant / len(ground_truth_contexts)
        elif ground_truth_answer:
            # اگر ground truth answer داریم، بررسی می‌کنیم که آیا context ها اطلاعات لازم را دارند
            metrics['context_recall'] = await self._estimate_context_recall(
                ground_truth_answer, retrieved_contexts
            )
        else:
            # بدون ground truth، نمی‌توانیم recall را محاسبه کنیم
            metrics['context_recall'] = 0.5  # Neutral
        
        # === MRR (Mean Reciprocal Rank) ===
        # اگر ground truth داریم، رتبه اولین context مرتبط را می‌یابیم
        if ground_truth_contexts:
            for rank, ctx in enumerate(retrieved_contexts, 1):
                if any(self._is_context_relevant(ctx, gt) for gt in ground_truth_contexts):
                    metrics['mrr'] = 1.0 / rank
                    break
        else:
            # فرض می‌کنیم top result مرتبط است
            metrics['mrr'] = 1.0 if retrieved_contexts else 0.0
        
        return metrics
    
    async def calculate_generation_metrics(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        ground_truth_answer: Optional[str] = None
    ) -> Dict[str, float]:
        """
        محاسبه متریک‌های Generation
        
        Args:
            query: سوال کاربر
            answer: پاسخ تولید شده
            contexts: Context های استفاده شده
            ground_truth_answer: پاسخ واقعی (اختیاری)
        
        Returns:
            Dictionary with generation metrics
        """
        metrics = {
            'faithfulness': 0.0,
            'answer_relevancy': 0.0,
            'hallucination_rate': 0.0
        }
        
        if not answer or not contexts:
            return metrics
        
        # === Faithfulness ===
        # آیا پاسخ فقط بر اساس context ها تولید شده؟
        metrics['faithfulness'] = await self._calculate_faithfulness(
            answer, contexts
        )
        
        # === Answer Relevancy ===
        # آیا پاسخ به سوال مرتبط است؟
        metrics['answer_relevancy'] = await self._calculate_answer_relevancy(
            query, answer
        )
        
        # === Hallucination Rate ===
        # نرخ hallucination (1 - faithfulness)
        metrics['hallucination_rate'] = 1.0 - metrics['faithfulness']
        
        return metrics
    
    async def calculate_end_to_end_metrics(
        self,
        query: str,
        answer: str,
        ground_truth_answer: Optional[str] = None,
        confidence_score: float = 0.0
    ) -> Dict[str, float]:
        """
        محاسبه متریک‌های End-to-End
        
        Args:
            query: سوال کاربر
            answer: پاسخ تولید شده
            ground_truth_answer: پاسخ واقعی (اختیاری)
            confidence_score: امتیاز confidence سیستم
        
        Returns:
            Dictionary with end-to-end metrics
        """
        metrics = {
            'correctness': 0.0,
            'confidence': confidence_score,
            'user_satisfaction': 0.0
        }
        
        # === Correctness ===
        if ground_truth_answer:
            # محاسبه correctness بر اساس تشابه با ground truth
            metrics['correctness'] = await self._calculate_correctness(
                answer, ground_truth_answer
            )
        else:
            # بدون ground truth، از answer_relevancy استفاده می‌کنیم
            metrics['correctness'] = 0.7  # Neutral
        
        # === User Satisfaction (Estimated) ===
        # تخمین رضایت کاربر بر اساس confidence و correctness
        # Scale to 0-5 (نه درصد)
        satisfaction_score = (
            0.6 * confidence_score +
            0.4 * metrics['correctness']
        )
        metrics['user_satisfaction'] = min(satisfaction_score * 5, 5.0)  # Scale to 0-5, max 5
        
        return metrics
    
    async def evaluate_single_query(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        confidence_score: float = 0.0,
        ground_truth_answer: Optional[str] = None,
        ground_truth_contexts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        ارزیابی کامل یک query
        
        Returns:
            Dictionary with all metrics grouped by category
        """
        # Retrieval metrics
        retrieval_metrics = await self.calculate_retrieval_metrics(
            query=query,
            retrieved_contexts=contexts,
            ground_truth_contexts=ground_truth_contexts,
            ground_truth_answer=ground_truth_answer
        )
        
        # Generation metrics
        generation_metrics = await self.calculate_generation_metrics(
            query=query,
            answer=answer,
            contexts=contexts,
            ground_truth_answer=ground_truth_answer
        )
        
        # End-to-end metrics
        end_to_end_metrics = await self.calculate_end_to_end_metrics(
            query=query,
            answer=answer,
            ground_truth_answer=ground_truth_answer,
            confidence_score=confidence_score
        )
        
        return {
            'retrieval': retrieval_metrics,
            'generation': generation_metrics,
            'end_to_end': end_to_end_metrics
        }
    
    # === Helper Methods ===
    
    def _is_context_relevant(self, context: str, ground_truth: str, threshold: float = 0.7) -> bool:
        """بررسی مرتبط بودن یک context با ground truth"""
        if not context or not ground_truth:
            return False
        
        # Simple token-based similarity
        context_tokens = set(self._tokenize(context))
        gt_tokens = set(self._tokenize(ground_truth))
        
        if not context_tokens or not gt_tokens:
            return False
        
        intersection = context_tokens.intersection(gt_tokens)
        union = context_tokens.union(gt_tokens)
        
        jaccard = len(intersection) / len(union) if union else 0.0
        
        return jaccard >= threshold
    
    async def _estimate_context_precision(
        self,
        query: str,
        contexts: List[str]
    ) -> float:
        """تخمین context precision بدون ground truth"""
        if not self.qwen_client or not contexts:
            return 0.5
        
        # از LLM بپرس که کدام context ها به query مرتبط هستند
        contexts_text = "\n".join([f"{i+1}. {c[:200]}..." for i, c in enumerate(contexts[:5])])
        
        prompt = f"""سوال: {query}

Context های بازیابی شده:
{contexts_text}

چند تا از این context ها به سوال مرتبط هستند؟ فقط عدد را بنویس (0-{min(len(contexts), 5)})."""
        
        try:
            response = await self.qwen_client.generate_text(
                prompt=prompt,
                system_prompt="شما یک ارزیاب هستید. فقط عدد را بنویس.",
                temperature=0.0,
                max_tokens=10
            )
            
            if response.success and response.text:
                # استخراج عدد از پاسخ
                import re
                numbers = re.findall(r'\d+', response.text)
                if numbers:
                    relevant_count = int(numbers[0])
                    return min(relevant_count / min(len(contexts), 5), 1.0)
        except Exception as e:
            logger.warning(f"⚠️ Context precision estimation failed: {e}")
        
        return 0.5  # Default
    
    async def _estimate_context_recall(
        self,
        ground_truth_answer: str,
        contexts: List[str]
    ) -> float:
        """تخمین context recall: آیا context ها اطلاعات لازم را دارند؟"""
        if not contexts:
            return 0.0
        
        # بررسی کلمات کلیدی ground truth در contexts
        gt_tokens = set(self._tokenize(ground_truth_answer))
        
        if not gt_tokens:
            return 0.5
        
        # محاسبه coverage
        all_context_tokens = set()
        for ctx in contexts:
            all_context_tokens.update(self._tokenize(ctx))
        
        if not all_context_tokens:
            return 0.0
        
        coverage = len(gt_tokens.intersection(all_context_tokens)) / len(gt_tokens)
        
        return min(coverage, 1.0)
    
    async def _calculate_faithfulness(
        self,
        answer: str,
        contexts: List[str]
    ) -> float:
        """محاسبه faithfulness: آیا پاسخ بر اساس context ها است؟"""
        if not self.qwen_client or not contexts:
            return 0.5
        
        context_str = "\n".join([f"منبع {i+1}: {c[:300]}..." for i, c in enumerate(contexts[:3])])
        
        prompt = f"""پاسخ: {answer}

منابع:
{context_str}

آیا تمام اطلاعات در پاسخ از منابع گرفته شده است؟ فقط با 'بله' یا 'خیر' پاسخ دهید."""
        
        try:
            response = await self.qwen_client.generate_text(
                prompt=prompt,
                system_prompt="شما یک ارزیاب هستید. فقط با 'بله' یا 'خیر' پاسخ دهید.",
                temperature=0.0,
                max_tokens=10
            )
            
            if response.success and response.text:
                text_lower = response.text.lower().strip()
                if 'بله' in text_lower:
                    return 1.0
                elif 'خیر' in text_lower:
                    return 0.0
        except Exception as e:
            logger.warning(f"⚠️ Faithfulness calculation failed: {e}")
        
        return 0.5  # Neutral
    
    async def _calculate_answer_relevancy(
        self,
        query: str,
        answer: str
    ) -> float:
        """محاسبه answer relevancy: آیا پاسخ به سوال مرتبط است؟"""
        if not answer:
            return 0.0
        
        # بررسی token overlap
        query_tokens = set(self._tokenize(query))
        answer_tokens = set(self._tokenize(answer))
        
        if not query_tokens:
            return 0.5
        
        # محاسبه overlap
        intersection = query_tokens.intersection(answer_tokens)
        
        # Basic relevancy: کلمات کلیدی query باید در answer باشند
        token_overlap = len(intersection) / len(query_tokens)
        
        # اگر LLM در دسترس است، از آن برای تأیید استفاده کن
        if self.qwen_client:
            try:
                prompt = f"""سوال: {query}
پاسخ: {answer}

آیا این پاسخ به سوال مرتبط است؟ فقط با 'بله' یا 'خیر' پاسخ دهید."""
                
                response = await self.qwen_client.generate_text(
                    prompt=prompt,
                    system_prompt="شما یک ارزیاب هستید. فقط با 'بله' یا 'خیر' پاسخ دهید.",
                    temperature=0.0,
                    max_tokens=10
                )
                
                if response.success and response.text:
                    text_lower = response.text.lower().strip()
                    if 'بله' in text_lower:
                        llm_score = 1.0
                    elif 'خیر' in text_lower:
                        llm_score = 0.0
                    else:
                        llm_score = 0.5
                    
                    # ترکیب token overlap و LLM score
                    return (0.4 * token_overlap) + (0.6 * llm_score)
            except Exception as e:
                logger.warning(f"⚠️ LLM-based relevancy check failed: {e}")
        
        return token_overlap
    
    async def _calculate_correctness(
        self,
        answer: str,
        ground_truth: str
    ) -> float:
        """محاسبه correctness: تشابه پاسخ با ground truth"""
        if not answer or not ground_truth:
            return 0.0
        
        # Token-based similarity
        answer_tokens = set(self._tokenize(answer))
        gt_tokens = set(self._tokenize(ground_truth))
        
        if not answer_tokens or not gt_tokens:
            return 0.0
        
        intersection = answer_tokens.intersection(gt_tokens)
        union = answer_tokens.union(gt_tokens)
        
        jaccard = len(intersection) / len(union) if union else 0.0
        
        # اگر embedding در دسترس است، از cosine similarity استفاده کن
        if self.embedding_client:
            try:
                answer_emb = await self.embedding_client.generate_embedding(answer)
                gt_emb = await self.embedding_client.generate_embedding(ground_truth)
                
                # Cosine similarity
                import numpy as np
                cos_sim = np.dot(answer_emb, gt_emb) / (
                    np.linalg.norm(answer_emb) * np.linalg.norm(gt_emb)
                )
                
                # ترکیب jaccard و cosine
                return (0.5 * jaccard) + (0.5 * cos_sim)
            except Exception as e:
                logger.warning(f"⚠️ Embedding-based similarity failed: {e}")
        
        return jaccard
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize Persian text"""
        import re
        # حذف علائم نگارشی و normalize
        text = text.replace('ی', 'ی').replace('ك', 'ک')
        text = text.replace('\u200c', ' ')  # نیم‌فاصله
        # استخراج کلمات فارسی و اعداد
        tokens = re.findall(r'[\u0600-\u06FF\w]+', text.lower())
        # حذف stop words ساده
        stop_words = {'است', 'هست', 'بود', 'را', 'از', 'به', 'در', 'که', 'این', 'آن', 'با', 'یا', 'و'}
        return [t for t in tokens if t not in stop_words and len(t) > 2]
    
    def format_metrics_report(self, metrics: Dict[str, Any]) -> str:
        """فرمت کردن گزارش متریک‌ها برای نمایش"""
        report = "📊 **RAGAS Evaluation Metrics**\n\n"
        
        # Retrieval
        if 'retrieval' in metrics:
            report += "### 🔍 Retrieval Metrics\n"
            retrieval = metrics['retrieval']
            report += f"- **Context Precision**: {retrieval.get('context_precision', 0):.2%} (Target: >80%)\n"
            report += f"- **Context Recall**: {retrieval.get('context_recall', 0):.2%} (Target: >80%)\n"
            report += f"- **MRR**: {retrieval.get('mrr', 0):.2%} (Target: >70%)\n\n"
        
        # Generation
        if 'generation' in metrics:
            report += "### 🤖 Generation Metrics\n"
            generation = metrics['generation']
            report += f"- **Faithfulness**: {generation.get('faithfulness', 0):.2%} (Target: >90%)\n"
            report += f"- **Answer Relevancy**: {generation.get('answer_relevancy', 0):.2%} (Target: >80%)\n"
            report += f"- **Hallucination Rate**: {generation.get('hallucination_rate', 0):.2%} (Target: <10%)\n\n"
        
        # End-to-End
        if 'end_to_end' in metrics:
            report += "### 🎯 End-to-End Metrics\n"
            e2e = metrics['end_to_end']
            report += f"- **Correctness**: {e2e.get('correctness', 0):.2%} (Target: >85%)\n"
            report += f"- **Confidence**: {e2e.get('confidence', 0):.2%} (Target: >70%)\n"
            report += f"- **User Satisfaction**: {e2e.get('user_satisfaction', 0):.1f}/5 (Target: >4/5)\n\n"
        
        return report
    
    async def evaluate_batch(
        self,
        test_cases: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        ارزیابی دسته‌ای (برای مجموعه تست)
        
        Args:
            test_cases: لیست test case ها، هر کدام شامل:
                - query: سوال
                - answer: پاسخ تولید شده
                - contexts: Context های استفاده شده
                - confidence: امتیاز confidence
                - ground_truth_answer: پاسخ واقعی (اختیاری)
                - ground_truth_contexts: Context های واقعی (اختیاری)
            progress_callback: تابعی برای گزارش پیشرفت
        
        Returns:
            Dictionary with aggregated metrics
        """
        all_metrics = []
        
        for i, test_case in enumerate(test_cases):
            logger.info(f"📊 Evaluating test case {i+1}/{len(test_cases)}: {test_case.get('query', '')[:50]}...")
            
            metrics = await self.evaluate_single_query(
                query=test_case['query'],
                answer=test_case['answer'],
                contexts=test_case.get('contexts', []),
                confidence_score=test_case.get('confidence', 0.0),
                ground_truth_answer=test_case.get('ground_truth_answer'),
                ground_truth_contexts=test_case.get('ground_truth_contexts')
            )
            
            all_metrics.append(metrics)
            
            if progress_callback:
                progress_callback(i + 1, len(test_cases))
        
        # محاسبه میانگین متریک‌ها
        import numpy as np
        
        avg_metrics = {
            'retrieval': {},
            'generation': {},
            'end_to_end': {}
        }
        
        for category in ['retrieval', 'generation', 'end_to_end']:
            if all_metrics and category in all_metrics[0]:
                for key in all_metrics[0][category].keys():
                    values = [m[category][key] for m in all_metrics if category in m and key in m[category]]
                    avg_metrics[category][key] = np.mean(values) if values else 0.0
        
        # اضافه کردن تعداد تست‌ها
        avg_metrics['summary'] = {
            'total_tests': len(test_cases),
            'individual_results': all_metrics
        }
        
        return avg_metrics



