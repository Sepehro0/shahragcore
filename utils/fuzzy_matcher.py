# -*- coding: utf-8 -*-
"""
Fuzzy Matching Utility for Organization Names
ابزار تطبیق تقریبی برای نام دستگاه‌ها
"""

from typing import List, Tuple, Optional, Dict
import re
from difflib import SequenceMatcher


class FuzzyMatcher:
    """کلاس برای تطبیق تقریبی نام دستگاه‌ها"""
    
    def __init__(self, threshold: float = 0.6):
        """
        Args:
            threshold: حداقل امتیاز similarity (0 تا 1) برای match
        """
        self.threshold = threshold
        
        # نقشه نام‌های مخفف و کامل
        self.abbreviation_map = {
            'آموزش و پرورش': ['آموزش‌وپرورش', 'آموزشوپرورش'],
            'بهداشت': ['بهداشت، درمان و آموزش پزشکی', 'بهداشت و درمان'],
            'علوم': ['علوم، تحقیقات و فناوری', 'علوم تحقیقات'],
            'کار': ['کار، تعاون و رفاه اجتماعی', 'کار و امور اجتماعی'],
            'نیرو': ['نیرو'],
            'راه': ['راه و شهرسازی', 'راه‌وشهرسازی'],
            'دفاع': ['دفاع و پشتیبانی نیروهای مسلح'],
            'نفت': ['نفت'],
            'جهاد': ['جهاد کشاورزی', 'جهاد-کشاورزی'],
            'صنعت': ['صنعت، معدن و تجارت'],
            'ارتباطات': ['ارتباطات و فناوری اطلاعات'],
        }
        
        # الگوهای رایج
        self.common_patterns = [
            r'وزارت\s+',
            r'سازمان\s+',
            r'معاونت\s+',
            r'نهاد\s+',
            r'بنیاد\s+',
            r'مجمع\s+',
            r'شورای\s+',
            r'هیات\s+',
            r'ستاد\s+',
        ]
    
    def normalize_name(self, name: str) -> str:
        """نرمال‌سازی نام برای مقایسه بهتر"""
        if not name:
            return ""
        
        # حذف فضاهای اضافی
        name = ' '.join(name.split())
        
        # نرمال‌سازی کاراکترهای مشابه
        replacements = {
            'ي': 'ی',
            'ك': 'ک',
            'ة': 'ه',
            'ۀ': 'ه',
            'أ': 'ا',
            'إ': 'ا',
            'ٱ': 'ا',
            'آ': 'ا',
            '‌': ' ',  # نیم‌فاصله به فاصله
            '،': ',',
            '؛': ';',
        }
        
        for old, new in replacements.items():
            name = name.replace(old, new)
        
        return name.strip()
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """
        محاسبه شباهت بین دو رشته
        
        Returns:
            امتیاز شباهت (0 تا 1)
        """
        # نرمال‌سازی
        str1_norm = self.normalize_name(str1.lower())
        str2_norm = self.normalize_name(str2.lower())
        
        # اگر دقیقاً یکسان هستند
        if str1_norm == str2_norm:
            return 1.0
        
        # محاسبه با SequenceMatcher
        similarity = SequenceMatcher(None, str1_norm, str2_norm).ratio()
        
        # بررسی شامل بودن
        if str1_norm in str2_norm or str2_norm in str1_norm:
            # افزایش امتیاز اگر یکی شامل دیگری باشد
            similarity = max(similarity, 0.85)
        
        # بررسی کلمات مشترک
        words1 = set(str1_norm.split())
        words2 = set(str2_norm.split())
        
        if words1 and words2:
            common_words = words1.intersection(words2)
            word_similarity = len(common_words) / max(len(words1), len(words2))
            
            # ترکیب similarity کاراکتری و کلمه‌ای
            similarity = max(similarity, word_similarity * 0.9)
        
        # بررسی مخفف‌ها
        for key, variants in self.abbreviation_map.items():
            if key in str1_norm:
                for variant in variants:
                    if variant in str2_norm:
                        similarity = max(similarity, 0.95)
            if key in str2_norm:
                for variant in variants:
                    if variant in str1_norm:
                        similarity = max(similarity, 0.95)
        
        return similarity
    
    def find_best_match(
        self,
        query: str,
        candidates: List[str],
        return_all: bool = False
    ) -> Optional[Tuple[str, float]] | List[Tuple[str, float]]:
        """
        یافتن بهترین تطبیق برای query در لیست candidates
        
        Args:
            query: نام جستجو شده
            candidates: لیست نام‌های موجود
            return_all: اگر True، همه matches با امتیاز بالای threshold را برگردان
        
        Returns:
            (best_match, score) یا لیستی از (match, score) اگر return_all=True
        """
        if not query or not candidates:
            return None if not return_all else []
        
        matches = []
        
        for candidate in candidates:
            score = self.calculate_similarity(query, candidate)
            if score >= self.threshold:
                matches.append((candidate, score))
        
        if not matches:
            return None if not return_all else []
        
        # مرتب‌سازی بر اساس امتیاز
        matches.sort(key=lambda x: x[1], reverse=True)
        
        if return_all:
            return matches
        else:
            return matches[0]
    
    def extract_organization_type(self, name: str) -> Optional[str]:
        """استخراج نوع سازمان (وزارت، سازمان، ...)"""
        name_norm = self.normalize_name(name.lower())
        
        for pattern in self.common_patterns:
            match = re.search(pattern, name_norm)
            if match:
                return match.group(0).strip()
        
        return None
    
    def smart_match(
        self,
        query: str,
        candidates: List[Dict[str, str]],
        field_name: str = 'name'
    ) -> List[Tuple[Dict[str, str], float]]:
        """
        تطبیق هوشمند با در نظر گرفتن context
        
        Args:
            query: نام جستجو شده
            candidates: لیست دیکشنری‌های حاوی نام و اطلاعات اضافی
            field_name: نام فیلد حاوی نام سازمان
        
        Returns:
            لیست (candidate_dict, score) مرتب شده
        """
        matches = []
        
        query_type = self.extract_organization_type(query)
        
        for candidate in candidates:
            name = candidate.get(field_name, '')
            if not name:
                continue
            
            score = self.calculate_similarity(query, name)
            
            # بونوس برای نوع سازمان یکسان
            if query_type:
                candidate_type = self.extract_organization_type(name)
                if query_type == candidate_type:
                    score = min(1.0, score + 0.05)
            
            if score >= self.threshold:
                matches.append((candidate, score))
        
        # مرتب‌سازی
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    محاسبه فاصله Levenshtein بین دو رشته
    
    Args:
        s1: رشته اول
        s2: رشته دوم
    
    Returns:
        فاصله Levenshtein (تعداد تغییرات مورد نیاز)
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # کاست جایگزینی، حذف، یا اضافه
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def normalize_levenshtein_distance(s1: str, s2: str) -> float:
    """
    محاسبه فاصله Levenshtein نرمال شده (0 تا 1)
    
    Returns:
        امتیاز شباهت (1 = یکسان، 0 = کاملاً متفاوت)
    """
    distance = levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    
    if max_len == 0:
        return 1.0
    
    return 1.0 - (distance / max_len)


# نمونه استفاده
if __name__ == "__main__":
    matcher = FuzzyMatcher(threshold=0.6)
    
    # تست
    query = "وزارت بهداشت"
    candidates = [
        "وزارت بهداشت، درمان و آموزش پزشکی",
        "وزارت آموزش و پرورش",
        "وزارت نفت",
    ]
    
    result = matcher.find_best_match(query, candidates)
    if result:
        print(f"Query: {query}")
        print(f"Best match: {result[0]} (score: {result[1]:.2f})")

