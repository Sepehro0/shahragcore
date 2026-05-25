# -*- coding: utf-8 -*-
"""
Suggestion Generator
تولید سوالات پیشنهادی مرتبط برای کاربر
"""

import logging
from typing import List, Dict, Any, Optional
import re

logger = logging.getLogger(__name__)


class SuggestionGenerator:
    """
    تولید سوالات پیشنهادی هوشمند بر اساس:
    - سوال فعلی کاربر
    - پاسخ داده شده
    - نتایج database
    - ساختار collection
    """
    
    def __init__(self, qwen_client=None):
        """Initialize suggestion generator"""
        self.qwen_client = qwen_client
        
        # الگوهای رایج سوالات
        self.question_patterns = {
            "financial": {
                "aggregation": [
                    "مجموع {entity} در {timeframe} چقدر بوده است؟",
                    "میانگین {metric} {entity} در {period} چقدر است؟",
                    "{entity} چقدر {metric} داشته است؟"
                ],
                "comparison": [
                    "تفاوت {metric} {entity} در {year1} و {year2} چقدر است؟",
                    "{entity1} و {entity2} کدام بیشتر {metric} داشته‌اند؟",
                    "مقایسه {metric} {entity} در {period} با {period2}"
                ],
                "top_n": [
                    "کدام {entities} بیشترین {metric} را داشته‌اند؟",
                    "{n} {entity} برتر از نظر {metric} کدامند؟",
                    "رتبه‌بندی {entities} بر اساس {metric}"
                ],
                "breakdown": [
                    "{metric} {entity} از چه {components} تشکیل شده است؟",
                    "جزئیات {metric} {entity} در {dimension}",
                    "تفکیک {metric} {entity} به تفکیک {category}"
                ],
                "trend": [
                    "روند {metric} {entity} در {period} چطور بوده است؟",
                    "تغییرات {metric} {entity} از {year1} تا {year2}",
                    "آیا {metric} {entity} رو به رشد بوده است؟"
                ]
            }
        }
    
    async def generate_suggestions(
        self,
        original_query: str,
        answer: str,
        database_results: Optional[Dict[str, Any]] = None,
        domain: str = "financial",
        collection_name: Optional[str] = None,
        query_analysis: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        تولید 3 سوال پیشنهادی مرتبط
        
        Args:
            original_query: سوال اصلی کاربر
            answer: پاسخ داده شده
            database_results: نتایج database (اگر وجود دارد)
            domain: دامنه سوال (financial, educational, ...)
            collection_name: نام collection
            query_analysis: تحلیل query (از QueryAnalyzer)
            
        Returns:
            لیست 3 سوال پیشنهادی
        """
        try:
            suggestions = []
            
            # روش 1: استفاده از LLM (اگر موجود باشد)
            if self.qwen_client and len(answer) > 50:
                llm_suggestions = await self._generate_with_llm(
                    original_query, answer, database_results, query_analysis
                )
                if llm_suggestions and len(llm_suggestions) >= 3:
                    return llm_suggestions[:3]
                suggestions.extend(llm_suggestions)
            
            # روش 2: Rule-based generation (fallback یا تکمیل‌کننده)
            rule_suggestions = self._generate_with_rules(
                original_query, database_results, domain, query_analysis
            )
            suggestions.extend(rule_suggestions)
            
            # انتخاب 3 سوال برتر (unique و متنوع)
            unique_suggestions = self._deduplicate_suggestions(suggestions)
            
            # اگر کمتر از 3 تا داریم، generic suggestions اضافه کن
            if len(unique_suggestions) < 3:
                generic = self._generate_generic_suggestions(
                    original_query, domain, query_analysis
                )
                unique_suggestions.extend(generic)
            
            return unique_suggestions[:3]
            
        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            # Fallback: حداقل یک سوال کلی برگردان
            return self._generate_fallback_suggestions(original_query, domain)
    
    async def _generate_with_llm(
        self,
        query: str,
        answer: str,
        database_results: Optional[Dict[str, Any]],
        query_analysis: Optional[Dict[str, Any]]
    ) -> List[str]:
        """تولید سوالات با استفاده از LLM"""
        try:
            # ساخت context برای LLM
            context = f"سوال کاربر: {query}\n\nپاسخ: {answer[:500]}\n\n"
            
            if database_results and database_results.get('results'):
                context += f"تعداد نتایج: {len(database_results['results'])}\n"
                if database_results.get('columns'):
                    context += f"ستون‌ها: {', '.join(database_results['columns'][:5])}\n"
            
            prompt = f"""بر اساس سوال و پاسخ زیر، 3 سوال مرتبط و مفید برای ادامه جستجوی کاربر پیشنهاد بده.

{context}

سوالات پیشنهادی باید:
1. مرتبط با موضوع اصلی باشند
2. اطلاعات جدیدی به کاربر بدهند
3. واضح و قابل فهم باشند

فقط 3 سوال را در خطوط جداگانه بنویس (بدون شماره):
"""
            
            # فراخوانی LLM
            response = await self.qwen_client.generate(
                prompt,
                max_tokens=200,
                temperature=0.7,
                stop=["\n\n", "سوال 4"]
            )
            
            # Parse کردن پاسخ
            if response and response.get('text'):
                lines = response['text'].strip().split('\n')
                suggestions = []
                for line in lines:
                    line = line.strip()
                    # حذف شماره اول سطر (1. 2. 3. یا ۱. ۲. ۳.)
                    line = re.sub(r'^[\d۰-۹]+[\.\)]\s*', '', line)
                    if line and len(line) > 10 and '؟' in line:
                        suggestions.append(line)
                
                return suggestions[:3]
            
        except Exception as e:
            logger.warning(f"LLM suggestion generation failed: {e}")
        
        return []
    
    def _generate_with_rules(
        self,
        query: str,
        database_results: Optional[Dict[str, Any]],
        domain: str,
        query_analysis: Optional[Dict[str, Any]]
    ) -> List[str]:
        """تولید سوالات با قوانین هوشمند"""
        suggestions = []
        
        if not query_analysis:
            return suggestions
        
        # Extract information
        years = query_analysis.get('years', [])
        entity_filter = query_analysis.get('entity_filter', '')
        query_type = query_analysis.get('query_type', '')
        query_category = query_analysis.get('query_category', '')
        
        # استخراج entity اصلی
        entities = self._extract_entities_from_query(query)
        main_entity = entities[0] if entities else "دستگاه"
        
        # تولید سوالات بر اساس نوع query
        if query_category == 'simple_sum':
            # اگر sum پرسیده، breakdown و comparison پیشنهاد بده
            suggestions.append(
                f"{main_entity} از چه راه‌هایی درآمد کسب کرده است؟"
            )
            if years:
                other_year = self._get_nearby_year(years[0])
                suggestions.append(
                    f"درآمد {main_entity} در سال {other_year} چقدر بوده است؟"
                )
            suggestions.append(
                f"مقایسه درآمد ملی و استانی {main_entity}"
            )
        
        elif query_category == 'top_n':
            # اگر top-n پرسیده، جزئیات اولی‌ها و مقایسه پیشنهاد بده
            suggestions.append(
                f"جزئیات هزینه‌های {main_entity} به تفکیک بخش‌ها"
            )
            if years:
                suggestions.append(
                    f"روند هزینه‌ها در سال‌های {years[0]-1} تا {years[0]+1}"
                )
            suggestions.append(
                f"کم‌هزینه‌ترین دستگاه‌ها در همین دسته کدامند؟"
            )
        
        elif query_category == 'breakdown':
            # اگر breakdown پرسیده، aggregation و comparison پیشنهاد بده
            if years:
                suggestions.append(
                    f"مجموع کل در سال {years[0]} چقدر بوده است؟"
                )
            suggestions.append(
                f"بیشترین سهم مربوط به کدام بخش است؟"
            )
            suggestions.append(
                f"مقایسه با سال قبل چطور است؟"
            )
        
        elif query_category == 'cross_table':
            # اگر cross-table پرسیده، جزئیات و روند پیشنهاد بده
            suggestions.append(
                f"چه دستگاه‌هایی سودآور بوده‌اند؟"
            )
            suggestions.append(
                f"تفکیک درآمد و هزینه به صورت جزئی"
            )
            if years:
                suggestions.append(
                    f"روند سود و زیان در سال‌های اخیر"
                )
        
        # تکمیل با سوالات کلی اگر کم داریم
        if len(suggestions) < 3:
            suggestions.extend(self._generate_variation_questions(query, query_analysis))
        
        return suggestions
    
    def _generate_variation_questions(
        self,
        query: str,
        query_analysis: Optional[Dict[str, Any]]
    ) -> List[str]:
        """تولید variations از سوال اصلی"""
        variations = []
        
        if not query_analysis:
            return variations
        
        years = query_analysis.get('years', [])
        
        # تغییر بازه زمانی
        if years:
            if len(years) == 1:
                # اگر یک سال، range پیشنهاد بده
                year = years[0]
                variations.append(
                    re.sub(r'\d{4}', f"{year} تا {year+2}", query)
                )
            else:
                # اگر range، سال خاص پیشنهاد بده
                variations.append(
                    re.sub(r'\d{4}\s*تا\s*\d{4}', str(years[-1]), query)
                )
        
        # تغییر metric (درآمد <-> هزینه)
        if 'درآمد' in query or 'درامد' in query:
            variations.append(query.replace('درآمد', 'هزینه').replace('درامد', 'هزینه'))
        elif 'هزینه' in query:
            variations.append(query.replace('هزینه', 'درآمد'))
        
        # تغییر aggregation type
        if 'مجموع' in query or 'جمع' in query:
            variations.append(query.replace('مجموع', 'میانگین').replace('جمع', 'میانگین'))
        
        return variations
    
    def _generate_generic_suggestions(
        self,
        query: str,
        domain: str,
        query_analysis: Optional[Dict[str, Any]]
    ) -> List[str]:
        """تولید سوالات عمومی مرتبط"""
        suggestions = []
        
        if domain == "financial":
            years = query_analysis.get('years', []) if query_analysis else []
            current_year = years[0] if years else "1402"
            
            suggestions.extend([
                f"بیشترین درآمدها در سال {current_year} مربوط به کدام دستگاه‌ها بوده است؟",
                f"روند هزینه‌ها در سال‌های اخیر چطور بوده است؟",
                f"مقایسه درآمد ملی و استانی در سال {current_year}",
                "کدام دستگاه‌ها بیشترین رشد را داشته‌اند؟",
                "تفکیک هزینه‌ها به تفکیک نوع"
            ])
        
        return suggestions
    
    def _generate_fallback_suggestions(
        self,
        query: str,
        domain: str
    ) -> List[str]:
        """سوالات fallback در صورت خطا"""
        if domain == "financial":
            return [
                "بیشترین درآمدها مربوط به کدام دستگاه‌ها است؟",
                "روند هزینه‌ها در سال‌های اخیر چطور بوده است؟",
                "مقایسه درآمد و هزینه دستگاه‌های اجرایی"
            ]
        
        return [
            "اطلاعات بیشتر در مورد این موضوع",
            "مقایسه با موارد مشابه",
            "جزئیات و تفکیک اطلاعات"
        ]
    
    def _extract_entities_from_query(self, query: str) -> List[str]:
        """استخراج نام entities از query"""
        entities = []
        
        # الگوهای رایج
        patterns = [
            r'(وزارت\s+[آ-ی]+)',
            r'(سازمان\s+[آ-ی]+(?:\s+[آ-ی]+)?)',
            r'(نهاد\s+[آ-ی]+(?:\s+[آ-ی]+)?)',
            r'(جمعیت\s+[آ-ی]+)',
            r'(انستیتو\s+[آ-ی]+)',
            r'(بنیاد\s+[آ-ی]+)',
            r'([آ-ی]{3,}(?:\s+[آ-ی]+){0,2})\s+در\s+سال'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query)
            entities.extend(matches)
        
        return entities[:3]  # حداکثر 3 entity
    
    def _get_nearby_year(self, year: int) -> int:
        """پیدا کردن سال نزدیک (قبل یا بعد)"""
        # ترجیحاً سال بعد، مگر اینکه سال جاری باشد
        if year >= 1403:
            return year - 1
        return year + 1
    
    def _deduplicate_suggestions(self, suggestions: List[str]) -> List[str]:
        """حذف تکراری‌ها و نگه‌داشتن متنوع‌ترین‌ها"""
        if not suggestions:
            return []
        
        unique = []
        seen_lower = set()
        
        for suggestion in suggestions:
            suggestion = suggestion.strip()
            if not suggestion:
                continue
            
            # normalize برای بررسی تکراری
            normalized = suggestion.lower().replace('؟', '').strip()
            normalized = re.sub(r'\s+', ' ', normalized)
            
            # اگر خیلی شبیه به یکی از قبلی‌هاست، skip کن
            is_duplicate = False
            for seen in seen_lower:
                similarity = self._simple_similarity(normalized, seen)
                if similarity > 0.7:  # 70% شباهت
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(suggestion)
                seen_lower.add(normalized)
        
        return unique
    
    def _simple_similarity(self, s1: str, s2: str) -> float:
        """محاسبه شباهت ساده دو رشته"""
        if not s1 or not s2:
            return 0.0
        
        # تعداد کلمات مشترک / کل کلمات
        words1 = set(s1.split())
        words2 = set(s2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0


