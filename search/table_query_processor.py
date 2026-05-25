# -*- coding: utf-8 -*-
"""
Table Query Processing Module
پردازش هوشمند سوالات مربوط به جداول
"""

import re
import json
import logging
import asyncio
from typing import List, Dict, Optional, Any, Tuple
import numpy as np

from services.qwen_client import QwenClient
from processors.numeric_processor import NumericProcessor

logger = logging.getLogger(__name__)


class QueryClassifier:
    """
    دسته‌بندی سوالات به انواع مختلف
    """
    
    def __init__(self):
        # الگوهای مختلف سوالات
        self.patterns = {
            'exact_value': [
                r'چقدر',
                r'مقدار',
                r'میزان',
                r'چند',
                r'کدام',
                r'چه عددی'
            ],
            'comparison': [
                r'تفاوت',
                r'اختلاف',
                r'مقایسه',
                r'بیشتر',
                r'کمتر',
                r'فرق',
                r'بزرگتر',
                r'کوچکتر'
            ],
            'aggregation': [
                r'جمع',
                r'کل',
                r'مجموع',
                r'total',
                r'sum'
            ],
            'breakdown': [
                r'تقسیم',
                r'تفکیک',
                r'بخش',
                r'شامل',
                r'چه\s+چیز',
                r'فصل',
                r'اجزا'
            ],
            'percentage': [
                r'درصد',
                r'نسبت',
                r'سهم',
                r'چند\s+درصد'
            ],
            'ranking': [
                r'بالاترین',
                r'پایین\s*ترین',
                r'بزرگترین',
                r'کوچکترین',
                r'اولین',
                r'آخرین',
                r'top',
                r'رتبه'
            ],
            'trend': [
                r'روند',
                r'تغییر',
                r'افزایش',
                r'کاهش',
                r'رشد'
            ]
        }
    
    def classify_query(self, query: str) -> Dict[str, Any]:
        """
        دسته‌بندی نوع سوال
        """
        query_lower = query.lower()
        
        classification = {
            'primary_type': 'general',
            'secondary_types': [],
            'confidence': 0.0,
            'is_numeric': False,
            'is_comparative': False,
            'requires_calculation': False
        }
        
        # بررسی تمام الگوها
        type_scores = {}
        for query_type, patterns in self.patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, query_lower, re.IGNORECASE))
                score += matches
            type_scores[query_type] = score
        
        # تعیین نوع اصلی
        if type_scores:
            primary_type = max(type_scores.items(), key=lambda x: x[1])[0]
            classification['primary_type'] = primary_type
            classification['confidence'] = min(type_scores[primary_type] / 3.0, 1.0)
        
        # تعیین انواع ثانویه
        for query_type, score in type_scores.items():
            if score > 0 and query_type != classification['primary_type']:
                classification['secondary_types'].append(query_type)
        
        # تعیین ویژگی‌های سوال
        classification['is_numeric'] = classification['primary_type'] in ['exact_value', 'aggregation', 'percentage', 'ranking']
        classification['is_comparative'] = classification['primary_type'] in ['comparison', 'ranking']
        classification['requires_calculation'] = classification['primary_type'] in ['aggregation', 'percentage', 'comparison']
        
        return classification


class TableQueryRewriter:
    """
    بازنویسی سوالات برای بهبود جستجو
    """
    
    def __init__(self, qwen_url: str = "http://localhost:8009"):  # Qwen 30B on port 8009
        self.qwen_client = QwenClient(qwen_url)
    
    async def rewrite_query(self, query: str, context: Dict[str, Any] = None) -> str:
        """
        بازنویسی سوال برای بهبود جستجو
        """
        try:
            context_info = ""
            if context:
                context_info = f"Context: {json.dumps(context, ensure_ascii=False)}"
            
            prompt = f"""
            سوال زیر را برای جستجو در جداول مالی بازنویسی کن:

            سوال اصلی: {query}
            {context_info}

            هدف: بهبود سوال برای پیدا کردن اطلاعات دقیق در جداول مالی فارسی

            قوانین:
            1. حفظ معنای اصلی سوال
            2. اضافه کردن کلمات کلیدی مرتبط با جداول مالی
            3. استفاده از اصطلاحات مالی مناسب
            4. واضح‌تر کردن سوال

            سوال بازنویسی شده:
            """
            
            response = await self.qwen_client.generate_text(
                prompt=prompt,
                system_prompt="شما یک متخصص بازنویسی سوالات برای جستجو در جداول مالی هستید.",
                max_tokens=512,
                temperature=0.3
            )
            
            if response.success:
                return response.text.strip()
            else:
                logger.warning(f"Query rewriting failed: {response.error}")
                return query
                
        except Exception as e:
            logger.error(f"Query rewriting failed: {e}")
            return query


