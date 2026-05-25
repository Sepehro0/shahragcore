# -*- coding: utf-8 -*-
"""
LLaVA Processor
پردازشگر LLaVA برای multimodal conversational AI
"""

import torch
import time
import numpy as np
from typing import List, Dict, Union, Optional
from PIL import Image
from loguru import logger

from multimodal.base_multimodal_processor import BaseMultimodalProcessor

class LLaVAHandler(BaseMultimodalProcessor):
    """پردازشگر LLaVA برای multimodal conversational AI"""
    
    def __init__(
        self,
        model_name: str = "llava-hf/llava-1.5-7b-hf",
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
        
        # LLaVA specific settings
        self.max_new_tokens = 512
        self.temperature = 0.7
        self.top_p = 0.9
        self.do_sample = True
        
        # Conversation history
        self.conversation_history = []
        
    def _estimate_memory_usage(self) -> int:
        """تخمین استفاده از حافظه برای LLaVA"""
        if self.load_in_8bit:
            return 10000  # 10GB for 8-bit
        return 14000  # 14GB for full precision
    
    def _load_model_components(self) -> bool:
        """بارگذاری کامپوننت‌های LLaVA"""
        try:
            from transformers import LlavaForConditionalGeneration, AutoProcessor
            
            logger.info(f"🔄 Loading LLaVA components for {self.model_name}...")
            
            # بارگذاری processor
            self.processor = AutoProcessor.from_pretrained(self.model_path)
            logger.info("✅ LLaVA processor loaded")
            
            # بارگذاری مدل
            if self.load_in_8bit:
                self.model = LlavaForConditionalGeneration.from_pretrained(
                    self.model_path,
                    load_in_8bit=True,
                    device_map="auto"
                )
            else:
                self.model = LlavaForConditionalGeneration.from_pretrained(self.model_path)
                self.model.to(self.device)
            
            logger.info("✅ LLaVA model loaded")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load LLaVA components: {e}")
            return False
    
    def _unload_model_components(self) -> bool:
        """حذف کامپوننت‌های LLaVA"""
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
            logger.error(f"❌ Failed to unload LLaVA components: {e}")
            return False
    
    def chat(
        self, 
        image: Union[Image.Image, str, np.ndarray],
        prompt: str,
        conversation_history: List[Dict] = None,
        system_message: str = None
    ) -> str:
        """گفتگوی multimodal با LLaVA"""
        if not self.is_loaded:
            logger.warning("LLaVA model not loaded. Loading now...")
            if not self.load_model():
                return ""
        
        try:
            start_time = time.time()
            
            # پیش‌پردازش تصویر
            processed_image = self._preprocess_image(image)
            
            # آماده‌سازی prompt
            full_prompt = self._prepare_conversation_prompt(
                prompt, conversation_history, system_message
            )
            
            # پردازش با LLaVA
            inputs = self.processor(
                text=full_prompt,
                images=processed_image,
                return_tensors="pt"
            )
            
            if torch.cuda.is_available() and self.device.startswith("cuda"):
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # تولید پاسخ
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=self.max_new_tokens,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    do_sample=self.do_sample,
                    pad_token_id=self.processor.tokenizer.pad_token_id
                )
            
            # تبدیل به متن
            generated_text = self.processor.batch_decode(
                generated_ids, 
                skip_special_tokens=True
            )[0]
            
            # استخراج پاسخ از متن کامل
            response = self._extract_response(generated_text, full_prompt)
            
            # ذخیره در تاریخچه
            self._update_conversation_history(prompt, response, image)
            
            # ردیابی عملکرد
            inference_time = time.time() - start_time
            self._track_inference(inference_time)
            
            logger.debug(f"LLaVA chat completed in {inference_time:.3f}s: {response[:100]}...")
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to chat with LLaVA: {e}")
            return ""
    
    def analyze_document(
        self, 
        image: Union[Image.Image, str, np.ndarray],
        analysis_type: str = "comprehensive"
    ) -> Dict:
        """تحلیل جامع سند"""
        analysis_prompts = {
            "comprehensive": """
            Please analyze this document comprehensively. Include:
            1. Document type and purpose
            2. Key information and data
            3. Structure and layout
            4. Any tables, charts, or visual elements
            5. Important numbers or dates
            6. Overall summary
            """,
            "financial": """
            Analyze this financial document. Focus on:
            1. Document type (invoice, receipt, statement, etc.)
            2. Financial figures and amounts
            3. Dates and periods
            4. Parties involved
            5. Key financial information
            """,
            "technical": """
            Analyze this technical document. Focus on:
            1. Document type and purpose
            2. Technical specifications
            3. Diagrams or technical drawings
            4. Key technical information
            5. Procedures or instructions
            """
        }
        
        try:
            prompt = analysis_prompts.get(analysis_type, analysis_prompts["comprehensive"])
            analysis = self.chat(image, prompt)
            
            return {
                'analysis': analysis,
                'analysis_type': analysis_type,
                'confidence': 1.0  # LLaVA doesn't provide confidence scores
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze document with LLaVA: {e}")
            return {'analysis': '', 'analysis_type': analysis_type, 'confidence': 0.0}
    
    def extract_structured_data(
        self, 
        image: Union[Image.Image, str, np.ndarray],
        data_format: str = "json"
    ) -> Dict:
        """استخراج داده‌های ساختاریافته"""
        try:
            if data_format == "json":
                prompt = """
                Extract all structured data from this document and format it as JSON.
                Include all text, numbers, dates, and key information in a structured format.
                """
            elif data_format == "table":
                prompt = """
                Extract all tabular data from this document.
                Present it in a clear table format with headers and rows.
                """
            else:
                prompt = f"""
                Extract all structured data from this document in {data_format} format.
                """
            
            result = self.chat(image, prompt)
            
            return {
                'data': result,
                'format': data_format,
                'confidence': 1.0
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to extract structured data with LLaVA: {e}")
            return {'data': '', 'format': data_format, 'confidence': 0.0}
    
    def _prepare_conversation_prompt(
        self, 
        prompt: str, 
        conversation_history: List[Dict] = None,
        system_message: str = None
    ) -> str:
        """آماده‌سازی prompt برای گفتگو"""
        full_prompt = ""
        
        # اضافه کردن system message
        if system_message:
            full_prompt += f"System: {system_message}\n\n"
        
        # اضافه کردن تاریخچه گفتگو
        if conversation_history:
            for turn in conversation_history[-5:]:  # آخرین 5 turn
                full_prompt += f"Human: {turn.get('human', '')}\n"
                full_prompt += f"Assistant: {turn.get('assistant', '')}\n\n"
        
        # اضافه کردن prompt فعلی
        full_prompt += f"Human: {prompt}\nAssistant:"
        
        return full_prompt
    
    def _extract_response(self, full_text: str, prompt: str) -> str:
        """استخراج پاسخ از متن کامل"""
        # حذف prompt از پاسخ
        if prompt in full_text:
            response = full_text.split(prompt)[-1].strip()
        else:
            response = full_text.strip()
        
        # حذف کاراکترهای اضافی
        response = response.replace("Assistant:", "").strip()
        
        return response
    
    def _update_conversation_history(
        self, 
        prompt: str, 
        response: str, 
        image: Union[Image.Image, str, np.ndarray] = None
    ):
        """به‌روزرسانی تاریخچه گفتگو"""
        self.conversation_history.append({
            'human': prompt,
            'assistant': response,
            'image': image is not None,
            'timestamp': time.time()
        })
        
        # محدود کردن تاریخچه به 10 turn آخر
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
    
    def clear_conversation_history(self):
        """پاک کردن تاریخچه گفتگو"""
        self.conversation_history = []
        logger.info("✅ Conversation history cleared")
    
    def get_conversation_history(self) -> List[Dict]:
        """دریافت تاریخچه گفتگو"""
        return self.conversation_history.copy()
    
    def get_model_info(self) -> Dict:
        """اطلاعات مدل"""
        return {
            'model_name': self.model_name,
            'model_type': 'LLaVA',
            'task': 'Multimodal Conversational AI',
            'max_new_tokens': self.max_new_tokens,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'conversation_turns': len(self.conversation_history),
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
            test_image = Image.new('RGB', (224, 224), color='blue')
            
            # تست گفتگو
            response = self.chat(test_image, "What color is this image?")
            
            logger.info(f"✅ LLaVA test completed. Response: '{response[:100]}...'")
            return bool(response)
            
        except Exception as e:
            logger.error(f"❌ LLaVA test failed: {e}")
            return False

# Factory function
def create_llava_handler(
    model_name: str = "llava-hf/llava-1.5-7b-hf",
    **kwargs
) -> LLaVAHandler:
    """ایجاد LLaVA handler"""
    return LLaVAHandler(model_name=model_name, **kwargs)
