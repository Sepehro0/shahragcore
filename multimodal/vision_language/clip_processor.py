# -*- coding: utf-8 -*-
"""
CLIP Processor
پردازشگر CLIP برای image-text similarity
"""

import torch
import time
import numpy as np
from typing import List, Dict, Union, Optional, Tuple
from PIL import Image
from loguru import logger

from multimodal.base_multimodal_processor import BaseMultimodalProcessor

class CLIPHandler(BaseMultimodalProcessor):
    """پردازشگر CLIP برای image-text similarity"""
    
    def __init__(
        self,
        model_name: str = "openai/clip-vit-base-patch32",
        model_path: Optional[str] = None,
        device: Optional[str] = None,
        load_in_8bit: bool = False,
        load_in_4bit: bool = False,
        auto_allocate_gpu: bool = True
    ):
        super().__init__(
            model_name=model_name,
            model_path=model_path,
            device=device,
            load_in_8bit=load_in_8bit,
            load_in_4bit=load_in_4bit,
            auto_allocate_gpu=auto_allocate_gpu
        )
        
        # CLIP specific settings
        self.similarity_threshold = 0.2
        self.max_text_length = 77
        
    def _estimate_memory_usage(self) -> int:
        """تخمین استفاده از حافظه برای CLIP"""
        if self.load_in_4bit:
            return 600  # 600MB for 4-bit
        elif self.load_in_8bit:
            return 1500  # 1.5GB for 8-bit
        return 2000  # 2GB for full precision
    
    def _load_model_components(self) -> bool:
        """بارگذاری کامپوننت‌های CLIP"""
        try:
            from transformers import CLIPProcessor, CLIPModel
            
            logger.info(f"🔄 Loading CLIP components for {self.model_name}...")
            
            # بارگذاری processor
            self.processor = CLIPProcessor.from_pretrained(self.model_path)
            logger.info("✅ CLIP processor loaded")
            
            # بارگذاری مدل
            if self.load_in_8bit:
                self.model = CLIPModel.from_pretrained(
                    self.model_path,
                    load_in_8bit=True,
                    device_map="auto"
                )
            else:
                self.model = CLIPModel.from_pretrained(self.model_path)
                self.model.to(self.device)
            
            logger.info("✅ CLIP model loaded")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load CLIP components: {e}")
            return False
    
    def _unload_model_components(self) -> bool:
        """حذف کامپوننت‌های CLIP"""
        try:
            if self.model is not None:
                del self.model
                self.model = None
            
            if self.processor is not None:
                del self.processor
                self.processor = None
            
            # پاک‌سازی حافظه
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to unload CLIP components: {e}")
            return False
    
    def get_image_text_similarity(
        self, 
        image: Union[Image.Image, str, np.ndarray],
        texts: List[str]
    ) -> List[float]:
        """محاسبه similarity بین تصویر و متون"""
        if not self.is_loaded:
            logger.warning("CLIP model not loaded. Loading now...")
            if not self.load_model():
                return [0.0] * len(texts)
        
        try:
            start_time = time.time()
            
            # پیش‌پردازش تصویر
            processed_image = self._preprocess_image(image)
            
            # پردازش با CLIP
            inputs = self.processor(
                text=texts, 
                images=processed_image, 
                return_tensors="pt", 
                padding=True
            )
            
            if torch.cuda.is_available() and self.device.startswith("cuda"):
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # محاسبه similarity
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)
                similarities = probs.cpu().numpy()[0]
            
            # ردیابی عملکرد
            inference_time = time.time() - start_time
            self._track_inference(inference_time)
            
            logger.debug(f"CLIP similarity computed in {inference_time:.3f}s")
            return similarities.tolist()
            
        except Exception as e:
            logger.error(f"❌ Failed to compute similarity with CLIP: {e}")
            return [0.0] * len(texts)
    
    def get_image_embedding(
        self, 
        image: Union[Image.Image, str, np.ndarray]
    ) -> np.ndarray:
        """دریافت embedding تصویر"""
        if not self.is_loaded:
            logger.warning("CLIP model not loaded. Loading now...")
            if not self.load_model():
                return np.zeros(512)  # Default CLIP embedding size
        
        try:
            start_time = time.time()
            
            # پیش‌پردازش تصویر
            processed_image = self._preprocess_image(image)
            
            # پردازش با CLIP
            inputs = self.processor(images=processed_image, return_tensors="pt")
            
            if torch.cuda.is_available() and self.device.startswith("cuda"):
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # استخراج embedding
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                embedding = image_features.cpu().numpy()[0]
            
            # ردیابی عملکرد
            inference_time = time.time() - start_time
            self._track_inference(inference_time)
            
            logger.debug(f"CLIP image embedding computed in {inference_time:.3f}s")
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Failed to get image embedding with CLIP: {e}")
            return np.zeros(512)
    
    def get_text_embedding(self, text: str) -> np.ndarray:
        """دریافت embedding متن"""
        if not self.is_loaded:
            logger.warning("CLIP model not loaded. Loading now...")
            if not self.load_model():
                return np.zeros(512)  # Default CLIP embedding size
        
        try:
            start_time = time.time()
            
            # پردازش متن
            inputs = self.processor(text=[text], return_tensors="pt", padding=True)
            
            if torch.cuda.is_available() and self.device.startswith("cuda"):
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # استخراج embedding
            with torch.no_grad():
                text_features = self.model.get_text_features(**inputs)
                embedding = text_features.cpu().numpy()[0]
            
            # ردیابی عملکرد
            inference_time = time.time() - start_time
            self._track_inference(inference_time)
            
            logger.debug(f"CLIP text embedding computed in {inference_time:.3f}s")
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Failed to get text embedding with CLIP: {e}")
            return np.zeros(512)
    
    def classify_image(
        self, 
        image: Union[Image.Image, str, np.ndarray],
        candidate_labels: List[str],
        threshold: float = 0.1
    ) -> Dict:
        """طبقه‌بندی تصویر بر اساس لیبل‌های کاندید"""
        if not candidate_labels:
            return {'label': '', 'score': 0.0, 'confidence': 'low'}
        
        try:
            # محاسبه similarity
            similarities = self.get_image_text_similarity(image, candidate_labels)
            
            # پیدا کردن بهترین match
            best_idx = np.argmax(similarities)
            best_score = similarities[best_idx]
            best_label = candidate_labels[best_idx]
            
            # تعیین confidence
            if best_score > 0.7:
                confidence = 'high'
            elif best_score > 0.4:
                confidence = 'medium'
            else:
                confidence = 'low'
            
            # فیلتر بر اساس threshold
            if best_score < threshold:
                best_label = ''
                confidence = 'low'
            
            return {
                'label': best_label,
                'score': float(best_score),
                'confidence': confidence,
                'all_scores': {label: float(score) for label, score in zip(candidate_labels, similarities)}
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to classify image with CLIP: {e}")
            return {'label': '', 'score': 0.0, 'confidence': 'low'}
    
    def find_similar_images(
        self,
        query_image: Union[Image.Image, str, np.ndarray],
        candidate_images: List[Union[Image.Image, str, np.ndarray]],
        top_k: int = 5
    ) -> List[Dict]:
        """پیدا کردن تصاویر مشابه"""
        if not candidate_images:
            return []
        
        try:
            # دریافت embedding تصویر query
            query_embedding = self.get_image_embedding(query_image)
            
            # محاسبه similarity با تمام تصاویر کاندید
            similarities = []
            for i, candidate_image in enumerate(candidate_images):
                try:
                    candidate_embedding = self.get_image_embedding(candidate_image)
                    
                    # محاسبه cosine similarity
                    similarity = np.dot(query_embedding, candidate_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(candidate_embedding)
                    )
                    
                    similarities.append({
                        'index': i,
                        'similarity': float(similarity),
                        'image': candidate_image
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to process candidate image {i}: {e}")
                    similarities.append({
                        'index': i,
                        'similarity': 0.0,
                        'image': candidate_image,
                        'error': str(e)
                    })
            
            # مرتب‌سازی بر اساس similarity
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"❌ Failed to find similar images with CLIP: {e}")
            return []
    
    def get_model_info(self) -> Dict:
        """اطلاعات مدل"""
        return {
            'model_name': self.model_name,
            'model_type': 'CLIP',
            'task': 'Image-Text Similarity',
            'embedding_size': 512,
            'max_text_length': self.max_text_length,
            'similarity_threshold': self.similarity_threshold,
            'is_loaded': self.is_loaded,
            'device': self.device,
            'memory_usage_mb': self.memory_usage,
            'performance_stats': self.get_performance_stats()
        }
    
    def test_model(self) -> bool:
        """تست عملکرد مدل"""
        try:
            if not self.is_loaded:
                logger.warning("Model not loaded for testing")
                return False
            
            # ایجاد تصویر تست
            test_image = Image.new('RGB', (224, 224), color='red')
            test_texts = ['a red image', 'a blue image', 'a green image']
            
            # تست similarity
            similarities = self.get_image_text_similarity(test_image, test_texts)
            
            logger.info(f"✅ CLIP test completed. Similarities: {similarities}")
            return len(similarities) == len(test_texts)
            
        except Exception as e:
            logger.error(f"❌ CLIP test failed: {e}")
            return False

# Factory function
def create_clip_handler(
    model_name: str = "openai/clip-vit-base-patch32",
    **kwargs
) -> CLIPHandler:
    """ایجاد CLIP handler"""
    return CLIPHandler(model_name=model_name, **kwargs)