class NumericAwareSearch:
    """
    جستجوی هوشمند برای سوالات عددی
    """
    
    def __init__(self, vector_db, rag_system):
        self.vector_db = vector_db
        self.rag_system = rag_system
        self.numeric_processor = NumericProcessor()
        self.classifier = QueryClassifier()
    
    async def search_numeric_query(self, query: str, collection_name: str, 
                                   top_k: int = 10) -> Dict[str, Any]:
        """
        جستجوی هوشمند برای سوالات عددی
        """
        logger.info(f"🔍 Numeric-aware search: {query}")
        
        # دسته‌بندی سوال
        classification = self.classifier.classify_query(query)
        query_type = classification['primary_type']
        
        logger.info(f"  Query type: {query_type}")
        
        # Embedding query
        query_embedding = await self.rag_system.embedding_service.generate_embedding_async(
            query, task="retrieval.query"
        )
        
        # جستجو در vector DB
        try:
            collection = self.vector_db.get_collection(collection_name)
            search_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
        except Exception as e:
            logger.error(f"Error searching in vector DB: {e}")
            return {
                'success': False,
                'results': [],
                'query_type': query_type
            }
        
        if not search_results['documents'] or not search_results['documents'][0]:
            return {
                'success': False,
                'results': [],
                'query_type': query_type
            }
        
        # پردازش نتایج
        processed_results = []
        for i, (doc, meta, distance) in enumerate(zip(
            search_results['documents'][0],
            search_results['metadatas'][0],
            search_results['distances'][0]
        )):
            # استخراج اعداد از سند
            numbers = self.numeric_processor.extract_numbers(doc)
            
            # محاسبه امتیاز عددی
            numeric_score = self._calculate_numeric_score(query, numbers, query_type)
            
            processed_results.append({
                'document': doc,
                'metadata': meta,
                'distance': distance,
                'similarity': 1 - distance,
                'numbers': numbers,
                'numeric_score': numeric_score,
                'combined_score': (1 - distance) * 0.7 + numeric_score * 0.3
            })
        
        # مرتب‌سازی بر اساس امتیاز ترکیبی
        processed_results.sort(key=lambda x: x['combined_score'], reverse=True)
        
        return {
            'success': True,
            'results': processed_results,
            'query_type': query_type,
            'classification': classification
        }
    
    def _calculate_numeric_score(self, query: str, numbers: List, query_type: str) -> float:
        """
        محاسبه امتیاز عددی
        """
        if not numbers:
            return 0.0
        
        # استخراج اعداد از query
        query_numbers = self.numeric_processor.extract_numbers(query)
        
        if not query_numbers:
            # اگر query عدد ندارد، امتیاز بر اساس وجود اعداد
            return min(len(numbers) / 10.0, 1.0)
        
        # محاسبه امتیاز بر اساس تطبیق اعداد
        score = 0.0
        for query_num in query_numbers:
            for doc_num in numbers:
                if abs(query_num.normalized_value - doc_num.normalized_value) < 0.01:
                    score += 1.0
                elif abs(query_num.normalized_value - doc_num.normalized_value) < query_num.normalized_value * 0.1:
                    score += 0.5
        
        return min(score / len(query_numbers), 1.0)
    
    async def _text_search_fallback(self, query: str, collection_name: str) -> Dict:
        """جستجوی متنی fallback"""
        try:
            collection = self.vector_db.get_collection(collection_name)
            
            # Get all documents
            all_docs = collection.get()
            
            if not all_docs['documents'] or not all_docs['documents'][0]:
                return {
                    'success': False,
                    'results': [],
                    'answer_hints': {}
                }
            
            # Simple text matching
            matching_docs = []
            query_lower = query.lower()
            
            for i, doc in enumerate(all_docs['documents'][0]):
                if query_lower in doc.lower():
                    matching_docs.append({
                        'document': doc,
                        'distance': 0.0,
                        'relevance_score': 1.0,
                        'metadata': all_docs['metadatas'][0][i] if all_docs['metadatas'] and all_docs['metadatas'][0] else {},
                        'rank': len(matching_docs) + 1
                    })
            
            return {
                'success': True,
                'results': matching_docs,
                'answer_hints': {}
            }
            
        except Exception as e:
            logger.error(f"Error in text search fallback: {e}")
            return {
                'success': False,
                'results': [],
                'answer_hints': {}
            }


