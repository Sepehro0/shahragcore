# -*- coding: utf-8 -*-
"""
Fund Knowledge Base
دانش پایه تفاوت‌های صندوق‌ها برای پاسخ‌دهی هوشمند
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ==========================================
# تفاوت‌های کلیدی صندوق‌ها
# ==========================================

FUND_KEY_DIFFERENCES = {
    "ایده_خام": {
        "description": "پذیرش ایده‌های خام و اولیه",
        "صندوق نوآور": {
            "status": True,
            "detail": "بله؛ صندوق نوآور برای ایده‌های خام و اولیه طراحی شده است. این صندوق به تیم‌ها کمک می‌کند ایده‌های پژوهشی یا فناورانه خود را به نمونه اولیه (Prototype/MVP) تبدیل کنند."
        },
        "صندوق باور": {
            "status": False,
            "detail": "خیر؛ صندوق باور برای استارتاپ‌هایی است که از مرحله ایده عبور کرده‌اند و محصول اولیه (MVP) دارند. ایده خام در صندوق باور پذیرفته نمی‌شود."
        },
        "معاونت توسعه فناوری ": {
            "status": False,
            "detail": "خیر؛ معاونت توسعه فناوری  یک پلتفرم تبادل فناوری است و برای حل مشکلات فنی صنایع طراحی شده، نه برای ایده‌های خام."
        }
    },
    "MVP": {
        "description": "نیاز به محصول اولیه (MVP)",
        "صندوق نوآور": {
            "status": False,
            "detail": "خیر؛ صندوق نوآور نیازی به MVP ندارد و حتی ایده‌های خام را می‌پذیرد. خروجی این صندوق تبدیل ایده به MVP است."
        },
        "صندوق باور": {
            "status": True,
            "detail": "بله؛ صندوق باور شرط ورود داشتن MVP است. استارتاپ باید محصول اولیه تأیید شده (حداقل TRL 3 تا 5) داشته باشد."
        },
        "معاونت توسعه فناوری ": {
            "status": False,
            "detail": "معاونت توسعه فناوری  نیازی به MVP ندارد؛ فقط توانایی حل مشکل فنی صنعت مهم است."
        }
    },
    "سهام": {
        "description": "دریافت سهام از تیم",
        "صندوق نوآور": {
            "status": False,
            "detail": "خیر؛ صندوق نوآور سهامی دریافت نمی‌کند. مالکیت فکری (IP) متعلق به تیم فناور باقی می‌ماند."
        },
        "صندوق باور": {
            "status": True,
            "detail": "بله؛ صندوق باور در ازای سرمایه‌گذاری، حداکثر ۲۰٪ سهام شرکت را دریافت می‌کند."
        },
        "معاونت توسعه فناوری ": {
            "status": False,
            "detail": "خیر؛ معاونت توسعه فناوری  قرارداد پیمانکاری می‌بندد و سهامی دریافت نمی‌کند."
        }
    },
    "ثبت_شرکت": {
        "description": "نیاز به ثبت شرکت",
        "صندوق نوآور": {
            "status": False,
            "detail": "خیر؛ در صندوق نوآور نیازی به ثبت شرکت در مراحل اولیه نیست. تیم‌های دانشجویی و پژوهشگران مستقل هم می‌توانند شرکت کنند."
        },
        "صندوق باور": {
            "status": True,
            "detail": "بله؛ برای صندوق باور باید شرکت ثبت شده داشته باشید چون قرار است سهام دریافت شود."
        },
        "معاونت توسعه فناوری ": {
            "status": True,
            "detail": "معمولاً بله؛ برای قرارداد پیمانکاری نیاز به شخصیت حقوقی است."
        }
    },
    "مدل_همکاری": {
        "description": "نوع همکاری با صندوق",
        "صندوق نوآور": {
            "status": None,
            "detail": "پرداخت مرحله‌ای: بودجه پس از تأیید خروجی هر فاز آزاد می‌شود. مالکیت فکری متعلق به تیم است."
        },
        "صندوق باور": {
            "status": None,
            "detail": "شراکتی: سرمایه‌گذاری در ازای سهام (حداکثر ۲۰٪). مدت شراکت معمولاً ۵ سال."
        },
        "معاونت توسعه فناوری ": {
            "status": None,
            "detail": "پیمانکاری: قرارداد پروژه‌ای برای حل مشکل فنی صنعت. پرداخت بر اساس قرارداد."
        }
    }
}



# ==========================================
# کلمات کلیدی برای تشخیص موضوع
# ==========================================

TOPIC_KEYWORDS = {
    "ایده_خام": ["ایده خام", "ایده اولیه", "خیلی خام", "ایده ناقص", "ایده‌ خام", "خام بودن"],
    "MVP": ["mvp", "محصول اولیه", "نمونه اولیه", "prototype", "پروتوتایپ", "نمونه آزمایشگاهی"],
    "سهام": ["سهام", "شراکت", "equity", "سهامدار", "درصد سهام"],
    "ثبت_شرکت": ["ثبت شرکت", "شخصیت حقوقی", "شرکت ثبت", "بدون شرکت"],
    "مدل_همکاری": ["مدل همکاری", "نوع همکاری", "چطور همکاری", "شرایط همکاری"]
}


def detect_topic_from_query(query: str) -> List[str]:
    """
    تشخیص موضوعات مطرح در سوال کاربر
    
    Args:
        query: سوال کاربر
        
    Returns:
        لیست موضوعات تشخیص داده شده
    """
    query_lower = query.lower().replace('‌', ' ')
    detected_topics = []
    
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in query_lower:
                detected_topics.append(topic)
                break
    
    return detected_topics


def detect_fund_from_query(query: str) -> Optional[str]:
    """
    تشخیص صندوق مورد نظر در سوال
    
    Args:
        query: سوال کاربر
        
    Returns:
        نام صندوق یا None
    """
    query_lower = query.lower().replace('‌', ' ')
    
    if 'باور' in query_lower:
        return 'صندوق باور'
    elif 'نوآور' in query_lower:
        return 'صندوق نوآور'
    elif 'تبادل فناوری' in query_lower:
        return 'صندوق تبادل فناوری'
    
    return None


def get_fund_specific_answer(query: str, detected_topics: List[str], asked_fund: str) -> Optional[str]:
    """
    دریافت پاسخ خاص بر اساس صندوق و موضوع
    
    Args:
        query: سوال کاربر
        detected_topics: موضوعات تشخیص داده شده
        asked_fund: صندوق مورد سوال
        
    Returns:
        پاسخ خاص یا None
    """
    if not detected_topics or not asked_fund:
        return None
    
    responses = []
    
    for topic in detected_topics:
        if topic in FUND_KEY_DIFFERENCES:
            topic_info = FUND_KEY_DIFFERENCES[topic]
            
            if asked_fund in topic_info:
                fund_info = topic_info[asked_fund]
                responses.append(fund_info["detail"])
    
    if responses:
        return "\n\n".join(responses)
    
    return None


def get_cross_fund_warning(query: str, sources_fund: str, asked_fund: str) -> Optional[str]:
    """
    تولید هشدار برای تفاوت صندوق سوال و منابع
    
    Args:
        query: سوال کاربر
        sources_fund: صندوق منابع بازیابی شده
        asked_fund: صندوق مورد سوال کاربر
        
    Returns:
        متن هشدار یا None
    """
    if sources_fund == asked_fund:
        return None
    
    # تشخیص موضوعات
    topics = detect_topic_from_query(query)
    
    if not topics:
        return None
    
    # بررسی تفاوت‌های کلیدی
    warnings = []
    
    for topic in topics:
        if topic in FUND_KEY_DIFFERENCES:
            topic_info = FUND_KEY_DIFFERENCES[topic]
            
            # اطلاعات صندوق منابع
            sources_info = topic_info.get(sources_fund, {})
            sources_status = sources_info.get("status")
            
            # اطلاعات صندوق سوال
            asked_info = topic_info.get(asked_fund, {})
            asked_status = asked_info.get("status")
            asked_detail = asked_info.get("detail", "")
            
            # اگر وضعیت متفاوت است
            if sources_status != asked_status and asked_detail:
                warnings.append(f"""
