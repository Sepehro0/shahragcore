# -*- coding: utf-8 -*-
"""
Cross-Encoder Reranker Service
سرویس Reranking با Cross-Encoder برای بهبود نتایج
"""

import logging
from typing import List, Dict, Any, Tuple
import torch

try:
    from sentence_transformers import CrossEncoder
    CROSSENCODER_AVAILABLE = True
except ImportError:
    CROSSENCODER_AVAILABLE = False
    logging.warning("CrossEncoder not available")

logger = logging.getLogger(__name__)

# ===== Global Model Cache =====
_CACHED_RERANKER = None
_RERANKER_LOADED = False


class CrossEncoderReranker:
    """
    Cross-Encoder Reranker برای reranking نتایج RAG
    """
    
    def __init__(self, model_name: str = None):
        """
        Initialize Cross-Encoder
        
        Args:
            model_name: نام مدل cross-encoder (اختیاری)
        """
        # استفاده از مدل محلی
        self.model_name = model_name or "cross-encoder/ms-marco-MiniLM-L6-v2"
        self.model = None
        # 🔧 CRITICAL FIX: Force CPU to avoid CUDA OOM with vLLM
        self.device = "cpu"
        
        # مسیر مدل محلی - استفاده از _dev
        self.local_model_path = "/home/user01/qwen-api/enhanced_rag_system_dev/models/models--cross-encoder--ms-marco-MiniLM-L6-v2/snapshots/c5ee24cb16019beea0893ab7796b1df96625c6b8"
        
        if CROSSENCODER_AVAILABLE:
            self._load_model()
        else:
            logger.warning("CrossEncoder not available, reranking will be disabled")
    
    def _load_model(self):
        """بارگذاری مدل Cross-Encoder از cache"""
        global _CACHED_RERANKER, _RERANKER_LOADED
        
        try:
            import os
            
            # استفاده از cache
            if _RERANKER_LOADED and _CACHED_RERANKER is not None:
                self.model = _CACHED_RERANKER
                logger.debug("Using cached Cross-Encoder model")
                return
            
            # بررسی وجود مدل محلی
            if os.path.exists(self.local_model_path):
                logger.info(f"🔄 Loading local Cross-Encoder from: {self.local_model_path}")
                self.model = CrossEncoder(self.local_model_path, device=self.device)
                logger.info("✅ Local Cross-Encoder loaded and cached")
            else:
                logger.info(f"🔄 Loading Cross-Encoder from HuggingFace: {self.model_name} on {self.device}")
                self.model = CrossEncoder(self.model_name, device=self.device)
                logger.info("✅ Cross-Encoder loaded and cached")
            
            # Cache کردن
            _CACHED_RERANKER = self.model
            _RERANKER_LOADED = True
        except Exception as e:
            logger.error(f"Failed to load Cross-Encoder: {e}")
            self.model = None
    
    def rerank(self, query: str, documents: List[Dict[str, Any]], 
               top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Rerank documents using Cross-Encoder
        
        Args:
            query: سوال کاربر
            documents: لیست documents با structure:
                       [{"text": "...", "metadata": {...}, "score": 0.5}, ...]
            top_k: تعداد نتایج برتر
            
        Returns:
            لیست documents reranked شده
        """
        if not self.model or not documents:
            logger.warning("Cross-Encoder not available or no documents to rerank")
            return documents[:top_k]
        
        try:
            # Clear GPU cache before reranking
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            
            # آماده‌سازی pairs برای cross-encoder
            pairs = [[query, doc["text"]] for doc in documents]
            
            # محاسبه scores
            logger.info(f"Reranking {len(documents)} documents...")
            try:
                scores = self.model.predict(pairs)
            except Exception as e:
                logger.warning(f"Cross-encoder CUDA error, using fallback: {e}")
                # Fallback: return original documents with dummy scores
                for doc in documents:
                    doc["rerank_score"] = doc.get("hybrid_score", doc.get("score", 0.5))
                return documents[:top_k]
            
            # اضافه کردن rerank_score به documents
            for doc, score in zip(documents, scores):
                doc["rerank_score"] = float(score)
                doc["original_score"] = doc.get("hybrid_score", doc.get("score", 0))
            
            # مرتب‌سازی بر اساس rerank_score
            reranked = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)
            
            logger.info(f"✅ Reranking completed. Top score: {reranked[0]['rerank_score']:.4f}")
            
            return reranked[:top_k]
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return documents[:top_k]
    
    def rerank_with_fusion(self, query: str, documents: List[Dict[str, Any]], 
                          top_k: int = 5, alpha: float = 0.6) -> List[Dict[str, Any]]:
        """
        Rerank با ترکیب score های قبلی و rerank score
        
        Args:
            query: سوال کاربر
            documents: لیست documents
            top_k: تعداد نتایج برتر
            alpha: وزن rerank_score (0-1)
                   final_score = alpha * rerank + (1-alpha) * original
            
        Returns:
            لیست documents reranked شده با final_score
        """
        if not self.model or not documents:
            return documents[:top_k]
        
        try:
            # Rerank
            reranked = self.rerank(query, documents, top_k=len(documents))
            
            # Normalize rerank scores
            if reranked:
                max_rerank = max(doc["rerank_score"] for doc in reranked)
                min_rerank = min(doc["rerank_score"] for doc in reranked)
                
                if max_rerank > min_rerank:
                    for doc in reranked:
                        # نرمال‌سازی به [0, 1]
                        normalized_rerank = (doc["rerank_score"] - min_rerank) / (max_rerank - min_rerank)
                        original = doc.get("original_score", 0)
                        
                        # ترکیب scores
                        doc["final_score"] = alpha * normalized_rerank + (1 - alpha) * original
                        doc["normalized_rerank"] = normalized_rerank
            
            # مرتب‌سازی نهایی
            final_reranked = sorted(reranked, key=lambda x: x.get("final_score", 0), reverse=True)
            
            return final_reranked[:top_k]
            
        except Exception as e:
            logger.error(f"Fusion reranking failed: {e}")
            return documents[:top_k]
    
    def get_model_info(self) -> Dict[str, Any]:
        """اطلاعات مدل"""
        if self.model:
            return {
                "model_name": self.model_name,
                "device": self.device,
                "available": True
            }
        return {
            "model_name": self.model_name,
            "available": False
        }


# Test function
def test_reranker():
    """تست reranker"""
    print("🧪 Testing Cross-Encoder Reranker...")
    
    if not CROSSENCODER_AVAILABLE:
        print("❌ CrossEncoder not available, installing...")
        import os
        os.system("pip install sentence-transformers -q")
        print("✅ Installed, please restart")
        return False
    
    # Initialize
    reranker = CrossEncoderReranker()
    
    # Test documents
    query = "بند چهارم توی این جدول چیه؟"
    documents = [
        {
            "text": "جدول 1 - صفحه 1\nردیف 4: 21,126,965,178 | درآمدهای مالیاتی",
            "metadata": {"row": 4},
            "hybrid_score": 0.5
        },
        {
            "text": "جدول 2 - صفحه 2\nردیف 1: جمع کل مالیات",
            "metadata": {"row": 1},
            "hybrid_score": 0.48
        },
        {
            "text": "جدول 3 - صفحه 3\nردیف 4: مالیات مشاغل",
            "metadata": {"row": 4},
            "hybrid_score": 0.47
        }
    ]
    
    # Test reranking
    reranked = reranker.rerank(query, documents, top_k=3)
    
    print(f"\n📊 Results:")
    for i, doc in enumerate(reranked, 1):
        print(f"\n{i}. Rerank Score: {doc['rerank_score']:.4f} | Original: {doc['original_score']:.4f}")
        print(f"   Text: {doc['text'][:80]}...")
    
    # Test fusion
    print(f"\n🔄 Fusion Reranking:")
    fused = reranker.rerank_with_fusion(query, documents, top_k=3, alpha=0.7)
    
    for i, doc in enumerate(fused, 1):
        print(f"\n{i}. Final Score: {doc['final_score']:.4f} | Rerank: {doc['normalized_rerank']:.4f} | Original: {doc['original_score']:.4f}")
        print(f"   Text: {doc['text'][:80]}...")
    
    print("\n✅ Cross-Encoder Reranker test completed!")
    return True


if __name__ == "__main__":
    test_reranker()

