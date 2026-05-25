# -*- coding: utf-8 -*-
"""
Budget Typo Corrector
تصحیح غلط‌املایی‌های رایج در سوالات بودجه‌ای

این ماژول شامل:
1. تصحیح غلط‌املایی‌های فارسی رایج
2. تشخیص و تصحیح عبارات سلسله‌مراتبی (قسمت، بخش، بند، جزء)
3. Fuzzy matching برای یافتن عنوان‌های صحیح
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class BudgetTypoCorrector:
    """
    تصحیح کننده غلط‌املایی برای سوالات بودجه‌ای
    """
    
    def __init__(self):
        """Initialize with common typo mappings"""
        
        # غلط‌املایی‌های رایج فارسی
        self.common_typos = {
            # الف - ا
            'آ': 'ا',  # آموزش -> اموزش (اختیاری)
            
            # ی - ي
            'ي': 'ی',
            'ى': 'ی',
            
            # ک - ك
            'ك': 'ک',
            
            # ه - ة
            'ة': 'ه',
            'ۀ': 'ه',
            
            # همزه
            'أ': 'ا',
            'إ': 'ا',
            'ٱ': 'ا',
        }
        
        # غلط‌املایی‌های کلمه‌ای رایج
        self.word_typos = {
            # حاضل -> حاصل (خیلی رایج!)
            'حاضل': 'حاصل',
            
            # درامد -> درآمد
            'درامد': 'درآمد',
            'درامدها': 'درآمدها',
            'درامدهای': 'درآمدهای',
            'درامدهاي': 'درآمدهای',
            
            # اموزش -> آموزش
            'اموزش': 'آموزش',
            
            # هزینه
            'هزينه': 'هزینه',
            'هزینه ها': 'هزینه‌ها',
            'هزينه ها': 'هزینه‌ها',
            
            # اعتبارات
            'اعتبار': 'اعتبارات',
            
            # سرمایه
            'سرمايه': 'سرمایه',
            
            # واگذاری
            'واگزاری': 'واگذاری',
            'واگذاري': 'واگذاری',
            
            # فروش
            'فروش': 'فروش',
            
            # خدمات
            'خدمت': 'خدمات',
            
            # مالیات
            'ماليات': 'مالیات',
            'مالیاتي': 'مالیاتی',
            
            # گمرک
            'گمرك': 'گمرک',
            'گمرکي': 'گمرکی',
            
            # تملک
            'تملك': 'تملک',
            
            # شورا / شوار
            'شواری': 'شورای',
            'شوری': 'شورای',
            'شورا ': 'شورای ',  # شورا نگهبان -> شورای نگهبان
            
            # بهداشت
            'بهداشت': 'بهداشت',
            'بهدشت': 'بهداشت',
            
            # براورد / برآورد
            'براورد': 'برآورد',
            
            # دفاعی / دقاعی
            'دقاعی': 'دفاعی',  # typo رایج: ق به جای ف
            'دقاعي': 'دفاعی',
            
            # ثروت / ثرورت (typo رایج: اضافه شدن ر)
            'ثرورت': 'ثروت',
            
            # واردات / وارادات
            'وارادات': 'واردات',
            
            # درآمد / درامد (already covered but add variants)
            'درامدهاي': 'درآمدهای',
            
            # المپیک
            'المپيک': 'المپیک',
            'المپيك': 'المپیک',
            
            # 🔧 FIX: Entity aliases - نام‌های مختلف سازمان‌ها و وزارت‌خانه‌ها
            'وزارت اقتصاد و دارایی': 'وزارت امور اقتصادی و دارایی',  # canonical name
            'وزارت اقتصاد': 'وزارت امور اقتصادی',  # short form
            # 🔧 REMOVED: 'سازمان برنامه و بودجه' mapping - این نام صحیح در database است
        }
        
        # الگوهای سلسله‌مراتبی صحیح (از دیتابیس)
        self.hierarchy_patterns = {
            'band': [
                'بنداول: درآمدهای حاصل از خدمات',
                'بند اول: درآمدهای حاصل از جرایم و خسارات',
                'بند اول: درآمدهای متفرقه',
                'بند اول: سود سهام شرکتهای دولتی',
                'بند اول: مالیات اشخاص حقوقی',
                'بند اول: منابع حاصل از فروش و واگذاری انواع اوراق مالی اسلامی',
                'بند اول: منابع حاصل از نفت و فرآورده‌های نفتی',
                'بند دوم: درآمدهای حاصل از فروش کالاها',
                'بند دوم: مالیات بر درآمدها',
                'بند سوم: درآمدهای حاصل از اجاره',
                'بند سوم: مالیات بر ثروت',
                'بند چهارم: سایر درآمدهای حاصل از مالکیت دولت',
                'بند چهارم: مالیات بر واردات',
                'بند پنجم: مالیات بر کالاها و خدمات',
            ],
            'bakhsh': [
                'بخش اول: مالیات‌ها',
                'بخش دوم: سود سهام دولت و بازپرداخت وام‌ها',
                'بخش سوم: درآمدهای حاصل از مالکیت دولت',
                'بخش چهارم: درآمدهای حاصل از فروش کالاها و خدمات',
                'بخش پنجم: درآمدهای متفرقه',
            ],
            'ghesmat': [
                'قسمت اول: درآمدها',
                'قسمت دوم: واگذاری دارایی‌های سرمایه‌ای',
                'قسمت سوم: واگذاری دارایی‌های مالی',
            ],
        }
        
        # کلمات کلیدی برای تشخیص نوع سلسله‌مراتب
        self.hierarchy_keywords = {
            'band': ['بند', 'بنداول', 'بند اول', 'بند دوم', 'بند سوم', 'بند چهارم', 'بند پنجم'],
            'bakhsh': ['بخش', 'بخش اول', 'بخش دوم', 'بخش سوم', 'بخش چهارم', 'بخش پنجم'],
            'ghesmat': ['قسمت', 'قسمت اول', 'قسمت دوم', 'قسمت سوم'],
            'jozv': ['جزء', 'جزو'],
        }
    
    def normalize_text(self, text: str) -> str:
        """نرمال‌سازی متن فارسی"""
        if not text:
            return ''
        
        # حذف فاصله‌های اضافی
        text = ' '.join(text.split())
        
        # تصحیح کاراکترهای عربی به فارسی
        for old, new in self.common_typos.items():
            text = text.replace(old, new)
        
        return text
    
    def correct_word_typos(self, text: str) -> Tuple[str, List[Dict]]:
        """
        تصحیح غلط‌املایی‌های کلمه‌ای
        
        🔧 CRITICAL FIX: استفاده از word boundary برای جلوگیری از تبدیل
        "اعتبارات" به "اعتباراتات" (وقتی "اعتبار" -> "اعتبارات" اعمال میشه)
        
        Returns:
            (corrected_text, list of corrections made)
        """
        corrections = []
        corrected = text
        
        for typo, correct in self.word_typos.items():
            if typo in corrected.lower():
                # 🔧 CRITICAL FIX: استفاده از word boundary ((?<![آ-ی]) و (?![آ-ی]))
                # تا "اعتبار" فقط وقتی به عنوان کلمه مستقل باشد تصحیح شود
                # نه وقتی بخشی از "اعتبارات" یا "اعتباری" است
                pattern = re.compile(
                    r'(?<![آ-ی\u0600-\u06FF])' + re.escape(typo) + r'(?![آ-ی\u0600-\u06FF])',
                    re.IGNORECASE
                )
                if pattern.search(corrected):
                    corrected = pattern.sub(correct, corrected)
                    corrections.append({
                        'original': typo,
                        'corrected': correct,
                        'type': 'word_typo'
                    })
        
        return corrected, corrections
    
    def detect_hierarchy_type(self, text: str) -> Optional[str]:
        """تشخیص نوع سلسله‌مراتب در سوال"""
        text_lower = self.normalize_text(text).lower()
        
        for hierarchy_type, keywords in self.hierarchy_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return hierarchy_type
        
        return None
    
    def find_best_hierarchy_match(self, query_phrase: str, hierarchy_type: str) -> Optional[Tuple[str, float]]:
        """
        یافتن بهترین تطابق برای عبارت سلسله‌مراتبی
        
        Args:
            query_phrase: عبارت جستجو شده (مثل "بند درامدهای حاضل از خدمات")
            hierarchy_type: نوع سلسله‌مراتب (band, bakhsh, ghesmat)
        
        Returns:
            (best_match, score) یا None
        """
        candidates = self.hierarchy_patterns.get(hierarchy_type, [])
        if not candidates:
            return None
        
        # نرمال‌سازی query
        query_norm = self.normalize_text(query_phrase).lower()
        
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            candidate_norm = self.normalize_text(candidate).lower()
            
            # محاسبه شباهت
            score = SequenceMatcher(None, query_norm, candidate_norm).ratio()
            
            # بونوس برای کلمات مشترک
            query_words = set(query_norm.split())
            candidate_words = set(candidate_norm.split())
            common = query_words.intersection(candidate_words)
            
            if common:
                word_bonus = len(common) / max(len(query_words), len(candidate_words)) * 0.3
                score = min(1.0, score + word_bonus)
            
            if score > best_score:
                best_score = score
                best_match = candidate
        
        if best_score >= 0.5:  # threshold
            return (best_match, best_score)
        
        return None
    
    def correct_query(self, query: str) -> Dict:
        """
        تصحیح کامل سوال
        
        Args:
            query: سوال کاربر
        
        Returns:
            {
                'original': سوال اصلی,
                'corrected': سوال تصحیح شده,
                'corrections': لیست تصحیحات,
                'hierarchy_match': تطابق سلسله‌مراتبی (اگر پیدا شد),
                'confidence': میزان اطمینان
            }
        """
        result = {
            'original': query,
            'corrected': query,
            'corrections': [],
            'hierarchy_match': None,
            'confidence': 1.0
        }
        
        # مرحله 1: نرمال‌سازی
        corrected = self.normalize_text(query)
        if corrected != query:
            result['corrections'].append({
                'type': 'normalization',
                'detail': 'نرمال‌سازی کاراکترها'
            })
        
        # مرحله 2: تصحیح غلط‌املایی کلمات
        corrected, word_corrections = self.correct_word_typos(corrected)
        result['corrections'].extend(word_corrections)
        
        # مرحله 3: تشخیص و تطابق سلسله‌مراتبی
        hierarchy_type = self.detect_hierarchy_type(corrected)
        if hierarchy_type:
            match_result = self.find_best_hierarchy_match(corrected, hierarchy_type)
            if match_result:
                result['hierarchy_match'] = {
                    'type': hierarchy_type,
                    'matched_title': match_result[0],
                    'score': match_result[1]
                }
                result['confidence'] = min(result['confidence'], match_result[1])
        
        result['corrected'] = corrected
        
        # لاگ تصحیحات
        if result['corrections']:
            logger.info(f"🔧 [TYPO_CORRECTOR] تصحیحات انجام شده:")
            logger.info(f"   اصلی: {query}")
            logger.info(f"   تصحیح شده: {corrected}")
            for correction in result['corrections']:
                logger.info(f"   - {correction}")
        
        return result
    
    def get_corrected_sql_filter(self, query: str, column_name: str = 'عنوان_بند') -> Optional[str]:
        """
        ایجاد فیلتر SQL با در نظر گرفتن تصحیحات
        
        Args:
            query: سوال کاربر
            column_name: نام ستون برای فیلتر
        
        Returns:
            فیلتر SQL یا None
        """
        correction_result = self.correct_query(query)
        
        if correction_result['hierarchy_match']:
            matched_title = correction_result['hierarchy_match']['matched_title']
            # ایجاد فیلتر با عنوان صحیح
            safe_title = matched_title.replace("'", "''")
            return f'TRANSLATE("{column_name}", \'يكيۀةأإٱ\', \'یکیهههاا\') ILIKE \'%{safe_title}%\''
        
        # اگر تطابق پیدا نشد، از متن تصحیح شده استفاده کن
        corrected = correction_result['corrected']
        
        # استخراج کلمات کلیدی
        keywords = []
        for word in corrected.split():
            if len(word) > 2 and word not in ['در', 'از', 'به', 'با', 'که', 'این', 'آن', 'سال', 'های', 'منابع']:
                keywords.append(word)
        
        if keywords:
            conditions = []
            for kw in keywords[:3]:  # حداکثر 3 کلمه کلیدی
                safe_kw = kw.replace("'", "''")
                conditions.append(f'TRANSLATE("{column_name}", \'يكيۀةأإٱ\', \'یکیهههاا\') ILIKE \'%{safe_kw}%\'')
            
            return ' AND '.join(conditions)
        
        return None


# ========== Singleton Instance ==========
_corrector_instance = None

def get_budget_typo_corrector() -> BudgetTypoCorrector:
    """دریافت instance سینگلتون"""
    global _corrector_instance
    if _corrector_instance is None:
        _corrector_instance = BudgetTypoCorrector()
    return _corrector_instance


def correct_budget_query(query: str) -> Dict:
    """
    تابع کمکی برای تصحیح سریع سوال
    
    Args:
        query: سوال کاربر
    
    Returns:
        نتیجه تصحیح
    """
    corrector = get_budget_typo_corrector()
    return corrector.correct_query(query)
