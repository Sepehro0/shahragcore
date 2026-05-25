#!/bin/bash
# -*- coding: utf-8 -*-
# اسکریپت نصب وابستگی‌های سیستم
# System Dependencies Installation Script

set -e

# رنگ‌ها
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

# تشخیص سیستم عامل
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
    else
        print_error "نمی‌توان سیستم عامل را تشخیص داد"
        exit 1
    fi
    print_info "سیستم عامل: $OS $VER"
}

# نصب وابستگی‌های Ubuntu/Debian
install_ubuntu_deps() {
    print_info "نصب وابستگی‌های Ubuntu/Debian..."
    
    sudo apt-get update
    sudo apt-get install -y \
        build-essential \
        python3-dev \
        python3-pip \
        python3-venv \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 \
        ghostscript \
        poppler-utils \
        curl \
        git \
        wget
    
    print_success "وابستگی‌های Ubuntu/Debian نصب شدند"
}

# نصب وابستگی‌های CentOS/RHEL
install_centos_deps() {
    print_info "نصب وابستگی‌های CentOS/RHEL..."
    
    sudo yum install -y \
        gcc \
        gcc-c++ \
        python3-devel \
        python3-pip \
        mesa-libGL \
        glib2 \
        libSM \
        libXext \
        libXrender \
        ghostscript \
        poppler-utils \
        curl \
        git \
        wget
    
    print_success "وابستگی‌های CentOS/RHEL نصب شدند"
}

# نصب وابستگی‌های Python
install_python_deps() {
    print_info "نصب وابستگی‌های Python..."
    
    # ایجاد virtual environment
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual environment ایجاد شد"
    fi
    
    # فعال‌سازی
    source venv/bin/activate
    
    # به‌روزرسانی pip
    pip install --upgrade pip setuptools wheel
    
    # نصب وابستگی‌ها
    if [ -f "requirements_api.txt" ]; then
        print_info "نصب از requirements_api.txt..."
        pip install -r requirements_api.txt
    elif [ -f "requirements.txt" ]; then
        print_info "نصب از requirements.txt..."
        pip install -r requirements.txt
    else
        print_error "فایل requirements یافت نشد!"
        exit 1
    fi
    
    deactivate
    print_success "وابستگی‌های Python نصب شدند"
}

# تابع اصلی
main() {
    echo "📦 نصب وابستگی‌های سیستم"
    echo "========================"
    echo ""
    
    detect_os
    
    # نصب وابستگی‌های سیستم
    case $OS in
        ubuntu|debian)
            install_ubuntu_deps
            ;;
        centos|rhel|fedora)
            install_centos_deps
            ;;
        *)
            print_warning "سیستم عامل پشتیبانی نشده، فقط وابستگی‌های Python نصب می‌شوند"
            ;;
    esac
    
    # نصب وابستگی‌های Python
    install_python_deps
    
    echo ""
    print_success "نصب کامل شد!"
    echo ""
    echo "مراحل بعدی:"
    echo "1. فعال‌سازی virtual environment: source venv/bin/activate"
    echo "2. تست import: python3 -c 'from core.refactored_rag_system import RefactoredRAGSystem'"
}

main "$@"


