# -*- coding: utf-8 -*-
"""
Table Row Extractor - استخراج‌کننده دقیق ردیف‌های جدول
هر ردیف جدول را با metadata کامل و اعداد دقیق استخراج می‌کند
"""

import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class TableRowExtractor:
    """استخراج‌کننده ردیف‌های جدول با metadata دقیق"""
    
    def __init__(self):
        self.code_pattern = re.compile(r'\b\d{6}\b')
        self.number_pattern = re.compile(r'[\d,]+')
    
    def extract_code_from_text(self, text: str) -> Optional[str]:
        """استخراج کد 6 رقمی از متن"""
        # Look for patterns like "شماره طبقه بندی: 110105" or just "110105"
        codes = self.code_pattern.findall(text)
        return codes[-1] if codes else None  # آخرین کد (که معمولاً کد اصلی است)
    
    def extract_numbers_from_row(self, text: str) -> Dict[str, Any]:
        """استخراج اعداد از یک ردیف جدول"""
        numbers = {}
        
        # الگوهای بهبود یافته - با توجه به ساختار واقعی متن
        # Format: [L2]جمع کل > [L3]جمع کل: 6,656,617,991
        
        # جمع کل اصلی (معمولاً اولین عدد بزرگ)
        jame_kol = re.search(r'\[L3\]جمع کل:\s*([\d,]+)', text)
        if jame_kol:
            try:
                numbers['جمع_کل'] = int(jame_kol.group(1).replace(',', ''))
            except:
                pass
        
        # ملی و استانی در بخش جمع کل
        # Pattern: بعد از جمع کل، استانی و ملی می‌آیند
        parts = text.split('[L2]')
        for part in parts:
            if 'جمع کل' in part:
                melli = re.search(r'\[L3\]ملی:\s*([\d,]+)', part)
                ostani = re.search(r'\[L3\]استانی:\s*([\d,]+)', part)
                if melli:
                    try:
                        numbers['ملی'] = int(melli.group(1).replace(',', ''))
                    except:
                        pass
                if ostani:
                    try:
                        numbers['استانی'] = int(ostani.group(1).replace(',', ''))
                    except:
                        pass
            
            elif 'اختصاصی' in part:
                jame = re.search(r'\[L3\]جمع:\s*([\d,]+)', part)
                melli = re.search(r'\[L3\]ملی:\s*([\d,]+)', part)
                if jame:
                    try:
                        numbers['اختصاصی_جمع'] = int(jame.group(1).replace(',', ''))
                    except:
                        pass
                if melli:
                    try:
                        numbers['اختصاصی_ملی'] = int(melli.group(1).replace(',', ''))
                    except:
                        pass
            
            elif 'عمومی' in part:
                jame = re.search(r'\[L3\]جمع:\s*([\d,]+)', part)
                melli = re.search(r'\[L3\]ملی:\s*([\d,]+)', part)
                if jame:
                    try:
                        numbers['عمومی_جمع'] = int(jame.group(1).replace(',', ''))
                    except:
                        pass
                if melli:
                    try:
                        numbers['عمومی_ملی'] = int(melli.group(1).replace(',', ''))
                    except:
                        pass
        
        return numbers
    
    def split_combined_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        تقسیم chunks ترکیب‌شده به chunks تک‌ردیفی و استخراج اعداد
        
        اگر یک chunk شامل چندین ردیف جدول باشد، آن را به chunks جداگانه تقسیم می‌کند
        برای همه chunks، اعداد را استخراج و به metadata اضافه می‌کند
        """
        separated_chunks = []
        
        for chunk in chunks:
            text = chunk.get('text', '')
            metadata = chunk.get('metadata', {})
            
            # بررسی: آیا این chunk شامل چندین ردیف است؟
            row_markers = re.findall(r'Page \d+, Table \d+, Row \d+', text)
            
            if len(row_markers) <= 1:
                # این chunk تک‌ردیفی است، اما باید اعداد را استخراج کنیم
                enriched_chunk = self._create_single_row_chunk(text, metadata)
                separated_chunks.append(enriched_chunk)
                continue
            
            # این chunk شامل چندین ردیف است، باید تقسیم شود
            logger.info(f"Splitting chunk with {len(row_markers)} rows")
            
            # تقسیم متن بر اساس "Page X, Table Y, Row Z"
            parts = re.split(r'(Page \d+, Table \d+, Row \d+)', text)
            
            current_row_text = ""
            current_row_marker = None
            
            for i, part in enumerate(parts):
                if re.match(r'Page \d+, Table \d+, Row \d+', part):
                    # این یک row marker است
                    if current_row_marker and current_row_text:
                        # ذخیره ردیف قبلی
                        new_chunk = self._create_single_row_chunk(
                            current_row_marker + current_row_text,
                            metadata
                        )
                        separated_chunks.append(new_chunk)
                    
                    current_row_marker = part
                    current_row_text = ""
                else:
                    # این محتوای ردیف است
                    current_row_text += part
            
            # ذخیره آخرین ردیف
            if current_row_marker and current_row_text:
                new_chunk = self._create_single_row_chunk(
                    current_row_marker + current_row_text,
                    metadata
                )
                separated_chunks.append(new_chunk)
        
        logger.info(f"Separated {len(chunks)} chunks into {len(separated_chunks)} chunks")
        return separated_chunks
    
    def _create_single_row_chunk(self, text: str, original_metadata: Dict) -> Dict[str, Any]:
        """ایجاد chunk جدید برای یک ردیف"""
        # استخراج کد از متن
        code = self.extract_code_from_text(text)
        
        # استخراج اعداد از متن
        numbers = self.extract_numbers_from_row(text)
        
        # استخراج عنوان (متن فارسی بعد از "عنوان:")
        title = None
        title_match = re.search(r'عنوان:\s*([^\n\[]+)', text)
        if title_match:
            title = title_match.group(1).strip()
        
        # ساخت metadata جدید
        new_metadata = original_metadata.copy()
        
        if code:
            new_metadata['hierarchy_code'] = code
            new_metadata['row_code'] = code  # کد دقیق این ردیف
        
        if title:
            # اگر عنوان در original_metadata موجود است، از آن استفاده کن (که قبلاً fix شده)
            if 'hierarchy_title' in original_metadata and original_metadata['hierarchy_title']:
                new_metadata['hierarchy_title'] = original_metadata['hierarchy_title']
                new_metadata['row_title'] = original_metadata['hierarchy_title']
            else:
                # اگر عنوان در metadata نیست، از متن استخراج کن
                new_metadata['hierarchy_title'] = title
                new_metadata['row_title'] = title
        
        # اضافه کردن اعداد به metadata
        if numbers:
            new_metadata['row_numbers'] = numbers
            for key, value in numbers.items():
                new_metadata[f'number_{key}'] = str(value)
        
        return {
            'text': text,
            'metadata': new_metadata
        }
    
    def extract_all_codes_with_data(self, chunks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        استخراج تمام کدها با داده‌های مربوطه
        
        Returns:
            دیکشنری با کلید کد و مقدار شامل عنوان و اعداد
        """
        codes_data = {}
        
        for chunk in chunks:
            text = chunk.get('text', '')
            metadata = chunk.get('metadata', {})
            
            code = metadata.get('row_code') or metadata.get('hierarchy_code')
            
            if code:
                # استخراج داده‌های این کد
                title = metadata.get('row_title') or metadata.get('hierarchy_title')
                numbers = metadata.get('row_numbers', {})
                
                codes_data[code] = {
                    'title': title,
                    'numbers': numbers,
                    'text': text[:500],  # پیش‌نمایش متن
                    'metadata': metadata
                }
        
        return codes_data


# تست
if __name__ == "__main__":
    extractor = TableRowExtractor()
    
    # تست استخراج کد
    test_text = "Page 1, Table 1, Row 10   برآورد 1404 > جمع کل: 6,656,617,991   ملی: 323,097,991   عنوان: مالیات اشخاص حقوقی غیر دولتی   شماره طبقه بندی: 110105"
    
    code = extractor.extract_code_from_text(test_text)
    print(f"Code: {code}")
    
    numbers = extractor.extract_numbers_from_row(test_text)
    print(f"Numbers: {numbers}")

