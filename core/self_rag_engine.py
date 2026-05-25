# -*- coding: utf-8 -*-
"""
Self-RAG Engine
موتور Self-Reflective Retrieval-Augmented Generation
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger
from dataclasses import dataclass
from enum import Enum

class ReflectionType(Enum):
    """انواع reflection"""
    RETRIEVAL_QUALITY = "retrieval_quality"
    ANSWER_CONFIDENCE = "answer_confidence"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"

@dataclass
class ReflectionResult:
    """نتیجه reflection"""
    reflection_type: ReflectionType
    score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    reasoning: str
    needs_refinement: bool
    suggestions: List[str]

@dataclass
class RetrievalQuality:
    """کیفیت بازیابی"""
    relevance_score: float
    completeness_score: float
    diversity_score: float
    overall_score: float
    issues: List[str]
    suggestions: List[str]

@dataclass
class AnswerConfidence:
    """اطمینان پاسخ"""
    factual_accuracy: float
    completeness: float
    coherence: float
    overall_confidence: float
    concerns: List[str]
    improvements: List[str]

class SelfRAGEngine:
    """موتور Self-RAG برای reflection و refinement"""
    
    def __init__(
        self,
        qwen_client=None,
        confidence_threshold: float = 0.7,
        max_refinement_iterations: int = 3,
        enable_reflection: bool = True
    ):
        self.qwen_client = qwen_client
        self.confidence_threshold = confidence_threshold
        self.max_refinement_iterations = max_refinement_iterations
        self.enable_reflection = enable_reflection
        
        # Reflection prompts
        self.reflection_prompts = self._initialize_reflection_prompts()
        
        # Performance tracking
        self.reflection_count = 0
        self.refinement_count = 0
        self.total_reflection_time = 0.0
    
    def _initialize_reflection_prompts(self) -> Dict[str, str]:
        """مقداردهی اولیه reflection prompts"""
        return {
            "retrieval_quality": """
            شما یک متخصص ارزیابی کیفیت بازیابی اطلاعات هستید. لطفاً کیفیت اسناد بازیابی شده را ارزیابی کنید:

            سوال: {query}
            اسناد بازیابی شده: {retrieved_docs}

            لطفاً در مورد موارد زیر نظر دهید:
            1. آیا اسناد بازیابی شده مرتبط با سوال هستند؟ (0-1)
            2. آیا اطلاعات کافی برای پاسخ موجود است؟ (0-1)
            3. آیا تنوع مناسبی در اسناد وجود دارد؟ (0-1)
            4. چه مشکلاتی در بازیابی وجود دارد؟
            5. چه پیشنهاداتی برای بهبود دارید؟

            پاسخ را در قالب JSON ارائه دهید:
            {{
                "relevance_score": 0.8,
                "completeness_score": 0.7,
                "diversity_score": 0.6,
                "overall_score": 0.7,
                "issues": ["مشکل 1", "مشکل 2"],
                "suggestions": ["پیشنهاد 1", "پیشنهاد 2"]
            }}
            """,
            
            "answer_confidence": """
            شما یک متخصص ارزیابی کیفیت پاسخ هستید. لطفاً کیفیت پاسخ تولید شده را ارزیابی کنید:

            سوال: {query}
            پاسخ: {answer}
            منابع: {sources}

            لطفاً در مورد موارد زیر نظر دهید:
            1. آیا پاسخ از نظر واقعی درست است؟ (0-1)
            2. آیا پاسخ کامل است؟ (0-1)
            3. آیا پاسخ منسجم و منطقی است؟ (0-1)
            4. چه نگرانی‌هایی در مورد پاسخ وجود دارد؟
            5. چه بهبودهایی می‌توان انجام داد؟

            پاسخ را در قالب JSON ارائه دهید:
            {{
                "factual_accuracy": 0.8,
                "completeness": 0.7,
                "coherence": 0.9,
                "overall_confidence": 0.8,
                "concerns": ["نگرانی 1", "نگرانی 2"],
                "improvements": ["بهبود 1", "بهبود 2"]
            }}
            """,
            
            "completeness_check": """
            آیا پاسخ ارائه شده کامل است؟ آیا تمام جنبه‌های سوال پوشش داده شده است؟

            سوال: {query}
            پاسخ: {answer}

            لطفاً بررسی کنید:
            1. آیا تمام بخش‌های سوال پاسخ داده شده؟
            2. آیا جزئیات کافی ارائه شده؟
            3. آیا مثال‌ها یا توضیحات اضافی نیاز است؟

            پاسخ: بله/خیر - توضیح
            """,
            
            "consistency_check": """
            آیا اطلاعات ارائه شده در پاسخ سازگار و منطقی است؟

            سوال: {query}
            پاسخ: {answer}
            منابع: {sources}

            لطفاً بررسی کنید:
            1. آیا اطلاعات متناقض وجود دارد؟
            2. آیا استدلال منطقی است؟
            3. آیا منابع با پاسخ همخوانی دارند؟

            پاسخ: بله/خیر - توضیح
            """
        }
    
    async def evaluate_retrieval_quality(
        self, 
        query: str, 
        retrieved_docs: List[Dict[str, Any]]
    ) -> RetrievalQuality:
        """ارزیابی کیفیت بازیابی"""
        if not self.enable_reflection:
            return RetrievalQuality(1.0, 1.0, 1.0, 1.0, [], [])
        
        try:
            start_time = time.time()
            
            # آماده‌سازی اسناد برای ارزیابی
            docs_text = []
            for i, doc in enumerate(retrieved_docs[:5]):  # فقط 5 سند اول
                doc_text = f"سند {i+1}: {doc.get('text', '')[:200]}..."
                docs_text.append(doc_text)
            
            retrieved_docs_text = "\n\n".join(docs_text)
            
            # ارسال به LLM برای ارزیابی
            prompt = self.reflection_prompts["retrieval_quality"].format(
                query=query,
                retrieved_docs=retrieved_docs_text
            )
            
            if self.qwen_client:
                response = await self.qwen_client.generate_response(
                    prompt=prompt,
                    max_tokens=500,
                    temperature=0.1
                )
                
                # Parse JSON response
                try:
                    import json
                    # Extract text from GenerationResponse
                    response_text = response.text if hasattr(response, 'text') else str(response)
                    result = json.loads(response_text)
                    
                    quality = RetrievalQuality(
                        relevance_score=result.get("relevance_score", 0.5),
                        completeness_score=result.get("completeness_score", 0.5),
                        diversity_score=result.get("diversity_score", 0.5),
                        overall_score=result.get("overall_score", 0.5),
                        issues=result.get("issues", []),
                        suggestions=result.get("suggestions", [])
                    )
                    
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    quality = RetrievalQuality(0.5, 0.5, 0.5, 0.5, ["JSON parsing failed"], [])
            else:
                # Fallback if no LLM client
                quality = RetrievalQuality(0.5, 0.5, 0.5, 0.5, ["No LLM client"], [])
            
            # ردیابی عملکرد
            reflection_time = time.time() - start_time
            self._track_reflection(reflection_time)
            
            logger.debug(f"Retrieval quality evaluated: {quality.overall_score:.3f}")
            return quality
            
        except Exception as e:
            logger.error(f"❌ Failed to evaluate retrieval quality: {e}")
            return RetrievalQuality(0.5, 0.5, 0.5, 0.5, [str(e)], [])
    
    async def assess_answer_confidence(
        self, 
        query: str, 
        answer: str, 
        sources: List[Dict[str, Any]]
    ) -> AnswerConfidence:
        """ارزیابی اطمینان پاسخ"""
        if not self.enable_reflection:
            return AnswerConfidence(1.0, 1.0, 1.0, 1.0, [], [])
        
        try:
            start_time = time.time()
            
            # آماده‌سازی منابع
            sources_text = []
            for i, source in enumerate(sources[:3]):  # فقط 3 منبع اول
                source_text = f"منبع {i+1}: {source.get('text', '')[:150]}..."
                sources_text.append(source_text)
            
            sources_text_combined = "\n\n".join(sources_text)
            
            # ارسال به LLM برای ارزیابی
            prompt = self.reflection_prompts["answer_confidence"].format(
                query=query,
                answer=answer,
                sources=sources_text_combined
            )
            
            if self.qwen_client:
                response = await self.qwen_client.generate_response(
                    prompt=prompt,
                    max_tokens=500,
                    temperature=0.1
                )
                
                # Parse JSON response
                try:
                    import json
                    # Extract text from GenerationResponse
                    response_text = response.text if hasattr(response, 'text') else str(response)
                    result = json.loads(response_text)
                    
                    confidence = AnswerConfidence(
                        factual_accuracy=result.get("factual_accuracy", 0.5),
                        completeness=result.get("completeness", 0.5),
                        coherence=result.get("coherence", 0.5),
                        overall_confidence=result.get("overall_confidence", 0.5),
                        concerns=result.get("concerns", []),
                        improvements=result.get("improvements", [])
                    )
                    
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    confidence = AnswerConfidence(0.5, 0.5, 0.5, 0.5, ["JSON parsing failed"], [])
            else:
                # Fallback if no LLM client
                confidence = AnswerConfidence(0.5, 0.5, 0.5, 0.5, ["No LLM client"], [])
            
            # ردیابی عملکرد
            reflection_time = time.time() - start_time
            self._track_reflection(reflection_time)
            
            logger.debug(f"Answer confidence assessed: {confidence.overall_confidence:.3f}")
            return confidence
            
        except Exception as e:
            logger.error(f"❌ Failed to assess answer confidence: {e}")
            return AnswerConfidence(0.5, 0.5, 0.5, 0.5, [str(e)], [])
    
    async def check_completeness(
        self, 
        query: str, 
        answer: str
    ) -> ReflectionResult:
        """بررسی کامل بودن پاسخ"""
        if not self.enable_reflection:
            return ReflectionResult(
                ReflectionType.COMPLETENESS, 1.0, 1.0, "Reflection disabled", False, []
            )
        
        try:
            start_time = time.time()
            
            prompt = self.reflection_prompts["completeness_check"].format(
                query=query,
                answer=answer
            )
            
            if self.qwen_client:
                response = await self.qwen_client.generate_response(
                    prompt=prompt,
                    max_tokens=200,
                    temperature=0.1
                )
                
                # Parse response
                response_text = response.text if hasattr(response, 'text') else str(response)
                is_complete = "بله" in response_text or "yes" in response_text.lower()
                score = 1.0 if is_complete else 0.3
                needs_refinement = not is_complete
                
                result = ReflectionResult(
                    reflection_type=ReflectionType.COMPLETENESS,
                    score=score,
                    confidence=0.8,
                    reasoning=response_text,
                    needs_refinement=needs_refinement,
                    suggestions=["پاسخ کامل‌تر ارائه دهید"] if needs_refinement else []
                )
            else:
                result = ReflectionResult(
                    ReflectionType.COMPLETENESS, 0.5, 0.5, "No LLM client", False, []
                )
            
            # ردیابی عملکرد
            reflection_time = time.time() - start_time
            self._track_reflection(reflection_time)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to check completeness: {e}")
            return ReflectionResult(
                ReflectionType.COMPLETENESS, 0.5, 0.5, str(e), False, []
            )
    
    async def check_consistency(
        self, 
        query: str, 
        answer: str, 
        sources: List[Dict[str, Any]]
    ) -> ReflectionResult:
        """بررسی سازگاری پاسخ"""
        if not self.enable_reflection:
            return ReflectionResult(
                ReflectionType.CONSISTENCY, 1.0, 1.0, "Reflection disabled", False, []
            )
        
        try:
            start_time = time.time()
            
            sources_text = "\n".join([s.get('text', '')[:100] for s in sources[:3]])
            
            prompt = self.reflection_prompts["consistency_check"].format(
                query=query,
                answer=answer,
                sources=sources_text
            )
            
            if self.qwen_client:
                response = await self.qwen_client.generate_response(
                    prompt=prompt,
                    max_tokens=200,
                    temperature=0.1
                )
                
                # Parse response
                response_text = response.text if hasattr(response, 'text') else str(response)
                is_consistent = "بله" in response_text or "yes" in response_text.lower()
                score = 1.0 if is_consistent else 0.3
                needs_refinement = not is_consistent
                
                result = ReflectionResult(
                    reflection_type=ReflectionType.CONSISTENCY,
                    score=score,
                    confidence=0.8,
                    reasoning=response_text,
                    needs_refinement=needs_refinement,
                    suggestions=["بررسی سازگاری اطلاعات"] if needs_refinement else []
                )
            else:
                result = ReflectionResult(
                    ReflectionType.CONSISTENCY, 0.5, 0.5, "No LLM client", False, []
                )
            
            # ردیابی عملکرد
            reflection_time = time.time() - start_time
            self._track_reflection(reflection_time)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to check consistency: {e}")
            return ReflectionResult(
                ReflectionType.CONSISTENCY, 0.5, 0.5, str(e), False, []
            )
    
    async def refine_retrieval(
        self, 
        query: str, 
        low_quality_docs: List[Dict[str, Any]],
        suggestions: List[str]
    ) -> List[Dict[str, Any]]:
        """بهبود بازیابی بر اساس پیشنهادات"""
        try:
            # اینجا می‌توانید از استراتژی‌های مختلف برای بهبود بازیابی استفاده کنید
            # فعلاً یک پیاده‌سازی ساده ارائه می‌دهم
            
            refined_docs = low_quality_docs.copy()
            
            # اعمال پیشنهادات
            for suggestion in suggestions:
                if "تنوع" in suggestion or "diversity" in suggestion.lower():
                    # اضافه کردن اسناد متنوع‌تر
                    pass
                elif "مرتبط" in suggestion or "relevant" in suggestion.lower():
                    # فیلتر کردن اسناد نامرتبط
                    pass
            
            self.refinement_count += 1
            logger.debug(f"Retrieval refined based on {len(suggestions)} suggestions")
            
            return refined_docs
            
        except Exception as e:
            logger.error(f"❌ Failed to refine retrieval: {e}")
            return low_quality_docs
    
    async def generate_citations(
        self, 
        answer: str, 
        sources: List[Dict[str, Any]]
    ) -> str:
        """تولید پاسخ با ارجاع به منابع"""
        try:
            if not sources:
                return answer
            
            # ایجاد citations
            citations = []
            for i, source in enumerate(sources[:5]):  # حداکثر 5 منبع
                citation = f"[{i+1}] {source.get('text', '')[:100]}..."
                citations.append(citation)
            
            # اضافه کردن citations به پاسخ
            cited_answer = f"{answer}\n\n**منابع:**\n" + "\n".join(citations)
            
            logger.debug(f"Generated citations for {len(sources)} sources")
            return cited_answer
            
        except Exception as e:
            logger.error(f"❌ Failed to generate citations: {e}")
            return answer
    
    def _track_reflection(self, reflection_time: float):
        """ردیابی عملکرد reflection"""
        self.reflection_count += 1
        self.total_reflection_time += reflection_time
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """آمار عملکرد"""
        avg_reflection_time = self.total_reflection_time / max(self.reflection_count, 1)
        
        return {
            'reflection_count': self.reflection_count,
            'refinement_count': self.refinement_count,
            'total_reflection_time': self.total_reflection_time,
            'average_reflection_time': avg_reflection_time,
            'confidence_threshold': self.confidence_threshold,
            'max_refinement_iterations': self.max_refinement_iterations,
            'enable_reflection': self.enable_reflection
        }
    
    def reset_stats(self):
        """بازنشانی آمار"""
        self.reflection_count = 0
        self.refinement_count = 0
        self.total_reflection_time = 0.0
    
    async def evaluate_database_quality(
        self,
        query: str,
        database_results: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        ارزیابی کیفیت نتایج database
        
        Args:
            query: سوال کاربر
            database_results: نتایج database
            
        Returns:
            Dict با relevance, completeness, confidence
        """
        try:
            rows = database_results.get("results") or database_results.get("rows") or []
            columns = database_results.get("columns") or []
            
            # بررسی پایه: آیا داده وجود دارد؟
            if not rows or not columns:
                return {
                    "relevance": 0.0,
                    "completeness": 0.0,
                    "confidence": 0.0,
                    "issues": ["نتایج خالی است"]
                }
            
            # محاسبه relevance بر اساس تعداد سطرها
            relevance = min(len(rows) / 10.0, 1.0)  # حداکثر 10 سطر = relevance کامل
            
            # محاسبه completeness بر اساس تعداد ستون‌ها
            completeness = min(len(columns) / 5.0, 1.0)  # حداکثر 5 ستون = completeness کامل
            
            # محاسبه confidence کلی
            confidence = (relevance + completeness) / 2.0
            
            logger.info(f"📊 DB Quality: relevance={relevance:.2f}, completeness={completeness:.2f}, confidence={confidence:.2f}")
            
            return {
                "relevance": relevance,
                "completeness": completeness,
                "confidence": confidence,
                "rows_count": len(rows),
                "columns_count": len(columns)
            }
            
        except Exception as e:
            logger.error(f"❌ Database quality evaluation failed: {e}")
            return {
                "relevance": 0.5,
                "completeness": 0.5,
                "confidence": 0.5,
                "error": str(e)
            }

