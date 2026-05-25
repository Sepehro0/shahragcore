# -*- coding: utf-8 -*-
"""
Document Domain Classifier
تشخیص خودکار دامنه/حوزه اسناد با استفاده از Qwen LLM و fallback heuristics
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


class DocumentDomain:
    """دامنه‌های پشتیبانی شده"""
    FINANCIAL = "financial"  # مالی و بودجه
    EDUCATIONAL = "educational"  # آموزشی و تحقیقاتی
    TECHNICAL = "technical"  # فنی و تکنولوژی
    MEDICAL = "medical"  # پزشکی و سلامت
    LEGAL = "legal"  # حقوقی و قانونی
    GENERAL = "general"  # عمومی
    
    ALL_DOMAINS = [FINANCIAL, EDUCATIONAL, TECHNICAL, MEDICAL, LEGAL, GENERAL]
    
    DOMAIN_NAMES_FA = {
        FINANCIAL: "مالی و بودجه",
        EDUCATIONAL: "آموزشی و تحقیقاتی",
        TECHNICAL: "فنی و تکنولوژی",
        MEDICAL: "پزشکی و سلامت",
        LEGAL: "حقوقی و قانونی",
        GENERAL: "عمومی"
    }


class DocumentDomainClassifier:
    """
    کلاس تشخیص دامنه سند با استفاده از:
    1. Qwen LLM (zero-shot classification)
    2. Heuristic fallback (کلمات کلیدی)
    """
    
    def __init__(self, qwen_client=None):
        """
        Args:
            qwen_client: کلاینت Qwen برای classification (اختیاری)
        """
        self.qwen_client = qwen_client
        
        # کلمات کلیدی برای هر دامنه
        self.domain_keywords = {
            DocumentDomain.FINANCIAL: [
                'بودجه', 'budget', 'مالی', 'financial', 'هزینه', 'درآمد', 'expense', 'revenue',
                'تخصیص', 'allocation', 'سازمان', 'دولتی', 'طبقه‌بندی', 'classification',
                'بند', 'بخش', 'قسمت', 'clause', 'section', 'ریال', 'تومان', 'میلیون',
                'میلیارد', 'حساب', 'account', 'دارایی', 'asset', 'بدهی', 'liability',
                'سرمایه', 'capital', 'اعتبار', 'credit', 'سال مالی', 'fiscal year'
            ],
            DocumentDomain.EDUCATIONAL: [
                'آموزش', 'education', 'learning', 'یادگیری', 'دانشگاه', 'university',
                'تحقیق', 'research', 'مقاله', 'paper', 'article', 'دانشجو', 'student',
                'استاد', 'professor', 'teacher', 'معلم', 'درس', 'lesson', 'course',
                'کلاس', 'class', 'آزمون', 'exam', 'test', 'تمرین', 'exercise',
                'مفهوم', 'concept', 'نظریه', 'theory', 'روش', 'method', 'مطالعه',
                'study', 'تحلیل', 'analysis', 'پژوهش', 'محقق', 'researcher',
                'tutorial', 'guide', 'راهنما', 'آموزشی', 'instructional',
                'agent', 'agents', 'multi-agent', 'reinforcement', 'supervised',
                'دوره', 'period', 'دوره آموزشی', 'training', 'دوره تخصصی',
                'واحد آموزش', 'آموزش های تخصصی', 'ذی نفع', 'کاربران عمومی',
                'zinaf', 'dakheli', 'karbaran', 'omomi', 'سوال', 'پاسخ', 'question', 'answer'
            ],
            DocumentDomain.TECHNICAL: [
                'api', 'code', 'کد', 'برنامه', 'program', 'software', 'نرم‌افزار',
                'algorithm', 'الگوریتم', 'function', 'تابع', 'method', 'متد',
                'class', 'کلاس', 'interface', 'رابط', 'database', 'پایگاه داده',
                'server', 'سرور', 'client', 'کلاینت', 'network', 'شبکه',
                'protocol', 'پروتکل', 'architecture', 'معماری', 'framework',
                'library', 'کتابخانه', 'module', 'ماژول', 'package', 'پکیج',
                'deployment', 'استقرار', 'config', 'configuration', 'پیکربندی',
                'docker', 'kubernetes', 'gpu', 'cpu', 'memory', 'حافظه',
                'model', 'مدل', 'training', 'inference', 'استنتاج',
                'rag', 'retrieval-augmented', 'llm', 'embedding', 'vector', 'بردار'
            ],
            DocumentDomain.MEDICAL: [
                'پزشکی', 'medical', 'بیمار', 'patient', 'درمان', 'treatment',
                'دارو', 'drug', 'medicine', 'بیماری', 'disease', 'illness',
                'تشخیص', 'diagnosis', 'جراحی', 'surgery', 'عمل', 'operation',
                'دکتر', 'doctor', 'پزشک', 'physician', 'بیمارستان', 'hospital',
                'کلینیک', 'clinic', 'آزمایش', 'test', 'laboratory', 'آزمایشگاه',
                'سلامت', 'health', 'بهداشت', 'hygiene', 'واکسن', 'vaccine'
            ],
            DocumentDomain.LEGAL: [
                'قانون', 'law', 'legal', 'حقوقی', 'ماده', 'article', 'clause',
                'تبصره', 'note', 'دادگاه', 'court', 'قاضی', 'judge', 'وکیل',
                'lawyer', 'attorney', 'قرارداد', 'contract', 'agreement', 'توافق',
                'مجازات', 'punishment', 'penalty', 'جریمه', 'fine', 'محکومیت',
                'verdict', 'حکم', 'شکایت', 'complaint', 'دعوی', 'lawsuit'
            ],
            DocumentDomain.GENERAL: [
                'عمومی', 'general', 'اطلاعات', 'information', 'گزارش', 'report'
            ]
        }
    
    async def classify_document(
        self,
        chunks: List[Dict[str, Any]],
        filename: str = "",
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        تشخیص دامنه سند با استفاده ترکیبی از LLM + Heuristic
        
        Args:
            chunks: لیست chunks سند
            filename: نام فایل (می‌تواند راهنمای اضافی باشد)
            use_llm: استفاده از LLM برای classification
        
        Returns:
            {
                'domain': str,  # نوع دامنه
                'confidence': float,  # اطمینان (0-1)
                'keywords': List[str],  # کلمات کلیدی استخراج شده
                'summary': str,  # خلاصه کوتاه از محتوا
                'method': str  # روش تشخیص: 'llm', 'heuristic', یا 'hybrid'
            }
        """
        logger.info(f"🔍 Classifying document domain: {filename}")
        
        # مرحله 1: همیشه heuristic را محاسبه کن (سریع و رایگان)
        logger.info("📊 Running heuristic classification...")
        heuristic_result = self._classify_with_heuristics(chunks, filename)
        logger.info(f"   Heuristic: {heuristic_result['domain']} (confidence: {heuristic_result['confidence']:.2f})")
        
        # مرحله 2: اگر LLM فعال است، از آن هم استفاده کن
        llm_result = None
        if use_llm and self.qwen_client:
            try:
                logger.info("🤖 Running LLM classification...")
                llm_result = await self._classify_with_llm(chunks, filename)
                if llm_result:
                    logger.info(f"   LLM: {llm_result['domain']} (confidence: {llm_result['confidence']:.2f})")
            except Exception as e:
                logger.warning(f"⚠️  LLM classification failed: {e}")
        
        # مرحله 3: ترکیب نتایج
        if llm_result and llm_result.get('confidence', 0) > 0.6:
            # اگر LLM confidence بالایی دارد، از آن استفاده کن
            if llm_result['domain'] == heuristic_result['domain']:
                # هر دو روش موافق هستند - confidence بالا
                logger.info(f"✅ HYBRID: Both methods agree on '{llm_result['domain']}'")
                return {
                    'domain': llm_result['domain'],
                    'confidence': min(0.95, (llm_result['confidence'] + heuristic_result['confidence']) / 2 + 0.1),
                    'keywords': list(set(llm_result.get('keywords', []) + heuristic_result.get('keywords', [])))[:15],
                    'summary': llm_result.get('summary', heuristic_result.get('summary', '')),
                    'method': 'hybrid'
                }
            else:
                # روش‌ها مختلف هستند - از روشی با confidence بالاتر استفاده کن
                if llm_result['confidence'] > heuristic_result['confidence'] + 0.2:
                    logger.info(f"✅ LLM has higher confidence: {llm_result['domain']}")
                    llm_result['method'] = 'llm'
                    return llm_result
                else:
                    logger.info(f"✅ Heuristic has higher confidence: {heuristic_result['domain']}")
                    heuristic_result['method'] = 'heuristic_preferred'
                    return heuristic_result
        
        # مرحله 4: فقط heuristic
        logger.info(f"✅ Using heuristic result: {heuristic_result['domain']}")
        return heuristic_result
    
    async def _classify_with_llm(
        self,
        chunks: List[Dict[str, Any]],
        filename: str
    ) -> Optional[Dict[str, Any]]:
        """تشخیص دامنه با استفاده از Qwen LLM"""
        if not self.qwen_client:
            return None
        
        # انتخاب sample از chunks (حداکثر 5 chunk اول)
        sample_chunks = chunks[:5]
        sample_text = "\n\n".join([
            chunk.get('text', '')[:500]  # حداکثر 500 کاراکتر از هر chunk
            for chunk in sample_chunks
            if chunk.get('text', '').strip()
        ])
        
        if not sample_text.strip():
            return None
        
        # ساخت prompt برای classification
        prompt = f"""لطفاً دامنه/حوزه این سند را تشخیص دهید.

**نام فایل:** {filename}

**نمونه محتوا:**
{sample_text[:2000]}

**دامنه‌های موجود:**
1. مالی و بودجه (financial): اسناد مربوط به بودجه، هزینه، درآمد، تخصیص منابع مالی
2. آموزشی و تحقیقاتی (educational): مقالات، راهنماها، آموزش‌ها، تحقیقات علمی
3. فنی و تکنولوژی (technical): مستندات فنی، API، کد، معماری نرم‌افزار، راهنمای فنی
4. پزشکی و سلامت (medical): اسناد پزشکی، درمان، بیماری‌ها، سلامت
5. حقوقی و قانونی (legal): قوانین، قراردادها، مقررات، احکام
6. عمومی (general): سایر موارد که در دسته‌های بالا نمی‌گنجند

لطفاً پاسخ خود را به صورت JSON با فرمت زیر ارائه دهید:
{{
    "domain": "نام دامنه به انگلیسی (مثلاً technical)",
    "confidence": عدد بین 0 تا 1,
    "keywords": ["کلمه کلیدی 1", "کلمه کلیدی 2", ...],
    "summary": "خلاصه کوتاه از موضوع سند (حداکثر 200 کاراکتر)"
}}

فقط JSON را برگردانید، بدون توضیحات اضافی."""
        
        try:
            # فراخوانی Qwen
            response = await self.qwen_client.generate_response(
                prompt=prompt,
                temperature=0.1,
                max_tokens=500
            )
            
            # پارس JSON از response
            result = self._extract_json_from_response(response)
            
            if result and 'domain' in result:
                # اعتبارسنجی domain
                domain = result['domain'].lower()
                if domain not in DocumentDomain.ALL_DOMAINS:
                    logger.warning(f"Invalid domain from LLM: {domain}, falling back")
                    return None
                
                return {
                    'domain': domain,
                    'confidence': float(result.get('confidence', 0.7)),
                    'keywords': result.get('keywords', [])[:10],  # حداکثر 10 کلمه
                    'summary': result.get('summary', '')[:500],  # حداکثر 500 کاراکتر
                    'method': 'llm'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"LLM classification error: {e}")
            return None
    
    def _extract_json_from_response(self, response) -> Optional[Dict]:
        """استخراج JSON از response LLM"""
        try:
            # اگر response رشته نبود، تبدیل کن
            if not isinstance(response, str):
                response = str(response)
            
            # حذف markdown code blocks
            cleaned = re.sub(r'```json\s*', '', response)
            cleaned = re.sub(r'```\s*', '', cleaned)
            cleaned = cleaned.strip()
            
            # پیدا کردن اولین JSON object
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            
            if start != -1 and end != -1:
                json_str = cleaned[start:end+1]
                return json.loads(json_str)
            
            return None
        except Exception as e:
            logger.error(f"JSON extraction failed: {e}")
            logger.debug(f"Response type: {type(response)}, Response content: {str(response)[:200]}")
            return None
    
    def _classify_with_heuristics(
        self,
        chunks: List[Dict[str, Any]],
        filename: str
    ) -> Dict[str, Any]:
        """تشخیص دامنه با استفاده از heuristics (کلمات کلیدی)"""
        
        # ترکیب متن chunks (sample)
        sample_size = min(10, len(chunks))
        chunk_texts = []
        
        # فقط chunks با محتوای واقعی (نه structure summary)
        for chunk in chunks[:sample_size]:
            chunk_text = chunk.get('text', '')
            # رد کردن structure summary
            if chunk.get('metadata', {}).get('type') != 'structure_summary':
                # فقط متن انگلیسی واقعی (نه RTL reversed)
                if len(chunk_text) > 50 and any(c.isalnum() for c in chunk_text):
                    chunk_texts.append(chunk_text[:1000])
        
        combined_text = " ".join(chunk_texts).lower()
        
        # اضافه کردن filename به text (با وزن بیشتر)
        combined_text += " " + filename.lower() * 5  # وزن بیشتر برای filename
        
        # شمارش کلمات کلیدی هر دامنه
        domain_scores = {}
        matched_keywords = {}
        
        for domain, keywords in self.domain_keywords.items():
            score = 0
            matches = []
            
            for keyword in keywords:
                keyword_lower = keyword.lower()
                count = combined_text.count(keyword_lower)
                if count > 0:
                    score += count
                    matches.append(keyword)
            
            domain_scores[domain] = score
            matched_keywords[domain] = matches
        
        # پیدا کردن دامنه با بالاترین امتیاز
        if not domain_scores or max(domain_scores.values()) == 0:
            # هیچ کلمه کلیدی پیدا نشد - default به general
            detected_domain = DocumentDomain.GENERAL
            confidence = 0.5
            keywords_found = []
        else:
            detected_domain = max(domain_scores, key=domain_scores.get)
            
            # محاسبه confidence بر اساس نسبت امتیازها
            total_score = sum(domain_scores.values())
            max_score = domain_scores[detected_domain]
            confidence = min(0.95, max_score / (total_score + 1))  # +1 برای جلوگیری از division by zero
            
            keywords_found = matched_keywords[detected_domain][:10]
        
        # تولید خلاصه ساده
        summary = self._generate_simple_summary(detected_domain, chunks[:3])
        
        logger.info(f"📊 Heuristic classification: {detected_domain} (confidence: {confidence:.2f})")
        logger.info(f"   Matched keywords: {', '.join(keywords_found[:5])}")
        
        return {
            'domain': detected_domain,
            'confidence': confidence,
            'keywords': keywords_found,
            'summary': summary,
            'method': 'heuristic',
            'domain_scores': domain_scores  # برای debugging
        }
    
    def _generate_simple_summary(
        self,
        domain: str,
        sample_chunks: List[Dict[str, Any]]
    ) -> str:
        """تولید خلاصه ساده بر اساس دامنه"""
        
        domain_summaries = {
            DocumentDomain.FINANCIAL: "سند مالی و بودجه شامل اطلاعات تخصیص منابع، هزینه‌ها و درآمدها",
            DocumentDomain.EDUCATIONAL: "سند آموزشی و تحقیقاتی شامل مفاهیم، توضیحات و مطالب علمی",
            DocumentDomain.TECHNICAL: "سند فنی شامل اطلاعات تکنولوژی، معماری، API و راهنماهای فنی",
            DocumentDomain.MEDICAL: "سند پزشکی شامل اطلاعات سلامت، درمان و بیماری‌ها",
            DocumentDomain.LEGAL: "سند حقوقی شامل قوانین، مقررات و احکام",
            DocumentDomain.GENERAL: "سند عمومی شامل اطلاعات متنوع"
        }
        
        base_summary = domain_summaries.get(domain, "سند با محتوای متنوع")
        
        # سعی در استخراج عنوان از chunks
        for chunk in sample_chunks:
            text = chunk.get('text', '')
            # جستجوی الگوهای عنوان
            title_match = re.search(r'(?:عنوان|Title|Subject|موضوع)\s*:?\s*(.+?)(?:\n|$)', text)
            if title_match:
                title = title_match.group(1).strip()[:200]
                return f"{base_summary}: {title}"
        
        return base_summary
    
    def get_domain_display_name(self, domain: str) -> str:
        """دریافت نام فارسی دامنه"""
        return DocumentDomain.DOMAIN_NAMES_FA.get(domain, "نامشخص")


