# -*- coding: utf-8 -*-
"""
Document Structure Analyzer - تحلیل‌گر هوشمند ساختار اسناد
تشخیص ساختار سلسله مراتبی: قسمت > بخش > بند > ردیف
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class DocumentStructureAnalyzer:
    """
    تحلیل‌گر هوشمند ساختار اسناد
    - تشخیص کدهای عددی سلسله مراتبی (مثل 110000، 110100)
    - تشخیص عناوین متنی (بخش اول، بند دوم)
    - ساخت درخت سلسله مراتبی
    - غنی‌سازی metadata با اطلاعات ساختاری
    """
    
    def __init__(self):
        """مقداردهی اولیه"""
        
        # تعریف سطوح سلسله مراتبی
        self.hierarchy_levels = {
            'part': {
                'persian': ['قسمت', 'بخش بزرگ'],
                'code_pattern': r'^\d{2}0000$',  # مثل 110000
                'level': 1,
                'name_fa': 'قسمت',
                'name_en': 'part'
            },
            'section': {
                'persian': ['بخش'],
                'code_pattern': r'^\d{3}000$',  # مثل 110000 یا 111000
                'level': 2,
                'name_fa': 'بخش',
                'name_en': 'section'
            },
            'clause': {
                'persian': ['بند'],
                'code_pattern': r'^\d{4}00$',  # مثل 110100
                'level': 3,
                'name_fa': 'بند',
                'name_en': 'clause'
            },
            'item': {
                'persian': ['ردیف', 'جزء', 'مورد'],
                'code_pattern': r'^\d{5,6}$',  # مثل 110101 یا 110169
                'level': 4,
                'name_fa': 'ردیف',
                'name_en': 'item'
            }
        }
        
        # الگوهای خاص برای کدهای بودجه
        self.budget_code_patterns = {
            'section': [
                r'^11\d{4}$',  # 110000-119999 (بخش درآمدها)
                r'^12\d{4}$',  # 120000-129999 (بخش دیگر)
                r'^13\d{4}$',  # 130000-139999 (بخش دیگر)
                r'^14\d{4}$',  # 140000-149999 (بخش دیگر)
            ],
            'clause': [
                r'^11\d{2}00$',  # 110100, 110200, etc.
                r'^12\d{2}00$',  # 120100, 120200, etc.
                r'^13\d{2}00$',  # 130100, 130200, etc.
                r'^14\d{2}00$',  # 140100, 140200, etc.
            ],
            'item': [
                r'^11\d{3}$',  # 110101, 110102, etc.
                r'^12\d{3}$',  # 120101, 120102, etc.
                r'^13\d{3}$',  # 130101, 130102, etc.
                r'^14\d{3}$',  # 140101, 140102, etc.
            ]
        }
        
        # ساختار سلسله مراتبی واقعی
        self.hierarchy_structure = {
            '110000': {'type': 'section', 'title': 'درآمدهای مالیاتی', 'level': 1},
            '120000': {'type': 'section', 'title': 'درآمدهای غیرمالیاتی', 'level': 1},
            '130000': {'type': 'section', 'title': 'درآمدهای متفرقه', 'level': 1},
            '140000': {'type': 'section', 'title': 'درآمدهای اختصاصی', 'level': 1},
        }
        
        # الگوهای عددی فارسی و انگلیسی
        self.persian_numbers = {
            'اول': 1, 'یکم': 1, 'یک': 1,
            'دوم': 2, 'دو': 2,
            'سوم': 3, 'سه': 3,
            'چهارم': 4, 'چهار': 4,
            'پنجم': 5, 'پنج': 5,
            'ششم': 6, 'شش': 6,
            'هفتم': 7, 'هفت': 7,
            'هشتم': 8, 'هشت': 8,
            'نهم': 9, 'نه': 9,
            'دهم': 10, 'ده': 10
        }
    
    def analyze_document(self, chunks: List[Dict]) -> Dict[str, Any]:
        """
        تحلیل کامل ساختار سند
        
        Args:
            chunks: لیست چانک‌های استخراج شده از سند
        
        Returns:
            دیکشنری حاوی ساختار کامل سند
        """
        logger.info("🔍 Analyzing document structure...")
        
        # 1. تحلیل کدهای عددی
        code_hierarchy = self._analyze_numerical_codes(chunks)
        
        # 2. تحلیل عناوین متنی
        title_hierarchy = self._analyze_text_titles(chunks)
        
        # 3. ترکیب هر دو روش
        final_hierarchy = self._merge_hierarchies(code_hierarchy, title_hierarchy)
        
        # 4. ساخت درخت سلسله مراتبی
        tree = self._build_hierarchy_tree(final_hierarchy)
        
        logger.info(f"✅ Structure analysis complete:")
        logger.info(f"   - Total parts: {tree.get('total_parts', 0)}")
        logger.info(f"   - Total sections: {tree.get('total_sections', 0)}")
        logger.info(f"   - Total clauses: {tree.get('total_clauses', 0)}")
        logger.info(f"   - Total items: {tree.get('total_items', 0)}")
        
        return tree
    
    def _analyze_numerical_codes(self, chunks: List[Dict]) -> Dict[str, Any]:
        """
        تحلیل کدهای عددی سلسله مراتبی
        
        مثال: 110000 (بخش) → 110100 (بند) → 110169 (ردیف)
        """
        logger.info("   🔢 Analyzing numerical codes...")
        
        hierarchy = {
            'parts': [],
            'sections': [],
            'clauses': [],
            'items': []
        }
        
        # استخراج تمام کدها از chunks
        for chunk_idx, chunk in enumerate(chunks):
            text = chunk.get('text', '')
            
            # جستجوی کدهای 6 رقمی (با الگوهای مختلف)
            code_patterns = [
                r'\b(\d{6})\b',  # کدهای 6 رقمی عادی
                r'(\d{6})',      # کدهای 6 رقمی بدون word boundary
                r'(\d{3}\d{3})', # کدهای 6 رقمی با فاصله
            ]
            
            all_codes = set()
            for pattern in code_patterns:
                matches = re.findall(pattern, text)
                all_codes.update(matches)
            
            # همچنین جستجو برای کدهای 5 رقمی که ممکن است بخش باشند
            five_digit_codes = re.findall(r'\b(\d{5})\b', text)
            for code in five_digit_codes:
                # اگر کد 5 رقمی با 000 تمام می‌شود، آن را به 6 رقمی تبدیل کن
                if code.endswith('000'):
                    extended_code = code + '0'  # 11000 -> 110000
                    all_codes.add(extended_code)
            
            for code in all_codes:
                # تشخیص سطح کد
                level_info = self._classify_code(code)
                
                if level_info:
                    # استخراج عنوان مرتبط با کد
                    title = self._extract_title_near_code(text, code)
                    
                    entry = {
                        'code': code,
                        'title': title,
                        'chunk_idx': chunk_idx,
                        'confidence': 'high'
                    }
                    
                    # افزودن به دسته مناسب
                    if level_info['type'] == 'part':
                        hierarchy['parts'].append(entry)
                    elif level_info['type'] == 'section':
                        hierarchy['sections'].append(entry)
                    elif level_info['type'] == 'clause':
                        hierarchy['clauses'].append(entry)
                    elif level_info['type'] == 'item':
                        hierarchy['items'].append(entry)
        
        logger.info(f"      Found: {len(hierarchy['parts'])} parts, {len(hierarchy['sections'])} sections, "
                   f"{len(hierarchy['clauses'])} clauses, {len(hierarchy['items'])} items")
        
        return hierarchy
    
    def _classify_code(self, code: str) -> Optional[Dict[str, Any]]:
        """
        تشخیص سطح یک کد عددی
        
        Args:
            code: کد 6 رقمی (مثل "110000")
        
        Returns:
            {'type': 'section', 'level': 2} یا None
        """
        # ابتدا الگوهای بودجه را چک کن
        for level_name, patterns in self.budget_code_patterns.items():
            for pattern in patterns:
                if re.match(pattern, code):
                    level_config = self.hierarchy_levels[level_name]
                    return {
                        'type': level_name,
                        'level': level_config['level']
                    }
        
        # سپس الگوهای عمومی را چک کن
        for level_name, level_config in self.hierarchy_levels.items():
            pattern = level_config['code_pattern']
            if re.match(pattern, code):
                return {
                    'type': level_name,
                    'level': level_config['level']
                }
        
        return None
    
    def _extract_title_near_code(self, text: str, code: str) -> str:
        """
        استخراج عنوان نزدیک به کد با استفاده از RTL Processor
        """
        try:
            # استفاده از Advanced PDF Table Processor برای RTL fix
            from .advanced_pdf_table_processor import AdvancedPDFTableProcessor
            rtl_processor = AdvancedPDFTableProcessor()
            
            # رفع مشکل RTL
            processed_text = rtl_processor.fix_rtl_text(text)
            
            # اگر RTL processing کار نکرد، از روش ساده استفاده کن
            if not processed_text or processed_text == text:
                processed_text = self._simple_rtl_fix(text)
            
            # جستجوی کد و عنوان در متن پردازش شده
            lines = processed_text.split('\n')
            
            for i, line in enumerate(lines):
                if code in line:
                    # جستجوی عنوان در خطوط اطراف
                    for j in range(max(0, i-2), min(len(lines), i+3)):
                        if j != i:  # خط خود کد را نادیده بگیر
                            title_line = lines[j].strip()
                            
                            # اگر خط شامل کد است، آن را نادیده بگیر
                            if code in title_line:
                                continue
                            
                            # اگر خط خالی است، نادیده بگیر
                            if not title_line:
                                continue
                            
                            # اگر خط فقط عدد است، نادیده بگیر
                            if re.match(r'^[\d,\.\s]+$', title_line):
                                continue
                            
                            # اگر خط خیلی کوتاه است، نادیده بگیر
                            if len(title_line) < 5:
                                continue
                            
                            # پاک‌سازی عنوان
                            title = self._clean_title(title_line)
                            
                            if title and len(title) > 3:
                                return title[:150]
            
            # اگر در خطوط اطراف چیزی پیدا نشد، در کل متن جستجو کن
            return self._search_title_in_text(processed_text, code)
            
        except Exception as e:
            logger.warning(f"RTL processing failed: {e}")
            return self._search_title_in_text(text, code)
    
    def _clean_title(self, title: str) -> str:
        """پاک‌سازی عنوان"""
        if not title:
            return ""
        
        # حذف کاراکترهای غیرضروری
        title = re.sub(r'[^\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF\s\w]', '', title)
        
        # حذف whitespace اضافی
        title = ' '.join(title.split())
        
        # حذف کلمات کوتاه و غیرضروری
        words = title.split()
        cleaned_words = []
        
        for word in words:
            # اگر کلمه خیلی کوتاه است، نادیده بگیر
            if len(word) < 2:
                continue
            
            # اگر کلمه فقط عدد است، نادیده بگیر
            if re.match(r'^\d+$', word):
                continue
            
            # اگر کلمه شامل کاراکترهای غیرفارسی است، نادیده بگیر
            if not re.search(r'[\u0600-\u06FF]', word):
                continue
            
            cleaned_words.append(word)
        
        return ' '.join(cleaned_words)
    
    def _search_title_in_text(self, text: str, code: str) -> str:
        """جستجوی عنوان در متن"""
        # الگوهای مختلف برای جستجوی عنوان
        patterns = [
            # الگوی اصلی: کد + عنوان:
            rf'{code}[^\n]*?عنوان:\s*(.+?)(?:\[L|$|\n)',
            # الگوی RTL: عنوان: + کد
            rf'عنوان:\s*(.+?)\s*{code}',
            # الگوی ساده: کد + متن
            rf'{code}\s+(.+?)(?:\[L|$|\n)',
            # الگوی با فاصله: کد + فاصله + متن
            rf'{code}\s+([^\n]+?)(?:\n|$)',
            # الگوی بدون فاصله: کد + متن
            rf'{code}([^\n]+?)(?:\n|$)',
            # الگوی RTL: متن + کد
            rf'([^\n]+?)\s*{code}',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                title = match.group(1).strip()
                title = self._clean_title(title)
                
                if title and len(title) > 3:
                    return title[:150]
        
        return "عنوان نامشخص"
    
    def _simple_rtl_fix(self, text: str) -> str:
        """رفع ساده مشکل RTL"""
        if not text or not isinstance(text, str):
            return ""
        
        try:
            # تبدیل کاراکترهای presentation form به فارسی استاندارد
            import unicodedata
            normalized = unicodedata.normalize('NFKC', text)
            
            # تبدیل کاراکترهای عربی به فارسی
            arabic_to_persian = {
                'ي': 'ی',  # Arabic Yeh to Persian Yeh
                'ك': 'ک',  # Arabic Kaf to Persian Kaf
                'ﻱ': 'ی',
                'ﻙ': 'ک',
            }
            
            result = []
            for char in normalized:
                result.append(arabic_to_persian.get(char, char))
            
            return ''.join(result)
        except Exception:
            return text
    
    def _analyze_text_titles(self, chunks: List[Dict]) -> Dict[str, Any]:
        """
        تحلیل عناوین متنی (مثل "بخش اول"، "بند دوم")
        """
        logger.info("   📝 Analyzing text titles...")
        
        hierarchy = {
            'parts': [],
            'sections': [],
            'clauses': [],
            'items': []
        }
        
        for chunk_idx, chunk in enumerate(chunks):
            text = chunk.get('text', '')
            
            # جستجو برای هر سطح
            for level_name, level_config in self.hierarchy_levels.items():
                for persian_keyword in level_config['persian']:
                    # الگو: "بخش اول"، "بند دوم" و غیره
                    pattern = rf'{persian_keyword}\s+(\w+)'
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    
                    for match in matches:
                        number_word = match.group(1)
                        number = self.persian_numbers.get(number_word.lower())
                        
                        if number:
                            # استخراج عنوان
                            title = self._extract_title_after_match(text, match.end())
                            
                            entry = {
                                'number': number,
                                'title': title,
                                'chunk_idx': chunk_idx,
                                'confidence': 'medium',
                                'keyword': persian_keyword
                            }
                            
                            # افزودن به دسته مناسب
                            if level_name == 'part':
                                hierarchy['parts'].append(entry)
                            elif level_name == 'section':
                                hierarchy['sections'].append(entry)
                            elif level_name == 'clause':
                                hierarchy['clauses'].append(entry)
                            elif level_name == 'item':
                                hierarchy['items'].append(entry)
        
        return hierarchy
    
    def _extract_title_after_match(self, text: str, start_pos: int) -> str:
        """استخراج عنوان بعد از match"""
        # بگیر تا 100 کاراکتر بعد
        remaining = text[start_pos:start_pos + 100]
        
        # جدا کردن بر اساس newline یا ":"
        parts = re.split(r'[\n:]', remaining, maxsplit=1)
        if parts:
            title = parts[0].strip()
            return title[:100]
        
        return ""
    
    def _merge_hierarchies(self, code_hierarchy: Dict, title_hierarchy: Dict) -> Dict[str, Any]:
        """
        ترکیب نتایج تحلیل کد و عنوان با ساختار سلسله مراتبی درست
        """
        logger.info("   🔄 Merging hierarchies...")
        
        # ساخت ساختار سلسله مراتبی درست
        hierarchy_tree = {
            'sections': [],
            'clauses': [],
            'items': [],
            'total_sections': 0,
            'total_clauses': 0,
            'total_items': 0
        }
        
        # گروه‌بندی کدها بر اساس بخش
        section_groups = {}
        
        # ابتدا بخش‌ها را شناسایی کن
        for item in code_hierarchy.get('sections', []):
            code = item['code']
            section_code = code[:2] + '0000'  # 110100 -> 110000
            
            if section_code not in section_groups:
                section_groups[section_code] = {
                    'section': {
                        'code': section_code,
                        'title': self.hierarchy_structure.get(section_code, {}).get('title', 'بخش نامشخص'),
                        'level': 1,
                        'confidence': 'high'
                    },
                    'clauses': [],
                    'items': []
                }
        
        # سپس بندها و ردیف‌ها را به بخش‌های مربوطه اضافه کن
        for item in code_hierarchy.get('clauses', []):
            code = item['code']
            section_code = code[:2] + '0000'
            
            if section_code in section_groups:
                section_groups[section_code]['clauses'].append(item)
            else:
                # اگر بخش وجود ندارد، آن را ایجاد کن
                section_groups[section_code] = {
                    'section': {
                        'code': section_code,
                        'title': self.hierarchy_structure.get(section_code, {}).get('title', 'بخش نامشخص'),
                        'level': 1,
                        'confidence': 'high'
                    },
                    'clauses': [item],
                    'items': []
                }
        
        for item in code_hierarchy.get('items', []):
            code = item['code']
            section_code = code[:2] + '0000'
            
            if section_code in section_groups:
                section_groups[section_code]['items'].append(item)
        
        # ساخت درخت نهایی
        for section_code, group in section_groups.items():
            hierarchy_tree['sections'].append(group['section'])
            hierarchy_tree['clauses'].extend(group['clauses'])
            hierarchy_tree['items'].extend(group['items'])
        
        # شمارش نهایی
        hierarchy_tree['total_sections'] = len(hierarchy_tree['sections'])
        hierarchy_tree['total_clauses'] = len(hierarchy_tree['clauses'])
        hierarchy_tree['total_items'] = len(hierarchy_tree['items'])
        
        logger.info(f"   - Sections: {hierarchy_tree['total_sections']}")
        logger.info(f"   - Clauses: {hierarchy_tree['total_clauses']}")
        logger.info(f"   - Items: {hierarchy_tree['total_items']}")
        
        return hierarchy_tree
    
    def _build_hierarchy_tree(self, hierarchy: Dict[str, Any]) -> Dict[str, Any]:
        """
        ساخت درخت سلسله مراتبی نهایی
        """
        logger.info("   🌳 Building hierarchy tree...")
        
        tree = {
            'total_parts': len(hierarchy.get('parts', [])),
            'total_sections': len(hierarchy.get('sections', [])),
            'total_clauses': len(hierarchy.get('clauses', [])),
            'total_items': len(hierarchy.get('items', [])),
            'parts': hierarchy.get('parts', []),
            'sections': hierarchy.get('sections', []),
            'clauses': hierarchy.get('clauses', []),
            'items': hierarchy.get('items', [])
        }
        
        # ساختار parts
        for part in hierarchy.get('parts', []):
            tree['parts'].append({
                'code': part.get('code', ''),
                'title': part.get('title', ''),
                'number': part.get('number'),
                'chunk_idx': part.get('chunk_idx', 0)
            })
        
        # ساختار sections
        section_map = {}
        for section in hierarchy.get('sections', []):
            code = section.get('code', '')
            section_entry = {
                'code': code,
                'title': section.get('title', ''),
                'number': section.get('number'),
                'chunk_idx': section.get('chunk_idx', 0),
                'clauses': []
            }
            section_map[code] = section_entry
            tree['sections'].append(section_entry)
        
        # ربط clauses به sections
        for clause in hierarchy.get('clauses', []):
            clause_code = clause.get('code', '')
            # پیدا کردن section والد (اولین 3 رقم)
            if len(clause_code) >= 4:
                section_prefix = clause_code[:3] + '000'
                
                # اگر section پیدا شد
                if section_prefix in section_map:
                    section_map[section_prefix]['clauses'].append({
                        'code': clause_code,
                        'title': clause.get('title', ''),
                        'number': clause.get('number'),
                        'chunk_idx': clause.get('chunk_idx', 0)
                    })
                else:
                    # اگر section پیدا نشد، مستقیم اضافه کن
                    tree['clauses'].append({
                        'code': clause_code,
                        'title': clause.get('title', ''),
                        'number': clause.get('number'),
                        'chunk_idx': clause.get('chunk_idx', 0)
                    })
            else:
                tree['clauses'].append({
                    'code': clause.get('code', ''),
                    'title': clause.get('title', ''),
                    'number': clause.get('number'),
                    'chunk_idx': clause.get('chunk_idx', 0)
                })
        
        # محاسبه تعداد clauses در هر section
        for section in tree['sections']:
            section['clause_count'] = len(section['clauses'])
        
        return tree
    
    def enrich_chunk_metadata(self, chunk: Dict, hierarchy: Dict, chunk_idx: int) -> Dict:
        """
        غنی‌سازی metadata یک chunk با اطلاعات ساختاری
        
        Args:
            chunk: chunk برای غنی‌سازی
            hierarchy: درخت سلسله مراتبی
            chunk_idx: ایندکس chunk
        
        Returns:
            chunk با metadata غنی شده
        """
        # پیدا کردن اطلاعات ساختاری این chunk
        hierarchy_info = self._find_chunk_hierarchy_info(chunk_idx, hierarchy)
        
        if hierarchy_info:
            # افزودن به metadata
            if 'metadata' not in chunk:
                chunk['metadata'] = {}
            
            chunk['metadata']['hierarchy_level'] = hierarchy_info.get('level')
            chunk['metadata']['hierarchy_code'] = hierarchy_info.get('code', '')
            chunk['metadata']['hierarchy_title'] = hierarchy_info.get('title', '')
            chunk['metadata']['parent_section'] = hierarchy_info.get('parent_section', '')
            chunk['metadata']['hierarchy_path'] = hierarchy_info.get('path', '')
        
        return chunk
    
    def _find_chunk_hierarchy_info(self, chunk_idx: int, hierarchy: Dict) -> Optional[Dict[str, Any]]:
        """
        پیدا کردن اطلاعات سلسله مراتبی یک chunk خاص
        """
        # جستجو در sections
        for section in hierarchy.get('sections', []):
            if section.get('chunk_idx') == chunk_idx:
                return {
                    'level': 'section',
                    'code': section.get('code', ''),
                    'title': section.get('title', ''),
                    'path': f"بخش: {section.get('title', '')}"
                }
            
            # جستجو در clauses این section
            for clause in section.get('clauses', []):
                if clause.get('chunk_idx') == chunk_idx:
                    return {
                        'level': 'clause',
                        'code': clause.get('code', ''),
                        'title': clause.get('title', ''),
                        'parent_section': section.get('title', ''),
                        'path': f"{section.get('title', '')} > بند: {clause.get('title', '')}"
                    }
        
        # جستجو در clauses مستقل
        for clause in hierarchy.get('clauses', []):
            if clause.get('chunk_idx') == chunk_idx:
                return {
                    'level': 'clause',
                    'code': clause.get('code', ''),
                    'title': clause.get('title', ''),
                    'path': f"بند: {clause.get('title', '')}"
                }
        
        return None
    
    def create_structure_summary_text(self, hierarchy: Dict) -> str:
        """
        ایجاد متن خلاصه ساختار برای ذخیره به عنوان chunk
        
        Args:
            hierarchy: درخت سلسله مراتبی
        
        Returns:
            متن فرمت‌شده خلاصه ساختار
        """
        summary = "📊 خلاصه ساختار سند\n"
        summary += "=" * 60 + "\n\n"
        
        # آمار کلی
        summary += f"📈 آمار کلی:\n"
        summary += f"   • تعداد کل قسمت‌ها: {hierarchy.get('total_parts', 0)}\n"
        summary += f"   • تعداد کل بخش‌ها: {hierarchy.get('total_sections', 0)}\n"
        summary += f"   • تعداد کل بندها: {hierarchy.get('total_clauses', 0)}\n"
        summary += f"   • تعداد کل ردیف‌ها: {hierarchy.get('total_items', 0)}\n\n"
        
        # جزئیات sections
        if hierarchy.get('sections'):
            summary += "📋 جزئیات بخش‌ها:\n\n"
            
            for idx, section in enumerate(hierarchy['sections'], 1):
                code = section.get('code', 'بدون کد')
                title = section.get('title', 'بدون عنوان')
                clause_count = section.get('clause_count', 0)
                
                summary += f"{idx}. بخش {code}: {title}\n"
                summary += f"   تعداد بندها: {clause_count}\n"
                
                # لیست بندها
                if section.get('clauses'):
                    summary += f"   بندها:\n"
                    for clause_idx, clause in enumerate(section['clauses'], 1):
                        clause_code = clause.get('code', '')
                        clause_title = clause.get('title', '')
                        summary += f"      {clause_idx}. {clause_code}: {clause_title[:80]}\n"
                
                summary += "\n"
        
        # clauses مستقل (بدون section)
        independent_clauses = hierarchy.get('clauses', [])
        if independent_clauses:
            summary += f"📌 بندهای مستقل (بدون بخش): {len(independent_clauses)}\n\n"
            for idx, clause in enumerate(independent_clauses[:10], 1):  # فقط 10 تای اول
                summary += f"   {idx}. {clause.get('code', '')}: {clause.get('title', '')[:80]}\n"
        
        return summary

