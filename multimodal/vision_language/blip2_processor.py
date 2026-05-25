# -*- coding: utf-8 -*-
"""
BLIP-2 Processor
پردازشگر BLIP-2 برای image captioning و visual question answering
"""

import torch
import time
import numpy as np
from typing import List, Dict, Union, Optional
from PIL import Image
from loguru import logger

from multimodal.base_multimodal_processor import BaseMultimodalProcessor

class BLIP2Handler(BaseMultimodalProcessor):
    """پردازشگر BLIP-2 برای image captioning و VQA"""
    
    def __init__(
        self,
        model_name: str = "Salesforce/blip2-opt-2.7b",
        model_path: Optional[str] = None,
        device: Optional[str] = None,
        load_in_8bit: bool = True,  # Default to 8-bit for memory efficiency
        auto_allocate_gpu: bool = True
    ):
        super().__init__(
            model_name=model_name,
            model_path=model_path,
            device=device,
            load_in_8bit=load_in_8bit,
            auto_allocate_gpu=auto_allocate_gpu
        )
        
        # BLIP-2 specific settings
        self.max_length = 50
        self.num_beams = 5
        self.early_stopping = True
        self.temperature = 0.7
        
    def _estimate_memory_usage(self) -> int:
        """تخمین استفاده از حافظه برای BLIP-2"""
        if self.load_in_8bit:
            return 8000  # 8GB for 8-bit
        return 10000  # 10GB for full precision
    
    def _load_model_components(self) -> bool:
        """بارگذاری کامپوننت‌های BLIP-2"""
        try:
            from transformers import Blip2Processor, Blip2ForConditionalGeneration
            
            logger.info(f"🔄 Loading BLIP-2 components for {self.model_name}...")
            
            # بارگذاری processor
            self.processor = Blip2Processor.from_pretrained(self.model_path)
            logger.info("✅ BLIP-2 processor loaded")
            
            # بارگذاری مدل
            if self.load_in_8bit:
                self.model = Blip2ForConditionalGeneration.from_pretrained(
                    self.model_path,
                    load_in_8bit=True,
                    device_map="auto"
                )
            else:
                self.model = Blip2ForConditionalGeneration.from_pretrained(self.model_path)
                self.model.to(self.device)
            
            logger.info("✅ BLIP-2 model loaded")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load BLIP-2 components: {e}")
            return False
    
    def _unload_model_components(self) -> bool:
        """حذف کامپوننت‌های BLIP-2"""
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
            logger.error(f"❌ Failed to unload BLIP-2 components: {e}")
            return False
    
    def generate_caption(
        self, 
        image: Union[Image.Image, str, np.ndarray],
        max_length: int = None
    ) -> str:
        """تولید caption برای تصویر"""
        if not self.is_loaded:
            logger.warning("BLIP-2 model not loaded. Loading now...")
            if not self.load_model():
                return ""
        
        try:
            start_time = time.time()
            
            # پیش‌پردازش تصویر
            processed_image = self._preprocess_image(image)
            
            # پردازش با BLIP-2
            inputs = self.processor(processed_image, return_tensors="pt")
            
            if torch.cuda.is_available() and self.device.startswith("cuda"):
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # تولید caption
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_length=max_length or self.max_length,
                    num_beams=self.num_beams,
                    early_stopping=self.early_stopping,
                    temperature=self.temperature,
                    do_sample=True
                )
            
            # تبدیل به متن
            generated_text = self.processor.batch_decode(
                generated_ids, 
                skip_special_tokens=True
            )[0]
            
            # پس‌پردازش
            caption = self._postprocess_caption(generated_text)
            
            # ردیابی عملکرد
            inference_time = time.time() - start_time
            self._track_inference(inference_time)
            
            logger.debug(f"BLIP-2 generated caption in {inference_time:.3f}s: {caption}")
            return caption
            
        except Exception as e:
            logger.error(f"❌ Failed to generate caption with BLIP-2: {e}")
            return ""
    
    def answer_question(
        self, 
        image: Union[Image.Image, str, np.ndarray],
        question: str
    ) -> str:
        """پاسخ به سوال بر اساس تصویر"""
        if not self.is_loaded:
            logger.warning("BLIP-2 model not loaded. Loading now...")
            if not self.load_model():
                return ""
        
        try:
            start_time = time.time()
            
            # پیش‌پردازش تصویر
            processed_image = self._preprocess_image(image)
            
            # پردازش با BLIP-2
            inputs = self.processor(
                images=processed_image,
                text=question,
                return_tensors="pt"
            )
            
            if torch.cuda.is_available() and self.device.startswith("cuda"):
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # تولید پاسخ
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_length=self.max_length,
                    num_beams=self.num_beams,
                    early_stopping=self.early_stopping,
                    temperature=self.temperature
                )
            
            # تبدیل به متن
            generated_text = self.processor.batch_decode(
                generated_ids, 
                skip_special_tokens=True
            )[0]
            
            # پس‌پردازش
            answer = self._postprocess_answer(generated_text, question)
            
            # ردیابی عملکرد
            inference_time = time.time() - start_time
            self._track_inference(inference_time)
            
            logger.debug(f"BLIP-2 answered question in {inference_time:.3f}s: {answer}")
            return answer
            
        except Exception as e:
            logger.error(f"❌ Failed to answer question with BLIP-2: {e}")
            return ""
    
    def generate_multiple_captions(
        self, 
        image: Union[Image.Image, str, np.ndarray],
        num_captions: int = 3
    ) -> List[str]:
        """تولید چندین caption برای تصویر"""
        captions = []
        
        for i in range(num_captions):
            try:
                # تغییر temperature برای تنوع
                original_temp = self.temperature
                self.temperature = 0.7 + (i * 0.1)  # افزایش تنوع
                
                caption = self.generate_caption(image)
                if caption and caption not in captions:
                    captions.append(caption)
                
                self.temperature = original_temp
                
            except Exception as e:
                logger.warning(f"Failed to generate caption {i+1}: {e}")
                continue
        
        return captions
    
    def analyze_image_content(
        self, 
        image: Union[Image.Image, str, np.ndarray],
        analysis_questions: List[str] = None
    ) -> Dict:
        """تحلیل محتوای تصویر"""
        if analysis_questions is None:
            analysis_questions = [
                "What is in this image?",
                "What colors are prominent?",
                "What is the main subject?",
                "What is the setting or background?",
                "Are there any text or numbers visible?"
            ]
        
        try:
            # تولید caption کلی
            caption = self.generate_caption(image)
            
            # پاسخ به سوالات تحلیل
            answers = {}
            for question in analysis_questions:
                answer = self.answer_question(image, question)
                answers[question] = answer
            
            return {
                'caption': caption,
                'analysis': answers,
                'confidence': 1.0  # BLIP-2 doesn't provide confidence scores
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze image content with BLIP-2: {e}")
            return {'caption': '', 'analysis': {}, 'confidence': 0.0}
    
    def batch_process_images(
        self, 
        images: List[Union[Image.Image, str, np.ndarray]],
        questions: List[str] = None
    ) -> List[Dict]:
        """پردازش دسته‌ای تصاویر"""
        results = []
        
        for i, image in enumerate(images):
            try:
                question = questions[i] if questions and i < len(questions) else None
                
                if question:
                    result = self.answer_question(image, question)
                else:
                    result = self.generate_caption(image)
                
                results.append({
                    'index': i,
                    'result': result,
                    'success': True
                })
                
            except Exception as e:
                logger.error(f"❌ Failed to process image {i}: {e}")
                results.append({
                    'index': i,
                    'result': None,
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def _postprocess_caption(self, caption: str) -> str:
        """پس‌پردازش caption"""
        if not caption:
            return ""
        
        # حذف کاراکترهای اضافی
        caption = caption.strip()
        
        # حذف special tokens
        special_tokens = ['<pad>', '<unk>', '<s>', '</s>']
        for token in special_tokens:
            caption = caption.replace(token, '')
        
        # تصحیح مشکلات رایج
        caption = caption.replace('  ', ' ')  # حذف فاصله‌های اضافی
        
        return caption
    
    def _postprocess_answer(self, answer: str, question: str) -> str:
        """پس‌پردازش پاسخ"""
        if not answer:
            return ""
        
        # حذف سوال از پاسخ (اگر موجود باشد)
        if question.lower() in answer.lower():
            answer = answer.replace(question, '').strip()
        
        # حذف کاراکترهای اضافی
        answer = answer.strip()
        
        # حذف special tokens
        special_tokens = ['<pad>', '<unk>', '<s>', '</s>']
        for token in special_tokens:
            answer = answer.replace(token, '')
        
        return answer
    
    def get_model_info(self) -> Dict:
        """اطلاعات مدل"""
        return {
            'model_name': self.model_name,
            'model_type': 'BLIP-2',
            'task': 'Image Captioning & Visual Question Answering',
            'max_length': self.max_length,
            'num_beams': self.num_beams,
            'temperature': self.temperature,
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
            
            # تست تولید caption
            caption = self.generate_caption(test_image)
            
            # تست پاسخ به سوال
            answer = self.answer_question(test_image, "What color is this image?")
            
            logger.info(f"✅ BLIP-2 test completed. Caption: '{caption}', Answer: '{answer}'")
            return bool(caption) and bool(answer)
            
        except Exception as e:
            logger.error(f"❌ BLIP-2 test failed: {e}")
            return False

# Factory function
def create_blip2_handler(
    model_name: str = "Salesforce/blip2-opt-2.7b",
    **kwargs
) -> BLIP2Handler:
    """ایجاد BLIP-2 handler"""
    return BLIP2Handler(model_name=model_name, **kwargs)
