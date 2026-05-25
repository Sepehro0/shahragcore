#!/bin/bash
# -*- coding: utf-8 -*-
# اسکریپت انتقال خودکار به سرور Production
# Automated Deployment Script for Production Server

set -e  # Exit on error

# رنگ‌ها برای خروجی
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# متغیرهای پیش‌فرض
PROJECT_DIR="/home/user01/qwen-api/enhanced_rag_system_dev"
PRODUCTION_USER=""
PRODUCTION_HOST=""
PRODUCTION_PATH="/home"
VENV_NAME="venv"
PYTHON_VERSION="python3"

# تابع نمایش پیام
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# بررسی پیش‌نیازها
check_prerequisites() {
    print_info "بررسی پیش‌نیازها..."
    
    # بررسی Python
    if ! command -v $PYTHON_VERSION &> /dev/null; then
        print_error "Python 3 یافت نشد!"
        exit 1
    fi
    print_success "Python پیدا شد: $($PYTHON_VERSION --version)"
    
    # بررسی pip
    if ! $PYTHON_VERSION -m pip --version &> /dev/null; then
        print_error "pip یافت نشد!"
        exit 1
    fi
    print_success "pip پیدا شد"
    
    # بررسی virtualenv
    if ! $PYTHON_VERSION -m venv --help &> /dev/null; then
        print_warning "virtualenv یافت نشد، نصب می‌شود..."
        $PYTHON_VERSION -m pip install virtualenv
    fi
    print_success "virtualenv آماده است"
}

# ایجاد لیست فایل‌های ضروری
create_essential_files_list() {
    print_info "ایجاد لیست فایل‌های ضروری..."
    
    cat > essential_files.txt << 'EOF'
# فایل‌های اصلی
api_server.py
requirements.txt
requirements_api.txt
__init__.py

# دایرکتوری‌های اصلی
core/
config/
services/
processors/
utils/
search/
integrations/

# فایل‌های تنظیمات
config/settings.py
config/feature_flags.py
config/collection_prompts.py
config/domain_configs.py

# فایل‌های Docker (در صورت نیاز)
Dockerfile
docker-compose.yml
EOF

    print_success "لیست فایل‌های ضروری ایجاد شد: essential_files.txt"
}

# نصب وابستگی‌ها
install_dependencies() {
    print_info "نصب وابستگی‌های Python..."
    
    # ایجاد virtual environment
    if [ ! -d "$VENV_NAME" ]; then
        print_info "ایجاد virtual environment..."
        $PYTHON_VERSION -m venv $VENV_NAME
    fi
    
    # فعال‌سازی virtual environment
    source $VENV_NAME/bin/activate
    
    # به‌روزرسانی pip
    print_info "به‌روزرسانی pip..."
    pip install --upgrade pip setuptools wheel --quiet
    
    # نصب وابستگی‌ها
    print_info "نصب وابستگی‌ها از requirements_api.txt..."
    if [ -f "requirements_api.txt" ]; then
        pip install -r requirements_api.txt
        print_success "وابستگی‌ها نصب شدند"
    else
        print_warning "requirements_api.txt یافت نشد، استفاده از requirements.txt..."
        if [ -f "requirements.txt" ]; then
            pip install -r requirements.txt
            print_success "وابستگی‌ها نصب شدند"
        else
            print_error "هیچ فایل requirements یافت نشد!"
            exit 1
        fi
    fi
    
    deactivate
}

# تنظیم مسیرها در کد
update_paths() {
    print_info "به‌روزرسانی مسیرها در کد..."
    
    NEW_PATH="$1"
    
    # به‌روزرسانی api_server.py
    if [ -f "api_server.py" ]; then
        sed -i "s|sys.path.insert(0, \"/home/user01/qwen-api/enhanced_rag_system_dev\")|sys.path.insert(0, \"$NEW_PATH\")|g" api_server.py
        print_success "api_server.py به‌روزرسانی شد"
    fi
    
    # به‌روزرسانی config/settings.py
    if [ -f "config/settings.py" ]; then
        sed -i "s|chroma_db_path: str = \"/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db\"|chroma_db_path: str = \"$NEW_PATH/chroma_db\"|g" config/settings.py
        print_success "config/settings.py به‌روزرسانی شد"
    fi
    
    # به‌روزرسانی core/refactored_rag_system.py
    if [ -f "core/refactored_rag_system.py" ]; then
        sed -i "s|db_path: str = \"/home/user01/qwen-api/enhanced_rag_system_dev/chroma_db\"|db_path: str = \"$NEW_PATH/chroma_db\"|g" core/refactored_rag_system.py
        print_success "core/refactored_rag_system.py به‌روزرسانی شد"
    fi
}

# ایجاد دایرکتوری‌های لازم
create_directories() {
    print_info "ایجاد دایرکتوری‌های لازم..."
    
    mkdir -p chroma_db
    mkdir -p logs
    mkdir -p models
    mkdir -p memory
    mkdir -p .entity_cache
    mkdir -p .entity_learning
    
    chmod -R 755 chroma_db logs models memory
    
    print_success "دایرکتوری‌ها ایجاد شدند"
}

# تست import
test_import() {
    print_info "تست import ماژول‌ها..."
    
    source $VENV_NAME/bin/activate
    
    python3 << 'PYEOF'
import sys
sys.path.insert(0, '.')

try:
    from core.refactored_rag_system import RefactoredRAGSystem
    print("✅ RefactoredRAGSystem import موفق بود")
except Exception as e:
    print(f"❌ خطا در import: {e}")
    sys.exit(1)
PYEOF

    if [ $? -eq 0 ]; then
        print_success "تست import موفق بود"
    else
        print_error "تست import ناموفق بود"
        exit 1
    fi
    
    deactivate
}

# نمایش خلاصه
show_summary() {
    print_info "خلاصه نصب:"
    echo ""
    echo "📁 مسیر پروژه: $(pwd)"
    echo "🐍 Python: $($PYTHON_VERSION --version)"
    echo "📦 Virtual Environment: $VENV_NAME/"
    echo "💾 ChromaDB: chroma_db/"
    echo ""
    print_success "نصب با موفقیت انجام شد!"
    echo ""
    echo "مراحل بعدی:"
    echo "1. انتقال ChromaDB از سرور development"
    echo "2. تنظیم متغیرهای محیطی (.env)"
    echo "3. راه‌اندازی API server: python3 api_server.py"
}

# تابع اصلی
main() {
    echo "🚀 اسکریپت انتقال به Production"
    echo "=================================="
    echo ""
    
    # بررسی اینکه در دایرکتوری درست هستیم
    if [ ! -f "api_server.py" ]; then
        print_error "فایل api_server.py یافت نشد!"
        print_info "لطفاً در دایرکتوری پروژه اجرا کنید"
        exit 1
    fi
    
    # دریافت مسیر جدید (اختیاری)
    if [ -z "$1" ]; then
        NEW_PATH=$(pwd)
        print_info "استفاده از مسیر فعلی: $NEW_PATH"
    else
        NEW_PATH="$1"
        print_info "استفاده از مسیر: $NEW_PATH"
    fi
    
    # اجرای مراحل
    check_prerequisites
    create_essential_files_list
    install_dependencies
    update_paths "$NEW_PATH"
    create_directories
    test_import
    show_summary
}

# اجرای تابع اصلی
main "$@"


