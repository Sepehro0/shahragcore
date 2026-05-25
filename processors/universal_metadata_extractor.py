# -*- coding: utf-8 -*-
"""
Universal Metadata Extractor
استخراج پویا metadata از هر نوع سند
"""

import re
import logging
from typing import Dict, Any, List, Optional
from collections import Counter

logger = logging.getLogger(__name__)


class UniversalMetadataExtractor:
    """
    استخراج‌کننده Universal metadata
    به صورت پویا از هر نوع سند
    """
    
    def __init__(self):
        # الگوهای شناخته شده برای metadata
        self.metadata_patterns = {
            'title': [
                r'عنوان\s*:?\s*(.+?)(?:\n|$)',
                r'Title\s*:?\s*(.+?)(?:\n|$)',
                r'Subject\s*:?\s*(.+?)(?:\n|$)',
                r'موضوع\s*:?\s*(.+?)(?:\n|$)',
                r'\[L1\]عنوان:\s*(.+?)(?:\[L|$)',  # مخصوص جداول ساختاریافته
            ],
            'author': [
                r'نویسنده\s*:?\s*(.+?)(?:\n|$)',
                r'Author\s*:?\s*(.+?)(?:\n|$)',
                r'مولف\s*:?\s*(.+?)(?:\n|$)',
            ],
            'date': [
                r'تاریخ\s*:?\s*(\d{4}[/-]\d{2}[/-]\d{2})',
                r'Date\s*:?\s*(\d{4}[/-]\d{2}[/-]\d{2})',
            ],
            'number': [
                r'شماره\s*:?\s*(\d+)',
                r'Number\s*:?\s*(\d+)',
                r'کد\s*:?\s*(\d+)',
                r'Code\s*:?\s*(\d+)',
                r'ID\s*:?\s*(\d+)',
            ],
            'reference': [
                r'مرجع\s*:?\s*(.+?)(?:\n|$)',
                r'Reference\s*:?\s*(.+?)(?:\n|$)',
                r'Ref\s*:?\s*(.+?)(?:\n|$)',
            ],
            'category': [
                r'دسته[\s\u200c]*بندی\s*:?\s*(.+?)(?:\n|$)',
                r'Category\s*:?\s*(.+?)(?:\n|$)',
                r'طبقه[\s\u200c]*بندی\s*:?\s*(.+?)(?:\n|$)',
                r'Classification\s*:?\s*(.+?)(?:\n|$)',
            ],
            'version': [
                r'نسخه\s*:?\s*(.+?)(?:\n|$)',
                r'Version\s*:?\s*(.+?)(?:\n|$)',
                r'v\.?\s*(\d+(?:\.\d+)*)',
            ],
            'page': [
                r'صفحه\s*:?\s*(\d+)',
                r'Page\s*:?\s*(\d+)',
            ],
        }
    
    def extract_metadata(self, text: str, existing_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        استخراج metadata از متن به صورت پویا
        
        Args:
            text: متن سند
            existing_metadata: metadata موجود (از PDF، DOCX، و غیره)
        
        Returns:
            Dictionary کامل metadata
        """
        metadata = existing_metadata.copy() if existing_metadata else {}
        
        # استخراج metadata از text
        for field_name, patterns in self.metadata_patterns.items():
            if field_name not in metadata or not metadata[field_name]:
                for pattern in patterns:
                    match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        if value:
                            metadata[field_name] = value
                            break
        
        # استخراج اعداد به صورت خودکار
        metadata['numeric_ids'] = self._extract_numeric_ids(text)
        
        # استخراج dominant pattern
        metadata['dominant_pattern'] = self._detect_dominant_pattern(text)
        
        # تشخیص زبان
        metadata['language'] = self._detect_language(text)
        
        # تشخیص نوع محتوا
        metadata['content_type'] = self._detect_content_type(text)
        
        return metadata
    
    def _extract_numeric_ids(self, text: str) -> Dict[str, List[str]]:
        """استخراج همه اعداد به صورت ساختاریافته"""
        result = {}
        
        # اعداد 3 تا 8 رقمی
        for length in range(3, 9):
            pattern = rf'\b\d{{{length}}}\b'
            matches = re.findall(pattern, text)
            if matches:
                result[f'{length}_digit'] = list(set(matches))
        
        return result
    
    def _detect_dominant_pattern(self, text: str) -> Optional[str]:
        """تشخیص الگوی غالب اعداد در متن"""
        # شمارش تعداد اعداد با طول‌های مختلف
        length_counts = Counter()
        
        for length in range(3, 9):
            pattern = rf'\b\d{{{length}}}\b'
            matches = re.findall(pattern, text)
            length_counts[length] = len(matches)
        
        # پیدا کردن غالب‌ترین
        if length_counts:
            dominant_length = length_counts.most_common(1)[0][0]
            return f'{dominant_length}_digit'
        
        return None
    
    def _detect_language(self, text: str) -> str:
        """تشخیص زبان متن"""
        # شمارش کاراکترهای فارسی
        persian_chars = len(re.findall(r'[\u0600-\u06FF]', text))
        
        # شمارش کاراکترهای لاتین
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        
        total = persian_chars + english_chars
        if total == 0:
            return 'unknown'
        
        persian_ratio = persian_chars / total
        
        if persian_ratio > 0.5:
            return 'persian'
        elif persian_ratio > 0.1:
            return 'mixed'
        else:
            return 'english'
    
    def _detect_content_type(self, text: str) -> str:
        """تشخیص نوع محتوا"""
        # شمارش جداول
        table_indicators = len(re.findall(r'\|.*\|', text))
        
        # شمارش لیست‌ها
        list_indicators = len(re.findall(r'^\s*[\-\*\d\.]\s+', text, re.MULTILINE))
        
        # شمارش عناوین
        heading_indicators = len(re.findall(r'^#+\s+', text, re.MULTILINE))
        
        # تشخیص
        if table_indicators > 10:
            return 'tabular'
        elif list_indicators > 10:
            return 'list_based'
        elif heading_indicators > 5:
            return 'structured_document'
        else:
            return 'plain_text'
    
    def extract_from_chunk_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        استخراج metadata از metadata موجود chunk
        به صورت پویا و intelligent
        """
        extracted = {}
        
        for key, value in metadata.items():
            key_lower = key.lower()
            
            # تشخیص نوع field بر اساس key
            if any(x in key_lower for x in ['title', 'عنوان', 'subject', 'موضوع']):
                extracted['title'] = value
            
            elif any(x in key_lower for x in ['number', 'شماره', 'code', 'کد', 'id']):
                extracted['number'] = str(value)
                
                # اگر عدد است، تشخیص طول
                if isinstance(value, (int, str)) and str(value).isdigit():
                    length = len(str(value))
                    extracted['number_length'] = length
                    extracted['number_type'] = f'{length}_digit'
            
            elif any(x in key_lower for x in ['page', 'صفحه']):
                extracted['page'] = value
            
            elif any(x in key_lower for x in ['author', 'نویسنده']):
                extracted['author'] = value
            
            elif any(x in key_lower for x in ['date', 'تاریخ']):
                extracted['date'] = value
            
            elif any(x in key_lower for x in ['category', 'دسته', 'طبقه', 'classification']):
                extracted['category'] = value
        
        return extracted
    
    def build_search_keywords(self, metadata: Dict[str, Any]) -> List[str]:
        """
        ساخت کلیدواژه‌های جستجو از metadata
        """
        keywords = []
        
        # اضافه کردن title
        if 'title' in metadata:
            keywords.append(metadata['title'])
        
        # اضافه کردن numbers
        if 'number' in metadata:
            keywords.append(str(metadata['number']))
        
        # اضافه کردن numeric_ids
        if 'numeric_ids' in metadata:
            for digit_type, values in metadata['numeric_ids'].items():
                keywords.extend(values[:5])  # محدود به 5 مورد
        
        # اضافه کردن category
        if 'category' in metadata:
            keywords.append(metadata['category'])
        
        return keywords
    
    def merge_metadata(self, *metadata_dicts: Dict[str, Any]) -> Dict[str, Any]:
        """
        ادغام چندین metadata dictionary
        با اولویت بر اساس کیفیت و completeness
        """
        merged = {}
        
        for meta_dict in metadata_dicts:
            for key, value in meta_dict.items():
                # اگر key وجود ندارد یا value بهتری داریم
                if key not in merged or not merged[key]:
                    merged[key] = value
                elif value and len(str(value)) > len(str(merged[key])):
                    # اگر value جدید طولانی‌تر است (احتمالاً کامل‌تر)
                    merged[key] = value
        
        return merged


# Global instance
universal_metadata_extractor = UniversalMetadataExtractor()

