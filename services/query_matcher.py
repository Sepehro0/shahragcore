# -*- coding: utf-8 -*-
"""
Query Matcher Module
Matching query با metadata و results
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple

from utils.text_utils import TextNormalizer
from utils.similarity_utils import SimilarityCalculator

logger = logging.getLogger(__name__)


class QueryMatcher:
    """Matching query با metadata"""
    
    def __init__(
        self,
        similarity_calculator: SimilarityCalculator = None,
        text_normalizer: TextNormalizer = None
    ):
        """
        Args:
            similarity_calculator: Similarity calculator instance
            text_normalizer: Text normalizer instance
        """
        self.similarity_calculator = similarity_calculator
        self.text_normalizer = text_normalizer or TextNormalizer()
    
    def match_metadata_answer(
        self,
        sub_query: str,
        candidates: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Matching sub_query با candidates"""
        if not candidates:
            return None
        
        normalized_sub = self.text_normalizer.normalize_text(sub_query)
        sub_tokens = self.text_normalizer.tokenize_meaningful(normalized_sub)
        
        best_match = None
        best_score = 0.0
        
        for result in candidates:
            metadata = result.get('metadata', {}) or {}
            question = metadata.get('question')
            answer = metadata.get('answer')
            
            if not question or not answer:
                continue
            
            normalized_question = self.text_normalizer.normalize_text(question)
            question_tokens = self.text_normalizer.tokenize_meaningful(normalized_question)
            
            if not sub_tokens or not question_tokens:
                continue
            
            # محاسبه شباهت معنایی
            if self.similarity_calculator:
                score = self.similarity_calculator.calculate_semantic_similarity(
                    sub_tokens, question_tokens
                )
            else:
                # Simple overlap calculation
                common = sub_tokens.intersection(question_tokens)
                score = len(common) / max(len(sub_tokens), 1)
            
            # بررسی تطابق دقیق
            if normalized_sub == normalized_question:
                score += 10
            elif normalized_sub in normalized_question or normalized_question in normalized_sub:
                score += 5
            
            # بررسی overlap
            common_tokens = sub_tokens.intersection(question_tokens)
            overlap_ratio = len(common_tokens) / max(len(sub_tokens), 1)
            if overlap_ratio >= 0.6:
                score += 3
            elif overlap_ratio >= 0.4:
                score += 1.5
            
            # بررسی شباهت کلی
            if not self._are_queries_similar(normalized_sub, normalized_question):
                continue
            
            if score > best_score and score >= 2.0:
                best_score = score
                best_match = {
                    'question': question.strip(),
                    'answer': answer.strip(),
                    'result': result,
                    'score': score
                }
        
        return best_match
    
    def check_question_intent_match(
        self,
        user_query: str,
        matched_question: str
    ) -> Tuple[bool, float]:
        """
        بررسی آیا سوال کاربر و سوال موجود در دیتابیس منظور یکسانی دارند
        
        Returns:
            (is_match, similarity_score)
        """
        if not user_query or not matched_question:
            return False, 0.0
        
        def normalize(text: str) -> str:
            text = re.sub(r'[^\w\s]', ' ', text.lower())
            text = text.replace('ي', 'ی').replace('ك', 'ک')
            return ' '.join(text.split())
        
        user_normalized = normalize(user_query)
        matched_normalized = normalize(matched_question)
        
        stopwords = {
            'و', 'در', 'به', 'از', 'که', 'این', 'را', 'با', 'است', 'یک', 'برای',
            'آیا', 'چه', 'چگونه', 'کجا', 'کی', 'چرا', 'می', 'هم', 'یا', 'اگر',
            'آن', 'ها', 'های', 'شود', 'شده', 'باشد', 'بود', 'خود', 'همه', 'هر',
            'چطوری', 'چطور', 'میشه', 'میتونم', 'بشه', 'کنم', 'بده', 'بگو', 'رو',
            'چی', 'چیه', 'کجاست', 'چجوری', 'الان', 'خیلی', 'داره', 'دارد',
            'روی', 'هستن', 'هستند', 'چیا', 'چیست',
        }
        
        user_words = set(user_normalized.split()) - stopwords
        matched_words = set(matched_normalized.split()) - stopwords
        
        if not user_words or not matched_words:
            return True, 0.5
        
        # Jaccard similarity
        intersection = len(user_words & matched_words)
        union = len(user_words | matched_words)
        jaccard = intersection / union if union > 0 else 0.0
        
        # User overlap
        user_overlap = intersection / len(user_words) if user_words else 0.0
        
        # Intent patterns
        intent_patterns = {
            'impact_effect': ['تاثیر', 'تأثیر', 'اثر', 'تغییر', 'نتیجه', 'فایده', 'مزیت'],
            'criteria': ['معیار', 'شاخص', 'ملاک', 'معیارها', 'شاخص‌ها'],
            'list_items': ['چیا', 'چیست', 'کدام', 'چه چیزی', 'چه چیزهایی'],
            'how_to': ['چگونه', 'چطور', 'نحوه', 'روش'],
            'why': ['چرا', 'علت', 'دلیل'],
        }
        
        # Check intent matching
        user_intents = set()
        matched_intents = set()
        
        for intent, keywords in intent_patterns.items():
            if any(kw in user_normalized for kw in keywords):
                user_intents.add(intent)
            if any(kw in matched_normalized for kw in keywords):
                matched_intents.add(intent)
        
        intent_match = len(user_intents & matched_intents) > 0 if (user_intents or matched_intents) else True
        
        # Combined score
        similarity_score = (jaccard * 0.4) + (user_overlap * 0.4) + (0.2 if intent_match else 0.0)
        
        is_match = similarity_score >= 0.3 or (jaccard >= 0.2 and intent_match)
        
        return is_match, similarity_score
    
    def find_exact_metadata_question(
        self,
        query: str,
        collection_results: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """جستجوی سوال/جواب دقیق در metadata"""
        if not query or not collection_results:
            return None
        
        try:
            normalized_query = self.text_normalizer.normalize_text(query)
            if not normalized_query:
                return None
            
            best_match: Optional[Dict[str, Any]] = None
            best_score: float = 0.0
            
            for res in collection_results:
                meta = res.get("metadata") or {}
                q = meta.get("question")
                a = meta.get("answer")
                
                if not q or not a:
                    continue
                
                normalized_q = self.text_normalizer.normalize_text(q)
                if not normalized_q:
                    continue
                
                # بررسی شباهت
                if not self._are_queries_similar(normalized_query, normalized_q):
                    continue
                
                # بررسی intent match
                intent_match, intent_score = self.check_question_intent_match(query, q)
                if not intent_match:
                    continue
                
                # محاسبه similarity score
                q_tokens = self.text_normalizer.tokenize_meaningful(normalized_q)
                query_tokens = self.text_normalizer.tokenize_meaningful(normalized_query)
                
                if not q_tokens or not query_tokens:
                    continue
                
                if self.similarity_calculator:
                    sim_score = self.similarity_calculator.calculate_semantic_similarity(
                        query_tokens, q_tokens
                    )
                else:
                    common = query_tokens.intersection(q_tokens)
                    sim_score = len(common) / max(len(query_tokens), 1) * 10
                
                # ترکیب scores
                normalized_sim = min(sim_score / 20.0, 1.0)
                combined_score = (normalized_sim * 0.3) + (intent_score * 0.7)
                combined_score = combined_score * 10.0
                
                if normalized_q == normalized_query:
                    combined_score += 20.0
                
                if combined_score > best_score and combined_score >= 5.0:
                    best_score = combined_score
                    enriched_result = dict(res)
                    normalized_score = min(combined_score / 30.0, 1.0)
                    enriched_result["hybrid_score"] = normalized_score
                    enriched_result["final_score"] = normalized_score
                    enriched_result["dense_score"] = normalized_score
                    
                    best_match = {
                        "question": q.strip(),
                        "answer": a.strip(),
                        "result": enriched_result,
                        "score": combined_score,
                        "intent_score": intent_score
                    }
            
            if best_match:
                logger.info(f"✅ Found exact metadata match (score={best_score:.2f})")
            
            return best_match
            
        except Exception as e:
            logger.warning(f"Exact metadata question lookup failed: {e}")
            return None
    
    def is_answer_relevant_to_query(
        self,
        query: str,
        answer: str,
        question: str
    ) -> bool:
        """بررسی relevance پاسخ به query"""
        if not query or not answer:
            return False
        
        normalized_query = self.text_normalizer.normalize_text(query).lower()
        normalized_answer = self.text_normalizer.normalize_text(answer).lower()
        
        # بررسی وجود کلمات کلیدی query در answer
        query_tokens = set(normalized_query.split())
        answer_tokens = set(normalized_answer.split())
        
        # حذف stopwords
        stopwords = TextNormalizer.SIMILARITY_STOPWORDS
        query_tokens = query_tokens - stopwords
        answer_tokens = answer_tokens - stopwords
        
        if not query_tokens:
            return True
        
        overlap = len(query_tokens & answer_tokens)
        overlap_ratio = overlap / len(query_tokens)
        
        return overlap_ratio >= 0.3
    
    def _are_queries_similar(self, first: str, second: str) -> bool:
        """بررسی شباهت دو query"""
        if not first or not second:
            return False
        
        if first == second or first in second or second in first:
            return True
        
        tokens1 = self.text_normalizer.tokenize_meaningful(first)
        tokens2 = self.text_normalizer.tokenize_meaningful(second)
        
        if not tokens1 or not tokens2:
            return False
        
        common_tokens = tokens1.intersection(tokens2)
        return len(common_tokens) >= min(3, len(tokens1), len(tokens2))

