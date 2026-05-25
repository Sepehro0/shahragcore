# -*- coding: utf-8 -*-
"""
Persian Text Classifier Service
سرویس طبقه‌بندی متن فارسی با استفاده از ParsBERT
"""

import logging
import torch
from typing import List, Dict, Any, Optional
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np

logger = logging.getLogger(__name__)


class PersianClassifierService:
    """
    سرویس طبقه‌بندی متن فارسی
    می‌تواند برای تشخیص سریع‌تر دامنه استفاده شود
    """
    
    def __init__(
        self,
        model_path: str = "/home/user01/qwen-api/persian_models/parsbert",
        device: Optional[str] = None
    ):
        """
        Args:
            model_path: مسیر مدل ParsBERT
            device: دستگاه (cuda یا cpu)
        """
        self.model_path = model_path
        
        # تعیین device
        if device:
            self.device = device
        else:
            # 🔧 CRITICAL FIX: Force CPU to avoid CUDA OOM with vLLM
            self.device = "cpu"
        
        logger.info(f"🔧 Initializing PersianClassifierService on {self.device}...")
        
        try:
            # بارگذاری tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            
            # بارگذاری مدل (برای zero-shot از base model استفاده می‌کنیم)
            # در صورت نیاز می‌توان fine-tune کرد
            self.model = None  # فعلاً از مدل آماده استفاده نمی‌کنیم
            
            logger.info("✅ PersianClassifierService initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize PersianClassifierService: {e}")
            raise
    
    def classify_text_batch(
        self,
        texts: List[str],
        candidate_labels: List[str]
    ) -> List[Dict[str, Any]]:
        """
        طبقه‌بندی batch از متن‌ها
        
        Args:
            texts: لیست متن‌ها
            candidate_labels: برچسب‌های کاندید
        
        Returns:
            لیست نتایج طبقه‌بندی
        """
        # این متد می‌تواند در آینده با fine-tuned model پیاده‌سازی شود
        # فعلاً یک placeholder است
        
        logger.warning("classify_text_batch not implemented yet - requires fine-tuned model")
        return []
    
    def extract_embeddings(
        self,
        texts: List[str],
        max_length: int = 512
    ) -> np.ndarray:
        """
        استخراج embeddings از متن‌ها
        می‌تواند برای similarity-based classification استفاده شود
        
        Args:
            texts: لیست متن‌ها
            max_length: حداکثر طول tokenization
        
        Returns:
            آرایه embeddings
        """
        try:
            # Tokenize
            encoded = self.tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors='pt'
            )
            
            # اگر مدل وجود داشته باشد، embeddings استخراج می‌کنیم
            if self.model:
                with torch.no_grad():
                    outputs = self.model(**encoded.to(self.device))
                    embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
                return embeddings
            else:
                logger.warning("Model not loaded - cannot extract embeddings")
                return np.array([])
                
        except Exception as e:
            logger.error(f"Failed to extract embeddings: {e}")
            return np.array([])
    
    def calculate_domain_similarity(
        self,
        text: str,
        domain_keywords: Dict[str, List[str]]
    ) -> Dict[str, float]:
        """
        محاسبه شباهت متن با دامنه‌های مختلف بر اساس کلمات کلیدی
        
        Args:
            text: متن ورودی
            domain_keywords: دیکشنری دامنه‌ها و کلمات کلیدی
        
        Returns:
            دیکشنری از دامنه‌ها و امتیاز شباهت
        """
        text_lower = text.lower()
        similarities = {}
        
        for domain, keywords in domain_keywords.items():
            # شمارش تعداد کلمات کلیدی یافت شده
            matches = sum(1 for keyword in keywords if keyword.lower() in text_lower)
            # نرمال‌سازی بر اساس تعداد کلمات کلیدی
            similarity = matches / len(keywords) if keywords else 0.0
            similarities[domain] = similarity
        
        return similarities
    
    @staticmethod
    def get_best_domain_from_keywords(
        text: str,
        domain_keywords: Dict[str, List[str]],
        threshold: float = 0.1
    ) -> Optional[str]:
        """
        تشخیص بهترین دامنه بر اساس کلمات کلیدی (static method)
        
        Args:
            text: متن ورودی
            domain_keywords: دیکشنری دامنه‌ها و کلمات کلیدی
            threshold: حداقل امتیاز برای قبول
        
        Returns:
            نام دامنه یا None
        """
        text_lower = text.lower()
        scores = {}
        
        for domain, keywords in domain_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    score += text_lower.count(keyword.lower())
            scores[domain] = score
        
        if not scores or max(scores.values()) == 0:
            return None
        
        best_domain = max(scores, key=scores.get)
        total_score = sum(scores.values())
        confidence = scores[best_domain] / total_score if total_score > 0 else 0
        
        if confidence >= threshold:
            return best_domain
        return None


