# -*- coding: utf-8 -*-
"""
Conversation Context Enhancer
غنی‌سازی query با استفاده از context گفتگو
"""

import logging
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ConversationContextEnhancer:
    """
    غنی‌سازی query های مبهم با استفاده از chat history
    
    برای سوالاتی مثل "چقدر پول میدید؟" که در وسط conversation هستند
    context گفتگو را اضافه می‌کند
    """
    
    def __init__(self):
        # الگوهای سوالات مبهم که نیاز به context دارند
        self.ambiguous_patterns = [
            # سوالات پرداخت/پول
            r'چ(ه|ی)\s*قدر\s+(پول|مبلغ|بودجه|تومان|ریال)',
            r'(پول|مبلغ|بودجه)\s+(می\s*د(ه|ی)د|دارید)',
            r'(چند|چقدر)\s+(می\s*د(ه|ی)د)',
            
            # سوالات "این/آن" که به چیز قبلی اشاره دارند
            r'^(این|آن|اون)\s+(چیه|چیست|کیه|کیست)',
            r'^(این|آن|اون)',
            
            # سوالات کوتاه و عمومی
            r'^(چطور|چجور)\s*[؟?]?\s*$',
            r'^(چی|چه)\s*[؟?]?\s*$',
            r'^(کجا|کی|چرا)\s*[؟?]?\s*$',
            
            # پرسش‌های ادامه‌دار
            r'^(خب|پس|بعد)',
            r'(بعدش|بعد\s*از\s*اون)',
            
            # سوالات "مدارک/شرایط"
            r'^(مدارک|شرایط|چیز(ای)?)\s+(چی|چیه|چیست|لازمه)',
        ]
        
        # کلمات کلیدی برای استخراج موضوع از history
        self.domain_keywords = {
            'صندوق نوآور': ['نوآور', 'noavar', 'ایده خام', 'mvp', 'نمونه اولیه'],
            'صندوق باور': ['باور', 'bavar', 'سرمایه', 'سهام', 'استارتاپ'],
            'صندوق تبادل فناوری': ['تبادل فناوری', 'rfp', 'فراخوان', 'پروژه صنعتی'],
            'پرداخت': ['پرداخت', 'مالی', 'بودجه', 'پول', 'مبلغ', 'تومان', 'ریال'],
            'همکاری': ['همکاری', 'مراحل', 'فرآیند', 'درخواست', 'ثبت نام'],
            'ایده': ['ایده', 'طرح', 'پروژه', 'idea'],
        }
    
    def is_ambiguous(self, query: str) -> bool:
        """
        بررسی اینکه query مبهم هست یا نه
        
        Args:
            query: سوال کاربر
            
        Returns:
            True اگر سوال مبهم باشد و نیاز به context داشته باشد
        """
        query_lower = query.lower().strip()
        
        # بررسی الگوهای مبهم
        for pattern in self.ambiguous_patterns:
            if re.search(pattern, query_lower):
                logger.info(f"🔍 [CONTEXT] Ambiguous query detected: '{query}' matches pattern '{pattern}'")
                return True
        
        # اگر query خیلی کوتاه باشد (کمتر از 4 کلمه)
        word_count = len(query.split())
        if word_count <= 3:
            logger.info(f"🔍 [CONTEXT] Ambiguous query detected: very short query ({word_count} words)")
            return True
        
        return False
    
    def extract_context_from_history(
        self,
        chat_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        استخراج موضوعات و entities از chat history
        
        Args:
            chat_history: تاریخچه گفتگو
            
        Returns:
            Dict حاوی اطلاعات context
        """
        context_info = {
            'topics': set(),
            'entities': set(),
            'last_topic': None,
            'summary': ''
        }
        
        if not chat_history:
            return context_info
        
        # بررسی 3-5 پیام آخر
        recent_messages = chat_history[-5:]
        
        all_text = []
        for msg in recent_messages:
            user_text = msg.get('user', '')
            assistant_text = msg.get('assistant', '')
            all_text.append(user_text)
            all_text.append(assistant_text)
        
        combined_text = ' '.join(all_text).lower()
        
        # استخراج topics
        for topic, keywords in self.domain_keywords.items():
            if any(kw in combined_text for kw in keywords):
                context_info['topics'].add(topic)
        
        # استخراج آخرین موضوع از آخرین پیام
        if recent_messages:
            last_msg = recent_messages[-1]
            last_text = (last_msg.get('user', '') + ' ' + last_msg.get('assistant', '')).lower()
            
            for topic, keywords in self.domain_keywords.items():
                if any(kw in last_text for kw in keywords):
                    context_info['last_topic'] = topic
                    break
        
        # ساخت خلاصه
        if context_info['topics']:
            context_info['summary'] = f"گفتگو درباره: {', '.join(context_info['topics'])}"
            if context_info['last_topic']:
                context_info['summary'] += f" (آخرین موضوع: {context_info['last_topic']})"
        
        return context_info
    
    def enrich_query(
        self,
        query: str,
        chat_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        غنی‌سازی query با context از chat history
        
        Args:
            query: سوال اصلی کاربر
            chat_history: تاریخچه گفتگو
            
        Returns:
            Dict حاوی:
                - enriched_query: query غنی‌شده
                - original_query: query اصلی
                - context_used: آیا از context استفاده شد
                - context_info: اطلاعات context
        """
        # بررسی اینکه query مبهم هست یا نه
        if not self.is_ambiguous(query):
            return {
                'enriched_query': query,
                'original_query': query,
                'context_used': False,
                'context_info': {}
            }
        
        # استخراج context از history
        context_info = self.extract_context_from_history(chat_history)
        
        if not context_info['topics']:
            # اگر context پیدا نشد، query را همان‌طور برگردان
            logger.info(f"ℹ️ [CONTEXT] No relevant context found in history for: '{query}'")
            return {
                'enriched_query': query,
                'original_query': query,
                'context_used': False,
                'context_info': context_info
            }
        
        # ساخت enriched query
        enriched_query = self._build_enriched_query(query, context_info, chat_history)
        
        logger.info(f"✅ [CONTEXT] Query enriched:")
        logger.info(f"   Original: '{query}'")
        logger.info(f"   Enriched: '{enriched_query}'")
        logger.info(f"   Context: {context_info['summary']}")
        
        return {
            'enriched_query': enriched_query,
            'original_query': query,
            'context_used': True,
            'context_info': context_info
        }
    
    def _build_enriched_query(
        self,
        query: str,
        context_info: Dict[str, Any],
        chat_history: List[Dict[str, str]]
    ) -> str:
        """ساخت query غنی‌شده"""
        
        # الگوهای خاص برای انواع سوالات
        query_lower = query.lower()
        
        # 1. سوالات پرداخت/پول
        if re.search(r'(چقدر|چند).*?(پول|مبلغ|بودجه)', query_lower):
            if 'صندوق نوآور' in context_info['topics']:
                return f"در صندوق نوآور {query}"
            elif 'صندوق باور' in context_info['topics']:
                return f"در صندوق باور {query}"
            elif 'پرداخت' in context_info['topics'] or 'همکاری' in context_info['topics']:
                # استخراج صندوق از history
                last_msg = chat_history[-1] if chat_history else {}
                last_text = (last_msg.get('user', '') + ' ' + last_msg.get('assistant', '')).lower()
                
                if 'نوآور' in last_text:
                    return f"در صندوق نوآور {query}"
                elif 'باور' in last_text:
                    return f"در صندوق باور {query}"
        
        # 2. سوالات کوتاه با last_topic
        if context_info.get('last_topic'):
            topic = context_info['last_topic']
            
            # اگر query شروع با "خب" یا "پس" یا "بعد"
            if re.match(r'^(خب|پس|بعد)', query_lower):
                return f"{query} در {topic}"
            
            # اگر query خیلی کوتاه است
            if len(query.split()) <= 3:
                # استفاده از last assistant response برای context بهتر
                if chat_history:
                    last_assistant = chat_history[-1].get('assistant', '')
                    
                    # استخراج موضوع اصلی از پاسخ قبلی
                    if 'صندوق' in topic.lower() and 'صندوق' not in query_lower:
                        return f"{query} در {topic}"
        
        # 3. Default: افزودن summary
        if context_info['summary']:
            return f"{query} ({context_info['summary']})"
        
        return query

