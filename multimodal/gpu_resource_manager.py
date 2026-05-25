# -*- coding: utf-8 -*-
"""
GPU Resource Manager
مدیریت منابع GPU برای سیستم Multimodal RAG
"""

import torch
import gc
from typing import Dict, List, Optional, Any
from loguru import logger
from config.gpu_config import gpu_config

class GPUResourceManager:
    """مدیریت منابع GPU و VRAM"""
    
    def __init__(self):
        self.gpu_config = gpu_config
        self.loaded_models = {}  # {model_name: {'gpu_id': int, 'memory_usage': int}}
        self.model_allocations = {}  # {gpu_id: {'models': [], 'used_memory': int}}
        self._initialize_allocations()
    
    def _initialize_allocations(self):
        """مقداردهی اولیه تخصیص‌ها"""
        for gpu_id in self.gpu_config.available_vram.keys():
            self.model_allocations[gpu_id] = {
                'models': [],
                'used_memory': 0
            }
    
    def can_load_model(self, model_name: str, required_vram_gb: int) -> bool:
        """بررسی امکان بارگذاری مدل"""
        best_gpu = self.gpu_config.get_best_gpu_for_model(model_name)
        if best_gpu == -1:
            return False
        
        required_vram_mb = required_vram_gb * 1024
        available_vram = self.gpu_config.available_vram[best_gpu]['available']
        allocated_vram = self.model_allocations[best_gpu]['used_memory']
        
        return (available_vram - allocated_vram) >= required_vram_mb
    
    def allocate_model(self, model_name: str, gpu_id: int, memory_usage_mb: int) -> bool:
        """تخصیص مدل به GPU"""
        try:
            if gpu_id not in self.model_allocations:
                logger.error(f"Invalid GPU ID: {gpu_id}")
                return False
            
            # بررسی فضای کافی
            available = self.gpu_config.available_vram[gpu_id]['available']
            allocated = self.model_allocations[gpu_id]['used_memory']
            
            if (available - allocated) < memory_usage_mb:
                logger.warning(f"Insufficient VRAM on GPU {gpu_id}")
                return False
            
            # تخصیص مدل
            self.loaded_models[model_name] = {
                'gpu_id': gpu_id,
                'memory_usage': memory_usage_mb
            }
            
            self.model_allocations[gpu_id]['models'].append(model_name)
            self.model_allocations[gpu_id]['used_memory'] += memory_usage_mb
            
            logger.info(f"✅ Allocated {model_name} to GPU {gpu_id} ({memory_usage_mb}MB)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to allocate model {model_name}: {e}")
            return False
    
    def deallocate_model(self, model_name: str) -> bool:
        """حذف تخصیص مدل"""
        try:
            if model_name not in self.loaded_models:
                logger.warning(f"Model {model_name} not found in allocations")
                return False
            
            gpu_id = self.loaded_models[model_name]['gpu_id']
            memory_usage = self.loaded_models[model_name]['memory_usage']
            
            # حذف از تخصیص‌ها
            if model_name in self.model_allocations[gpu_id]['models']:
                self.model_allocations[gpu_id]['models'].remove(model_name)
                self.model_allocations[gpu_id]['used_memory'] -= memory_usage
            
            # حذف از لیست مدل‌های بارگذاری شده
            del self.loaded_models[model_name]
            
            logger.info(f"✅ Deallocated {model_name} from GPU {gpu_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deallocate model {model_name}: {e}")
            return False
    
    def get_optimal_gpu_for_model(self, model_name: str, required_vram_gb: int) -> int:
        """انتخاب بهینه‌ترین GPU برای مدل"""
        required_vram_mb = required_vram_gb * 1024
        
        # پیدا کردن GPU با بیشترین فضای آزاد
        best_gpu = -1
        max_available = 0
        
        for gpu_id, info in self.gpu_config.available_vram.items():
            available = info['available'] - self.model_allocations[gpu_id]['used_memory']
            
            if available >= required_vram_mb and available > max_available:
                max_available = available
                best_gpu = gpu_id
        
        return best_gpu
    
    def get_memory_usage_summary(self) -> Dict:
        """خلاصه استفاده از حافظه"""
        summary = {
            'total_gpus': len(self.gpu_config.available_vram),
            'loaded_models': len(self.loaded_models),
            'gpu_usage': {}
        }
        
        for gpu_id, allocation in self.model_allocations.items():
            gpu_info = self.gpu_config.available_vram[gpu_id]
            summary['gpu_usage'][gpu_id] = {
                'total_memory': gpu_info['total'],
                'used_by_system': gpu_info['used'],
                'used_by_models': allocation['used_memory'],
                'available': gpu_info['available'] - allocation['used_memory'],
                'loaded_models': allocation['models']
            }
        
        return summary
    
    def cleanup_unused_models(self) -> int:
        """پاک‌سازی مدل‌های استفاده نشده"""
        cleaned = 0
        
        try:
            # Clear CUDA cache for all GPUs
            for gpu_id in range(torch.cuda.device_count()):
                try:
                    with torch.cuda.device(gpu_id):
                        torch.cuda.empty_cache()
                        torch.cuda.synchronize()
                except Exception as e:
                    logger.warning(f"Failed to clear cache for GPU {gpu_id}: {e}")
            
            # Force garbage collection
            gc.collect()
            
            # Reset memory allocations
            self.model_allocations = {}
            for gpu_id in self.gpu_config.available_vram.keys():
                self.model_allocations[gpu_id] = {
                    'models': [],
                    'used_memory': 0
                }
            
            cleaned = len(self.loaded_models)
            self.loaded_models.clear()
            
            logger.info(f"🧹 Cleaned up {cleaned} models and cache")
            return cleaned
            
        except Exception as e:
            logger.error(f"Failed to cleanup models: {e}")
            return 0
    
    def check_vram_availability(self) -> Dict[str, Any]:
        """بررسی VRAM موجود در تمام GPUها"""
        try:
            vram_info = {
                'total_available_gb': 0.0,
                'gpu_details': {},
                'can_load_models': [],
                'recommendations': []
            }
            
            # بررسی هر GPU
            for gpu_id, allocation in self.model_allocations.items():
                gpu_info = self.gpu_config.available_vram[gpu_id]
                available_mb = gpu_info['available'] - allocation['used_memory']
                available_gb = available_mb / 1024
                
                vram_info['gpu_details'][gpu_id] = {
                    'total_gb': gpu_info['total'] / 1024,
                    'used_gb': gpu_info['used'] / 1024,
                    'allocated_gb': allocation['used_memory'] / 1024,
                    'available_gb': available_gb,
                    'loaded_models': allocation['models']
                }
                
                vram_info['total_available_gb'] += available_gb
            
            # بررسی مدل‌های قابل بارگذاری
            model_requirements = self.gpu_config._get_model_requirements()
            for priority, models in model_requirements.items():
                for model_name, required_gb in models.items():
                    if vram_info['total_available_gb'] >= required_gb:
                        vram_info['can_load_models'].append({
                            'model': model_name,
                            'required_gb': required_gb,
                            'priority': priority
                        })
            
            # توصیه‌ها
            if vram_info['total_available_gb'] >= 20:
                vram_info['recommendations'].append("Can load all multimodal models simultaneously")
            elif vram_info['total_available_gb'] >= 10:
                vram_info['recommendations'].append("Can load LayoutLMv3 + Donut + TrOCR + CLIP")
            elif vram_info['total_available_gb'] >= 6:
                vram_info['recommendations'].append("Can load TrOCR + CLIP + one heavy model")
            else:
                vram_info['recommendations'].append("Limited VRAM - use only lightweight models")
            
            return vram_info
            
        except Exception as e:
            logger.error(f"Failed to check VRAM availability: {e}")
            return {
                'total_available_gb': 0.0,
                'gpu_details': {},
                'can_load_models': [],
                'recommendations': ['Error checking VRAM']
            }
    
    def get_recommended_loading_order(self) -> List[str]:
        """ترتیب توصیه‌شده بارگذاری مدل‌ها"""
        recommendations = self.gpu_config.get_recommended_models()
        return recommendations['recommended_priority']
    
    def can_load_multiple_models(self, models: List[tuple]) -> bool:
        """بررسی امکان بارگذاری چندین مدل همزمان"""
        # models: [(model_name, required_vram_gb), ...]
        total_required = sum(vram for _, vram in models)
        
        # محاسبه VRAM کل موجود
        total_available = 0
        for gpu_id, info in self.gpu_config.available_vram.items():
            allocated = self.model_allocations[gpu_id]['used_memory']
            available = info['available'] - allocated
            total_available += available
        
        total_available_gb = total_available / 1024
        
        return total_available_gb >= total_required
    
    def optimize_model_distribution(self) -> Dict:
        """بهینه‌سازی توزیع مدل‌ها روی GPUها"""
        # اینجا می‌توانید الگوریتم‌های بهینه‌سازی توزیع مدل‌ها را پیاده کنید
        # فعلاً فقط وضعیت فعلی را برمی‌گردانیم
        
        return {
            'current_distribution': self.model_allocations,
            'recommendations': self.get_recommended_loading_order(),
            'memory_summary': self.get_memory_usage_summary()
        }

# Global instance
gpu_resource_manager = GPUResourceManager()
