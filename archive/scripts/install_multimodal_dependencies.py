#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Install Multimodal Dependencies
نصب وابستگی‌های Multimodal RAG
"""

import subprocess
import sys
import os
from loguru import logger

def install_package(package):
    """نصب یک پکیج"""
    try:
        logger.info(f"📦 Installing {package}...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", package, "--upgrade"
        ], capture_output=True, text=True, check=True)
        
        logger.info(f"✅ {package} installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to install {package}: {e}")
        logger.error(f"   Error output: {e.stderr}")
        return False

def main():
    """تابع اصلی نصب"""
    print("🚀 Installing Multimodal RAG Dependencies")
    print("=" * 50)
    
    # لیست وابستگی‌های جدید
    new_dependencies = [
        "pillow>=10.0.0",
        "opencv-python>=4.8.0", 
        "timm>=0.9.0",
        "einops>=0.7.0",
        "accelerate>=0.24.0",
        "bitsandbytes>=0.41.0",
        "huggingface-hub>=0.19.0",
        "PyMuPDF>=1.23.0",  # برای PDF processing
        "transformers>=4.35.0",  # به‌روزرسانی transformers
        "torch>=2.1.0",  # به‌روزرسانی torch
        "torchvision>=0.16.0",  # برای image processing
    ]
    
    # وابستگی‌های اختیاری برای مدل‌های خاص
    optional_dependencies = [
        "sentence-transformers>=2.2.0",  # اگر نصب نشده باشد
        "datasets>=2.14.0",  # برای HuggingFace datasets
        "tokenizers>=0.14.0",  # برای tokenization
    ]
    
    success_count = 0
    total_count = len(new_dependencies)
    
    print(f"\n📦 Installing {total_count} required dependencies...")
    
    # نصب وابستگی‌های اصلی
    for package in new_dependencies:
        if install_package(package):
            success_count += 1
        else:
            logger.warning(f"⚠️  Failed to install {package}")
    
    print(f"\n📦 Installing {len(optional_dependencies)} optional dependencies...")
    
    # نصب وابستگی‌های اختیاری
    optional_success = 0
    for package in optional_dependencies:
        if install_package(package):
            optional_success += 1
    
    # خلاصه نتایج
    print("\n📊 Installation Summary:")
    print(f"   Required dependencies: {success_count}/{total_count} installed")
    print(f"   Optional dependencies: {optional_success}/{len(optional_dependencies)} installed")
    
    if success_count == total_count:
        print("✅ All required dependencies installed successfully!")
        
        # تست import کردن ماژول‌های مهم
        print("\n🧪 Testing imports...")
        test_imports = [
            ("PIL", "Pillow"),
            ("cv2", "OpenCV"),
            ("torch", "PyTorch"),
            ("transformers", "Transformers"),
            ("huggingface_hub", "HuggingFace Hub"),
            ("accelerate", "Accelerate"),
            ("bitsandbytes", "BitsAndBytes"),
        ]
        
        import_success = 0
        for module, name in test_imports:
            try:
                __import__(module)
                print(f"   ✅ {name}: OK")
                import_success += 1
            except ImportError as e:
                print(f"   ❌ {name}: Failed - {e}")
        
        if import_success == len(test_imports):
            print("\n🎉 All imports successful! Multimodal RAG is ready to use!")
            return True
        else:
            print(f"\n⚠️  {len(test_imports) - import_success} imports failed. Some features may not work.")
            return False
    else:
        print(f"\n❌ {total_count - success_count} required dependencies failed to install!")
        print("   Please check the error messages above and install manually if needed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
