# -*- coding: utf-8 -*-
"""
TrOCR Processor
پردازشگر TrOCR برای تشخیص متن از تصاویر
"""

import torch
import time
import numpy as np
from typing import List, Dict, Union, Optional
from PIL import Image
from loguru import logger

from multimodal.base_multimodal_processor import BaseMultimodalProcessor

class TrOCRHandler(BaseMultimodalProcessor):
    """پردازشگر TrOCR برای OCR پیشرفته"""
    
    def __init__(
        self,
        model_name: str = "microsoft/trocr-base-printed",
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
        
        # TrOCR specific settings
        self.max_length = 256
        self.num_beams = 5
        self.early_stopping = True
        
    def _estimate_memory_usage(self) -> int:
        """تخمین استفاده از حافظه برای TrOCR"""
        if self.load_in_4bit:
            return 600  # 600MB for 4-bit
        elif self.load_in_8bit:
            return 1500  # 1.5GB for 8-bit
        return 2000  # 2GB for full precision
    
    def _load_model_components(self) -> bool:
        """بارگذاری کامپوننت‌های TrOCR"""
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            
            logger.info(f"🔄 Loading TrOCR components for {self.model_name}...")
            
            # بارگذاری processor
            self.processor = TrOCRProcessor.from_pretrained(self.model_path)
            logger.info("✅ TrOCR processor loaded")
            
            # بارگذاری مدل
            if self.load_in_8bit:
                self.model = VisionEncoderDecoderModel.from_pretrained(
                    self.model_path,
                    load_in_8bit=True,
                    device_map="auto"
                )
            else:
                self.model = VisionEncoderDecoderModel.from_pretrained(self.model_path)
                self.model.to(self.device)
            
            logger.info("✅ TrOCR model loaded")
            
            # تنظیم پارامترهای تولید
            self.model.config.max_length = self.max_length
            self.model.config.num_beams = self.num_beams
            self.model.config.early_stopping = self.early_stopping
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load TrOCR components: {e}")
            return False
    
    def _unload_model_components(self) -> bool:
        """حذف کامپوننت‌های TrOCR"""
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
            logger.error(f"❌ Failed to unload TrOCR components: {e}")
            return False
    
    def extract_text_from_image(
        self, 
        image: Union[Image.Image, str, np.ndarray],
        confidence_threshold: float = 0.5
    ) -> str:
        """استخراج متن از تصویر"""
        if not self.is_loaded:
            logger.warning("TrOCR model not loaded. Loading now...")
            if not self.load_model():
                return ""
        
        try:
            start_time = time.time()
            
            # پیش‌پردازش تصویر
            processed_image = self._preprocess_image(image)
            
            # پردازش با TrOCR
            pixel_values = self.processor(processed_image, return_tensors="pt").pixel_values
            
            if torch.cuda.is_available() and self.device.startswith("cuda"):
                try:
                    pixel_values = pixel_values.to(self.device)
                    
                    # تولید متن
                    with torch.no_grad():
                        generated_ids = self.model.generate(
                            pixel_values,
                            max_length=self.max_length,
                            num_beams=self.num_beams,
                            early_stopping=self.early_stopping,
                            pad_token_id=self.processor.tokenizer.pad_token_id
                        )
                except Exception as cuda_error:
                    logger.warning(f"CUDA error in TrOCR, using CPU fallback: {cuda_error}")
                    # Fallback to CPU
                    pixel_values = pixel_values.to("cpu")
                    self.model = self.model.to("cpu")
                    
                    with torch.no_grad():
                        generated_ids = self.model.generate(
                            pixel_values,
                            max_length=self.max_length,
                            num_beams=self.num_beams,
                            early_stopping=self.early_stopping,
                            pad_token_id=self.processor.tokenizer.pad_token_id
                        )
            else:
                # CPU processing
                with torch.no_grad():
                    generated_ids = self.model.generate(
                        pixel_values,
                        max_length=self.max_length,
                        num_beams=self.num_beams,
                        early_stopping=self.early_stopping,
                        pad_token_id=self.processor.tokenizer.pad_token_id
                    )
            
            # تبدیل به متن
            generated_text = self.processor.batch_decode(
                generated_ids, 
                skip_special_tokens=True
            )[0]
            
            # پس‌پردازش
            generated_text = self._postprocess_text(generated_text)
            
            # ردیابی عملکرد
            inference_time = time.time() - start_time
            self._track_inference(inference_time)
            
            logger.debug(f"TrOCR extracted text in {inference_time:.3f}s: {generated_text[:50]}...")
            return generated_text
            
        except Exception as e:
            logger.error(f"❌ Failed to extract text with TrOCR: {e}")
            return ""
    
    def extract_text_from_images(
        self, 
        images: List[Union[Image.Image, str, np.ndarray]],
        confidence_threshold: float = 0.5
    ) -> List[Dict]:
        """استخراج متن از چندین تصویر"""
        results = []
        
        for i, image in enumerate(images):
            try:
                text = self.extract_text_from_image(image, confidence_threshold)
                results.append({
                    'image_index': i,
                    'text': text,
                    'confidence': 1.0,  # TrOCR doesn't provide confidence scores
                    'success': bool(text.strip())
                })
                
            except Exception as e:
                logger.error(f"❌ Failed to process image {i}: {e}")
                results.append({
                    'image_index': i,
                    'text': '',
                    'confidence': 0.0,
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def _postprocess_text(self, text: str) -> str:
        """پس‌پردازش متن استخراج شده"""
        if not text:
            return ""
        
        # حذف کاراکترهای اضافی
        text = text.strip()
        
        # تصحیح مشکلات رایج فارسی
        text = text.replace('ي', 'ی')  # تصحیح ی عربی
        text = text.replace('ك', 'ک')  # تصحیح ک عربی
        text = text.replace('ة', 'ه')  # تصحیح ه عربی
        
        # حذف فاصله‌های اضافی
        import re
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def get_model_info(self) -> Dict:
        """اطلاعات مدل"""
        return {
            'model_name': self.model_name,
            'model_type': 'TrOCR',
            'task': 'OCR',
            'languages': ['Persian', 'English', 'Arabic'],
            'max_length': self.max_length,
            'num_beams': self.num_beams,
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
            
            # ایجاد تصویر تست ساده
            test_image = Image.new('RGB', (200, 50), color='white')
            
            # تست استخراج متن
            result = self.extract_text_from_image(test_image)
            
            logger.info(f"✅ TrOCR test completed. Result: '{result}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ TrOCR test failed: {e}")
            return False

# Factory function
def create_trocr_handler(
    model_name: str = "microsoft/trocr-base-printed",
    **kwargs
) -> TrOCRHandler:
    """ایجاد TrOCR handler"""
    return TrOCRHandler(model_name=model_name, **kwargs)
