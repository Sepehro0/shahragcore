#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت تست کامل deployment
Comprehensive Deployment Test Script
"""

import sys
import os
import traceback
from pathlib import Path

# اضافه کردن مسیر پروژه به PYTHONPATH
project_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_dir))

def print_header(text):
    """چاپ هدر با فرمت زیبا"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_success(text):
    """چاپ پیام موفقیت"""
    print(f"✅ {text}")

def print_error(text):
    """چاپ پیام خطا"""
    print(f"❌ {text}")

def print_info(text):
    """چاپ اطلاعات"""
    print(f"ℹ️  {text}")

def test_imports():
    """تست import ماژول‌های اصلی"""
    print_header("تست Import ماژول‌ها")
    
    modules_to_test = [
        ("core.refactored_rag_system", "RefactoredRAGSystem"),
        ("core.initialization", "ComponentInitializer"),
        ("core.answer_generator", "AnswerGenerator"),
        ("core.chat_manager", "ChatManager"),
        ("processors.document_manager", "DocumentManager"),
        ("search.retrieval_manager", "RetrievalManager"),
        ("services.qwen_client", "QwenClient"),
        ("integrations.database_handler", "DatabaseHandler"),
        ("utils.text_utils", "TextNormalizer"),
        ("config.settings", "Settings"),
    ]
    
    failed_imports = []
    
    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            print_success(f"{module_name}.{class_name}")
        except Exception as e:
            print_error(f"{module_name}.{class_name}: {str(e)}")
            failed_imports.append((module_name, class_name, str(e)))
    
    if failed_imports:
        print(f"\n⚠️  {len(failed_imports)} ماژول import نشدند")
        return False
    else:
        print(f"\n✅ تمام {len(modules_to_test)} ماژول با موفقیت import شدند")
        return True

def test_directories():
    """تست وجود دایرکتوری‌های لازم"""
    print_header("تست دایرکتوری‌ها")
    
    required_dirs = [
        "core",
        "config",
        "services",
        "processors",
        "utils",
        "search",
        "integrations",
        "chroma_db",
    ]
    
    missing_dirs = []
    
    for dir_name in required_dirs:
        dir_path = project_dir / dir_name
        if dir_path.exists():
            print_success(f"{dir_name}/")
        else:
            print_error(f"{dir_name}/ (یافت نشد)")
            missing_dirs.append(dir_name)
    
    if missing_dirs:
        print(f"\n⚠️  {len(missing_dirs)} دایرکتوری یافت نشد")
        return False
    else:
        print(f"\n✅ تمام {len(required_dirs)} دایرکتوری موجود هستند")
        return True

def test_files():
    """تست وجود فایل‌های مهم"""
    print_header("تست فایل‌های مهم")
    
    required_files = [
        "api_server.py",
        "requirements.txt",
        "requirements_api.txt",
        "core/refactored_rag_system.py",
        "config/settings.py",
        "__init__.py",
    ]
    
    missing_files = []
    
    for file_name in required_files:
        file_path = project_dir / file_name
        if file_path.exists():
            size = file_path.stat().st_size
            print_success(f"{file_name} ({size:,} bytes)")
        else:
            print_error(f"{file_name} (یافت نشد)")
            missing_files.append(file_name)
    
    if missing_files:
        print(f"\n⚠️  {len(missing_files)} فایل یافت نشد")
        return False
    else:
        print(f"\n✅ تمام {len(required_files)} فایل موجود هستند")
        return True

def test_chromadb():
    """تست دسترسی به ChromaDB"""
    print_header("تست ChromaDB")
    
    chroma_db_path = project_dir / "chroma_db"
    
    if not chroma_db_path.exists():
        print_error("دایرکتوری chroma_db یافت نشد")
        return False
    
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(chroma_db_path))
        collections = client.list_collections()
        
        print_success(f"ChromaDB قابل دسترسی است")
        print_info(f"تعداد collections: {len(collections)}")
        
        if collections:
            for col in collections[:5]:  # نمایش 5 تا اول
                print_info(f"  - {col.name}")
            if len(collections) > 5:
                print_info(f"  ... و {len(collections) - 5} collection دیگر")
        
        return True
    except Exception as e:
        print_error(f"خطا در دسترسی به ChromaDB: {str(e)}")
        traceback.print_exc()
        return False

def test_rag_initialization():
    """تست initialization سیستم RAG"""
    print_header("تست Initialization سیستم RAG")
    
    try:
        from core.refactored_rag_system import RefactoredRAGSystem
        
        chroma_db_path = str(project_dir / "chroma_db")
        
        print_info("در حال initialize کردن RefactoredRAGSystem...")
        rag = RefactoredRAGSystem(db_path=chroma_db_path)
        
        print_success("RefactoredRAGSystem با موفقیت initialize شد")
        
        # تست دریافت collections
        try:
            collections = rag.get_available_collections()
            print_success(f"Collections موجود: {len(collections)}")
            if collections:
                for col in collections[:5]:
                    print_info(f"  - {col}")
        except Exception as e:
            print_error(f"خطا در دریافت collections: {str(e)}")
        
        return True
        
    except Exception as e:
        print_error(f"خطا در initialization: {str(e)}")
        traceback.print_exc()
        return False

def test_dependencies():
    """تست نصب وابستگی‌های مهم"""
    print_header("تست وابستگی‌ها")
    
    critical_packages = [
        "chromadb",
        "transformers",
        "sentence_transformers",
        "torch",
        "fastapi",
        "uvicorn",
        "pandas",
        "numpy",
    ]
    
    missing_packages = []
    
    for package in critical_packages:
        try:
            __import__(package.replace("-", "_"))
            print_success(f"{package}")
        except ImportError:
            print_error(f"{package} (نصب نشده)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  {len(missing_packages)} package نصب نشده")
        print("لطفاً اجرا کنید: pip install -r requirements_api.txt")
        return False
    else:
        print(f"\n✅ تمام {len(critical_packages)} package نصب شده‌اند")
        return True

def main():
    """تابع اصلی"""
    print("\n" + "=" * 60)
    print("  🧪 تست کامل Deployment")
    print("=" * 60)
    print(f"\n📁 مسیر پروژه: {project_dir}")
    print(f"🐍 Python: {sys.version}")
    print()
    
    results = {
        "imports": test_imports(),
        "directories": test_directories(),
        "files": test_files(),
        "dependencies": test_dependencies(),
        "chromadb": test_chromadb(),
        "rag_init": test_rag_initialization(),
    }
    
    # خلاصه نتایج
    print_header("خلاصه نتایج")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\n{'=' * 60}")
    print(f"  نتایج: {passed}/{total} تست موفق")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 تمام تست‌ها موفق بودند! سیستم آماده است.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} تست ناموفق بودند. لطفاً مشکلات را برطرف کنید.")
        return 1

if __name__ == "__main__":
    sys.exit(main())


