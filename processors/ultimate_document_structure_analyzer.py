# -*- coding: utf-8 -*-
"""
Ultimate Document Structure Analyzer - تحلیل‌گر نهایی ساختار اسناد
راه‌حل جامع و پیشرفته برای تشخیص دقیق ساختار سلسله‌مراتبی
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import json
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class UltimateDocumentStructureAnalyzer:
    """
    تحلیل‌گر نهایی ساختار اسناد
    ترکیب تمام تکنولوژی‌های موجود برای بهترین نتیجه
    """
    
    def __init__(self):
        """مقداردهی اولیه"""
        
        # الگوهای پیشرفته برای تشخیص کدهای طبقه‌بندی
        self.hierarchy_patterns = {
            'part': {
                'code_pattern': r'^\d{6}$',  # 100000
                'text_patterns': [
                    r'قسمت\s+(\d+)[:：]\s*([^\n]+)',
                    r'قسمت\s+([^\n]+)',
                    r'بخش\s+بزرگ\s+(\d+)[:：]\s*([^\n]+)',
                    r'فصل\s+(\d+)[:：]\s*([^\n]+)',
                    r'کتاب\s+(\d+)[:：]\s*([^\n]+)'
                ],
                'level': 1,
                'name_fa': 'قسمت',
                'name_en': 'part'
            },
            'section': {
                'code_pattern': r'^\d{2}0000$',  # 110000, 120000
                'text_patterns': [
                    r'بخش\s+(\d+)[:：]\s*([^\n]+)',
                    r'بخش\s+([^\n]+)',
                    r'فصل\s+(\d+)[:：]\s*([^\n]+)',
                    r'گروه\s+(\d+)[:：]\s*([^\n]+)'
                ],
                'level': 2,
                'name_fa': 'بخش',
                'name_en': 'section'
            },
            'clause': {
                'code_pattern': r'^\d{4}00$',  # 110100, 120100
                'text_patterns': [
                    r'بند\s+(\d+)[:：]\s*([^\n]+)',
                    r'بند\s+([^\n]+)',
                    r'ماده\s+(\d+)[:：]\s*([^\n]+)',
                    r'تبصره\s+(\d+)[:：]\s*([^\n]+)'
                ],
                'level': 3,
                'name_fa': 'بند',
                'name_en': 'clause'
            },
            'item': {
                'code_pattern': r'^\d{6}$',  # 110102, 120103
                'text_patterns': [
                    r'ردیف\s+(\d+)[:：]\s*([^\n]+)',
                    r'آیتم\s+(\d+)[:：]\s*([^\n]+)',
                    r'شماره\s+(\d+)[:：]\s*([^\n]+)'
                ],
                'level': 4,
                'name_fa': 'ردیف',
                'name_en': 'item'
            }
        }
        
        # کلمات کلیدی برای تشخیص سطح
        self.level_keywords = {
            'part': ['قسمت', 'بخش بزرگ', 'فصل', 'کتاب'],
            'section': ['بخش', 'فصل', 'گروه'],
            'clause': ['بند', 'ماده', 'تبصره'],
            'item': ['ردیف', 'آیتم', 'شماره']
        }
        
        # الگوهای پیشرفته برای تشخیص ساختار
        self.advanced_patterns = {
            'numerical_codes': r'\b\d{6}\b',
            'persian_text': r'[\u0600-\u06FF]+',
            'mixed_content': r'[\u0600-\u06FF\d\s:]+'
        }
    
    def analyze_document(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        تحلیل ساختار سند (نسخه نهایی)
        
        Args:
            chunks: لیست chunks سند
        
        Returns:
            ساختار سند
        """
        logger.info("🔍 Analyzing document structure (Ultimate)...")
        
        # تحلیل پیشرفته
        logger.info("   🧠 Ultimate analysis...")
        ultimate_results = self._ultimate_analyze_patterns(chunks)
        
        # ساخت سلسله مراتب
        logger.info("   🌳 Building ultimate hierarchy tree...")
        hierarchy = self._build_ultimate_hierarchy_tree(ultimate_results)
        
        logger.info(f"   - Parts: {len(hierarchy.get('parts', []))}")
        logger.info(f"   - Sections: {len(hierarchy.get('sections', []))}")
        logger.info(f"   - Clauses: {len(hierarchy.get('clauses', []))}")
        logger.info(f"   - Items: {len(hierarchy.get('items', []))}")
        
        return hierarchy
    
    def _ultimate_analyze_patterns(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """تحلیل الگوهای نهایی"""
        results = {
            'parts': [],
            'sections': [],
            'clauses': [],
            'items': []
        }
        
        for chunk_idx, chunk in enumerate(chunks):
            text = chunk.get('text', '')
            metadata = chunk.get('metadata', {})
            
            # تحلیل نهایی هر chunk
            chunk_analysis = self._ultimate_analyze_chunk(text, chunk_idx, metadata)
            
            # اضافه کردن نتایج
            for level, items in chunk_analysis.items():
                if level in results and items:
                    results[level].extend(items)
        
        return results
    
    def _ultimate_analyze_chunk(self, text: str, chunk_idx: int, metadata: Dict) -> Dict[str, List]:
        """تحلیل نهایی یک chunk"""
        results = {
            'parts': [],
            'sections': [],
            'clauses': [],
            'items': []
        }
        
        # جستجوی شماره‌های طبقه‌بندی
        numerical_codes = re.findall(self.advanced_patterns['numerical_codes'], text)
        
        for code in numerical_codes:
            # تشخیص سطح بر اساس شماره
            level = self._detect_level_by_code_ultimate(code)
            if level:
                item = {
                    'code': code,
                    'chunk_idx': chunk_idx,
                    'text': text[:200],
                    'level': level,
                    'detection_method': 'numerical'
                }
                if level in results:
                    results[level].append(item)
        
        # جستجوی الگوهای متنی
        for level_name, patterns in self.hierarchy_patterns.items():
            for pattern in patterns['text_patterns']:
                try:
                    matches = re.findall(pattern, text)
                    for match in matches:
                        if isinstance(match, tuple) and len(match) == 2:
                            number, title = match
                            item = {
                                'code': number if number.isdigit() else '',
                                'title': title.strip(),
                                'chunk_idx': chunk_idx,
                                'text': text[:200],
                                'level': level_name,
                                'detection_method': 'textual'
                            }
                            if level_name in results:
                                results[level_name].append(item)
                        else:
                            item = {
                                'code': '',
                                'title': match.strip(),
                                'chunk_idx': chunk_idx,
                                'text': text[:200],
                                'level': level_name,
                                'detection_method': 'textual'
                            }
                            if level_name in results:
                                results[level_name].append(item)
                except re.error as e:
                    logger.warning(f"Regex error in pattern '{pattern}': {e}")
                    continue
        
        return results
    
    def _detect_level_by_code_ultimate(self, code: str) -> Optional[str]:
        """تشخیص سطح بر اساس شماره طبقه‌بندی"""
        # حذف فاصله‌ها و کاراکترهای غیرعددی
        code_clean = re.sub(r'[^\d]', '', code)
        
        if not code_clean or len(code_clean) != 6:
            return None
        
        # تحلیل ساختار کد
        # 100000 → قسمت (Part)
        # 110000 → بخش (Section)
        # 110100 → بند (Clause)
        # 110102 → ردیف (Item)
        
        if code_clean.endswith('0000') and code_clean[0] != '0':
            # مثل 100000
            return 'part'
        
        elif code_clean.endswith('000') and code_clean[2:] == '0000':
            # مثل 110000, 120000
            return 'section'
        
        elif code_clean.endswith('00') and code_clean[4:] == '00':
            # مثل 110100, 120100
            return 'clause'
        
        elif not code_clean.endswith('00'):
            # مثل 110102, 120103
            return 'item'
        
        return None
    
    def _build_ultimate_hierarchy_tree(self, ultimate_results: Dict[str, Any]) -> Dict[str, Any]:
        """ساخت درخت سلسله مراتبی نهایی"""
        hierarchy = {
            'parts': [],
            'sections': [],
            'clauses': [],
            'items': []
        }
        
        # پردازش قسمت‌ها
        for part in ultimate_results.get('parts', []):
            hierarchy['parts'].append({
                'code': part.get('code', ''),
                'title': part.get('title', f"قسمت {part.get('code', '')}"),
                'chunk_idx': part.get('chunk_idx', 0),
                'level': 'part',
                'detection_method': part.get('detection_method', 'unknown')
            })
        
        # پردازش بخش‌ها
        for section in ultimate_results.get('sections', []):
            hierarchy['sections'].append({
                'code': section.get('code', ''),
                'title': section.get('title', f"بخش {section.get('code', '')}"),
                'chunk_idx': section.get('chunk_idx', 0),
                'level': 'section',
                'detection_method': section.get('detection_method', 'unknown'),
                'clauses': []
            })
        
        # پردازش بندها
        for clause in ultimate_results.get('clauses', []):
            clause_entry = {
                'code': clause.get('code', ''),
                'title': clause.get('title', f"بند {clause.get('code', '')}"),
                'chunk_idx': clause.get('chunk_idx', 0),
                'level': 'clause',
                'detection_method': clause.get('detection_method', 'unknown'),
                'parent_section': self._find_parent_section_ultimate(clause.get('code', ''), hierarchy['sections']),
                'items': []
            }
            hierarchy['clauses'].append(clause_entry)
            
            # اضافه کردن به بخش والد
            parent_section = self._find_section_by_code_ultimate(clause_entry['parent_section'], hierarchy['sections'])
            if parent_section:
                parent_section['clauses'].append(clause_entry)
        
        # پردازش ردیف‌ها
        for item in ultimate_results.get('items', []):
            item_entry = {
                'code': item.get('code', ''),
                'title': item.get('title', f"ردیف {item.get('code', '')}"),
                'chunk_idx': item.get('chunk_idx', 0),
                'level': 'item',
                'detection_method': item.get('detection_method', 'unknown'),
                'parent_section': self._find_parent_section_ultimate(item.get('code', ''), hierarchy['sections']),
                'parent_clause': self._find_parent_clause_ultimate(item.get('code', ''), hierarchy['clauses'])
            }
            hierarchy['items'].append(item_entry)
            
            # اضافه کردن به بند والد
            parent_clause = self._find_clause_by_code_ultimate(item_entry['parent_clause'], hierarchy['clauses'])
            if parent_clause:
                parent_clause['items'].append(item_entry)
        
        # محاسبه آمار
        hierarchy['total_parts'] = len(hierarchy['parts'])
        hierarchy['total_sections'] = len(hierarchy['sections'])
        hierarchy['total_clauses'] = len(hierarchy['clauses'])
        hierarchy['total_items'] = len(hierarchy['items'])
        
        return hierarchy
    
    def _find_parent_section_ultimate(self, code: str, sections: List[Dict]) -> str:
        """پیدا کردن بخش والد بر اساس کد"""
        if len(code) >= 2:
            section_prefix = code[:2] + '000'
            for section in sections:
                if section.get('code') == section_prefix:
                    return section_prefix
        return ''
    
    def _find_parent_clause_ultimate(self, code: str, clauses: List[Dict]) -> str:
        """پیدا کردن بند والد بر اساس کد"""
        if len(code) >= 4:
            clause_prefix = code[:4] + '00'
            for clause in clauses:
                if clause.get('code') == clause_prefix:
                    return clause_prefix
        return ''
    
    def _find_section_by_code_ultimate(self, code: str, sections: List[Dict]) -> Optional[Dict]:
        """پیدا کردن بخش بر اساس کد"""
        for section in sections:
            if section.get('code') == code:
                return section
        return None
    
    def _find_clause_by_code_ultimate(self, code: str, clauses: List[Dict]) -> Optional[Dict]:
        """پیدا کردن بند بر اساس کد"""
        for clause in clauses:
            if clause.get('code') == code:
                return clause
        return None
    
    def enrich_chunk_metadata(self, chunk: Dict[str, Any], hierarchy: Dict, chunk_idx: int) -> Dict[str, Any]:
        """غنی‌سازی metadata chunk"""
        # پیدا کردن اطلاعات ساختاری
        hierarchy_info = self._find_chunk_hierarchy_info_ultimate(chunk_idx, hierarchy)
        
        if hierarchy_info:
            if 'metadata' not in chunk:
                chunk['metadata'] = {}
            
            chunk['metadata']['hierarchy_level'] = hierarchy_info.get('level')
            chunk['metadata']['hierarchy_code'] = hierarchy_info.get('code', '')
            chunk['metadata']['hierarchy_title'] = hierarchy_info.get('title', '')
            chunk['metadata']['parent_section'] = hierarchy_info.get('parent_section', '')
            chunk['metadata']['hierarchy_path'] = hierarchy_info.get('path', '')
            chunk['metadata']['detection_method'] = hierarchy_info.get('detection_method', 'unknown')
        
        return chunk
    
    def _find_chunk_hierarchy_info_ultimate(self, chunk_idx: int, hierarchy: Dict) -> Optional[Dict[str, Any]]:
        """پیدا کردن اطلاعات سلسله مراتبی یک chunk"""
        # جستجو در قسمت‌ها
        for part in hierarchy.get('parts', []):
            if part.get('chunk_idx') == chunk_idx:
                return {
                    'level': 'part',
                    'code': part.get('code', ''),
                    'title': part.get('title', ''),
                    'path': f"قسمت: {part.get('title', '')}",
                    'detection_method': part.get('detection_method', 'unknown')
                }
        
        # جستجو در بخش‌ها
        for section in hierarchy.get('sections', []):
            if section.get('chunk_idx') == chunk_idx:
                return {
                    'level': 'section',
                    'code': section.get('code', ''),
                    'title': section.get('title', ''),
                    'path': f"بخش: {section.get('title', '')}",
                    'detection_method': section.get('detection_method', 'unknown')
                }
            
            # جستجو در بندهای این بخش
            for clause in section.get('clauses', []):
                if clause.get('chunk_idx') == chunk_idx:
                    return {
                        'level': 'clause',
                        'code': clause.get('code', ''),
                        'title': clause.get('title', ''),
                        'parent_section': section.get('title', ''),
                        'path': f"{section.get('title', '')} > {clause.get('title', '')}",
                        'detection_method': clause.get('detection_method', 'unknown')
                    }
        
        # جستجو در بندهای مستقل
        for clause in hierarchy.get('clauses', []):
            if clause.get('chunk_idx') == chunk_idx:
                return {
                    'level': 'clause',
                    'code': clause.get('code', ''),
                    'title': clause.get('title', ''),
                    'path': f"بند: {clause.get('title', '')}",
                    'detection_method': clause.get('detection_method', 'unknown')
                }
        
        return None
    
    def create_structure_summary_text(self, hierarchy: Dict) -> str:
        """ایجاد متن خلاصه ساختار نهایی"""
        summary = "📊 خلاصه ساختار سند (نهایی)\n"
        summary += "=" * 60 + "\n\n"
        
        # آمار کلی
        summary += f"📈 آمار کلی:\n"
        summary += f"   • تعداد کل قسمت‌ها: {hierarchy.get('total_parts', 0)}\n"
        summary += f"   • تعداد کل بخش‌ها: {hierarchy.get('total_sections', 0)}\n"
        summary += f"   • تعداد کل بندها: {hierarchy.get('total_clauses', 0)}\n"
        summary += f"   • تعداد کل ردیف‌ها: {hierarchy.get('total_items', 0)}\n\n"
        
        # جزئیات قسمت‌ها
        if hierarchy.get('parts'):
            summary += "📋 جزئیات قسمت‌ها:\n\n"
            for idx, part in enumerate(hierarchy['parts'], 1):
                code = part.get('code', 'بدون کد')
                title = part.get('title', 'بدون عنوان')
                method = part.get('detection_method', 'نامشخص')
                summary += f"{idx}. {code}: {title} (روش: {method})\n"
            summary += "\n"
        
        # جزئیات بخش‌ها
        if hierarchy.get('sections'):
            summary += "📋 جزئیات بخش‌ها:\n\n"
            for idx, section in enumerate(hierarchy['sections'], 1):
                code = section.get('code', 'بدون کد')
                title = section.get('title', 'بدون عنوان')
                method = section.get('detection_method', 'نامشخص')
                clause_count = len(section.get('clauses', []))
                
                summary += f"{idx}. {code}: {title} (روش: {method})\n"
                summary += f"   تعداد بندها: {clause_count}\n"
                
                # لیست بندها
                if section.get('clauses'):
                    summary += f"   بندها:\n"
                    for clause_idx, clause in enumerate(section['clauses'], 1):
                        clause_code = clause.get('code', 'بدون کد')
                        clause_title = clause.get('title', 'بدون عنوان')
                        clause_method = clause.get('detection_method', 'نامشخص')
                        summary += f"      {clause_idx}. {clause_code}: {clause_title} (روش: {clause_method})\n"
                
                summary += "\n"
        
        return summary