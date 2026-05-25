# -*- coding: utf-8 -*-
"""
Multi-Hop Retrieval System - Integrated with Enhanced Comparison
سیستم بازیابی چند مرحله‌ای با قابلیت‌های پیشرفته مقایسه
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import re
import sys
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

# Import intelligent components
try:
    from services.intelligent_multihop_analyzer import IntelligentMultiHopAnalyzer, QueryType
    from services.entity_enricher import EntityEnricher
    INTELLIGENT_MODE = True
except ImportError:
    INTELLIGENT_MODE = False

# Import enhanced comparison system
try:
    from search.enhanced_comparison import (
        EnhancedComparisonDetector,
        EnhancedEntityExtractor,
        ImprovedMultiHopAnalyzer,
        ComparisonPair
    )
    ENHANCED_MODE = True
except ImportError:
    ComparisonPair = None

# Helper function to get entity from ComparisonPair (namedtuple or dict)
def get_cp_entity(cp, field: str, default: str = "") -> str:
    """Get entity field from ComparisonPair (supports both namedtuple and dict)"""
    if cp is None:
        return default
    if hasattr(cp, field):
        return getattr(cp, field)
    if isinstance(cp, dict):
        return cp.get(field, default)
    return default

    ENHANCED_MODE = False

logger = logging.getLogger(__name__)


class MultiHopRetriever:
    """
    Integrated Multi-Hop Retriever با سیستم پیشرفته مقایسه 🔄
    
    ویژگی‌ها:
    - سیستم پیشرفته تشخیص مقایسه (EnhancedComparisonDetector)
    - استخراج هوشمند entities (EnhancedEntityExtractor)
    - تحلیل‌گر بهبود یافته (ImprovedMultiHopAnalyzer)
    - fallback به روش‌های قدیمی
    """
    
    def __init__(self):
        """Initialize Multi-Hop Retriever with all intelligent systems"""
        # سیستم‌های قدیمی (برای fallback)
        self.hop_patterns = {
            "aggregation": {
                "keywords": ["جمع", "مجموع", "total", "sum", "کل"],
                "requires": ["target"]
            },
            "comparison": {
                "keywords": ["تفاوت", "مقایسه", "بیشتر", "کمتر", "difference", "compare"],
                "requires": ["entity1", "entity2"]
            },
            "calculation": {
                "keywords": ["میانگین", "درصد", "نسبت", "average", "percentage"],
                "requires": ["target"]
            }
        }
        
        # 🆕 سیستم‌های پیشرفته جدید
        if ENHANCED_MODE:
            self.comparison_detector = EnhancedComparisonDetector()
            self.entity_extractor = EnhancedEntityExtractor()
            self.improved_analyzer = ImprovedMultiHopAnalyzer()
            logger.info("🚀 Multi-Hop Retriever initialized in ENHANCED mode")
        else:
            self.comparison_detector = None
            self.entity_extractor = None
            self.improved_analyzer = None
            logger.warning("⚠️ Enhanced mode not available")
        
        # سیستم‌های قدیمی intelligent
        if INTELLIGENT_MODE:
            self.intelligent_analyzer = IntelligentMultiHopAnalyzer()
            self.entity_enricher = EntityEnricher()
            logger.info("🧠 Intelligent mode also available")
        else:
            self.intelligent_analyzer = None
            self.entity_enricher = None
            logger.info("📦 Basic mode active")
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        تحلیل سوال با ترکیب روش‌های پیشرفته و قدیمی 🔄
        
        استراتژی:
        1. اول از سیستم ENHANCED استفاده کن (بهترین برای مقایسه‌ها)
        2. اگر confidence بالا بود، نتیجه رو برگردون
        3. اگر نه، از INTELLIGENT MODE استفاده کن
        4. آخرین fallback: BASIC MODE
        
        Returns:
            {
                "type": str,
                "hops": List[Dict],
                "target_entity": str,
                "operation": str,
                "requires_multi_hop": bool,
                "estimated_rows": int,
                "confidence": float,
                "entities": List[str],
                "comparison_pair": Optional[ComparisonPair],
                "reasoning": str
            }
        """
        
        # 🆕 STEP 1: سیستم ENHANCED (اولویت اول برای مقایسه‌ها)
        if ENHANCED_MODE and self.improved_analyzer:
            logger.info("🚀 Using ENHANCED multi-hop analysis")
            enhanced_analysis = self.improved_analyzer.analyze(query)
            
            # اگر confidence بالا بود، از نتیجه جدید استفاده کن
            if enhanced_analysis['confidence'] >= 0.8:
                result = self._convert_enhanced_to_standard(enhanced_analysis, query)
                logger.info(f"✅ ENHANCED analysis: type={result['type']}, confidence={result['confidence']:.2f}, hops={len(result['hops'])}")
                return result
        
        # 🧠 STEP 2: Fallback به INTELLIGENT MODE
        if INTELLIGENT_MODE and self.intelligent_analyzer:
            logger.info("🧠 Using INTELLIGENT multi-hop analysis")
            decision = self.intelligent_analyzer.analyze(query)
            
            # تبدیل decision به format استاندارد
            result = {
                "type": decision.query_type.value,
                "hops": [],
                "target_entity": decision.entities[0] if decision.entities else None,
                "operation": decision.query_type.value,
                "requires_multi_hop": decision.should_use_multihop,
                "estimated_rows": decision.estimated_rows_needed,
                "confidence": decision.confidence,
                "entities": decision.entities,
                "sub_questions": decision.sub_questions,
                "complexity": decision.complexity.value,
                "reasoning": decision.reasoning,
                "comparison_pair": None
            }
            
            # ساخت hops بر اساس intelligent analysis
            if decision.should_use_multihop:
                result["hops"] = self._build_intelligent_hops(query, decision)
            
            logger.info(f"✅ INTELLIGENT analysis: type={result['type']}, confidence={result['confidence']:.2f}, hops={len(result['hops'])}")
            return result
        
        # 📦 STEP 3: BASIC MODE (آخرین fallback)
        logger.info("📦 Using BASIC multi-hop analysis")
        result = self._analyze_query_basic(query)
        logger.info(f"✅ BASIC analysis: type={result['type']}, requires_multi_hop={result['requires_multi_hop']}, hops={len(result['hops'])}")
        return result
    
    def _convert_enhanced_to_standard(self, enhanced_analysis: Dict, query: str) -> Dict[str, Any]:
        """
        تبدیل format ENHANCED به format استاندارد
        """
        result = {
            "type": enhanced_analysis['type'],
            "hops": [],
            "target_entity": None,
            "operation": enhanced_analysis['type'],
            "requires_multi_hop": enhanced_analysis['requires_multi_hop'],
            "entities": enhanced_analysis['entities'],
            "estimated_rows": enhanced_analysis['estimated_rows'],
            "confidence": enhanced_analysis['confidence'],
            "reasoning": enhanced_analysis['reasoning'],
            # ⚠️ ComparisonPair را به dict تبدیل کن تا JSON serializable باشد
            "comparison_pair": {
                "entity1": enhanced_analysis['comparison_pair'].entity1,
                "entity2": enhanced_analysis['comparison_pair'].entity2,
                "confidence": enhanced_analysis['comparison_pair'].confidence,
                "pattern_used": enhanced_analysis['comparison_pair'].pattern_used
            } if enhanced_analysis.get('comparison_pair') else None,
            "complexity": enhanced_analysis['complexity'].value
        }
        
        # ساخت hops بر اساس نوع
        if enhanced_analysis['type'] == 'comparison':
            comparison_pair = enhanced_analysis.get('comparison_pair')
            if comparison_pair:
                # 🎯 کلید اصلی: دو hop جداگانه برای comparison
                # افزایش top_k از 5 به 8 برای بازیابی بهتر
                result["hops"] = [
                    {
                        "query": get_cp_entity(comparison_pair, 'entity1'),
                        "purpose": "find_entity_1",
                        "top_k": 8,
                        "description": f"جستجو برای {get_cp_entity(comparison_pair, 'entity1')}"
                    },
                    {
                        "query": get_cp_entity(comparison_pair, 'entity2'),
                        "purpose": "find_entity_2",
                        "top_k": 8,
                        "description": f"جستجو برای {get_cp_entity(comparison_pair, 'entity2')}"
                    }
                ]
                result["target_entity"] = f"{get_cp_entity(comparison_pair, 'entity1')} vs {get_cp_entity(comparison_pair, 'entity2')}"
        
        elif enhanced_analysis['type'] == 'multi_entity':
            # هر entity یک hop جداگانه — top_k=8 برای coverage بهتر
            result["hops"] = [
                {
                    "query": entity,
                    "purpose": f"entity_{i+1}_info",
                    "top_k": 8,
                    "description": f"جستجو برای {entity}"
                }
                for i, entity in enumerate(enhanced_analysis['entities'])
            ]
        
        elif enhanced_analysis['type'] == 'aggregation':
            # جستجوی گسترده
            result["hops"] = [{
                "query": query,
                "purpose": "gather_all",
                "top_k": enhanced_analysis['estimated_rows']
            }]
        
        else:
            # سوال ساده
            result["hops"] = [{
                "query": query,
                "purpose": "main_query",
                "top_k": 5
            }]
        
        return result
    
    def _analyze_query_basic(self, query: str) -> Dict[str, Any]:
        """
        روش قدیمی BASIC تحلیل (آخرین fallback)
        """
        query_lower = query.lower()
        result = {
            "type": "simple",
            "hops": [],
            "target_entity": None,
            "operation": None,
            "requires_multi_hop": False,
            "confidence": 0.5,
            "entities": [],
            "comparison_pair": None,
            "reasoning": "Basic pattern matching"
        }
        
        # 1. تشخیص نوع query
        for query_type, pattern in self.hop_patterns.items():
            for keyword in pattern["keywords"]:
                if keyword in query_lower:
                    result["type"] = query_type
                    result["operation"] = keyword
                    result["requires_multi_hop"] = True
                    break
            if result["requires_multi_hop"]:
                break
        
        if not result["requires_multi_hop"]:
            return result
        
        # 2. استخراج target entity
        result["target_entity"] = self._extract_target_entity(query)
        
        # 3. ساخت hops
        if result["type"] == "aggregation":
            result["hops"] = [
                {
                    "query": result["target_entity"] if result["target_entity"] else query,
                    "purpose": "find_target",
                    "top_k": 10
                },
                {
                    "query": f"{result['operation']} {result['target_entity']}",
                    "purpose": "find_aggregation",
                    "top_k": 5,
                    "filter": {"contains": result["operation"]}
                }
            ]
        
        elif result["type"] == "comparison":
            entities = self._extract_comparison_entities(query)
            if entities[0] and entities[1]:
                result["hops"] = [
                    {"query": entities[0], "purpose": "find_entity_1", "top_k": 5},
                    {"query": entities[1], "purpose": "find_entity_2", "top_k": 5}
                ]
                result["entities"] = [entities[0], entities[1]]
        
        elif result["type"] == "calculation":
            result["hops"] = [
                {
                    "query": result["target_entity"],
                    "purpose": "find_all_values",
                    "top_k": 20
                }
            ]
        
        return result
    
    def _extract_target_entity(self, query: str) -> Optional[str]:
        """استخراج target entity از سوال"""
        # حذف کلمات عملیاتی
        operation_words = ["جمع", "مجموع", "total", "sum", "کل", "چقدر", "چند", "است", "چیست", "؟"]
        
        words = query.split()
        entity_words = []
        
        for word in words:
            clean_word = word.strip("؟،.")
            if clean_word not in operation_words and len(clean_word) > 1:
                entity_words.append(clean_word)
        
        if entity_words:
            return " ".join(entity_words)
        
        return None
    
    def _cleanup_entity(self, entity: str) -> str:
        """پاکسازی entity از کلمات اضافی"""
        # حذف کلمات کلیدی از ابتدا
        entity = re.sub(r'^(?:تفاوت|فرق|مقایسه|بین)\s+', '', entity, flags=re.IGNORECASE).strip()
        
        # حذف کلمات کلیدی از انتها
        entity = re.sub(r'\s+(?:چیست|چیه|است|هست|دارد|دارند|چه|تفاوتی|فرقی).*$', '', entity, flags=re.IGNORECASE).strip()
        
        # حذف نشانه‌گذاری
        entity = re.sub(r'[؟،.]', '', entity).strip()
        
        return entity
    
    def _build_intelligent_hops(self, query: str, decision) -> List[Dict[str, Any]]:
        """
        ساخت hops بر اساس تحلیل هوشمند
        
        Args:
            query: سوال اصلی
            decision: MultiHopDecision از IntelligentMultiHopAnalyzer
            
        Returns:
            لیست hops
        """
        hops = []
        
        # غنی‌سازی entities
        enriched_entities = decision.entities
        if self.entity_enricher:
            enriched_entities = self.entity_enricher.enrich_entities(decision.entities, query)
            logger.info(f"🌟 Enriched entities: {decision.entities} → {enriched_entities}")
        
        # ساخت hops بر اساس نوع سوال
        if decision.query_type.value == "comparison":
            # برای مقایسه، یک hop برای هر entity
            for i, entity in enumerate(enriched_entities, 1):
                hops.append({
                    "query": entity,
                    "purpose": f"find_entity_{i}",
                    "top_k": 8  # افزایش از 5 به 8 برای coverage بهتر
                })
        
        elif decision.query_type.value == "multi_part":
            # برای سوالات چندبخشی، یک hop برای هر sub-question
            sub_questions = decision.sub_questions if hasattr(decision, 'sub_questions') else []
            if not sub_questions:
                # fallback: تقسیم با ؟
                sub_questions = query.split('؟')
                sub_questions = [sq.strip() + '؟' for sq in sub_questions if sq.strip()]
            
            for i, sub_q in enumerate(sub_questions, 1):
                hops.append({
                    "query": sub_q,
                    "purpose": f"sub_question_{i}",
                    "top_k": 5  # برای هر sub-question حداقل 5 document
                })
            logger.info(f"🔄 Multi-part query split into {len(hops)} sub-questions")
        
        elif decision.query_type.value == "multi_entity":
            # برای multi-entity، یک hop برای هر entity (top_k=8 برای coverage بهتر)
            for i, entity in enumerate(enriched_entities, 1):
                hops.append({
                    "query": entity,
                    "purpose": f"entity_{i}_info",
                    "top_k": 8
                })
        
        elif decision.query_type.value == "aggregation":
            # برای aggregation، جستجوی گسترده
            hops.append({
                "query": query,
                "purpose": "gather_all",
                "top_k": decision.estimated_rows_needed
            })
        
        elif decision.query_type.value == "procedural":
            # برای سوالات فرآیندی، از sub-questions استفاده کن (top_k=8)
            for i, sub_q in enumerate(decision.sub_questions, 1):
                hops.append({
                    "query": sub_q,
                    "purpose": f"step_{i}",
                    "top_k": 8
                })
        
        else:
            # برای بقیه، از sub-questions یا سوال اصلی (top_k=8 برای coverage بهتر)
            if decision.sub_questions:
                for i, sub_q in enumerate(decision.sub_questions, 1):
                    hops.append({
                        "query": sub_q,
                        "purpose": f"sub_q_{i}",
                        "top_k": 8
                    })
            else:
                hops.append({
                    "query": query,
                    "purpose": "main_query",
                    "top_k": decision.estimated_rows_needed
                })
        
        logger.info(f"📋 Built {len(hops)} intelligent hops")
        return hops
    
    def _extract_comparison_entities(self, query: str) -> Tuple[str, str]:
        """استخراج دو entity برای مقایسه - با استراتژی ساده و موثر"""
        
        # استراتژی 1: جستجوی ' و ' (رایج‌ترین حالت)
        if ' و ' in query:
            parts = query.split(' و ', 1)  # فقط اولین ' و ' را split کن
            entity1 = self._cleanup_entity(parts[0])
            entity2 = self._cleanup_entity(parts[1])
            
            if entity1 and entity2 and entity1 != entity2 and len(entity1.split()) <= 4 and len(entity2.split()) <= 4:
                logger.info(f"Extracted entities: '{entity1}' vs '{entity2}'")
                return entity1, entity2
        
        # استراتژی 2: جستجوی ' با '
        if ' با ' in query:
            parts = query.split(' با ', 1)
            entity1 = self._cleanup_entity(parts[0])
            entity2 = self._cleanup_entity(parts[1])
            
            if entity1 and entity2 and entity1 != entity2 and len(entity1.split()) <= 4 and len(entity2.split()) <= 4:
                logger.info(f"Extracted entities: '{entity1}' vs '{entity2}'")
                return entity1, entity2
        
        logger.warning(f"Could not extract comparison entities from: {query}")
        return "", ""
    
    @staticmethod
    def _extract_paren_subtopics(query: str) -> List[str]:
        """
        Extract parenthetical sub-topics from a Persian multi-aspect query.
        
        Example:
          "ضوابط تعدیل در شرایط خاص (تأخیرات، کارهای جدید، اشتباه در شاخص) ..."
          → ["تعدیل شرایط خاص تأخیرات", "تعدیل شرایط خاص کارهای جدید", ...]
        
        Example 2:
          "محدودیت‌های تغییر مقادیر (قیمت جدید، سقف 25 درصد) مطابق شرایط خصوصی نشریه 4311"
          → ["محدودیت تغییر مقادیر قیمت جدید شرایط خصوصی نشریه 4311", ...]
        
        Strategy:
        1. Find anchor noun (meaningful tokens before parenthesis)
        2. Find trailing context (meaningful tokens immediately after parenthesis)
        3. Split parenthetical content on ، / و / یا
        4. Build contextualized sub-topics: "anchor + item + trailing_context"
        
        These are used as additional (low top_k) hops in multi-hop search
        to ensure each listed sub-topic is represented in the final results.
        """
        if not query or len(query) < 15:
            return []
        
        # Persian fillers/grammar tokens to skip (one-char suffixes, connectors)
        _SKIP_TOKENS = {
            'چیست', 'چگونه', 'است', 'مانند', 'مثل', 'های', 'ها', 'در',
            'از', 'به', 'که', 'این', 'آن', 'چه', 'و', 'یا', 'تا', 'بر',
            'می', 'هر', 'هم', 'برای', 'طبق', 'نظر', 'مورد', 'صورت', 'بوده',
        }
        _SKIP_PHRASES = {'چیست', 'چگونه است', 'چگونه', 'چیه'}
        
        def _meaningful(token: str) -> bool:
            if len(token) < 3:
                return False
            if token in _SKIP_TOKENS:
                return False
            return True
        
        results: List[str] = []
        seen: set = set()
        
        def _add(s: str) -> None:
            s = s.strip(' ،.؟?!()[]«»""\'')
            s = re.sub(r'\s+', ' ', s)
            if not s or len(s) < 5:
                return
            if s in _SKIP_PHRASES or s in seen:
                return
            seen.add(s)
            results.append(s)
        
        # Find each parenthetical with surrounding context
        for m in re.finditer(r'([^()（）]{0,80})\s*[\(（]([^()（）]{3,150})[\)）]\s*([^()（）]{0,60})', query):
            anchor_raw = (m.group(1) or '').strip()
            paren_content = m.group(2).strip()
            trailing_raw = (m.group(3) or '').strip()
            
            # Extract meaningful tokens from anchor (last 2-3 significant words)
            anchor_tokens = [t for t in anchor_raw.split() if _meaningful(t)]
            anchor = ' '.join(anchor_tokens[-3:]) if anchor_tokens else ''
            
            # Extract trailing context (first 3-5 significant words after the paren)
            # مهم: stop at punctuation like ؟ or .
            trailing_clean = re.split(r'[؟?.!]', trailing_raw, maxsplit=1)[0]
            trailing_tokens = [t for t in trailing_clean.split() if _meaningful(t)]
            trailing = ' '.join(trailing_tokens[:5])
            
            # Split paren content by comma / و / یا
            items = [p.strip() for p in re.split(r'[،,]|\s+و\s+|\s+یا\s+', paren_content) if p.strip()]
            items = [p for p in items if p.lower() not in {'مانند', 'مثل'}]
            
            for item in items:
                # skip items that are too short
                if len(item.split()) == 1 and len(item) < 4:
                    continue
                # Build contextualized sub-topic: "anchor + item"
                # trailing context is saved separately (used only if item alone is too generic)
                if anchor and anchor not in item:
                    _add(f"{anchor} {item}")
                else:
                    _add(item)
                # If item is very short (≤2 words), also add a variant with trailing context
                # to help semantic disambiguation (e.g., "سقف 25 درصد" → "سقف 25 درصد نشریه 4311")
                if trailing and len(item.split()) <= 2:
                    combined_short = f"{item} {trailing}"
                    _add(combined_short)
        
        return results[:8]
    
    def _clean_sub_questions(self, sub_questions: List[str]) -> List[str]:
        """پاکسازی سوالات فرعی تولید شده توسط Query Understanding"""
        cleaned = []
        for question in sub_questions:
            if not question:
                continue
            normalized = re.sub(r'\s+', ' ', question.strip())
            # کاهش threshold از 5 به 3 برای پذیرش sub-questions بیشتر
            if len(normalized) < 3:
                continue
            # حذف sub-questions خیلی کوتاه یا تکراری
            if normalized not in cleaned:
                cleaned.append(normalized)
        # افزایش از 4 به 6 برای پشتیبانی از multi-aspect queries (مثلاً چند موضوع در پرانتز)
        return cleaned[:6]  # جلوگیری از جستجوی بیش از حد

    def _build_decomposition_hops(self, sub_questions: List[str], original_query: str,
                                  top_k: int) -> List[Dict[str, Any]]:
        """تبدیل سوالات فرعی به مراحل multi-hop"""
        hops = []
        for idx, sub_question in enumerate(sub_questions, 1):
            hops.append({
                "query": sub_question,
                "purpose": f"sub_question_{idx}",
                "top_k": max(5, top_k)
            })
        if hops:
            hops.append({
                "query": original_query,
                "purpose": "final_aggregation",
                "top_k": max(top_k, 8)
            })
        return hops

    async def execute_multi_hop(self, query: str, search_function,
                                collection_name: str, top_k: int = 5,
                                sub_questions: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        اجرای multi-hop retrieval
        
        Args:
            query: سوال کاربر
            search_function: تابع جستجو (async)
            collection_name: نام collection
            
        Returns:
            {
                "success": True,
                "hops_results": [...],
                "final_documents": [...],
                "analysis": {...}
            }
        """
        # 1. تحلیل سوال - اول comparison را چک کن! 🎯
        # ⚠️ مهم: comparison detection باید اولویت داشته باشد چون sub_questions ممکن است اشتباه باشند
        analysis = self.analyze_query(query)
        cleaned_sub_questions: List[str] = []  # ← Initialize to avoid UnboundLocalError
        logger.info(f"🔍 Initial analysis: type={analysis.get('type')}, requires_multi_hop={analysis.get('requires_multi_hop')}")
        
        # اگر comparison است، از analyze_query استفاده کن (بدون override با sub_questions)
        if analysis.get("type") == "comparison" and analysis.get("requires_multi_hop"):
            logger.info(f"📊 Using COMPARISON analysis (entities: {analysis.get('entities', [])})")
            # برای comparison، sub_questions را از entities بساز
            entities = analysis.get("entities", [])
            cleaned_sub_questions = [f"{e} چیست؟" for e in entities]
        elif sub_questions:
            # فقط اگر comparison نبود، از sub_questions استفاده کن
            cleaned_sub_questions = self._clean_sub_questions(sub_questions)
            if cleaned_sub_questions:
                hops = self._build_decomposition_hops(cleaned_sub_questions, query, top_k)
                if hops and len(hops) > 1:
                    analysis = {
                        "type": "decomposition",
                        "hops": hops,
                        "target_entity": None,
                        "operation": "decomposition",
                        "requires_multi_hop": True,
                        "sub_questions": cleaned_sub_questions
                    }
                    logger.info(f"✅ Using {len(cleaned_sub_questions)} sub-questions for multi-hop: {cleaned_sub_questions[:2]}")
        
        if not analysis.get("requires_multi_hop", False):
            # سوال ساده، مستقیم جستجو کن
            results = await search_function(query, collection_name, top_k=5)
            return {
                "success": True,
                "is_multi_hop": False,
                "final_documents": results,
                "analysis": analysis
            }
        
        # 2. غنی‌سازی entities قبل از اجرای hops (برای comparison queries)
        if analysis.get("type") == "comparison" and analysis.get("comparison_pair") and ENHANCED_MODE:
            logger.info("🌟 Enriching entities before hop execution...")
            comparison_pair = analysis["comparison_pair"]
            
            # غنی‌سازی با EntityExtractor
            if self.entity_extractor:
                enriched = self.entity_extractor.extract_and_enrich(
                    [get_cp_entity(comparison_pair, 'entity1'), get_cp_entity(comparison_pair, 'entity2')],
                    query
                )
                
                # به‌روزرسانی hops با enriched entities
                if len(enriched) >= 2 and len(analysis["hops"]) >= 2:
                    analysis["hops"][0]["query"] = enriched[0]
                    analysis["hops"][1]["query"] = enriched[1]
                    logger.info(f"✅ Updated hops with enriched entities: {enriched}")
        
        # 3. اجرای هر hop
        hops_results = []
        all_documents = []
        
        # 🎯 FIX: همیشه سوال اصلی را به عنوان hop اصلی اضافه کن تا موضوع کلی گم نشود
        # این کار جلوی درهم‌شکستن بد entity extraction را می‌گیرد (مثلاً وقتی "تأمین مصالح توسط کارفرما"
        # به اشتباه به "ضوابط حقوقی" + "سیمان)" تبدیل می‌شود)
        hops_to_run = list(analysis["hops"])
        _original_query_hops = [h for h in hops_to_run if h.get("query", "").strip() == query.strip()]
        if not _original_query_hops and analysis.get("type") != "comparison":
            # سوال اصلی را در ابتدای hops قرار بده با top_k بالاتر
            # top_k کافی بزرگ تا docsای که برای سوال کلی مرتبط‌اند گم نشوند
            anchor_top_k = max(20, top_k if isinstance(top_k, int) else 20)
            hops_to_run.insert(0, {
                "query": query,
                "purpose": "original_query_anchor",
                "top_k": anchor_top_k,
                "description": "Full original query to preserve overall topic context"
            })
            logger.info(f"🎯 Added original query as anchor hop (top_k={anchor_top_k})")
        
        # 🎯 NEW: برای multi-aspect queries، زیر-موضوعات داخل پرانتز را به عنوان hops اضافی اضافه کن
        # مثل: "ضوابط تعدیل در شرایط خاص (تأخیرات، کارهای جدید، اشتباه در شاخص)"
        # این باعث می‌شود هر sub-topic در نتایج نمایندگی داشته باشد بدون اینکه کل جستجو را مسلط کند
        if analysis.get("type") != "comparison":
            try:
                _paren_items = self._extract_paren_subtopics(query)
                if _paren_items:
                    existing_queries = {h.get("query", "").strip() for h in hops_to_run}
                    for _item in _paren_items[:5]:  # حداکثر 5 زیر-موضوع
                        if _item not in existing_queries:
                            hops_to_run.append({
                                "query": _item,
                                "purpose": "parenthetical_subtopic",
                                "top_k": 5,  # top_k کمتر تا نتایج عمومی مسلط نشوند
                                "description": f"Parenthetical sub-topic: {_item}"
                            })
                            existing_queries.add(_item)
                    if _paren_items:
                        logger.info(f"🎯 Added {min(len(_paren_items), 5)} parenthetical sub-topic hops: {_paren_items[:5]}")
            except Exception as paren_err:
                logger.debug(f"Paren subtopic extraction skipped: {paren_err}")
        
        # 🎯 اجرای hops با مدیریت یکپارچه ID ها
        # کلید یکسان برای تمام بخش‌ها: از code metadata یا id یا متن اول استفاده می‌شود.
        def _get_doc_key(doc: Dict) -> str:
            md = doc.get("metadata", {}) or {}
            code = md.get("code", "")
            if code:
                return f"code:{code}"
            doc_id = doc.get("id")
            if doc_id:
                return f"id:{doc_id}"
            return f"text:{(doc.get('text') or '')[:80]}"
        
        # ذخیره top-k از هر paren hop جداگانه برای round-robin نهایی
        paren_hop_results: List[List[Dict]] = []  # هر ورودی = لیست top-3 docs یک paren hop
        # ذخیره rankهای doc در hop اصلی (original_query_anchor) — برای boost نهایی
        original_anchor_ranks: Dict[str, int] = {}  # key -> rank (0-based)
        
        for i, hop in enumerate(hops_to_run, 1):
            logger.info(f"🔍 Executing hop {i}/{len(hops_to_run)}: {hop['query']}")
            
            hop_results = await search_function(
                hop["query"],
                collection_name,
                top_k=hop.get("top_k", 10)
            )
            
            if "filter" in hop:
                filter_condition = hop["filter"]
                if "contains" in filter_condition:
                    keyword = filter_condition["contains"]
                    hop_results = [
                        doc for doc in hop_results
                        if keyword in doc["text"].lower()
                    ]
                    logger.info(f"Filtered by '{keyword}': {len(hop_results)} results")
            
            hops_results.append({
                "hop_number": i,
                "purpose": hop["purpose"],
                "query": hop["query"],
                "results_count": len(hop_results),
                "top_result_score": hop_results[0].get("hybrid_score", 0) if hop_results else 0
            })
            
            all_documents.extend(hop_results)
            
            # ثبت rank docها در original_query_anchor برای boost لنگر
            if hop.get("purpose") == "original_query_anchor":
                for rank_idx, doc in enumerate(hop_results[:20]):
                    key = _get_doc_key(doc)
                    if key not in original_anchor_ranks:
                        original_anchor_ranks[key] = rank_idx
            
            # ذخیره top-3 از هر paren hop برای round-robin بعدی
            if hop.get("purpose") == "parenthetical_subtopic":
                top3 = [d for d in hop_results[:3]
                        if d.get("hybrid_score", d.get("score", 0)) >= 0.3]
                if top3:
                    paren_hop_results.append(top3)
                    for rank, doc in enumerate(top3, 1):
                        logger.info(f"   📌 paren-hop#{i} rank#{rank} "
                                   f"score={doc.get('hybrid_score', 0):.3f} "
                                   f"code={doc.get('metadata',{}).get('code','?')}")
        
        # Round-robin اختصاص reserved slots: اول rank#1 از هر hop، سپس rank#2 از هر hop، ...
        # این تضمین می‌کند که هر sub-topic حداقل یک نماینده در نتایج داشته باشد
        paren_reserved_keys: List[str] = []
        if paren_hop_results:
            max_rank = max(len(lst) for lst in paren_hop_results)
            for rank_idx in range(max_rank):
                for hop_docs in paren_hop_results:
                    if rank_idx < len(hop_docs):
                        key = _get_doc_key(hop_docs[rank_idx])
                        if key not in paren_reserved_keys:
                            paren_reserved_keys.append(key)
        
        # 3. dedupe با کلید یکسان — take MAX score + multi-hop bonus
        doc_by_key: Dict[str, Dict] = {}
        hop_counts: Dict[str, int] = {}
        for doc in all_documents:
            key = _get_doc_key(doc)
            score = doc.get("hybrid_score", doc.get("score", 0))
            hop_counts[key] = hop_counts.get(key, 0) + 1
            if key not in doc_by_key:
                # کپی shallow برای تغییر score بدون mutating document اصلی
                doc_by_key[key] = dict(doc)
            else:
                # اگر score بالاتر دیده شد، update
                existing = doc_by_key[key]
                if score > existing.get("hybrid_score", 0):
                    existing["hybrid_score"] = score
                    existing["original_score"] = score
                    existing["score"] = score
        
        # اعمال multi-hop bonus: هر ظهور اضافی در یک hop +0.025 تا سقف 0.06 (کاهش از 0.09)
        # کاهش bonus تا docs sub-hop های narrow غلبه پیدا نکنند
        for key, doc in doc_by_key.items():
            count = hop_counts.get(key, 1)
            if count > 1:
                bonus = min(0.06, (count - 1) * 0.025)
                new_score = min(1.0, doc.get("hybrid_score", 0) + bonus)
                doc["hybrid_score"] = new_score
                doc["original_score"] = new_score
                doc["score"] = new_score
        
        # 🎯 boost docs که در original_query_anchor حضور داشتند (Q کلی)
        # این جلوی حذف docsای که برای سوال کامل مرتبط‌اند ولی در sub-hops نارو هستند را می‌گیرد
        # rank 0-19 → boost 0.15..0.05 (بیشتر از قبل تا docs اصلی گم نشوند)
        _anchor_boosted = 0
        for key, rank in original_anchor_ranks.items():
            if key in doc_by_key:
                doc = doc_by_key[key]
                anchor_bonus = max(0.05, 0.15 - rank * 0.005)
                new_score = min(1.0, doc.get("hybrid_score", 0) + anchor_bonus)
                doc["hybrid_score"] = new_score
                doc["original_score"] = new_score
                doc["score"] = new_score
                _anchor_boosted += 1
        if _anchor_boosted:
            logger.info(f"🎯 [MH_ANCHOR] Boosted {_anchor_boosted} docs from original-query anchor hop")
        
        # 🎯 boost docs که در paren sub-topic top-3 بودند — تا در sort نهایی جایگاه پیدا کنند
        # rank 0→+0.08, 1→+0.06, 2→+0.04
        _paren_boosted = 0
        for hop_docs in paren_hop_results:
            for rank_idx, pdoc in enumerate(hop_docs):
                key = _get_doc_key(pdoc)
                if key in doc_by_key:
                    paren_bonus = max(0.04, 0.08 - rank_idx * 0.02)
                    d = doc_by_key[key]
                    new_score = min(1.0, d.get("hybrid_score", 0) + paren_bonus)
                    d["hybrid_score"] = new_score
                    d["original_score"] = new_score
                    d["score"] = new_score
                    _paren_boosted += 1
        if _paren_boosted:
            logger.info(f"🎯 [MH_PAREN] Boosted {_paren_boosted} paren-top docs")
        
        unique_documents = list(doc_by_key.values())
        
        # 4. مرتب‌سازی نهایی با توجه ویژه به comparison queries 📊
        if analysis.get('type') == 'comparison' and analysis.get('comparison_pair'):
            # برای comparison queries: توزیع یکنواخت documents از هر entity
            cp = analysis['comparison_pair']
            # Support both namedtuple and dict
            entity1 = (cp.entity1 if hasattr(cp, 'entity1') else cp.get('entity1', '')).lower()
            entity2 = (cp.entity2 if hasattr(cp, 'entity2') else cp.get('entity2', '')).lower()
            
            entity1_docs = []
            entity2_docs = []
            other_docs = []
            
            for doc in unique_documents:
                text_lower = doc.get('text', '').lower()
                question_lower = doc.get('metadata', {}).get('question', '').lower()
                subcat_lower = doc.get('metadata', {}).get('subcategory', '').lower()
                full_content = f"{text_lower} {question_lower} {subcat_lower}"
                
                if entity1 in full_content:
                    entity1_docs.append(doc)
                elif entity2 in full_content:
                    entity2_docs.append(doc)
                else:
                    other_docs.append(doc)
            
            # Sort each group by score
            entity1_docs.sort(key=lambda x: x.get("hybrid_score", x.get("score", 0)), reverse=True)
            entity2_docs.sort(key=lambda x: x.get("hybrid_score", x.get("score", 0)), reverse=True)
            other_docs.sort(key=lambda x: x.get("hybrid_score", x.get("score", 0)), reverse=True)
            
            # Interleave documents from both entities
            final_documents = []
            max_per_entity = 5
            for i in range(max(len(entity1_docs), len(entity2_docs), max_per_entity)):
                if i < len(entity1_docs) and len([d for d in final_documents if entity1 in (d.get('text', '') + d.get('metadata', {}).get('question', '')).lower()]) < max_per_entity:
                    final_documents.append(entity1_docs[i])
                if i < len(entity2_docs) and len([d for d in final_documents if entity2 in (d.get('text', '') + d.get('metadata', {}).get('question', '')).lower()]) < max_per_entity:
                    final_documents.append(entity2_docs[i])
            
            # Add other docs if space available
            for doc in other_docs:
                if len(final_documents) < 10:
                    final_documents.append(doc)
            
            logger.info(f"📊 [COMPARISON] Balanced selection: {len([d for d in final_documents[:10] if entity1 in (d.get('text', '') + d.get('metadata', {}).get('question', '')).lower()])} x {entity1}, {len([d for d in final_documents[:10] if entity2 in (d.get('text', '') + d.get('metadata', {}).get('question', '')).lower()])} x {entity2}")
            final_documents = final_documents[:10]
        else:
            # برای non-comparison queries: top-N by hybrid_score سپس reserved paren slots
            # top_section_size را dynamic از top_k بگیر تا docs بااهمیت در نتایج نهایی حفظ شوند
            sorted_by_score = sorted(
                unique_documents,
                key=lambda x: x.get("hybrid_score", 0),
                reverse=True
            )
            
            # اندازه top section = max(12, top_k) تا حداقل به اندازه درخواست api پر شود
            _top_section_size = max(12, top_k if isinstance(top_k, int) else 12)
            top_section = sorted_by_score[:_top_section_size]
            final_keys_set = {_get_doc_key(d) for d in top_section}
            
            # رزرو: از round-robin keys، تا 3 doc که در top_section نیستند (کاهش از 5 به 3)
            reserved_docs = []
            for rkey in paren_reserved_keys:
                if rkey in doc_by_key and rkey not in final_keys_set:
                    reserved_docs.append(doc_by_key[rkey])
                    final_keys_set.add(rkey)
                if len(reserved_docs) >= 3:
                    break
            
            if reserved_docs:
                logger.info(f"🎯 Reserved {len(reserved_docs)} paren-hop docs in final results: "
                           f"{[d.get('metadata', {}).get('code', '?') for d in reserved_docs]}")
            
            final_documents = top_section + reserved_docs
            
            # تکمیل تا 20 با بقیه unique docs
            for d in sorted_by_score[_top_section_size:]:
                if len(final_documents) >= 20:
                    break
                dk = _get_doc_key(d)
                if dk not in final_keys_set:
                    final_documents.append(d)
                    final_keys_set.add(dk)
        
        logger.info(f"✅ Multi-hop completed: {len(hops_results)} hops, {len(final_documents)} final docs")
        analysis["executed_hops"] = hops_results
        
        # ⚠️ Sanitize analysis for JSON serialization
        # تبدیل ComparisonPair به dict اگر وجود دارد
        if "comparison_pair" in analysis and analysis["comparison_pair"] is not None:
            cp = analysis["comparison_pair"]
            # اگر ComparisonPair (namedtuple) است، به dict تبدیل کن
            if hasattr(cp, 'entity1') and hasattr(cp, '_asdict'):
                analysis["comparison_pair"] = {
                    "entity1": cp.entity1,
                    "entity2": cp.entity2,
                    "confidence": cp.confidence,
                    "pattern_used": cp.pattern_used
                }
        
        return {
            "success": True,
            "is_multi_hop": True,
            "hops_results": hops_results,
            "final_documents": final_documents,
            "analysis": analysis,
            "sub_questions": cleaned_sub_questions
        }
    
    def create_multi_hop_context(self, query: str, hops_results: List[Dict], 
                                 final_documents: List[Dict], analysis: Optional[Dict] = None) -> str:
        """
        ایجاد context بهتر برای LLM با اطلاعات multi-hop
        با پشتیبانی ویژه برای سوالات مقایسه‌ای 📊
        
        Args:
            query: سوال اصلی
            hops_results: نتایج هر hop
            final_documents: documents نهایی
            analysis: نتیجه تحلیل query
            
        Returns:
            context متنی برای LLM
        """
        context_parts = []
        
        # تشخیص نوع query
        query_type = analysis.get('type', 'simple') if analysis else 'simple'
        comparison_pair = analysis.get('comparison_pair') if analysis else None
        
        if query_type == "comparison" and comparison_pair:
            # 🎯 Context ویژه برای مقایسه با ComparisonPair
            context_parts.append("📊 سوال مقایسه‌ای تشخیص داده شد.")
            context_parts.append(f"مقایسه بین: **{get_cp_entity(comparison_pair, 'entity1')}** و **{get_cp_entity(comparison_pair, 'entity2')}**")
            context_parts.append("")
            
            # گروه‌بندی documents بر اساس entities
            entity1_docs = []
            entity2_docs = []
            
            for doc in final_documents:
                text_lower = doc.get('text', '').lower()
                question_lower = doc.get('metadata', {}).get('question', '').lower()
                
                # بررسی در هم text و هم question
                full_content = f"{text_lower} {question_lower}"
                
                if get_cp_entity(comparison_pair, 'entity1').lower() in full_content:
                    entity1_docs.append(doc)
                if get_cp_entity(comparison_pair, 'entity2').lower() in full_content:
                    entity2_docs.append(doc)
            
            # نمایش اطلاعات entity1
            context_parts.append(f"### 🔹 اطلاعات {get_cp_entity(comparison_pair, 'entity1')}:")
            if entity1_docs:
                for i, doc in enumerate(entity1_docs[:3], 1):
                    question = doc.get('metadata', {}).get('question', '')
                    text = doc.get('text', '')
                    if question:
                        context_parts.append(f"{i}. **سوال:** {question}")
                        context_parts.append(f"   **پاسخ:** {text[:400]}")
                    else:
                        context_parts.append(f"{i}. {text[:400]}")
            else:
                context_parts.append("⚠️ اطلاعات یافت نشد")
            
            context_parts.append("")
            
            # نمایش اطلاعات entity2
            context_parts.append(f"### 🔸 اطلاعات {get_cp_entity(comparison_pair, 'entity2')}:")
            if entity2_docs:
                for i, doc in enumerate(entity2_docs[:3], 1):
                    question = doc.get('metadata', {}).get('question', '')
                    text = doc.get('text', '')
                    if question:
                        context_parts.append(f"{i}. **سوال:** {question}")
                        context_parts.append(f"   **پاسخ:** {text[:400]}")
                    else:
                        context_parts.append(f"{i}. {text[:400]}")
            else:
                context_parts.append("⚠️ اطلاعات یافت نشد")
            
            context_parts.extend([
                "",
                "💡 **دستورالعمل:**",
                "- تفاوت‌ها و شباهت‌های کلیدی را به صورت واضح بیان کنید",
                "- از ساختار مقایسه‌ای استفاده کنید (bullet points یا جدول)",
                "- هر entity را به طور کامل توضیح دهید",
                ""
            ])
            
        elif query_type == "comparison":
            # برای مقایسه‌های بدون ComparisonPair (روش قدیمی)
            context_parts.append("📊 سوال مقایسه‌ای تشخیص داده شد.")
            context_parts.append("لطفاً اطلاعات مربوط به هر entity را جداگانه استخراج کرده و سپس مقایسه کنید.")
            context_parts.append("")
            
            # گروه‌بندی documents بر اساس hops
            hop_docs = {}
            for i, hop in enumerate(hops_results):
                hop_query = hop.get('query', '')
                # پیدا کردن documents مربوط به این hop
                related_docs = [doc for doc in final_documents if hop_query.lower() in doc.get('text', '').lower()[:200]]
                if related_docs:
                    hop_docs[hop_query] = related_docs[:3]
            
            # نمایش اطلاعات برای هر entity
            for entity, docs in hop_docs.items():
                context_parts.append(f"🔹 اطلاعات مربوط به '{entity}':")
                for doc in docs:
                    context_parts.append(f"  - {doc['text'][:300]}")
                context_parts.append("")
            
            # اگر documents گروه‌بندی نشدند، همه را نمایش بده
            if not hop_docs:
                context_parts.append("📄 اسناد مرتبط:")
                for i, doc in enumerate(final_documents[:6], 1):
                    context_parts.append(f"[سند {i}] {doc['text']}")
                    context_parts.append("")
        
        elif query_type == "multi_part":
            # 🎯 Context ویژه برای سوالات چندبخشی
            context_parts.append("📝 سوال چندبخشی تشخیص داده شد.")
            sub_questions = analysis.get('sub_questions', []) if analysis else []
            context_parts.append(f"تعداد sub-questions: {len(sub_questions)}")
            context_parts.append("")
            
            # برای هر sub-question، documents مرتبط را نمایش بده
            for i, (hop, sub_q) in enumerate(zip(hops_results, sub_questions), 1):
                context_parts.append(f"### ❓ سوال {i}: {sub_q}")
                
                # پیدا کردن documents مربوط به این sub-question
                related_docs = []
                hop_query = hop.get('query', '').lower()
                
                for doc in final_documents:
                    text_lower = doc.get('text', '').lower()
                    question_lower = doc.get('metadata', {}).get('question', '').lower()
                    # بررسی شباهت با sub-question یا hop query
                    if any(word in question_lower for word in hop_query.split() if len(word) >= 4):
                        related_docs.append(doc)
                
                # نمایش documents
                if related_docs:
                    for j, doc in enumerate(related_docs[:2], 1):  # حداکثر 2 doc برای هر sub-q
                        meta = doc.get('metadata', {})
                        question = meta.get('question', '')
                        answer = meta.get('answer', doc.get('text', ''))
                        tag = meta.get('tag', meta.get('تگ', ''))
                        
                        context_parts.append(f"  📄 سند {j}:")
                        if question:
                            context_parts.append(f"     سوال: {question}")
                        if tag:
                            context_parts.append(f"     تگ: {tag}")
                        context_parts.append(f"     پاسخ: {answer[:400]}")
                else:
                    context_parts.append("  ⚠️ سند مرتبط یافت نشد")
                
                context_parts.append("")
            
            context_parts.extend([
                "",
                "💡 **دستورالعمل:**",
                "- به هر sub-question به طور جداگانه پاسخ دهید",
                "- پاسخ را به صورت ساختاریافته و واضح بیان کنید",
                "- از اطلاعات هر سند مرتبط استفاده کنید",
                ""
            ])
        
        else:
            # برای سوالات عادی multi-hop
            context_parts.append("🔍 نتایج جستجوی چند مرحله‌ای:")
            context_parts.append("")
            
            for hop in hops_results:
                context_parts.append(f"مرحله {hop['hop_number']}: {hop['purpose']}")
                context_parts.append(f"  سوال: {hop['query']}")
                context_parts.append(f"  نتایج: {hop['results_count']} سند")
                context_parts.append("")
            
            context_parts.append("📄 اسناد مرتبط:")
            context_parts.append("")
            
            for i, doc in enumerate(final_documents[:5], 1):
                context_parts.append(f"[سند {i}]")
                context_parts.append(doc["text"])
                context_parts.append("")
        
        return "\n".join(context_parts)


# Test function
def test_multi_hop():
    """تست multi-hop retriever"""
    print("🧪 Testing Multi-Hop Retriever...")
    
    retriever = MultiHopRetriever()
    
    # Test queries
    test_queries = [
        "جمع کل مالیات مشاغل چقدره؟",
        "تفاوت بین ملی و استانی چیست؟",
        "میانگین درآمدها چقدر است؟",
        "بند چهارم چیست؟"  # simple query
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        analysis = retriever.analyze_query(query)
        
        print(f"  Type: {analysis['type']}")
        print(f"  Multi-hop: {analysis['requires_multi_hop']}")
        print(f"  Target entity: {analysis['target_entity']}")
        print(f"  Operation: {analysis['operation']}")
        print(f"  Hops: {len(analysis['hops'])}")
        
        if analysis['hops']:
            for i, hop in enumerate(analysis['hops'], 1):
                print(f"    Hop {i}: {hop['query']} (purpose: {hop['purpose']})")
    
    print("\n✅ Multi-Hop Retriever test completed!")


if __name__ == "__main__":
    test_multi_hop()

