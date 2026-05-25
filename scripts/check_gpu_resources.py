#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU Resources Check Script
اسکریپت بررسی منابع GPU
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
from config.gpu_config import gpu_config
from multimodal.gpu_resource_manager import gpu_resource_manager
from loguru import logger

def check_gpu_resources():
    """بررسی منابع GPU"""
    print("🔍 Checking GPU Resources...")
    print("=" * 60)
    
    # 1. Basic GPU Info
    print("\n📊 GPU Information:")
    print(gpu_config.get_gpu_summary())
    
    # 2. CUDA Availability
    print(f"\n🔧 CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   CUDA Version: {torch.version.cuda}")
        print(f"   PyTorch CUDA Version: {torch.version.cuda}")
        print(f"   Number of GPUs: {torch.cuda.device_count()}")
        
        for i in range(torch.cuda.device_count()):
            print(f"   GPU {i}: {torch.cuda.get_device_name(i)}")
    
    # 3. Model Recommendations
    print("\n🎯 Model Recommendations:")
    recommendations = gpu_config.get_recommended_models()
    
    print("\n✅ Can Load (Recommended):")
    for model in recommendations['can_load']:
        print(f"   - {model['model']} (Priority: {model['priority']}, VRAM: {model['required_vram']}GB)")
    
    print("\n❌ Cannot Load (Insufficient VRAM):")
    for model in recommendations['cannot_load']:
        print(f"   - {model['model']} (Priority: {model['priority']}, VRAM: {model['required_vram']}GB)")
    
    # 4. Loading Order
    print(f"\n📋 Recommended Loading Order:")
    for i, model in enumerate(recommendations['recommended_priority'], 1):
        print(f"   {i}. {model}")
    
    # 5. Memory Usage Summary
    print("\n💾 Current Memory Usage:")
    summary = gpu_resource_manager.get_memory_usage_summary()
    for gpu_id, usage in summary['gpu_usage'].items():
        print(f"   GPU {gpu_id}:")
        print(f"     Total: {usage['total_memory']}MB")
        print(f"     Used by System: {usage['used_by_system']}MB")
        print(f"     Used by Models: {usage['used_by_models']}MB")
        print(f"     Available: {usage['available']}MB")
        print(f"     Loaded Models: {usage['loaded_models']}")
    
    # 6. Test Model Loading
    print("\n🧪 Testing Model Loading Capabilities:")
    test_models = [
        ('microsoft/trocr-base-printed', 2),
        ('openai/clip-vit-base-patch32', 2),
        ('microsoft/layoutlmv3-base', 4),
        ('naver-clova-ix/donut-base-finetuned-docvqa', 6),
        ('Salesforce/blip2-opt-2.7b', 10),
        ('llava-hf/llava-1.5-7b-hf', 14)
    ]
    
    for model_name, required_vram in test_models:
        can_load = gpu_resource_manager.can_load_model(model_name, required_vram)
        status = "✅ Can Load" if can_load else "❌ Cannot Load"
        print(f"   {model_name}: {status} ({required_vram}GB)")
    
    # 7. Multiple Model Loading Test
    print("\n🔄 Multiple Model Loading Test:")
    test_combinations = [
        [('microsoft/trocr-base-printed', 2), ('openai/clip-vit-base-patch32', 2)],
        [('microsoft/trocr-base-printed', 2), ('microsoft/layoutlmv3-base', 4)],
        [('microsoft/layoutlmv3-base', 4), ('naver-clova-ix/donut-base-finetuned-docvqa', 6)],
        [('Salesforce/blip2-opt-2.7b', 10), ('llava-hf/llava-1.5-7b-hf', 14)]
    ]
    
    for i, combination in enumerate(test_combinations, 1):
        can_load = gpu_resource_manager.can_load_multiple_models(combination)
        status = "✅ Can Load" if can_load else "❌ Cannot Load"
        models_str = ", ".join([f"{name} ({vram}GB)" for name, vram in combination])
        print(f"   Combination {i}: {models_str} - {status}")
    
    # 8. Recommendations
    print("\n💡 Recommendations:")
    total_available = sum(info['available'] for info in gpu_config.available_vram.values())
    total_available_gb = total_available / 1024
    
    if total_available_gb >= 50:
        print("   🚀 Excellent! You have plenty of VRAM for all models.")
        print("   💡 You can load all models simultaneously.")
    elif total_available_gb >= 20:
        print("   ✅ Good! You can load most models.")
        print("   💡 Consider loading models on-demand to save VRAM.")
    elif total_available_gb >= 10:
        print("   ⚠️  Limited VRAM. Load only essential models.")
        print("   💡 Use 8-bit quantization for larger models.")
    else:
        print("   ❌ Very limited VRAM. Use only small models.")
        print("   💡 Consider using CPU for some models.")
    
    print("\n" + "=" * 60)
    print("✅ GPU Resources Check Complete!")

if __name__ == "__main__":
    check_gpu_resources()
