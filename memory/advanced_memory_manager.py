#!/usr/bin/env python3
"""
Advanced Memory Manager for 8 RTX 4090 GPUs
مدیریت پیشرفته حافظه برای 8 GPU RTX 4090
"""

import os
import sys
import torch
import gc
import psutil
import threading
import time
from typing import Dict, List, Optional, Tuple, Any
from loguru import logger

class AdvancedMemoryManager:
    """مدیریت پیشرفته حافظه برای سیستم‌های چند GPU"""
    
    def __init__(self):
        self.gpu_count = torch.cuda.device_count() if torch.cuda.is_available() else 0
        self.memory_threshold = 0.8  # 80% threshold
        self.cleanup_interval = 30  # seconds
        self.monitoring = False
        self.monitor_thread = None
        
        # GPU memory tracking
        self.gpu_memory_usage = {}
        self.model_allocations = {}
        
        # Initialize tracking
        self._initialize_tracking()
        
        logger.info(f"🚀 Advanced Memory Manager initialized for {self.gpu_count} GPUs")
    
    def _initialize_tracking(self):
        """مقداردهی اولیه tracking"""
        for i in range(self.gpu_count):
            self.gpu_memory_usage[i] = {
                'total': 0,
                'allocated': 0,
                'reserved': 0,
                'free': 0,
                'usage_percent': 0
            }
            self.model_allocations[i] = []
    
    def get_gpu_memory_info(self, gpu_id: int) -> Dict:
        """اطلاعات حافظه GPU"""
        if not torch.cuda.is_available() or gpu_id >= self.gpu_count:
            return {}
        
        with torch.cuda.device(gpu_id):
            props = torch.cuda.get_device_properties(gpu_id)
            total_memory = props.total_memory
            allocated_memory = torch.cuda.memory_allocated(gpu_id)
            reserved_memory = torch.cuda.memory_reserved(gpu_id)
            free_memory = total_memory - allocated_memory
            
            return {
                'total': total_memory / 1024**3,
                'allocated': allocated_memory / 1024**3,
                'reserved': reserved_memory / 1024**3,
                'free': free_memory / 1024**3,
                'usage_percent': (allocated_memory / total_memory) * 100
            }
    
    def find_best_gpu(self, required_memory_gb: float) -> Optional[int]:
        """پیدا کردن بهترین GPU برای تخصیص حافظه"""
        best_gpu = None
        best_free_memory = 0
        
        for i in range(self.gpu_count):
            memory_info = self.get_gpu_memory_info(i)
            free_memory = memory_info.get('free', 0)
            
            if free_memory >= required_memory_gb and free_memory > best_free_memory:
                best_gpu = i
                best_free_memory = free_memory
        
        return best_gpu
    
    def allocate_model_to_gpu(self, model, model_name: str, required_memory_gb: float) -> bool:
        """تخصیص مدل به GPU"""
        gpu_id = self.find_best_gpu(required_memory_gb)
        
        if gpu_id is None:
            logger.warning(f"❌ No GPU available for {model_name} (requires {required_memory_gb}GB)")
            return False
        
        try:
            device = torch.device(f'cuda:{gpu_id}')
            model = model.to(device)
            
            # Track allocation
            self.model_allocations[gpu_id].append({
                'model_name': model_name,
                'memory_required': required_memory_gb,
                'allocated_time': time.time()
            })
            
            logger.info(f"✅ {model_name} allocated to GPU {gpu_id} ({required_memory_gb}GB)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to allocate {model_name} to GPU {gpu_id}: {e}")
            return False
    
    def cleanup_gpu_memory(self, gpu_id: int = None, force: bool = False):
        """پاک‌سازی حافظه GPU"""
        if gpu_id is not None:
            gpu_ids = [gpu_id]
        else:
            gpu_ids = range(self.gpu_count)
        
        for i in gpu_ids:
            try:
                with torch.cuda.device(i):
                    # Clear cache
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    
                    # Force garbage collection
                    gc.collect()
                    
                    # Get memory info after cleanup
                    memory_info = self.get_gpu_memory_info(i)
                    logger.info(f"🧹 GPU {i} cleaned: {memory_info['free']:.1f}GB free")
                    
            except Exception as e:
                logger.error(f"❌ Failed to cleanup GPU {i}: {e}")
    
    def monitor_memory_usage(self):
        """مانیتورینگ استفاده از حافظه"""
        while self.monitoring:
            try:
                for i in range(self.gpu_count):
                    memory_info = self.get_gpu_memory_info(i)
                    usage_percent = memory_info['usage_percent']
                    
                    # Check if memory usage is high
                    if usage_percent > (self.memory_threshold * 100):
                        logger.warning(f"⚠️ GPU {i} memory usage high: {usage_percent:.1f}%")
                        
                        # Cleanup if needed
                        if usage_percent > 90:
                            self.cleanup_gpu_memory(i, force=True)
                
                time.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"❌ Memory monitoring error: {e}")
                break
    
    def start_memory_monitoring(self):
        """شروع مانیتورینگ حافظه"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self.monitor_memory_usage, daemon=True)
            self.monitor_thread.start()
            logger.info("🔍 Memory monitoring started")
    
    def stop_memory_monitoring(self):
        """توقف مانیتورینگ حافظه"""
        if self.monitoring:
            self.monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join()
            logger.info("🛑 Memory monitoring stopped")
    
    def get_memory_report(self) -> Dict:
        """گزارش استفاده از حافظه"""
        report = {
            'gpu_count': self.gpu_count,
            'system_memory': {
                'total': psutil.virtual_memory().total / 1024**3,
                'available': psutil.virtual_memory().available / 1024**3,
                'used': psutil.virtual_memory().used / 1024**3,
                'percent': psutil.virtual_memory().percent
            },
            'gpu_memory': {}
        }
        
        for i in range(self.gpu_count):
            report['gpu_memory'][i] = self.get_gpu_memory_info(i)
        
        return report
    
    def get_system_memory_info(self) -> Dict:
        """اطلاعات حافظه سیستم"""
        try:
            vm = psutil.virtual_memory()
            return {
                "total": vm.total / (1024**3),  # Convert to GB
                "available": vm.available / (1024**3),
                "used": vm.used / (1024**3),
                "percent": vm.percent
            }
        except Exception as e:
            logger.error(f"Error getting system memory info: {e}")
            return {"total": 0, "available": 0, "used": 0, "percent": 0}
    
    def get_full_memory_report(self) -> Dict[str, Any]:
        """گزارش کامل حافظه سیستم و GPUها"""
        report = {
            "system_ram": self.get_system_memory_info(),
            "gpus": {}
        }
        
        for i in range(self.gpu_count):
            report["gpus"][f"GPU {i}"] = self.get_gpu_memory_info(i)
        
        return report
    
    def optimize_memory_allocation(self):
        """بهینه‌سازی تخصیص حافظه"""
        logger.info("🔧 Optimizing memory allocation...")
        
        # Cleanup all GPUs
        self.cleanup_gpu_memory()
        
        # Set memory fraction for each GPU
        for i in range(self.gpu_count):
            try:
                torch.cuda.set_per_process_memory_fraction(0.8, device=i)
                logger.info(f"✅ GPU {i}: Memory fraction set to 0.8")
            except Exception as e:
                logger.error(f"❌ Failed to set memory fraction for GPU {i}: {e}")
        
        # Start monitoring
        self.start_memory_monitoring()
        
        logger.info("✅ Memory optimization completed")
    
    def emergency_cleanup(self):
        """پاک‌سازی اضطراری حافظه"""
        logger.warning("🚨 Emergency memory cleanup initiated...")
        
        # Force cleanup on all GPUs
        for i in range(self.gpu_count):
            try:
                with torch.cuda.device(i):
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    torch.cuda.reset_peak_memory_stats()
            except Exception as e:
                logger.error(f"❌ Emergency cleanup failed for GPU {i}: {e}")
        
        # Force garbage collection
        gc.collect()
        
        logger.info("✅ Emergency cleanup completed")

def test_memory_manager():
    """تست memory manager"""
    
    logger.info("🧪 Testing Advanced Memory Manager...")
    
    try:
        # Initialize memory manager
        mm = AdvancedMemoryManager()
        
        # Get initial report
        report = mm.get_memory_report()
        logger.info(f"📊 Initial memory report:")
        logger.info(f"   System: {report['system_memory']['used']:.1f}GB/{report['system_memory']['total']:.1f}GB")
        
        for gpu_id, gpu_info in report['gpu_memory'].items():
            logger.info(f"   GPU {gpu_id}: {gpu_info['allocated']:.1f}GB/{gpu_info['total']:.1f}GB")
        
        # Test memory allocation
        logger.info("🧪 Testing memory allocation...")
        
        models = []
        for i in range(min(4, mm.gpu_count)):
            try:
                # Create a model
                model = torch.nn.Linear(1000, 1000)
                model_name = f"test_model_{i}"
                
                # Allocate to GPU
                if mm.allocate_model_to_gpu(model, model_name, 0.1):
                    models.append((i, model, model_name))
                    logger.info(f"✅ Model {model_name} allocated to GPU {i}")
                
            except Exception as e:
                logger.error(f"❌ Failed to allocate model to GPU {i}: {e}")
        
        # Test cleanup
        logger.info("🧹 Testing memory cleanup...")
        mm.cleanup_gpu_memory()
        
        # Get final report
        final_report = mm.get_memory_report()
        logger.info(f"📊 Final memory report:")
        for gpu_id, gpu_info in final_report['gpu_memory'].items():
            logger.info(f"   GPU {gpu_id}: {gpu_info['allocated']:.1f}GB/{gpu_info['total']:.1f}GB")
        
        # Stop monitoring
        mm.stop_memory_monitoring()
        
        logger.info("✅ Memory manager test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Memory manager test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting Advanced Memory Manager Test...")
    
    success = test_memory_manager()
    
    if success:
        logger.info("✅ All memory management tests passed!")
    else:
        logger.error("❌ Memory management tests failed!")
        sys.exit(1)
