# -*- coding: utf-8 -*-
"""
Relevance Gate
Gate دوم: بررسی Relevance قبل از Retrieval برای جلوگیری از Retrieval غیرضروری
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import chromadb

logger = logging.getLogger(__name__)


@dataclass
class RelevanceDecision:
    """
    نتیجه تصمیم Relevance Gate
    """
    is_relevant: bool
    confidence: float
    reason: str
    message: Optional[str] = None


class RelevanceGate:
    """
    Gate دوم: بررسی Relevance قبل از Retrieval
    
    Responsibilities:
    - بررسی حداقل keywords مرتبط با domain
    - محاسبه semantic similarity با collection
    - Early rejection برای جلوگیری از Retrieval غیرضروری
    
    Benefits:
    - 🚀 صرفه‌جویی در منابع (بدون Retrieval برای queries نامرتبط)
    - 💰 کاهش هزینه LLM calls
    - ⚡ سرعت بیشتر (پاسخ سریع‌تر برای queries نامرتبط)
    """
    
    # ========== Deprecated: Static Keywords (for backward compatibility only) ==========
    # این keywords حذف شده‌اند - سیستم حالا fully semantic است
    
    # Removed all static definitions - now fully dynamic!
    
    def __init__(self, embedding_client=None, chroma_client=None):
        """
        Args:
            embedding_client: برای محاسبه semantic similarity (REQUIRED)
            chroma_client: برای دسترسی به collection (REQUIRED)
        """
        if not embedding_client:
            logger.warning("⚠️ [RELEVANCE_GATE] No embedding_client provided - gate will be limited")
        if not chroma_client:
            logger.warning("⚠️ [RELEVANCE_GATE] No chroma_client provided - gate will be limited")
        
        self.embedding_client = embedding_client
        self.chroma_client = chroma_client
    
    async def check_relevance(
        self,
        query: str,
        collection_name: str,
        chroma_client: chromadb.Client
    ) -> RelevanceDecision:
        """
        بررسی Relevance query با collection - FULLY SEMANTIC
        
        استراتژی جدید:
        1. فقط از semantic similarity استفاده می‌کند
        2. هیچ static keyword ندارد
        3. کاملاً داینامیک و هوشمند
        4. با sample documents واقعی collection مقایسه می‌کند
        
        Args:
            query: سوال کاربر
            collection_name: نام collection
            chroma_client: ChromaDB client برای دسترسی به documents
            
        Returns:
            RelevanceDecision با تصمیم نهایی
        """
        query_lower = query.lower().strip()
        
        # === Step 1: Semantic Similarity Check (Primary and Only) ===
        if not self.embedding_client:
            logger.warning("⚠️ [RELEVANCE_GATE] No embedding client - allowing pass")
            return RelevanceDecision(
                is_relevant=True,
                confidence=0.5,
                reason="no_embedding_client_allow_pass"
            )
        
        try:
            semantic_similarity = await self._calculate_collection_similarity(
                query,
                collection_name,
                chroma_client
            )
            
            logger.debug(
                f"📊 [RELEVANCE_GATE] Semantic similarity: {semantic_similarity:.3f}"
            )
            
        except Exception as e:
            logger.warning(f"⚠️ [RELEVANCE_GATE] Semantic check failed: {e}")
            # Fallback: اگر خطا داد، بگذار بگذرد
            return RelevanceDecision(
                is_relevant=True,
                confidence=0.5,
                reason="semantic_check_failed_allow_pass"
            )
        
        # === Step 2: Dynamic Threshold Based on Collection ===
        thresholds = {
            "karbaran_omomi": 0.27,   # عمومی - threshold متوسط (adjusted)
            "zabete_qa": 0.30,         # تخصصی - threshold متوسط
            "budget_financial": 0.30,
            "budget_tables": 0.25,     # جداول ۱-۴ بودجه - threshold پایین‌تر برای پوشش بهتر مسیرهای درختی
            "zinaf_dakheli": 0.23,     # آموزشی - threshold پایین (adjusted for diverse questions)
            "default": 0.28
        }
        
        threshold = thresholds.get(collection_name, thresholds["default"])
        
        # === Step 3: Decision Based on Semantic Similarity ===
        if semantic_similarity >= threshold:
            # Relevant
            confidence_level = "high" if semantic_similarity >= 0.5 else "medium" if semantic_similarity >= 0.35 else "low"
            logger.info(
                f"✅ [RELEVANCE_GATE] Query relevant with {confidence_level} confidence: "
                f"semantic={semantic_similarity:.3f} >= threshold={threshold:.3f}"
            )
            return RelevanceDecision(
                is_relevant=True,
                confidence=semantic_similarity,
                reason="relevant_semantic_match"
            )
        else:
            # Not relevant
            logger.info(
                f"🚫 [RELEVANCE_GATE] Query not relevant - low semantic similarity: "
                f"semantic={semantic_similarity:.3f} < threshold={threshold:.3f}"
            )
            
            suggestion_message = self._get_rejection_message(collection_name, semantic_similarity)
            
            return RelevanceDecision(
                is_relevant=False,
                confidence=semantic_similarity,
                reason="low_semantic_similarity",
                message=suggestion_message
            )
    
    def _get_rejection_message(self, collection_name: str, similarity: float) -> str:
        """
        ساخت پیام rejection مناسب بر اساس collection
        """
        base_messages = {
            "karbaran_omomi": (
                "سوال شما به نظر ارتباط کمی با موضوعات این بخش دارد.\n\n"
                "💡 **برای دریافت پاسخ بهتر، لطفاً سوال خود را دقیق‌تر و با جزئیات بیشتر مطرح کنید:**\n"
                "- نام صندوق مورد نظر را ذکر کنید (صندوق باور، صندوق نوآور، صندوق تبادل فناوری)\n"
                "- موضوع سوال را مشخص کنید (سرمایه‌گذاری، پذیرش، ارزیابی، سهام، مالکیت و...)\n\n"
                "**مثال سوالات بهتر:**\n"
                "- «سرمایه‌گذاری در صندوق باور چگونه انجام می‌شود؟»\n"
                "- «مالکیت پروژه در صندوق نوآور متعلق به کیست؟»"
            ),
            "zabete_qa": (
                "سوال شما به نظر ارتباط کمی با موضوعات این بخش دارد.\n\n"
                "💡 **برای دریافت پاسخ بهتر، لطفاً سوال خود را دقیق‌تر مطرح کنید:**\n"
                "- شماره ماده یا بند را ذکر کنید\n"
                "- موضوع سوال را مشخص کنید (پرداخت، تاخیر، تضمین، مناقصه و...)\n\n"
                "**مثال سوالات بهتر:**\n"
                "- «ماده 46 شرایط عمومی پیمان درباره چیست؟»\n"
                "- «پیش‌پرداخت در قراردادهای پیمانکاری چقدر است؟»"
            ),
            "budget_financial": (
                "سوال شما به نظر ارتباط کمی با موضوعات این بخش دارد.\n\n"
                "💡 **برای دریافت پاسخ بهتر:**\n"
                "- سال مالی را مشخص کنید (مثلاً «بودجه سال 1403»)\n"
                "- دستگاه یا نهاد مورد نظر را ذکر کنید"
            ),
            "budget_tables": (
                "سوال شما به نظر مربوط به جداول کلان منابع و مصارف کتاب بودجه نیست.\n\n"
                "💡 **برای دریافت پاسخ بهتر:**\n"
                "- مشخص کنید سوال درباره «منابع» است یا «مصارف»\n"
                "- عنوان دقیق آیتم را بنویسید (مثلاً «درآمدهای مالیاتی»، «تملک دارایی‌های سرمایه‌ای»)\n"
                "- سال موردنظر را ذکر کنید (۱۳۹۸ تا ۱۴۰۳)\n\n"
                "**نمونه سوال‌های مناسب:**\n"
                "- «منابع بودجه کل کشور در سال ۱۴۰۳ چقدر است؟»\n"
                "- «مقدار فصل اول هزینه‌ها (جبران خدمت کارکنان) در سال ۱۴۰۲»"
            ),
            "zinaf_dakheli": (
                "سوال شما به نظر ارتباط کمی با موضوعات این بخش دارد.\n\n"
                "💡 **برای دریافت پاسخ بهتر:**\n"
                "- موضوع دوره یا کارگاه را مشخص کنید\n"
                "- از کلیدواژه‌های مرتبط استفاده کنید: دوره، آموزش، ثبت نام، کارگاه، گواهینامه"
            )
        }
        
        return base_messages.get(
            collection_name,
            "سوال شما به نظر ارتباط کمی با موضوعات این بخش دارد. لطفاً سوال خود را دقیق‌تر و با جزئیات بیشتر مطرح کنید."
        )
    
    # Removed: _check_min_keywords - no longer needed with fully semantic approach
    
    async def _calculate_collection_similarity(
        self,
        query: str,
        collection_name: str,
        chroma_client: chromadb.Client
    ) -> float:
        """
        محاسبه semantic similarity با collection - FULLY DYNAMIC
        
        استراتژی:
        1. از sample documents واقعی collection استفاده می‌کند
        2. هیچ static description ندارد
        3. کاملاً داینامیک
        """
        if not self.embedding_client:
            return 0.5
        
        try:
            collection = chroma_client.get_collection(collection_name)
            
            # دریافت sample documents
            sample_docs = collection.get(limit=15)
            
            if not sample_docs or not sample_docs.get('documents'):
                logger.warning(f"⚠️ [RELEVANCE_GATE] No documents in collection {collection_name}")
                return 0.5
            
            # ترکیب چند document برای representation بهتر
            texts_to_compare = []
            
            # استفاده از metadata (questions/answers)
            if sample_docs.get('metadatas'):
                for metadata in sample_docs['metadatas'][:15]:
                    if metadata:
                        if metadata.get('question'):
                            texts_to_compare.append(metadata['question'])
                        if metadata.get('answer'):
                            texts_to_compare.append(metadata['answer'][:200])
            
            # اگر metadata نبود، از documents استفاده کن
            if not texts_to_compare:
                texts_to_compare = [doc[:300] for doc in sample_docs['documents'][:10]]
            
            # ترکیب texts
            combined_text = ' '.join(texts_to_compare)[:1200]
            
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
                f"🎯 [RELEVANCE_GATE] Dynamic semantic similarity: {similarity:.3f} "
                f"(compared with {len(texts_to_compare)} texts from collection)"
            )
            
            return float(similarity)
            
        except Exception as e:
            logger.warning(f"⚠️ [RELEVANCE_GATE] Collection similarity calculation failed: {e}")
            return 0.5
    
    # Removed: _calculate_text_similarity - no longer needed
    # All similarity calculations are now inline and optimized