⚠️ **توجه مهم**:
اطلاعات بازیابی شده مربوط به **{sources_fund}** است، اما شما درباره **{asked_fund}** پرسیده‌اید.

**پاسخ صحیح برای {asked_fund}:**
{asked_detail}
""")
    
    if warnings:
        return "\n".join(warnings)
    
    return None


def get_smart_fund_context(query: str, asked_fund: Optional[str] = None) -> str:
    """
    دریافت context هوشمند بر اساس سوال و صندوق
    
    این تابع فقط وقتی اطلاعات اضافه می‌کند که:
    1. سوال مربوط به تفاوت‌های کلیدی صندوق‌هاست
    2. صندوق خاصی در سوال ذکر شده
    
    Args:
        query: سوال کاربر
        asked_fund: صندوق مورد سوال (اختیاری)
        
    Returns:
        Context اضافی یا رشته خالی
    """
    if not asked_fund:
        asked_fund = detect_fund_from_query(query)
    
    if not asked_fund:
        return ""
    
    # تشخیص موضوعات
    topics = detect_topic_from_query(query)
    
    if not topics:
        return ""
    
    # ساخت context
    context_parts = []
    
    for topic in topics:
        if topic in FUND_KEY_DIFFERENCES:
            topic_info = FUND_KEY_DIFFERENCES[topic]
            
            if asked_fund in topic_info:
                fund_info = topic_info[asked_fund]
                
                # اضافه کردن تفاوت با سایر صندوق‌ها
                context_parts.append(f"""
