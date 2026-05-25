#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix CUDA Errors
رفع خطاهای CUDA در سیستم Multimodal
"""

import torch
import os
import gc
from loguru import logger

def fix_cuda_errors():
    """رفع خطاهای CUDA"""
    print("🔧 Fixing CUDA Errors...")
    
    try:
        # 1. Clear CUDA cache
        if torch.cuda.is_available():
            print("   🧹 Clearing CUDA cache...")
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            
            # Clear cache for all GPUs
            for i in range(torch.cuda.device_count()):
                with torch.cuda.device(i):
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
        
        # 2. Force garbage collection
        print("   🗑️  Running garbage collection...")
        gc.collect()
        
        # 3. Set CUDA environment variables
        print("   ⚙️  Setting CUDA environment variables...")
        os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
        os.environ['TORCH_USE_CUDA_DSA'] = '1'
        os.environ['CUDA_VISIBLE_DEVICES'] = '0,1,2,3,4,5,6,7'  # Use all GPUs
        
        # 4. Set PyTorch memory management
        print("   💾 Configuring PyTorch memory management...")
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        
        # 5. Set memory fraction to prevent OOM
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                torch.cuda.set_per_process_memory_fraction(0.8, device=i)
        
        print("✅ CUDA errors fixed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to fix CUDA errors: {e}")
        return False

def test_cuda_fix():
    """تست رفع خطاهای CUDA"""
    print("\n🧪 Testing CUDA fix...")
    
    try:
        # Test basic CUDA operations
        if torch.cuda.is_available():
            device = torch.device('cuda:0')
            
            # Test tensor creation
            x = torch.randn(100, 100, device=device)
            y = torch.randn(100, 100, device=device)
            
            # Test basic operations
            z = torch.matmul(x, y)
            z = z.cpu()
            
            # Test memory allocation
            large_tensor = torch.randn(1000, 1000, device=device)
            del large_tensor
            torch.cuda.empty_cache()
            
            print("   ✅ Basic CUDA operations working")
            
            # Test multi-GPU
            if torch.cuda.device_count() > 1:
                for i in range(min(2, torch.cuda.device_count())):
                    with torch.cuda.device(i):
                        test_tensor = torch.randn(10, 10, device=f'cuda:{i}')
                        del test_tensor
                print("   ✅ Multi-GPU operations working")
            
            return True
        else:
            print("   ⚠️  CUDA not available")
            return False
            
    except Exception as e:
        print(f"   ❌ CUDA test failed: {e}")
        return False

if __name__ == "__main__":
    success = fix_cuda_errors()
    if success:
        test_cuda_fix()
    else:
        print("❌ CUDA fix failed")
