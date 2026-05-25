#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Dynamic Extractor - تست استخراج‌کننده داینامیک
"""

import sys
sys.path.insert(0, '/home/user01/qwen-api/enhanced_rag_system')

from processors.dynamic_title_extractor import DynamicTitleExtractor

def test_dynamic_extractor():
    """تست استخراج داینامیک"""
    
    print("🔍 تست استخراج داینامیک عناوین از PDF...")
    print("="*80)
    
    pdf_path = '/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf'
    
    extractor = DynamicTitleExtractor(pdf_path)
    
    # چاپ ساختار کامل
    extractor.print_structure()
    
    # تست کدهای خاص
    print("\n" + "="*80)
    print("🧪 تست کدهای خاص:")
    print("="*80)
    
    test_codes = [
        ('100000', 'قسمت اول: درآمدها'),
        ('110000', 'بخش اول: درآمدهای مالیاتی'),
        ('110100', 'بند اول: مالیات اشخاص حقوقی'),
        ('110200', 'بند دوم: مالیات بر درآمدها'),
        ('110300', 'بند سوم: مالیات بر ثروت'),
        ('110400', 'بند چهارم: مالیات بر واردات'),
        ('110500', 'بند پنجم: مالیات بر کالاها و خدمات'),
        ('120000', 'بخش دوم: درآمدهای ناشی از کمک‌های اجتماعی'),
        ('120100', 'بند اول: حق بیمه'),
        ('130000', 'بخش سوم: درآمدهای حاصل از مالکیت'),
        ('140000', 'بخش چهارم: درآمدهای حاصل از فروش'),
        ('150000', 'بخش پنجم: درآمدهای حاصل از جرایم'),
        ('160000', 'بخش ششم: درآمدهای متفرقه'),
    ]
    
    success_count = 0
    total_count = len(test_codes)
    
    for code, expected_keywords in test_codes:
        title = extractor.get_title(code)
        
        if title:
            print(f"\n✅ {code}: {title}")
            success_count += 1
        else:
            print(f"\n❌ {code}: عنوان پیدا نشد!")
    
    print("\n" + "="*80)
    print(f"📊 نتیجه: {success_count}/{total_count} عنوان با موفقیت استخراج شد")
    print("="*80)

if __name__ == "__main__":
    test_dynamic_extractor()
