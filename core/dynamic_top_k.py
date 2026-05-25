# -*- coding: utf-8 -*-
"""
Dynamic Top-K Calculator
محاسبه داینامیک تعداد نتایج مورد نیاز بر اساس query complexity و relevance
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DynamicTopKCalculator:
    """
    محاسبه داینامیک top_k بر اساس:
    1. Query complexity (طول، تعداد entity ها، multi-hop بودن)
    2. Relevance score (اگر relevance پایین باشد، کمتر نتیجه برمی‌گردانیم)
    3. Collection type (QA datasets نیاز به نتایج کمتر دارند)
    """
    
    # حداقل و حداکثر top_k
    MIN_TOP_K = 1
    MAX_TOP_K = 20
    DEFAULT_TOP_K = 5
    
    def __init__(self):
        """Initialize calculator"""
        pass
    
    def calculate_dynamic_top_k(
        self,
        query: str,
        collection_name: str,
        initial_top_k: int = 5,
        query_complexity: Optional[Dict[str, Any]] = None,
        is_multi_hop: bool = False,
        relevance_score: Optional[float] = None
    ) -> int:
        """
        محاسبه top_k داینامیک
        
        Args:
            query: سوال کاربر
            collection_name: نام collection
            initial_top_k: top_k اولیه (از کاربر یا default)
            query_complexity: اطلاعات complexity query (از query_orchestrator)
            is_multi_hop: آیا query multi-hop است
            relevance_score: امتیاز relevance (اگر از قبل محاسبه شده)
            
        Returns:
            top_k محاسبه شده
        """
        # شروع با initial_top_k
        dynamic_k = initial_top_k
        
        # === 1. Query Complexity Analysis ===
        query_words = len(query.split())
        query_length_factor = 1.0
        
        # سوالات کوتاه (کمتر از 5 کلمه) - نیاز به نتایج کمتر
        if query_words < 5:
            query_length_factor = 0.6  # 60% از initial_top_k
        # سوالات متوسط (5-15 کلمه) - نیاز به نتایج متوسط
        elif query_words < 15:
            query_length_factor = 1.0  # 100% از initial_top_k
        # سوالات طولانی (بیشتر از 15 کلمه) - نیاز به نتایج بیشتر
        else:
            query_length_factor = 1.4  # 140% از initial_top_k
        
        dynamic_k = int(dynamic_k * query_length_factor)
        
        # === 2. Multi-hop Queries ===
        if is_multi_hop:
            # برای multi-hop queries، نیاز به نتایج بیشتر داریم
            dynamic_k = int(dynamic_k * 1.5)
            logger.info(f"🔗 Multi-hop query detected, increasing top_k to {dynamic_k}")
        
        # === 3. Query Complexity (از query_orchestrator) ===
        if query_complexity:
            # اگر query complex است (مثلاً مقایسه‌ای یا چند بخشی)
            if query_complexity.get('is_comparison', False):
                dynamic_k = int(dynamic_k * 1.6)  # 60% بیشتر برای مقایسه
                logger.info(f"📊 Comparison query detected, increasing top_k to {dynamic_k}")
            
            if query_complexity.get('is_multi_part', False):
                num_parts = len(query_complexity.get('sub_queries', []))
                if num_parts > 1:
                    dynamic_k = int(dynamic_k * (1 + 0.2 * num_parts))  # 20% بیشتر برای هر بخش اضافی
                    logger.info(f"📋 Multi-part query detected ({num_parts} parts), increasing top_k to {dynamic_k}")
        
        # === 4. Collection Type ===
        collection_lower = collection_name.lower()
        
        # برای QA datasets (مثل zabete_qa)، معمولاً یک نتیجه کافی است
        # اما برای comparison queries یا multi-hop، نیاز به نتایج بیشتر داریم
        if 'qa' in collection_lower or 'question' in collection_lower:
            # اگر comparison query است، نتایج بیشتری نیاز داریم
            if query_complexity and query_complexity.get('is_comparison', False):
                # برای comparison، حداقل 5-8 نتیجه نیاز داریم
                dynamic_k = max(dynamic_k, 5)
                logger.info(f"📊 QA dataset + Comparison query, setting min top_k to {dynamic_k}")
            # اگر relevance بالا باشد، 1-3 نتیجه کافی است
            elif relevance_score and relevance_score > 0.7:
                dynamic_k = min(dynamic_k, 3)
            # اگر relevance متوسط باشد، 3-5 نتیجه
            elif relevance_score and relevance_score > 0.5:
                dynamic_k = min(dynamic_k, 5)
            # اگر relevance پایین باشد یا None، 1-2 نتیجه
            else:
                # اگر multi-hop یا comparison است، کمتر محدود نکن
                if is_multi_hop or (query_complexity and query_complexity.get('is_comparison', False)):
                    dynamic_k = min(dynamic_k, 5)  # برای multi-hop/comparison، حداقل 5
                else:
                    dynamic_k = min(dynamic_k, 2)  # برای query های ساده، 2
            logger.info(f"📚 QA dataset detected, adjusting top_k to {dynamic_k}")
        
        # === 5. Relevance-based Adjustment ===
        if relevance_score is not None:
            # اگر relevance خیلی پایین است (کمتر از 0.3)، فقط 1-2 نتیجه برمی‌گردانیم
            if relevance_score < 0.3:
                dynamic_k = min(dynamic_k, 2)
                logger.info(f"⚠️ Low relevance ({relevance_score:.2f}), reducing top_k to {dynamic_k}")
            # اگر relevance متوسط است (0.3-0.6)، نتایج متوسط
            elif relevance_score < 0.6:
                dynamic_k = min(dynamic_k, 5)
                logger.info(f"📊 Medium relevance ({relevance_score:.2f}), keeping top_k at {dynamic_k}")
            # اگر relevance بالا است (بیشتر از 0.6)، می‌توانیم نتایج بیشتری برگردانیم
            else:
                dynamic_k = min(dynamic_k, 10)
                logger.info(f"✅ High relevance ({relevance_score:.2f}), allowing up to {dynamic_k} results")
        
        # === 6. Apply Min/Max Constraints ===
        dynamic_k = max(self.MIN_TOP_K, min(dynamic_k, self.MAX_TOP_K))
        
        logger.info(f"🎯 Dynamic top_k calculated: {initial_top_k} -> {dynamic_k} (query_words={query_words}, is_multi_hop={is_multi_hop}, relevance={relevance_score})")
        
        return dynamic_k
    
    def adjust_top_k_after_retrieval(
        self,
        results: List[Dict[str, Any]],
        min_score_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        فیلتر کردن نتایج بر اساس score بعد از retrieval
        
        Args:
            results: نتایج بازیابی شده
            min_score_threshold: حداقل score برای نگه داشتن نتیجه
            
        Returns:
            لیست نتایج فیلتر شده
        """
        if not results:
            return []
        
        # فیلتر بر اساس score
        filtered = [r for r in results if r.get('score', 0.0) >= min_score_threshold]
        
        # اگر بعد از فیلتر هیچ نتیجه‌ای نماند، حداقل top 1 را برگردان
        if not filtered and results:
            # اگر top result score بالای 0.1 دارد، آن را برگردان
            if results[0].get('score', 0.0) > 0.1:
                filtered = [results[0]]
                logger.info(f"⚠️ No results above threshold, keeping top result (score={results[0].get('score', 0.0):.2f})")
            else:
                # اگر حتی top result score خیلی پایین است، هیچ نتیجه‌ای برنگردان
                logger.warning(f"⚠️ All results have very low scores, returning empty list")
                return []
        
        logger.info(f"🔍 Filtered results: {len(results)} -> {len(filtered)} (threshold={min_score_threshold})")
        
        return filtered


