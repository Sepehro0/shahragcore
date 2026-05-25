#!/usr/bin/env python3
"""
Optimize CUDA settings for 8 RTX 4090 GPUs
بهینه‌سازی تنظیمات CUDA برای 8 GPU RTX 4090
"""

import os
import sys
import torch
import gc
import subprocess
from loguru import logger

def optimize_cuda_for_8gpu():
    """بهینه‌سازی CUDA برای 8 GPU RTX 4090"""
    
    logger.info("🚀 Optimizing CUDA for 8 RTX 4090 GPUs...")
    
    try:
        # 1. Set optimal environment variables
        os.environ['CUDA_VISIBLE_DEVICES'] = '0,1,2,3,4,5,6,7'  # Use all 8 GPUs
        os.environ['CUDA_LAUNCH_BLOCKING'] = '0'  # Async execution
        os.environ['TORCH_USE_CUDA_DSA'] = '0'    # Disable device-side assertions
        os.environ['CUDA_CACHE_DISABLE'] = '0'   # Enable CUDA cache
        os.environ['CUDA_CACHE_MAXSIZE'] = '2147483648'  # 2GB cache
        
        # 2. PyTorch memory management
        torch.backends.cudnn.benchmark = True  # Enable cuDNN benchmark
        torch.backends.cudnn.deterministic = False  # Allow non-deterministic for speed
        torch.backends.cudnn.enabled = True
        
        # 3. Memory management settings
        torch.backends.cuda.matmul.allow_tf32 = True  # Allow TF32 for speed
        torch.backends.cudnn.allow_tf32 = True
        
        # 4. Set memory fraction for each GPU (80% to leave room for system)
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                torch.cuda.set_per_process_memory_fraction(0.8, device=i)
                logger.info(f"✅ GPU {i}: Memory fraction set to 0.8")
        
        # 5. Clear all CUDA caches
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                with torch.cuda.device(i):
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
            logger.info("✅ CUDA cache cleared for all GPUs")
        
        # 6. Force garbage collection
        gc.collect()
        logger.info("✅ Garbage collection completed")
        
        # 7. Check GPU status
        if torch.cuda.is_available():
            logger.info(f"✅ CUDA available: {torch.cuda.device_count()} GPUs")
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                memory_allocated = torch.cuda.memory_allocated(i) / 1024**3
                memory_reserved = torch.cuda.memory_reserved(i) / 1024**3
                memory_total = props.total_memory / 1024**3
                memory_free = memory_total - memory_allocated
                
                logger.info(f"   GPU {i}: {props.name}")
                logger.info(f"      Total: {memory_total:.1f}GB")
                logger.info(f"      Allocated: {memory_allocated:.1f}GB")
                logger.info(f"      Reserved: {memory_reserved:.1f}GB")
                logger.info(f"      Free: {memory_free:.1f}GB")
        else:
            logger.warning("❌ CUDA not available")
            return False
        
        # 8. Test CUDA operations on all GPUs
        logger.info("🧪 Testing CUDA operations on all GPUs...")
        for i in range(torch.cuda.device_count()):
            try:
                device = torch.device(f'cuda:{i}')
                
                # Test tensor operations
                x = torch.randn(1000, 1000, device=device)
                y = torch.randn(1000, 1000, device=device)
                z = torch.mm(x, y)
                
                # Test model loading
                model = torch.nn.Linear(1000, 500).to(device)
                output = model(x)
                
                # Clean up
                del x, y, z, model, output
                torch.cuda.empty_cache()
                
                logger.info(f"✅ GPU {i}: Operations working correctly")
                
            except Exception as e:
                logger.error(f"❌ GPU {i}: Test failed: {e}")
                return False
        
        logger.info("✅ CUDA optimization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ CUDA optimization failed: {e}")
        return False

