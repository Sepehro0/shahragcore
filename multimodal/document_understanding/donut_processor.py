# -*- coding: utf-8 -*-
"""
Donut Processor
پردازشگر Donut برای Document Visual Question Answering
"""

import torch
import time
import json
import numpy as np
from typing import List, Dict, Union, Optional
from PIL import Image
from loguru import logger

from multimodal.base_multimodal_processor import BaseMultimodalProcessor

class DonutHandler(BaseMultimodalProcessor):
    """پردازشگر Donut برای Document Visual Question Answering"""
    
    def __init__(
        self,
        model_name: str = "naver-clova-ix/donut-base-finetuned-docvqa",
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
        
        # Donut specific settings
        self.max_length = 256
        self.num_beams = 1
        self.early_stopping = True
        
        # Predefined prompts for different tasks
        self.prompts = {
            'docvqa': '<s_docvqa><s_question>{question}</s_question><s_answer>',
            'table_parsing': '<s_table><s_table>',
            'receipt_parsing': '<s_receipt><s_receipt>',
            'general': '<s_cord-v2><s_cord-v2>'
        }
        
    def _estimate_memory_usage(self) -> int:
        """تخمین استفاده از حافظه برای Donut"""
        base_memory = 6000  # 6GB for full precision
        
        if self.load_in_4bit:
            return int(base_memory * 0.3)  # ~1.8GB for 4-bit
        elif self.load_in_8bit:
            return int(base_memory * 0.5)  # ~3GB for 8-bit
        else:
            return base_memory
    
    def _load_model_components(self) -> bool:
        """بارگذاری کامپوننت‌های Donut"""
        try:
            from transformers import DonutProcessor, VisionEncoderDecoderModel
            
            logger.info(f"🔄 Loading Donut components for {self.model_name}...")
            
            # بارگذاری processor
            self.processor = DonutProcessor.from_pretrained(self.model_path)
            logger.info("✅ Donut processor loaded")
            
            # بارگذاری مدل
            if self.load_in_4bit:
                from transformers import BitsAndBytesConfig
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                self.model = VisionEncoderDecoderModel.from_pretrained(
                    self.model_path,
                    quantization_config=quantization_config,
                    device_map="balanced"
                )
            elif self.load_in_8bit:
                self.model = VisionEncoderDecoderModel.from_pretrained(
                    self.model_path,
                    load_in_8bit=True,
                    device_map="balanced"  # Better distribution than "auto"
                )
            else:
                self.model = VisionEncoderDecoderModel.from_pretrained(self.model_path)
                self.model.to(self.device)
            
            # Ensure model is in eval mode and on correct device
            self.model.eval()
            if torch.cuda.is_available() and self.device.startswith("cuda"):
                torch.cuda.synchronize()
            
            logger.info("✅ Donut model loaded")
            
            # تنظیم پارامترهای تولید
            self.model.config.max_length = self.max_length
            self.model.config.num_beams = self.num_beams
            self.model.config.early_stopping = self.early_stopping
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load Donut components: {e}")
            return False
    
    def _unload_model_components(self) -> bool:
        """حذف کامپوننت‌های Donut"""
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
            logger.error(f"❌ Failed to unload Donut components: {e}")
            return False
    
    def extract_document_info(
        self, 
        image: Union[Image.Image, str, np.ndarray],
        prompt: str = None,
        task_type: str = 'general'
    ) -> Dict:
        """استخراج اطلاعات از document"""
        if not self.is_loaded:
            logger.warning("Donut model not loaded. Loading now...")
            if not self.load_model():
                return {'text': '', 'confidence': 0.0}
        
        try:
            start_time = time.time()
            
            # پیش‌پردازش تصویر
            processed_image = self._preprocess_image(image)
            
            # انتخاب prompt مناسب
            if prompt is None:
                prompt = self.prompts.get(task_type, self.prompts['general'])
            
            # پردازش با Donut
            inputs = self.processor(processed_image, return_tensors="pt")
            pixel_values = inputs.pixel_values
            
            # Prepare decoder inputs
            decoder_input_ids = self.processor.tokenizer(
                prompt, 
                return_tensors="pt", 
                add_special_tokens=False
            ).input_ids
            
            if torch.cuda.is_available() and self.device.startswith("cuda"):
                device = torch.device(self.device)
                pixel_values = pixel_values.to(device)
                decoder_input_ids = decoder_input_ids.to(device)
                
                # Ensure dtype compatibility - decoder_input_ids must be Long
                model_dtype = next(self.model.parameters()).dtype
                if model_dtype == torch.float16:
                    pixel_values = pixel_values.half()
                    # decoder_input_ids must remain Long for embedding lookup
                    decoder_input_ids = decoder_input_ids.long()
                elif model_dtype == torch.float32:
                    pixel_values = pixel_values.float()
                    # decoder_input_ids must remain Long for embedding lookup
                    decoder_input_ids = decoder_input_ids.long()
                else:
                    # Ensure decoder_input_ids is Long
                    decoder_input_ids = decoder_input_ids.long()
            
            # تولید پاسخ
            with torch.no_grad():
                generated_ids = self.model.generate(
                    pixel_values,
                    decoder_input_ids=decoder_input_ids,
                    max_length=self.max_length,
                    num_beams=self.num_beams,
                    early_stopping=self.early_stopping,
                    pad_token_id=self.processor.tokenizer.pad_token_id,
                    eos_token_id=self.processor.tokenizer.eos_token_id
                )
            
            # تبدیل به متن
            generated_text = self.processor.batch_decode(
                generated_ids, 
                skip_special_tokens=True
            )[0]
            
            # پس‌پردازش
            processed_text = self._postprocess_output(generated_text)
            
            # ردیابی عملکرد
            inference_time = time.time() - start_time
            self._track_inference(inference_time)
            
            logger.debug(f"Donut extracted info in {inference_time:.3f}s: {processed_text[:100]}...")
            return {
                'text': processed_text,
                'confidence': 1.0,  # Donut doesn't provide confidence scores
                'processing_time': inference_time,
                'task_type': task_type
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to extract document info with Donut: {e}")
            return {'text': '', 'confidence': 0.0}
    
    def answer_question(
        self, 
        image: Union[Image.Image, str, np.ndarray],
        question: str
    ) -> str:
        """پاسخ به سوال بر اساس تصویر"""
        try:
            # استفاده از prompt مخصوص DocVQA
            prompt = self.prompts['docvqa'].format(question=question)
            
            result = self.extract_document_info(image, prompt, 'docvqa')
            return result['text']
            
        except Exception as e:
            logger.error(f"❌ Failed to answer question with Donut: {e}")
            return ""
    
    def extract_table_data(
        self, 
        image: Union[Image.Image, str, np.ndarray]
    ) -> Dict:
        """استخراج داده‌های جدول"""
        try:
            # استفاده از prompt مخصوص table parsing
            result = self.extract_document_info(image, self.prompts['table_parsing'], 'table_parsing')
            
            # تلاش برای parse کردن JSON
            try:
                table_data = json.loads(result['text'])
                return {
                    'table_data': table_data,
                    'raw_text': result['text'],
                    'confidence': result['confidence']
                }
            except json.JSONDecodeError:
                # اگر JSON نبود، متن خام را برمی‌گردانیم
                return {
                    'table_data': None,
                    'raw_text': result['text'],
                    'confidence': result['confidence']
                }
            
        except Exception as e:
            logger.error(f"❌ Failed to extract table data with Donut: {e}")
            return {'table_data': None, 'raw_text': '', 'confidence': 0.0}
    
    def extract_receipt_info(
        self, 
        image: Union[Image.Image, str, np.ndarray]
    ) -> Dict:
        """استخراج اطلاعات از receipt"""
        try:
            # استفاده از prompt مخصوص receipt parsing
            result = self.extract_document_info(image, self.prompts['receipt_parsing'], 'receipt_parsing')
            
            # تلاش برای parse کردن JSON
            try:
                receipt_data = json.loads(result['text'])
                return {
                    'receipt_data': receipt_data,
                    'raw_text': result['text'],
                    'confidence': result['confidence']
                }
            except json.JSONDecodeError:
                # اگر JSON نبود، متن خام را برمی‌گردانیم
                return {
                    'receipt_data': None,
                    'raw_text': result['text'],
                    'confidence': result['confidence']
                }
            
        except Exception as e:
            logger.error(f"❌ Failed to extract receipt info with Donut: {e}")
            return {'receipt_data': None, 'raw_text': '', 'confidence': 0.0}
    
    def batch_process_documents(
        self, 
        images: List[Union[Image.Image, str, np.ndarray]],
        questions: List[str] = None,
        task_type: str = 'general'
    ) -> List[Dict]:
        """پردازش دسته‌ای اسناد"""
        results = []
        
        for i, image in enumerate(images):
            try:
                question = questions[i] if questions and i < len(questions) else None
                
                if question:
                    result = self.answer_question(image, question)
                else:
                    result = self.extract_document_info(image, task_type=task_type)
                
                results.append({
                    'index': i,
                    'result': result,
                    'success': True
                })
                
            except Exception as e:
                logger.error(f"❌ Failed to process document {i}: {e}")
                results.append({
                    'index': i,
                    'result': None,
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def _postprocess_output(self, text: str) -> str:
        """پس‌پردازش خروجی"""
        if not text:
            return ""
        
        # حذف کاراکترهای اضافی
        text = text.strip()
        
        # حذف special tokens
        special_tokens = ['<s_', '</s_', '<pad>', '<unk>']
        for token in special_tokens:
            text = text.replace(token, '')
        
        # تصحیح مشکلات رایج فارسی
        text = text.replace('ي', 'ی')  # تصحیح ی عربی
        text = text.replace('ك', 'ک')  # تصحیح ک عربی
        text = text.replace('ة', 'ه')  # تصحیح ه عربی
        
        return text
    
    def get_model_info(self) -> Dict:
        """اطلاعات مدل"""
        return {
            'model_name': self.model_name,
            'model_type': 'Donut',
            'task': 'Document Visual Question Answering',
            'max_length': self.max_length,
            'num_beams': self.num_beams,
            'supported_tasks': list(self.prompts.keys()),
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
            test_image = Image.new('RGB', (400, 300), color='white')
            
            # تست استخراج اطلاعات
            result = self.extract_document_info(test_image)
            
            logger.info(f"✅ Donut test completed. Result: '{result['text'][:50]}...'")
            return bool(result['text'])
            
        except Exception as e:
            logger.error(f"❌ Donut test failed: {e}")
            return False

# Factory function
def create_donut_handler(
    model_name: str = "naver-clova-ix/donut-base-finetuned-docvqa",
    **kwargs
) -> DonutHandler:
    """ایجاد Donut handler"""
    return DonutHandler(model_name=model_name, **kwargs)
