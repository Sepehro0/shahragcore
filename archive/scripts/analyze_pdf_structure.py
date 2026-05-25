#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze PDF Structure - تحلیل دقیق ساختار PDF
"""

import sys
sys.path.insert(0, '/home/user01/qwen-api/enhanced_rag_system')

import pdfplumber
import re
import unicodedata
from typing import List, Dict, Any

def normalize_persian_text(text: str) -> str:
    """تبدیل کاراکترهای presentation form به فارسی استاندارد"""
    if not text:
        return ""
    
    normalized = unicodedata.normalize('NFKC', text)
    
    arabic_to_persian = {
        'ي': 'ی', 'ك': 'ک', 'ﻱ': 'ی', 'ﻙ': 'ک',
        'ﺍ': 'ا', 'ﺏ': 'ب', 'ﺕ': 'ت', 'ﺙ': 'ث',
        'ﺝ': 'ج', 'ﺡ': 'ح', 'ﺥ': 'خ', 'ﺩ': 'د',
        'ﺫ': 'ذ', 'ﺭ': 'ر', 'ﺯ': 'ز', 'ﺱ': 'س',
        'ﺵ': 'ش', 'ﺹ': 'ص', 'ﺽ': 'ض', 'ﻁ': 'ط',
        'ﻅ': 'ظ', 'ﻉ': 'ع', 'ﻍ': 'غ', 'ﻑ': 'ف',
        'ﻕ': 'ق', 'ﻝ': 'ل', 'ﻡ': 'م', 'ﻥ': 'ن',
        'ﻩ': 'ه', 'ﻭ': 'و'
    }
    
    result = []
    for char in normalized:
        result.append(arabic_to_persian.get(char, char))
    
    return ''.join(result)

def fix_rtl_text(text: str) -> str:
    """رفع مشکل RTL"""
    if not text or not isinstance(text, str):
        return ""
    
    try:
        normalized = normalize_persian_text(text)
        
        parts = []
        for part in re.split(r'(\s*[|،,:]\s*)', normalized):
            if part.strip() and not re.match(r'^\s*[|،,:]\s*$', part):
                words = part.split()
                reversed_words = []
                for word in words:
                    if re.match(r'^[\d,\.]+$', word):
                        reversed_words.append(word)
                    else:
                        reversed_words.append(word[::-1])
                reversed_words = reversed_words[::-1]
                parts.append(' '.join(reversed_words))
            else:
                parts.append(part)
        
        return ''.join(parts)
    except Exception as e:
        print(f"RTL fix failed: {e}")
        return text

def analyze_pdf_detailed():
    """تحلیل دقیق ساختار PDF"""
    
    print("🔍 تحلیل دقیق ساختار PDF...")
    print("="*80)
    
    pdf_path = '/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf'
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"📄 تعداد کل صفحات: {len(pdf.pages)}\n")
        
        # بررسی صفحه اول با جزئیات کامل
        page = pdf.pages[0]
        print("📊 تحلیل صفحه 1 (با جزئیات کامل):")
        print("-"*80)
        
        # استخراج جداول
        tables = page.extract_tables()
        
        if tables:
            print(f"\n✅ تعداد جداول: {len(tables)}")
            
            for table_idx, table in enumerate(tables):
                print(f"\n{'='*80}")
                print(f"📋 جدول {table_idx + 1}:")
                print(f"   - تعداد سطرها: {len(table)}")
                print(f"   - تعداد ستون‌ها: {len(table[0]) if table and table[0] else 0}")
                
                # نمایش header
                if table and len(table) > 0:
                    print(f"\n   🔍 Header جدول:")
                    for i in range(min(3, len(table))):
                        print(f"   Row {i}: {table[i]}")
                
                # جستجوی سطرهایی که شامل کدهای 6 رقمی هستند
                print(f"\n   🔍 سطرهای شامل کدهای 6 رقمی:")
                
                for row_idx, row in enumerate(table):
                    if row:
                        # جستجوی کدهای 6 رقمی در تمام سلول‌ها
                        codes_found = []
                        persian_texts = []
                        
                        for col_idx, cell in enumerate(row):
                            if cell:
                                cell_str = str(cell).strip()
                                
                                # کدهای 6 رقمی
                                codes_in_cell = re.findall(r'\b\d{6}\b', cell_str)
                                if codes_in_cell:
                                    codes_found.extend([(col_idx, code) for code in codes_in_cell])
                                
                                # متن فارسی
                                if re.search(r'[\u0600-\u06FF]', cell_str):
                                    fixed = fix_rtl_text(cell_str)
                                    if len(fixed) > 10:
                                        persian_texts.append((col_idx, fixed[:100]))
                        
                        if codes_found:
                            print(f"\n   Row {row_idx}:")
                            print(f"      کدها: {codes_found}")
                            if persian_texts:
                                print(f"      متن‌های فارسی:")
                                for col, text in persian_texts:
                                    print(f"        Col {col}: {text}")
                            
                            # نمایش کل سطر
                            print(f"      کل سطر: {row}")

def find_section_headers():
    """یافتن header های بخش‌ها"""
    
    print("\n\n" + "="*80)
    print("🔍 جستجوی header های بخش‌ها (100000، 110000، ...):")
    print("="*80)
    
    pdf_path = '/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf'
    
    target_codes = ['100000', '110000', '120000', '130000', '140000', '150000', '160000',
                    '110100', '110200', '110300', '110400', '110500']
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # جستجو در متن خام
            text = page.extract_text()
            
            for code in target_codes:
                if code in text:
                    print(f"\n✅ پیدا شد: {code} در صفحه {page_num + 1}")
                    
                    # استخراج خطوط اطراف کد
                    lines = text.split('\n')
                    for i, line in enumerate(lines):
                        if code in line:
                            print(f"   خط {i}: {line}")
                            
                            # خطوط اطراف
                            if i > 0:
                                print(f"   خط قبل: {lines[i-1]}")
                            if i < len(lines) - 1:
                                print(f"   خط بعد: {lines[i+1]}")
                            
                            # رفع RTL
                            fixed = fix_rtl_text(line)
                            print(f"   Fixed RTL: {fixed}")

if __name__ == "__main__":
    analyze_pdf_detailed()
    find_section_headers()