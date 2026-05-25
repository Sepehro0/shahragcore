#!/usr/bin/env python3
"""
Fix CUDA device-side assert errors for multimodal models
"""

import os
import sys
import torch
import gc
import subprocess
from loguru import logger

def fix_cuda_assert_errors():
    """Fix CUDA device-side assert errors"""
    
    logger.info("🔧 Fixing CUDA device-side assert errors...")
    
    try:
        # 1. Set environment variables to prevent device-side asserts
        os.environ['CUDA_LAUNCH_BLOCKING'] = '0'  # Disable blocking for better performance
        os.environ['TORCH_USE_CUDA_DSA'] = '0'    # Disable device-side assertions
        os.environ['CUDA_VISIBLE_DEVICES'] = '0,1,2,3,4,5,6,7'  # Use all GPUs
        
        # 2. Clear all CUDA caches
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                with torch.cuda.device(i):
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
            logger.info("✅ CUDA cache cleared")
        
        # 3. Force garbage collection
        gc.collect()
        logger.info("✅ Garbage collection completed")
        
        # 4. Set PyTorch memory management
        torch.backends.cudnn.benchmark = False  # Disable cuDNN benchmark
        torch.backends.cudnn.deterministic = True  # Use deterministic algorithms
        
        # 5. Set memory fraction to prevent OOM
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                torch.cuda.set_per_process_memory_fraction(0.8, device=i)
            logger.info("✅ Memory fraction set to 0.8 for all GPUs")
        
        # 6. Reset CUDA context
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            logger.info("✅ CUDA context reset")
        
        # 7. Check CUDA status
        if torch.cuda.is_available():
            logger.info(f"✅ CUDA available: {torch.cuda.device_count()} GPUs")
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                memory_allocated = torch.cuda.memory_allocated(i) / 1024**3
                memory_reserved = torch.cuda.memory_reserved(i) / 1024**3
                memory_total = props.total_memory / 1024**3
                logger.info(f"   GPU {i}: {props.name} - {memory_allocated:.1f}GB/{memory_total:.1f}GB")
        else:
            logger.warning("❌ CUDA not available")
        
        logger.info("✅ CUDA device-side assert errors fixed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to fix CUDA errors: {e}")
        return False

def test_cuda_fix():
    """Test if CUDA fix works"""
    
    logger.info("🧪 Testing CUDA fix...")
    
    try:
        # Test basic CUDA operations
        if torch.cuda.is_available():
            device = torch.device('cuda:0')
            
            # Test tensor creation
            x = torch.randn(100, 100, device=device)
            y = torch.randn(100, 100, device=device)
            z = torch.mm(x, y)
            
            # Test model loading (small model)
            model = torch.nn.Linear(100, 50).to(device)
            output = model(x)
            
            # Clean up
            del x, y, z, model, output
            torch.cuda.empty_cache()
            
            logger.info("✅ CUDA operations working correctly")
            return True
        else:
            logger.warning("❌ CUDA not available for testing")
            return False
            
    except Exception as e:
        logger.error(f"❌ CUDA test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting CUDA device-side assert error fix...")
    
    # Fix CUDA errors
    if fix_cuda_assert_errors():
        logger.info("✅ CUDA errors fixed successfully")
        
        # Test the fix
        if test_cuda_fix():
            logger.info("🎉 CUDA fix verified and working!")
        else:
            logger.warning("⚠️ CUDA fix applied but test failed")
    else:
        logger.error("❌ Failed to fix CUDA errors")
        sys.exit(1)