def create_cuda_config():
    """ایجاد فایل تنظیمات CUDA"""
    
    config_content = '''# CUDA Configuration for 8 RTX 4090 GPUs
# تنظیمات CUDA برای 8 GPU RTX 4090

import os
import torch

def setup_cuda_environment():
    """تنظیم محیط CUDA"""
    
    # Environment variables
    os.environ['CUDA_VISIBLE_DEVICES'] = '0,1,2,3,4,5,6,7'
    os.environ['CUDA_LAUNCH_BLOCKING'] = '0'
    os.environ['TORCH_USE_CUDA_DSA'] = '0'
    os.environ['CUDA_CACHE_DISABLE'] = '0'
    os.environ['CUDA_CACHE_MAXSIZE'] = '2147483648'
    
    # PyTorch settings
    torch.backends.cudnn.benchmark = True
    torch.backends.cudnn.deterministic = False
    torch.backends.cudnn.enabled = True
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    
    # Memory management
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            torch.cuda.set_per_process_memory_fraction(0.8, device=i)

def get_gpu_info():
    """اطلاعات GPU"""
    if not torch.cuda.is_available():
        return None
    
    gpu_info = []
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        memory_allocated = torch.cuda.memory_allocated(i) / 1024**3
        memory_reserved = torch.cuda.memory_reserved(i) / 1024**3
        memory_total = props.total_memory / 1024**3
        
        gpu_info.append({
            'id': i,
            'name': props.name,
            'total_memory': memory_total,
            'allocated_memory': memory_allocated,
            'reserved_memory': memory_reserved,
            'free_memory': memory_total - memory_allocated
        })
    
    return gpu_info

def allocate_model_to_gpu(model, gpu_id: int):
    """تخصیص مدل به GPU مشخص"""
    if torch.cuda.is_available() and gpu_id < torch.cuda.device_count():
        device = torch.device(f'cuda:{gpu_id}')
        model = model.to(device)
        return model
    return model

def cleanup_gpu_memory(gpu_id: int = None):
    """پاک‌سازی حافظه GPU"""
    if torch.cuda.is_available():
        if gpu_id is not None:
            with torch.cuda.device(gpu_id):
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        else:
            for i in range(torch.cuda.device_count()):
                with torch.cuda.device(i):
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
'''
    
    with open('/home/user01/qwen-api/enhanced_rag_system/config/cuda_config.py', 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    logger.info("✅ CUDA config file created")

def test_memory_management():
    """تست مدیریت حافظه"""
    
    logger.info("🧪 Testing memory management...")
    
    try:
        # Test memory allocation and deallocation
        models = []
        
        for i in range(min(4, torch.cuda.device_count())):  # Test on first 4 GPUs
            device = torch.device(f'cuda:{i}')
            
            # Allocate memory
            model = torch.nn.Linear(1000, 1000).to(device)
            models.append(model)
            
            # Check memory usage
            allocated = torch.cuda.memory_allocated(i) / 1024**3
            logger.info(f"   GPU {i}: {allocated:.2f}GB allocated")
        
        # Deallocate memory
        for i, model in enumerate(models):
            del model
            torch.cuda.empty_cache()
            
            allocated = torch.cuda.memory_allocated(i) / 1024**3
            logger.info(f"   GPU {i}: {allocated:.2f}GB after cleanup")
        
        logger.info("✅ Memory management test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Memory management test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting CUDA Optimization for 8 RTX 4090 GPUs...")
    
    # Create config directory if it doesn't exist
    os.makedirs('/home/user01/qwen-api/enhanced_rag_system/config', exist_ok=True)
    
    # Optimize CUDA
    if optimize_cuda_for_8gpu():
        logger.info("✅ CUDA optimization successful")
        
        # Create config file
        create_cuda_config()
        
        # Test memory management
        if test_memory_management():
            logger.info("🎉 All CUDA optimizations completed successfully!")
        else:
            logger.warning("⚠️ CUDA optimization completed but memory test failed")
    else:
        logger.error("❌ CUDA optimization failed")
        sys.exit(1)
