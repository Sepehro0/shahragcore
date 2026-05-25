# -*- coding: utf-8 -*-
"""
Base Multimodal Processor
پردازشگر پایه برای تمام مدل‌های multimodal
"""

import torch
import gc
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from PIL import Image
import numpy as np
from loguru import logger
from .gpu_resource_manager import gpu_resource_manager

class BaseMultimodalProcessor(ABC):
    """کلاس پایه برای تمام پردازشگرهای multimodal"""
    
    def __init__(
        self, 
        model_name: str,
        model_path: Optional[str] = None,
        device: Optional[str] = None,
        load_in_8bit: bool = False,
        load_in_4bit: bool = False,
        auto_allocate_gpu: bool = True
    ):
        self.model_name = model_name
        self.model_path = model_path or model_name
        self.device = device or self._get_optimal_device()
        self.load_in_8bit = load_in_8bit
        self.load_in_4bit = load_in_4bit
        self.auto_allocate_gpu = auto_allocate_gpu
        
        # Validate quantization settings
        if self.load_in_4bit and self.load_in_8bit:
            logger.warning("Both 4-bit and 8-bit quantization enabled. Using 4-bit.")
            self.load_in_8bit = False
        
        # Model components
        self.processor = None
        self.model = None
        self.is_loaded = False
        
        # GPU management
        self.gpu_manager = gpu_resource_manager
        self.allocated_gpu = None
        self.memory_usage = 0
        
        # Performance tracking
        self.inference_count = 0
        self.total_inference_time = 0.0
        
    def _get_optimal_device(self) -> str:
        """انتخاب بهینه‌ترین device"""
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"
    
    def _estimate_memory_usage(self) -> int:
        """تخمین استفاده از حافظه (MB)"""
        # این مقدار باید در کلاس‌های فرزند override شود
        base_memory = 1000  # Default 1GB
        
        # Adjust for quantization
        if self.load_in_4bit:
            return int(base_memory * 0.3)  # 4-bit uses ~30% of original memory
        elif self.load_in_8bit:
            return int(base_memory * 0.5)  # 8-bit uses ~50% of original memory
        else:
            return base_memory
    
    def _allocate_gpu_resources(self) -> bool:
        """تخصیص منابع GPU"""
        if not self.auto_allocate_gpu:
            return True
        
        required_vram = self._estimate_memory_usage() / 1024  # Convert to GB
        optimal_gpu = self.gpu_manager.get_optimal_gpu_for_model(
            self.model_name, 
            required_vram
        )
        
        if optimal_gpu == -1:
            logger.warning(f"No suitable GPU found for {self.model_name}, using CPU fallback")
            self.device = "cpu"
            self.allocated_gpu = None
            return True
        
        # Set device to specific GPU with proper synchronization
        try:
            if torch.cuda.is_available():
                # Clear all GPU caches first
                for i in range(torch.cuda.device_count()):
                    with torch.cuda.device(i):
                        torch.cuda.empty_cache()
                
                self.device = f"cuda:{optimal_gpu}"
                self.allocated_gpu = optimal_gpu
                
                # Set CUDA device and synchronize
                torch.cuda.set_device(optimal_gpu)
                torch.cuda.synchronize()
                
                # Clear cache before allocation
                torch.cuda.empty_cache()
            
            # Allocate in resource manager
            success = self.gpu_manager.allocate_model(
                self.model_name,
                optimal_gpu,
                self._estimate_memory_usage()
            )
            
            if success:
                self.memory_usage = self._estimate_memory_usage()
                logger.info(f"✅ Allocated GPU resources for {self.model_name} on GPU {optimal_gpu}")
                return True
            else:
                logger.warning(f"GPU allocation failed for {self.model_name}, using CPU fallback")
                self.device = "cpu"
                self.allocated_gpu = None
                return True
                
        except Exception as e:
            logger.warning(f"CUDA error for {self.model_name}: {e}, using CPU fallback")
            self.device = "cpu"
            self.allocated_gpu = None
            return True
    
    def _deallocate_gpu_resources(self) -> bool:
        """حذف تخصیص منابع GPU"""
        if self.allocated_gpu is not None:
            success = self.gpu_manager.deallocate_model(self.model_name)
            if success:
                self.allocated_gpu = None
                self.memory_usage = 0
                logger.info(f"✅ Deallocated GPU resources for {self.model_name}")
            return success
        return True
    
    @abstractmethod
    def _load_model_components(self) -> bool:
        """بارگذاری کامپوننت‌های مدل (باید در کلاس‌های فرزند پیاده شود)"""
        pass
    
    @abstractmethod
    def _unload_model_components(self) -> bool:
        """حذف کامپوننت‌های مدل (باید در کلاس‌های فرزند پیاده شود)"""
        pass
    
    def load_model(self) -> bool:
        """بارگذاری مدل"""
        try:
            if self.is_loaded:
                logger.warning(f"Model {self.model_name} is already loaded")
                return True
            
            # تخصیص منابع GPU
            if not self._allocate_gpu_resources():
                logger.error(f"Failed to allocate GPU resources for {self.model_name}")
                return False
            
            # بارگذاری کامپوننت‌های مدل
            if not self._load_model_components():
                logger.error(f"Failed to load model components for {self.model_name}")
                self._deallocate_gpu_resources()
                return False
            
            self.is_loaded = True
            logger.info(f"✅ Successfully loaded {self.model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            self._deallocate_gpu_resources()
            return False
    
    def unload_model(self) -> bool:
        """حذف مدل"""
        try:
            if not self.is_loaded:
                logger.warning(f"Model {self.model_name} is not loaded")
                return True
            
            # حذف کامپوننت‌های مدل
            if not self._unload_model_components():
                logger.error(f"Failed to unload model components for {self.model_name}")
                return False
            
            # حذف تخصیص منابع GPU
            self._deallocate_gpu_resources()
            
            self.is_loaded = False
            logger.info(f"✅ Successfully unloaded {self.model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload model {self.model_name}: {e}")
            return False
    
    def _preprocess_image(self, image: Union[Image.Image, str, np.ndarray]) -> Image.Image:
        """پیش‌پردازش تصویر"""
        try:
            if image is None:
                # Create a default image if None
                return Image.new('RGB', (224, 224), color='white')
            
            if isinstance(image, str):
                image = Image.open(image)
            elif isinstance(image, np.ndarray):
                image = Image.fromarray(image)
            elif not isinstance(image, Image.Image):
                raise ValueError(f"Unsupported image type: {type(image)}")
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Ensure minimum size to prevent CUDA errors
            if image.size[0] < 32 or image.size[1] < 32:
                image = image.resize((max(32, image.size[0]), max(32, image.size[1])))
            
            return image
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}, using default image")
            return Image.new('RGB', (224, 224), color='white')
    
    def _postprocess_output(self, output: Any) -> Any:
        """پس‌پردازش خروجی"""
        # این متد می‌تواند در کلاس‌های فرزند override شود
        return output
    
    def _track_inference(self, inference_time: float):
        """ردیابی عملکرد inference"""
        self.inference_count += 1
        self.total_inference_time += inference_time
    
    def get_performance_stats(self) -> Dict:
        """آمار عملکرد"""
        avg_time = self.total_inference_time / max(self.inference_count, 1)
        return {
            'model_name': self.model_name,
            'is_loaded': self.is_loaded,
            'inference_count': self.inference_count,
            'total_inference_time': self.total_inference_time,
            'average_inference_time': avg_time,
            'memory_usage_mb': self.memory_usage,
            'allocated_gpu': self.allocated_gpu
        }
    
    def cleanup_memory(self):
        """پاک‌سازی حافظه"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
    
    def __enter__(self):
        """Context manager entry"""
        if not self.is_loaded:
            self.load_model()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        # می‌توانید تصمیم بگیرید که مدل را unload کنید یا نه
        # self.unload_model()
        pass
    
    def __del__(self):
        """Destructor"""
        try:
            if self.is_loaded:
                self.unload_model()
        except:
            pass
