# -*- coding: utf-8 -*-
"""
Intent Gate
Gate اول: تشخیص Intent و Domain قبل از Retrieval
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import chromadb

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """نوع Intent"""
    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"
    CROSS_DOMAIN = "cross_domain"
    AMBIGUOUS = "ambiguous"
    LOW_SIMILARITY = "low_similarity"


@dataclass
class IntentDecision:
    """
    نتیجه تصمیم Intent Gate
    """
    should_reject: bool
    intent_type: IntentType
    reason: str
    confidence: float
    response: Optional[str] = None
    domain_match: bool = True
    suggested_collection: Optional[str] = None


class IntentGate:
    """
    Gate اول: تشخیص Intent و Domain قبل از Retrieval
    
    Responsibilities:
    - تشخیص out-of-scope queries (هوا، ورزش، سیاست، موضوعات نامرتبط)
    - تشخیص cross-domain queries (سوال budget در zabete_qa)
    - تشخیص ambiguous queries (نیاز به clarification)
    - بررسی semantic similarity با domain
    
    Strategy:
    1. Rule-based checks (سریع و دقیق)
    2. Semantic checks (برای موارد مرزی)
    """
    
    # ========== Deprecated: Static Keywords (for backward compatibility only) ==========
    # این keywords فقط برای fallback نگه داشته شده‌اند
    # سیستم اصلی از dynamic extraction استفاده می‌کند
    
    # Removed all static definitions - now fully dynamic!
    
    def __init__(self, embedding_client=None, chroma_client=None):
        """
        Args:
            embedding_client: برای محاسبه semantic similarity
            chroma_client: برای دسترسی به collection metadata (برای dynamic keywords)
        """
        self.embedding_client = embedding_client
        self.chroma_client = chroma_client
        
        # Dynamic keyword extractor
        from core.gates.dynamic_keyword_extractor import DynamicKeywordExtractor
        self.keyword_extractor = DynamicKeywordExtractor(embedding_client=embedding_client)
    
    async def check_intent(
        self,
        query: str,
        collection_name: str
    ) -> IntentDecision:
        """
        بررسی Intent و Domain قبل از Retrieval - FULLY DYNAMIC
        
        استراتژی جدید:
        1. فقط از semantic similarity استفاده می‌کند
        2. هیچ static keyword ندارد
        3. کاملاً داینامیک و هوشمند
        
        Args:
            query: سوال کاربر
            collection_name: نام collection
            
        Returns:
            IntentDecision با تصمیم نهایی
        """
        query_lower = query.lower().strip()
        
        # === Step 1: Semantic Similarity Check (Primary) ===
        semantic_similarity = 0.5  # Default
        if self.embedding_client:
            try:
                semantic_similarity = await self._calculate_domain_similarity(
                    query,
                    collection_name
                )
                logger.debug(
                    f"📊 [INTENT_GATE] Semantic similarity: {semantic_similarity:.2f}"
                )
            except Exception as e:
                logger.warning(f"⚠️ [INTENT_GATE] Semantic similarity failed: {e}")
                # Fallback: اگر embedding fail کرد، بگذار بگذرد
                return IntentDecision(
                    should_reject=False,
                    intent_type=IntentType.IN_SCOPE,
                    reason="embedding_failed_allow_pass",
                    confidence=0.5,
                    domain_match=True
                )
        
        # === Step 2: Dynamic Threshold Based on Collection ===
        # threshold های داینامیک بر اساس نوع collection
        thresholds = {
            "karbaran_omomi": 0.22,  # عمومی - threshold پایین (adjusted)
            "zabete_qa": 0.30,        # تخصصی - threshold متوسط
            "budget_financial": 0.30,
            "budget_tables": 0.22,    # جداول ۱-۴ بودجه - threshold پایین برای سوالات ساختاری
            "zinaf_dakheli": 0.20,    # آموزشی - threshold پایین (adjusted for diverse questions)
            "default": 0.25
        }
        
        threshold = thresholds.get(collection_name, thresholds["default"])
        
        # === Step 3: Decision Based on Semantic Similarity ===
        if semantic_similarity >= threshold:
            # Relevant - اجازه بده
            confidence_level = "high" if semantic_similarity >= 0.5 else "medium" if semantic_similarity >= 0.35 else "low"
            logger.info(
                f"✅ [INTENT_GATE] Query passed with {confidence_level} confidence: "
                f"semantic={semantic_similarity:.2f} >= threshold={threshold:.2f}"
            )
            return IntentDecision(
                should_reject=False,
                intent_type=IntentType.IN_SCOPE,
                reason="in_scope_semantic_match",
                confidence=semantic_similarity,
                domain_match=True
            )
        else:
            # Not relevant enough - reject
            logger.info(
                f"🚫 [INTENT_GATE] Query rejected - low semantic similarity: "
                f"semantic={semantic_similarity:.2f} < threshold={threshold:.2f}"
            )
            return IntentDecision(
                should_reject=True,
                intent_type=IntentType.LOW_SIMILARITY,
                reason="low_semantic_similarity",
                confidence=semantic_similarity,
                response=self._get_low_similarity_response(collection_name),
                domain_match=False
            )
    
    # Removed: _check_out_of_scope, _check_cross_domain, _check_domain_keywords
    # این methods حذف شده‌اند چون سیستم حالا fully semantic است
    
    async def _calculate_domain_similarity(
        self,
        query: str,
        collection_name: str
    ) -> float:
        """
        محاسبه semantic similarity با domain - FULLY DYNAMIC
        
        استراتژی:
        1. از sample documents واقعی collection استفاده می‌کند
        2. هیچ static description ندارد
        3. کاملاً داینامیک
        """
        if not self.embedding_client or not self.chroma_client:
            logger.warning("⚠️ [INTENT_GATE] No embedding or chroma client - allowing pass")
            return 0.5
        
        try:
            # === Method 1: Compare with actual collection documents ===
            collection = self.chroma_client.get_collection(collection_name)
            
            # دریافت sample documents
            sample_docs = collection.get(limit=10)
            
            if not sample_docs or not sample_docs.get('documents'):
                logger.warning(f"⚠️ [INTENT_GATE] No documents in collection {collection_name}")
                return 0.5
            
            # ترکیب چند document برای representation بهتر
            # از questions و answers استفاده می‌کنیم اگر موجود باشند
            texts_to_compare = []
            
            # استفاده از metadata (questions/answers)
            if sample_docs.get('metadatas'):
                for metadata in sample_docs['metadatas'][:10]:
                    if metadata:
                        if metadata.get('question'):
                            texts_to_compare.append(metadata['question'])
                        if metadata.get('answer'):
                            texts_to_compare.append(metadata['answer'][:200])  # فقط 200 کاراکتر اول
            
            # اگر metadata نبود، از documents استفاده کن
            if not texts_to_compare:
                texts_to_compare = [doc[:300] for doc in sample_docs['documents'][:5]]
            
            # ترکیب texts
            combined_text = ' '.join(texts_to_compare)[:1000]  # محدود به 1000 کاراکتر
            
            # Generate embeddings
            query_embedding = await self.embedding_client.generate_embedding(query)
            text_embedding = await self.embedding_client.generate_embedding(combined_text)
            
            # Calculate cosine similarity
            import numpy as np
            
            if not isinstance(query_embedding, np.ndarray):
                query_embedding = np.array(query_embedding)
            if not isinstance(text_embedding, np.ndarray):
                text_embedding = np.array(text_embedding)
            
            similarity = np.dot(query_embedding, text_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(text_embedding)
            )
            
            logger.debug(
                f"🎯 [INTENT_GATE] Dynamic semantic similarity: {similarity:.3f} "
                f"(compared with {len(texts_to_compare)} texts from collection)"
            )
            
            return float(similarity)
            
        except Exception as e:
            logger.warning(f"⚠️ [INTENT_GATE] Semantic similarity calculation failed: {e}")
            # Fallback: اگر خطا داد، بگذار بگذرد
            return 0.5
    
    def _get_out_of_scope_response(
        self,
        collection_name: str,
        category: str
    ) -> str:
        """
        پاسخ برای out-of-scope queries
        """
        # پاسخ‌های اختصاصی بر اساس collection
        collection_responses = {
            "zabete_qa": (
                "متأسفانه این سوال در حیطه تخصصی من نیست. "
                "من یک دستیار هوشمند هستم که در زمینه نظام فنی و اجرایی، "
                "قراردادهای پیمانکاری، و ضوابط سازمان برنامه و بودجه کشور "
                "می‌توانم به شما کمک کنم.\n\n"
                "لطفاً سوال خود را در این زمینه‌ها مطرح کنید."
            ),
            "budget_financial": (
                "متأسفانه این سوال در حیطه تخصصی من نیست. "
                "من یک دستیار هوشمند مالی هستم که در زمینه بودجه، "
                "هزینه‌ها، درآمدها و گزارش‌های مالی می‌توانم به شما کمک کنم.\n\n"
                "لطفاً سوال خود را در این زمینه‌ها مطرح کنید."
            ),
            "budget_tables": (
                "متأسفانه این سوال در حیطه تخصصی من نیست. "
                "من یک کارشناس برنامه و بودجه هستم که فقط درباره «جداول ۱ تا ۴ کتاب بودجه» "
                "(منابع و مصارف کل کشور) برای سال‌های ۱۳۹۸ تا ۱۴۰۳ می‌توانم پاسخ دهم.\n\n"
                "لطفاً سوال خود را در همین حوزه مطرح کنید."
            )
        }
        
        return collection_responses.get(
            collection_name,
            "متأسفانه این سوال خارج از حوزه تخصصی من است. "
            "لطفاً سوال خود را در زمینه مرتبط مطرح کنید."
        )
    
    def _get_cross_domain_response(
        self,
        query: str,
        current_collection: str,
        detected_domain: str
    ) -> str:
        """
        پاسخ برای cross-domain queries
        """
        domain_names = {
            'budget': 'بودجه و امور مالی',
            'contract': 'قراردادها و نظام فنی و اجرایی'
        }
        
        domain_name = domain_names.get(detected_domain, 'دامنه دیگر')
        
        return (
            f"🔄 سوال شما به نظر مربوط به **{domain_name}** است، "
            f"اما شما در حال حاضر در بخش دیگری هستید.\n\n"
            f"لطفاً سوال خود را در بخش مرتبط مطرح کنید، "
            f"یا سوالی متناسب با این بخش بپرسید."
        )
    
    def _get_low_similarity_response(self, collection_name: str) -> str:
        """
        پاسخ برای similarity پایین
        """
        return (
            "متأسفانه نتوانستم ارتباط مستقیم سوال شما با موضوعات این بخش را تشخیص دهم.\n\n"
            "لطفاً:\n"
            "- سوال خود را واضح‌تر و با جزئیات بیشتر مطرح کنید\n"
            "- از کلیدواژه‌های مرتبط با موضوع استفاده کنید\n"
            "- مطمئن شوید که سوال در حیطه تخصصی این بخش است"
        )