class NumericResponseFormatter:
    """
    فرمت کردن پاسخ‌های عددی
    """
    
    def __init__(self):
        self.numeric_processor = NumericProcessor()
    
    def format_numeric_response(self, query: str, results: List[Dict[str, Any]], 
                               classification: Dict[str, Any]) -> str:
        """
        فرمت کردن پاسخ برای سوالات عددی
        """
        if not results:
            return "❌ هیچ اطلاعات عددی مرتبطی یافت نشد."
        
        # استخراج اعداد از نتایج
        all_numbers = []
        for result in results:
            numbers = result.get('numbers', [])
            all_numbers.extend(numbers)
        
        if not all_numbers:
            return "❌ هیچ عددی در نتایج یافت نشد."
        
        # فرمت کردن بر اساس نوع سوال
        query_type = classification['primary_type']
        
        if query_type == 'exact_value':
            return self._format_exact_value_response(query, all_numbers)
        elif query_type == 'aggregation':
            return self._format_aggregation_response(query, all_numbers)
        elif query_type == 'comparison':
            return self._format_comparison_response(query, all_numbers)
        elif query_type == 'ranking':
            return self._format_ranking_response(query, all_numbers)
        else:
            return self._format_general_numeric_response(query, all_numbers)
    
    def _format_exact_value_response(self, query: str, numbers: List) -> str:
        """فرمت پاسخ برای سوالات مقدار دقیق"""
        if not numbers:
            return "❌ هیچ عددی یافت نشد."
        
        # پیدا کردن نزدیک‌ترین عدد
        largest_number = self.numeric_processor.find_largest(numbers)
        if largest_number:
            formatted = self.numeric_processor.format_number(
                largest_number.normalized_value, "currency"
            )
            return f"✅ {formatted}"
        
        return "❌ هیچ عدد معتبری یافت نشد."
    
    def _format_aggregation_response(self, query: str, numbers: List) -> str:
        """فرمت پاسخ برای سوالات جمع"""
        if not numbers:
            return "❌ هیچ عددی برای محاسبه یافت نشد."
        
        # محاسبه مجموع
        total = self.numeric_processor.calculate_sum(numbers)
        if total:
            formatted = self.numeric_processor.format_number(
                total.normalized_value, "currency"
            )
            return f"✅ مجموع: {formatted}"
        
        return "❌ امکان محاسبه مجموع وجود ندارد."
    
    def _format_comparison_response(self, query: str, numbers: List) -> str:
        """فرمت پاسخ برای سوالات مقایسه"""
        if len(numbers) < 2:
            return "❌ برای مقایسه حداقل دو عدد نیاز است."
        
        largest = self.numeric_processor.find_largest(numbers)
        smallest = self.numeric_processor.find_smallest(numbers)
        
        if largest and smallest:
            largest_formatted = self.numeric_processor.format_number(
                largest.normalized_value, "currency"
            )
            smallest_formatted = self.numeric_processor.format_number(
                smallest.normalized_value, "currency"
            )
            difference = largest.normalized_value - smallest.normalized_value
            difference_formatted = self.numeric_processor.format_number(
                difference, "currency"
            )
            
            return f"""✅ مقایسه:
🔺 بالاترین: {largest_formatted}
🔻 پایین‌ترین: {smallest_formatted}
📊 تفاوت: {difference_formatted}"""
        
        return "❌ امکان مقایسه وجود ندارد."
    
    def _format_ranking_response(self, query: str, numbers: List) -> str:
        """فرمت پاسخ برای سوالات رتبه‌بندی"""
        if not numbers:
            return "❌ هیچ عددی برای رتبه‌بندی یافت نشد."
        
        # مرتب‌سازی اعداد
        sorted_numbers = sorted(numbers, key=lambda x: x.normalized_value, reverse=True)
        
        response = "✅ رتبه‌بندی:\n"
        for i, num in enumerate(sorted_numbers[:5]):  # 5 عدد اول
            formatted = self.numeric_processor.format_number(
                num.normalized_value, "currency"
            )
            response += f"{i+1}. {formatted}\n"
        
        return response.strip()
    
    def _format_general_numeric_response(self, query: str, numbers: List) -> str:
        """فرمت پاسخ عمومی برای سوالات عددی"""
        if not numbers:
            return "❌ هیچ عددی یافت نشد."
        
        # نمایش تمام اعداد
        response = "✅ اعداد یافت شده:\n"
        for i, num in enumerate(numbers[:10]):  # 10 عدد اول
            formatted = self.numeric_processor.format_number(
                num.normalized_value, "currency"
            )
            response += f"{i+1}. {formatted}\n"
        
        return response.strip()


class TableQueryProcessor:
    """پردازشگر اصلی سوالات مربوط به جداول"""
    
    def __init__(self, vector_db=None, rag_system=None):
        self.classifier = QueryClassifier()
        self.rewriter = TableQueryRewriter()
        self.search = NumericAwareSearch(vector_db, rag_system) if vector_db and rag_system else None
        self.formatter = NumericResponseFormatter()
    
    async def process_table_query(self, query: str, context: str = "") -> Dict[str, Any]:
        """پردازش سوال مربوط به جدول"""
        try:
            # طبقه‌بندی سوال
            classification = self.classifier.classify_query(query)
            
            # بازنویسی سوال
            rewritten_query = self.rewriter.rewrite_query(query, classification)
            
            # جستجوی عددی
            if self.search:
                search_results = await self.search.search_numeric_content(
                    rewritten_query, 
                    classification
                )
            else:
                search_results = {"results": [], "message": "Search not available"}
            
            # فرمت پاسخ
            formatted_response = self.formatter.format_response(
                search_results, 
                classification
            )
            
            return {
                "success": True,
                "original_query": query,
                "rewritten_query": rewritten_query,
                "classification": classification,
                "search_results": search_results,
                "formatted_response": formatted_response
            }
            
        except Exception as e:
            logger.error(f"Error processing table query: {e}")
            return {
                "success": False,
                "error": str(e),
                "original_query": query
            }


# Global instances
query_classifier = QueryClassifier()
table_query_rewriter = TableQueryRewriter()
numeric_response_formatter = NumericResponseFormatter()
# table_query_processor will be initialized when needed with proper dependencies
