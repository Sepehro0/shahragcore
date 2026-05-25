# -*- coding: utf-8 -*-
"""
Conversation Utilities
ابزارهای مدیریت conversation و follow-up detection
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def is_follow_up_query(
    query: str,
    chat_history: Optional[List[Dict[str, str]]] = None
) -> bool:
    """
    تشخیص اینکه آیا سوال یک follow-up است یا نه
    
    Args:
        query: سوال کاربر
        chat_history: تاریخچه چت
        
    Returns:
        True اگر سوال follow-up باشد
    """
    if not chat_history or len(chat_history) == 0:
        logger.debug("No chat history, not a follow-up")
        return False
    
    query_lower = query.lower().strip()
    
    # کلمات کلیدی follow-up
    follow_up_indicators = [
        # ضمایر اشاره
        'این', 'آن', 'اینا', 'اونا', 'اینها', 'آنها',
        # ضمایر فاعلی/مفعولی
        'اون', 'اینو', 'اونو', 'آن را', 'این را',
        # کلمات پرسشی follow-up
        'کدوم', 'کدومش', 'کدامش', 'کدام', 'کدام یک',
        # عبارات مقایسه‌ای
        'مناسب تر', 'بهتر', 'بدتر', 'برتر',
        # سوالات کوتاه (< 5 کلمه معمولاً follow-up هستند)
    ]
    
    for indicator in follow_up_indicators:
        if indicator in query_lower:
            logger.info(f"🔗 Follow-up detected: indicator '{indicator}' found in query")
            return True
    
    # اگر سوال خیلی کوتاه است (< 6 کلمه) احتمالاً follow-up است
    words = query.split()
    if len(words) <= 5 and len(chat_history) > 0:
        logger.info(f"🔗 Follow-up detected: short query ({len(words)} words) with existing history")
        return True
    
    logger.debug("Not a follow-up query")
    return False


def build_conversation_context(
    query: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    max_messages: int = 2,
    include_answers: bool = True
) -> str:
    """
    ساخت context از conversation history
    
    Args:
        query: سوال فعلی کاربر
        chat_history: تاریخچه چت
        max_messages: حداکثر تعداد پیام‌های قبلی
        include_answers: آیا پاسخ‌های قبلی را هم شامل شود؟
        
    Returns:
        متن context برای اضافه کردن به prompt
    """
    if not chat_history or len(chat_history) == 0:
        return ""
    
    # بررسی اینکه آیا سوال follow-up است
    is_followup = is_follow_up_query(query, chat_history)
    
    # اگر follow-up نیست، فقط سوالات قبلی کافی است
    if not is_followup:
        history_text = "\n\n### سوالات قبلی کاربر:\n"
        for msg in chat_history[-max_messages:]:
            history_text += f"- {msg['user']}\n"
        return history_text
    
    # اگر follow-up است، سوالات و پاسخ‌های قبلی را شامل شو
    history_text = "\n\n### بافت گفتگوی قبلی:\n"
    history_text += "(این سوال ادامه گفتگوی قبلی است و باید با توجه به context زیر پاسخ داده شود)\n\n"
    
    for i, msg in enumerate(chat_history[-max_messages:]):
        history_text += f"**گفتگوی {i+1}:**\n"
        history_text += f"کاربر: {msg['user']}\n"
        
        if include_answers and msg.get('assistant'):
            # خلاصه پاسخ (اگر خیلی طولانی باشد)
            assistant_answer = msg['assistant']
            if len(assistant_answer) > 500:
                assistant_answer = assistant_answer[:500] + "..."
            history_text += f"دستیار: {assistant_answer}\n"
        
        history_text += "\n"
    
    return history_text


def enhance_follow_up_query(
    query: str,
    chat_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    بهبود سوال follow-up با اضافه کردن context از سوال قبلی
    
    Args:
        query: سوال فعلی
        chat_history: تاریخچه چت
        
    Returns:
        سوال بهبود یافته
    """
    if not chat_history or len(chat_history) == 0:
        return query
    
    if not is_follow_up_query(query, chat_history):
        return query
    
    # سوال قبلی
    last_user_query = chat_history[-1].get('user', '')
    
    # اگر سوال قبلی در مورد مقایسه بود، context را اضافه کن
    if any(word in last_user_query.lower() for word in ['فرق', 'تفاوت', 'مقایسه', 'بهتر']):
        # استخراج موضوعات سوال قبلی
        enhanced_query = f"با توجه به سوال قبلی ({last_user_query}): {query}"
        return enhanced_query
    
    return query