class PersianDomainClassifierTrainer:
    """
    کلاس برای fine-tuning مدل ParsBERT روی task طبقه‌بندی دامنه
    می‌تواند در آینده برای بهبود دقت استفاده شود
    """
    
    def __init__(
        self,
        base_model_path: str = "/home/user01/qwen-api/persian_models/parsbert",
        num_labels: int = 6  # تعداد دامنه‌ها
    ):
        """
        Args:
            base_model_path: مسیر مدل پایه
            num_labels: تعداد کلاس‌ها (دامنه‌ها)
        """
        self.base_model_path = base_model_path
        self.num_labels = num_labels
        
        logger.info(f"🎓 Initializing PersianDomainClassifierTrainer with {num_labels} labels")
    
    def prepare_training_data(
        self,
        texts: List[str],
        labels: List[int]
    ) -> Dict[str, Any]:
        """
        آماده‌سازی داده‌های آموزشی
        
        Args:
            texts: متن‌های آموزشی
            labels: برچسب‌ها (0 to num_labels-1)
        
        Returns:
            داده‌های آماده برای آموزش
        """
        # این متد می‌تواند در آینده پیاده‌سازی شود
        logger.info(f"Preparing {len(texts)} training samples...")
        
        return {
            'texts': texts,
            'labels': labels,
            'num_samples': len(texts)
        }
    
    def train(
        self,
        train_data: Dict[str, Any],
        val_data: Optional[Dict[str, Any]] = None,
        epochs: int = 3,
        batch_size: int = 16,
        learning_rate: float = 2e-5
    ) -> Dict[str, Any]:
        """
        آموزش مدل
        
        Args:
            train_data: داده‌های آموزشی
            val_data: داده‌های اعتبارسنجی
            epochs: تعداد epoch
            batch_size: اندازه batch
            learning_rate: نرخ یادگیری
        
        Returns:
            نتایج آموزش
        """
        logger.warning("Training not implemented - placeholder for future fine-tuning")
        
        return {
            'status': 'not_implemented',
            'message': 'Fine-tuning can be implemented when training data is available'
        }
    
    def save_model(self, output_path: str):
        """ذخیره مدل آموزش دیده"""
        logger.warning(f"save_model not implemented - would save to {output_path}")
    
    @staticmethod
    def create_synthetic_training_data(
        domain_keywords: Dict[str, List[str]],
        samples_per_domain: int = 100
    ) -> Tuple[List[str], List[int]]:
        """
        تولید داده‌های synthetic برای آموزش اولیه
        (برای شروع سریع - کیفیت محدود)
        """
        texts = []
        labels = []
        
        domain_list = list(domain_keywords.keys())
        
        for domain_idx, (domain, keywords) in enumerate(domain_keywords.items()):
            for _ in range(samples_per_domain):
                # ایجاد متن synthetic با ترکیب کلمات کلیدی
                import random
                selected_keywords = random.sample(
                    keywords,
                    min(5, len(keywords))
                )
                synthetic_text = " ".join(selected_keywords)
                texts.append(synthetic_text)
                labels.append(domain_idx)
        
        logger.info(f"Created {len(texts)} synthetic training samples")
        return texts, labels


# Type hint برای Python < 3.9
from typing import Tuple


