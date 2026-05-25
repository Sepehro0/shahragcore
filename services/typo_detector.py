# -*- coding: utf-8 -*-
"""
Typo Detector - تشخیص کلمات اشتباه و پیشنهاد اصلاح
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
from collections import Counter

logger = logging.getLogger(__name__)


class TypoDetector:
    """تشخیص کلمات اشتباه در query و پیشنهاد اصلاح"""
    
    def __init__(self):
        """Initialize typo detector"""
        # کلمات رایج فارسی که نباید typo تشخیص داده شوند
        self.common_words = {
            'در', 'از', 'به', 'با', 'که', 'را', 'این', 'آن', 'است', 'می', 'شود',
            'های', 'برای', 'تا', 'یا', 'و', 'اگر', 'چه', 'چی', 'چیه', 'چگونه',
            'کجا', 'کی', 'چرا', 'چند', 'کدام', 'چطور', 'باید', 'میشه', 'میتونم',
            'داره', 'نداره', 'هست', 'نیست', 'بود', 'نبود', 'بشه', 'نشه',
            'ماده', 'قرارداد', 'پیمان', 'شرایط', 'عمومی', 'پیمانکار', 'کارفرما'
        }
        
        # فعل‌های رایج فارسی (نباید typo detection روی اینها اعمال شود)
        self.common_verbs = {
            'بدهیم', 'بدهد', 'بدهند', 'بگیریم', 'بگیرد', 'کنیم', 'کند', 'کنند',
            'توانیم', 'تواند', 'توانند', 'شود', 'شویم', 'شوند', 'باشد', 'باشیم',
            'داریم', 'دارد', 'دارند', 'نداریم', 'ندارد', 'ندارند'
        }
        
        # کلمات تخصصی حوزه پیمانکاری
        self.domain_keywords = {
            'پیمان', 'قرارداد', 'پیمانکار', 'کارفرما', 'مشاور', 'مهندس',
            'فهرست', 'بها', 'فهرست‌بها', 'صورت', 'وضعیت', 'صورت‌وضعیت',
            'تضمین', 'پیش‌پرداخت', 'پرداخت', 'تاخیر', 'خسارت',
            'ماده', 'بند', 'فصل', 'تبصره', 'بخشنامه', 'آیین‌نامه',
            'فسخ', 'خاتمه', 'تعلیق', 'تحویل', 'موقت', 'قطعی',
            'نظام', 'فنی', 'اجرایی', 'سازمان', 'برنامه', 'بودجه'
        }
    
    def _normalize_word(self, word: str) -> str:
        """Normalize a word for comparison"""
        # حذف نشانه‌گذاری
        word = re.sub(r'[؟!.,،؛:\-_\(\)\[\]{}«»]', '', word)
        # حذف فاصله
        word = word.strip()
        return word.lower()
    
    def _is_stop_word(self, word: str) -> bool:
        """Check if word is a stop word or verb"""
        normalized = self._normalize_word(word)
        return len(normalized) <= 2 or normalized in self.common_words or normalized in self.common_verbs
    
    def _calculate_similarity(self, word1: str, word2: str) -> float:
        """Calculate similarity between two words using multiple strategies"""
        # 1. Character-level similarity
        char_sim = SequenceMatcher(None, word1, word2).ratio()
        
        # 2. Phonetic similarity (برای فارسی)
        # تبدیل حروف مشابه صوتی
        phonetic_map = {
            'ا': 'آ', 'آ': 'ا',
            'ه': 'ح', 'ح': 'ه',
            'ت': 'ط', 'ط': 'ت',
            'ز': 'ذ', 'ذ': 'ز', 'ظ': 'ز', 'ض': 'ز',
            'س': 'ص', 'ص': 'س', 'ث': 'س',
            'و': 'ؤ', 'ؤ': 'و'
        }
        
        def phonetic_normalize(w):
            return ''.join([phonetic_map.get(c, c) for c in w])
        
        phonetic_sim = SequenceMatcher(
            None,
            phonetic_normalize(word1),
            phonetic_normalize(word2)
        ).ratio()
        
        # 3. Keyboard proximity (برای typo های کیبوردی)
        # برای مثال، 'ط' نزدیک 'ک' است در کیبورد فارسی
        keyboard_map = {
            'ط': ['ظ', 'ک'],
            'ک': ['گ', 'ق', 'ط'],
            'ل': ['م', 'ک'],
            'ا': ['آ', 'ء']
        }
        
        # Check if word1 can be converted to word2 with 1 keyboard error
        keyboard_bonus = 0.0
        if len(word1) == len(word2):
            diff_count = sum(1 for c1, c2 in zip(word1, word2) if c1 != c2)
            if diff_count == 1:
                for i, (c1, c2) in enumerate(zip(word1, word2)):
                    if c1 != c2 and c1 in keyboard_map and c2 in keyboard_map[c1]:
                        keyboard_bonus = 0.3  # افزودن bonus
                        break
        
        # ترکیب weighted
        final_sim = max(
            char_sim * 0.6 + phonetic_sim * 0.4 + keyboard_bonus,
            char_sim,
            phonetic_sim
        )
        
        return final_sim
    
    def _extract_words(self, text: str) -> List[str]:
        """Extract words from text"""
        # استخراج کلمات فارسی و انگلیسی
        words = re.findall(r'[\u0600-\u06FFa-zA-Z0-9]+', text)
        return [self._normalize_word(w) for w in words if len(self._normalize_word(w)) > 2]
    
    def detect_typos(
        self,
        query: str,
        retrieved_sources: List[Dict],
        min_word_length: int = 3,
        similarity_threshold: float = 0.4  # کاهش threshold برای flexibility بیشتر
    ) -> Optional[Dict[str, any]]:
        """
        تشخیص کلمات اشتباه در query
        
        Args:
            query: سوال کاربر
            retrieved_sources: منابع بازیابی شده (با 'text' یا 'metadata')
            min_word_length: حداقل طول کلمه برای بررسی
            similarity_threshold: آستانه شباهت برای پیشنهاد
        
        Returns:
            Dict with:
                - has_typo: bool
                - typo_word: str (کلمه اشتباه)
                - suggested_word: str (کلمه پیشنهادی)
                - confidence: float
                - message: str (پیام برای کاربر)
        """
        try:
            # استخراج کلمات از query
            query_words = self._extract_words(query)
            
            if not query_words:
                return None
            
            # استخراج کلمات از sources
            source_words = []
            for source in retrieved_sources[:10]:  # 10 منبع اول برای coverage بهتر
                # از همه فیلدهای موجود استفاده کن
                text_parts = []
                
                # از 'text'
                if 'text' in source:
                    text_parts.append(source['text'])
                
                # از 'content'
                if 'content' in source:
                    text_parts.append(source['content'])
                
                # از 'metadata'
                if 'metadata' in source:
                    meta = source['metadata']
                    for key in ['question', 'answer', 'title', 'zabete_title', 'madde_title']:
                        if key in meta and meta[key]:
                            text_parts.append(str(meta[key]))
                
                # ترکیب همه
                full_text = ' '.join(text_parts)
                if full_text:
                    source_words.extend(self._extract_words(full_text))
            
            if not source_words:
                return None
            
            # شمارش فراوانی کلمات در sources
            source_word_freq = Counter(source_words)
            
            # بررسی هر کلمه در query
            potential_typos = []
            
            for query_word in query_words:
                # Skip stop words, verbs, and very short words
                if self._is_stop_word(query_word):
                    continue
                
                # اگر کلمه در domain keywords است، skip
                if query_word in self.domain_keywords:
                    continue
                
                # اگر کلمه به نظر فعل می‌رسد (ختم به یم، ید، ند، د), skip
                if query_word.endswith(('یم', 'ید', 'ند', 'ستیم', 'ستید', 'ستند')):
                    logger.debug(f"⏭️ [TYPO] Skipping verb: '{query_word}'")
                    continue
                
                # اگر کلمه در sources است، OK
                if query_word in source_word_freq:
                    continue
                
                # کلمه در sources نیست - احتمال typo یا کلمه نامرتبط
                logger.info(f"🔍 [TYPO] Word '{query_word}' not found in top sources")
                
                # پیدا کردن مشابه‌ترین کلمه
                candidates = []
                
                # استراتژی 1: شباهت کاراکتری
                for source_word, freq in source_word_freq.most_common(100):
                    # فقط کلماتی که طول مشابه دارند
                    if abs(len(source_word) - len(query_word)) > 3:
                        continue
                    
                    similarity = self._calculate_similarity(query_word, source_word)
                    
                    if similarity >= similarity_threshold:
                        candidates.append({
                            'word': source_word,
                            'similarity': similarity,
                            'frequency': freq,
                            'score': similarity * (1 + 0.1 * min(freq, 10)),  # bonus برای فراوانی بالا
                            'method': 'character'
                        })
                
                # استراتژی 2: Context-based (کلماتی که در context مشابه استفاده می‌شوند)
                # مثل: "در پیمان [X] بیشتر" - X احتمالاً باید یک اسم باشد
                # پیدا کردن کلمات پرتکرار که در موقعیت مشابه استفاده شده‌اند
                query_words_list = self._extract_words(query)
                query_word_index = query_words_list.index(query_word) if query_word in query_words_list else -1
                
                if query_word_index > 0:  # اگر کلمه قبل داریم
                    prev_word = query_words_list[query_word_index - 1]
                    
                    # اگر کلمه قبل "پیمان" است، کلمه فعلی احتمالاً اسمی مثل "کار" است
                    if prev_word in ['پیمان', 'قرارداد', 'پیمانکار']:
                        # پیدا کردن کلماتی که بعد از این کلمات می‌آیند
                        for source in retrieved_sources[:10]:
                            text = source.get('text', '') + ' '
                            if 'metadata' in source:
                                text += source['metadata'].get('question', '') + ' ' + source['metadata'].get('answer', '')
                            
                            # پیدا کردن "پیمان X" patterns
                            import re
                            patterns = re.findall(rf'{prev_word}\s+(\S+)', text, re.IGNORECASE)
                            for match in patterns:
                                match_norm = self._normalize_word(match)
                                if len(match_norm) >= min_word_length and match_norm in source_word_freq:
                                    # این کلمه می‌تواند candidate باشد
                                    freq = source_word_freq[match_norm]
                                    candidates.append({
                                        'word': match_norm,
                                        'similarity': 0.5,  # similarity پایه
                                        'frequency': freq,
                                        'score': 0.5 * (1 + 0.2 * min(freq, 10)),  # bonus بیشتر برای context
                                        'method': 'context'
                                    })
                
                # Sort by score
                candidates.sort(key=lambda x: x['score'], reverse=True)
                
                # اگر match پیدا شد
                if candidates:
                    best = candidates[0]
                    logger.info(f"✅ [TYPO] Potential correction: '{query_word}' → '{best['word']}' (similarity: {best['similarity']:.2f}, freq: {best['frequency']}, score: {best['score']:.2f})")
                    
                    potential_typos.append({
                        'typo_word': query_word,
                        'suggested_word': best['word'],
                        'confidence': best['similarity'],
                        'frequency': best['frequency']
                    })
            
            # برگرداندن بهترین typo (با بالاترین confidence × frequency)
            if potential_typos:
                # Sort by confidence * log(frequency)
                import math
                for typo in potential_typos:
                    typo['score'] = typo['confidence'] * math.log(1 + typo['frequency'])
                
                best_typo = max(potential_typos, key=lambda x: x['score'])
                
                logger.info(f"✅ [TYPO] Best correction: '{best_typo['typo_word']}' → '{best_typo['suggested_word']}' (confidence: {best_typo['confidence']:.2f}, freq: {best_typo['frequency']})")
                
                return {
                    'has_typo': True,
                    'typo_word': best_typo['typo_word'],
                    'suggested_word': best_typo['suggested_word'],
                    'confidence': best_typo['confidence'],
                    'message': f"💡 کلمه '{best_typo['typo_word']}' در منابع یافت نشد. منظور شما '{best_typo['suggested_word']}' بود؟"
                }
            
            # هیچ typo یافت نشد
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ [TYPO] Typo detection failed: {e}")
            return None
    
    def correct_query(self, query: str, typo_info: Dict) -> str:
        """
        اصلاح query با استفاده از typo_info
        
        Args:
            query: سوال اصلی
            typo_info: اطلاعات typo از detect_typos
        
        Returns:
            Query اصلاح شده
        """
        if not typo_info or not typo_info.get('has_typo'):
            return query
        
        typo_word = typo_info['typo_word']
        suggested_word = typo_info['suggested_word']
        
        # Replace with case-insensitive regex
        pattern = re.compile(re.escape(typo_word), re.IGNORECASE)
        corrected_query = pattern.sub(suggested_word, query)
        
        logger.info(f"✅ [TYPO] Query corrected: '{query}' → '{corrected_query}'")
        
        return corrected_query

