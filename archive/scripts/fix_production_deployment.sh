#!/bin/bash
# -*- coding: utf-8 -*-
# اسکریپت رفع مشکل deployment روی سرور Production
# Fix Production Deployment Issues

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# بررسی اینکه در دایرکتوری درست هستیم
if [ ! -f "api_server.py" ]; then
    print_error "لطفاً در دایرکتوری enhanced_rag_system_dev اجرا کنید"
    exit 1
fi

print_info "رفع مشکلات deployment..."

# 1. ایجاد دایرکتوری‌های لازم با دسترسی مناسب
print_info "ایجاد دایرکتوری‌های لازم..."
mkdir -p chroma_db chroma_db_ultimate logs models memory .entity_cache .entity_learning
chmod -R 755 chroma_db chroma_db_ultimate logs models memory .entity_cache .entity_learning
print_success "دایرکتوری‌ها ایجاد شدند"

# 2. استخراج مجدد chroma_db با دسترسی مناسب
if [ -f "/tmp/chroma_db.tar.gz" ]; then
    print_info "استخراج chroma_db..."
    # حذف محتوای قبلی (اگر وجود دارد)
    rm -rf chroma_db/*
    # استخراج با دسترسی مناسب
    tar -xzf /tmp/chroma_db.tar.gz --no-same-owner --no-same-permissions 2>/dev/null || \
    tar -xzf /tmp/chroma_db.tar.gz
    chmod -R 755 chroma_db
    print_success "chroma_db استخراج شد"
else
    print_warning "فایل /tmp/chroma_db.tar.gz یافت نشد"
fi

# 3. اگر chroma_db_ultimate در rag_system.tar.gz وجود دارد، آن را هم استخراج کنیم
if [ -f "/tmp/rag_system.tar.gz" ]; then
    print_info "بررسی محتوای rag_system.tar.gz..."
    if tar -tzf /tmp/rag_system.tar.gz | grep -q "^\./chroma_db_ultimate"; then
        print_warning "chroma_db_ultimate در rag_system.tar.gz یافت شد"
        print_info "استخراج chroma_db_ultimate..."
        mkdir -p chroma_db_ultimate
        tar -xzf /tmp/rag_system.tar.gz --no-same-owner --no-same-permissions \
            --wildcards "./chroma_db_ultimate/*" 2>/dev/null || \
        tar -xzf /tmp/rag_system.tar.gz "./chroma_db_ultimate" 2>/dev/null || true
        chmod -R 755 chroma_db_ultimate 2>/dev/null || true
        print_success "chroma_db_ultimate استخراج شد"
    fi
fi

# 4. بررسی اینکه کدام دایرکتوری استفاده می‌شود
print_info "بررسی تنظیمات..."
if [ -d "chroma_db" ] && [ "$(ls -A chroma_db 2>/dev/null)" ]; then
    print_success "chroma_db موجود و دارای محتوا است"
    USE_DB="chroma_db"
elif [ -d "chroma_db_ultimate" ] && [ "$(ls -A chroma_db_ultimate 2>/dev/null)" ]; then
    print_warning "فقط chroma_db_ultimate موجود است"
    USE_DB="chroma_db_ultimate"
    # ایجاد symlink یا کپی
    if [ ! -d "chroma_db" ] || [ -z "$(ls -A chroma_db 2>/dev/null)" ]; then
        print_info "ایجاد symlink از chroma_db به chroma_db_ultimate..."
        rm -rf chroma_db
        ln -s chroma_db_ultimate chroma_db
        print_success "symlink ایجاد شد"
    fi
else
    print_error "هیچ دایرکتوری ChromaDB یافت نشد!"
    exit 1
fi

print_success "مشکلات برطرف شد!"
echo ""
echo "دایرکتوری استفاده شده: $USE_DB"
echo "مراحل بعدی:"
echo "1. اجرای: ./deploy_to_production.sh"
echo "2. یا ادامه با نصب دستی وابستگی‌ها"