📌 **{topic_info['description']} در {asked_fund}:**
{fund_info['detail']}
""")
    
    if context_parts:
        header = f"""
---
## 🎯 اطلاعات کلیدی درباره {asked_fund}
"""
        return header + "\n".join(context_parts)
    
    return ""


# ==========================================
# اطلاعات کلی صندوق‌ها (برای fallback)
# ==========================================

FUND_FULL_INFO = {
    "صندوق باور": """
**صندوق باور (Bavar Fund)** - سرمایه‌گذاری بذری (Seed Capital)

• **تعریف**: حلقه واسط میان «نمونه آزمایشگاهی» و «تولید صنعتی»
• **مخاطب**: استارتاپ‌هایی که از مرحله ایده عبور کرده‌اند و MVP دارند
• **شرط ورود**: 
  - داشتن MVP (حداقل TRL 3 تا 5)
  - طرح کسب‌وکار (Business Plan) مشخص
  - ثبت شرکت
• **مدل همکاری**: شراکتی
  - دریافت حداکثر ۲۰٪ سهام
  - مدت شراکت معمولاً ۵ سال
• **مزیت**: پول هوشمند + دسترسی به شبکه صنعتی بنیاد مستضعفان
• **ایده خام**: ❌ پذیرفته نمی‌شود
""",
    
    "صندوق نوآور": """
**صندوق نوآور (Noavar Fund)** - پیش‌شتابدهی و حمایت از ریسک

• **تعریف**: پر کردن «دره مرگ» بین ایده خام و محصول اولیه
• **مخاطب**: تیم‌های دانشجویی، پژوهشگران، نوآوران مستقل
• **شرط ورود**:
  - ایده فناورانه یا پژوهشی
  - نیازی به MVP نیست
  - نیازی به ثبت شرکت نیست
• **مدل همکاری**: پرداخت مرحله‌ای
  - بدون دریافت سهام
  - مالکیت فکری (IP) متعلق به تیم
• **خروجی**: تبدیل ایده به MVP
• **ایده خام**: ✅ پذیرفته می‌شود
""",
    
    "معاونت توسعه فناوری ": """
**معاونت توسعه فناوری  ** - تبادل فناوری

• **تعریف**: پلتفرم تبادل فناوری (Reverse Pitch)
• **مخاطب**: شرکت‌های فنی‌مهندسی و دانش‌بنیان
• **نوع همکاری**: قرارداد پیمانکاری
  - حل مشکلات فنی صنایع بنیاد مستضعفان
  - پرداخت بر اساس قرارداد
• **سهام**: ❌ گرفته نمی‌شود
• **ایده خام**: ❌ نیاز به توانایی حل مشکل فنی
"""
}

