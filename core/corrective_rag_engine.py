# -*- coding: utf-8 -*-
"""
Corrective RAG Engine
موتور Corrective Retrieval-Augmented Generation برای تشخیص و تصحیح خطاها
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger
from dataclasses import dataclass
from enum import Enum

class ErrorType(Enum):
    """انواع خطاهای قابل تشخیص"""
    HALLUCINATION = "hallucination"
    IRRELEVANT_RETRIEVAL = "irrelevant_retrieval"
    INCOMPLETE_ANSWER = "incomplete_answer"
    CONTRADICTORY_INFORMATION = "contradictory_information"
    FACTUAL_ERROR = "factual_error"
    LOGICAL_INCONSISTENCY = "logical_inconsistency"

@dataclass
class ErrorDetection:
    """نتیجه تشخیص خطا"""
    error_type: ErrorType
    confidence: float  # 0.0 to 1.0
    severity: str  # "low", "medium", "high"
    description: str
    evidence: List[str]
    suggestions: List[str]

@dataclass
class CorrectionResult:
    """نتیجه تصحیح"""
    original_answer: str
    corrected_answer: str
    corrections_applied: List[str]
    confidence: float
    success: bool

class CorrectiveRAGEngine:
    """موتور Corrective RAG برای تشخیص و تصحیح خطاها"""
    
    def __init__(
        self,
        qwen_client=None,
        error_threshold: float = 0.6,
        enable_verification: bool = True,
        enable_correction: bool = True
    ):
        self.qwen_client = qwen_client
        self.error_threshold = error_threshold
        self.enable_verification = enable_verification
        self.enable_correction = enable_correction
        
        # Error detection prompts
        self.error_detection_prompts = self._initialize_error_detection_prompts()
        
        # Performance tracking
        self.error_detection_count = 0
        self.correction_count = 0
        self.total_detection_time = 0.0
        self.total_correction_time = 0.0
    
    def _initialize_error_detection_prompts(self) -> Dict[str, str]:
        """مقداردهی اولیه prompts تشخیص خطا"""
        return {
            "hallucination": """
            شما یک متخصص تشخیص خطا در سیستم‌های RAG هستید. لطفاً بررسی کنید که آیا پاسخ ارائه شده شامل اطلاعات ساختگی (hallucination) است یا نه.

            سوال: {query}
            پاسخ: {answer}
            منابع: {sources}

            لطفاً بررسی کنید:
            1. آیا پاسخ شامل اطلاعاتی است که در منابع موجود نیست؟
            2. آیا اطلاعات ارائه شده بدون منبع است؟
            3. آیا پاسخ شامل جزئیات اضافی است که در منابع نیامده؟

            پاسخ را در قالب JSON ارائه دهید:
            {{
                "is_hallucinated": true/false,
                "confidence": 0.8,
                "evidence": ["شواهد 1", "شواهد 2"],
                "suggestions": ["پیشنهاد 1", "پیشنهاد 2"]
            }}
            """,
            
            "irrelevant_retrieval": """
            شما یک متخصص تشخیص خطا در سیستم‌های RAG هستید. لطفاً بررسی کنید که آیا اسناد بازیابی شده مرتبط با سوال هستند یا نه.

            سوال: {query}
            اسناد بازیابی شده: {retrieved_docs}

            لطفاً بررسی کنید:
            1. آیا اسناد بازیابی شده به سوال مرتبط هستند؟
            2. آیا اطلاعات موجود در اسناد برای پاسخ دادن کافی است؟
            3. آیا اسناد نامرتبط وجود دارد؟

            پاسخ را در قالب JSON ارائه دهید:
            {{
                "has_irrelevant_docs": true/false,
                "confidence": 0.8,
                "irrelevant_indices": [1, 3],
                "evidence": ["شواهد 1", "شواهد 2"],
                "suggestions": ["پیشنهاد 1", "پیشنهاد 2"]
            }}
            """,
            
            "incomplete_answer": """
            شما یک متخصص تشخیص خطا در سیستم‌های RAG هستید. لطفاً بررسی کنید که آیا پاسخ ارائه شده کامل است یا نه.

            سوال: {query}
            پاسخ: {answer}

            لطفاً بررسی کنید:
            1. آیا تمام جنبه‌های سوال پاسخ داده شده؟
            2. آیا جزئیات کافی ارائه شده؟
            3. آیا پاسخ ناقص است؟

            پاسخ را در قالب JSON ارائه دهید:
            {{
                "is_incomplete": true/false,
                "confidence": 0.8,
                "missing_aspects": ["جنبه 1", "جنبه 2"],
                "evidence": ["شواهد 1", "شواهد 2"],
                "suggestions": ["پیشنهاد 1", "پیشنهاد 2"]
            }}
            """,
            
            "contradictory_information": """
            شما یک متخصص تشخیص خطا در سیستم‌های RAG هستید. لطفاً بررسی کنید که آیا اطلاعات ارائه شده متناقض است یا نه.

            سوال: {query}
            پاسخ: {answer}
            منابع: {sources}

            لطفاً بررسی کنید:
            1. آیا اطلاعات متناقض در پاسخ وجود دارد؟
            2. آیا منابع با هم سازگار هستند؟
            3. آیا استدلال منطقی است؟

            پاسخ را در قالب JSON ارائه دهید:
            {{
                "has_contradictions": true/false,
                "confidence": 0.8,
                "contradictions": ["تناقض 1", "تناقض 2"],
                "evidence": ["شواهد 1", "شواهد 2"],
                "suggestions": ["پیشنهاد 1", "پیشنهاد 2"]
            }}
            """,
            
            "factual_error": """
            شما یک متخصص تشخیص خطا در سیستم‌های RAG هستید. لطفاً بررسی کنید که آیا پاسخ شامل خطاهای واقعی است یا نه.

            سوال: {query}
            پاسخ: {answer}
            منابع: {sources}

            لطفاً بررسی کنید:
            1. آیا اعداد و ارقام درست هستند؟
            2. آیا نام‌ها و تاریخ‌ها صحیح هستند؟
            3. آیا اطلاعات واقعی درست ارائه شده؟

            پاسخ را در قالب JSON ارائه دهید:
            {{
                "has_factual_errors": true/false,
                "confidence": 0.8,
                "errors": ["خطا 1", "خطا 2"],
                "evidence": ["شواهد 1", "شواهد 2"],
                "suggestions": ["پیشنهاد 1", "پیشنهاد 2"]
            }}
            """,
            
            "logical_inconsistency": """
            شما یک متخصص تشخیص خطا در سیستم‌های RAG هستید. لطفاً بررسی کنید که آیا پاسخ از نظر منطقی سازگار است یا نه.

            سوال: {query}
            پاسخ: {answer}

            لطفاً بررسی کنید:
            1. آیا استدلال منطقی است؟
            2. آیا نتیجه‌گیری درست است؟
            3. آیا تناقض منطقی وجود دارد؟

            پاسخ را در قالب JSON ارائه دهید:
            {{
                "has_logical_inconsistency": true/false,
                "confidence": 0.8,
                "inconsistencies": ["ناسازگاری 1", "ناسازگاری 2"],
                "evidence": ["شواهد 1", "شواهد 2"],
                "suggestions": ["پیشنهاد 1", "پیشنهاد 2"]
            }}
            """
        }
    
    async def detect_hallucination(
        self, 
        query: str, 
        answer: str, 
        sources: List[Dict[str, Any]]
    ) -> ErrorDetection:
        """تشخیص hallucination در پاسخ"""
        if not self.enable_verification:
            return ErrorDetection(
                ErrorType.HALLUCINATION, 0.0, "low", "Verification disabled", [], []
            )
        
        try:
            start_time = time.time()
            
            # آماده‌سازی منابع
            sources_text = []
            for i, source in enumerate(sources[:3]):
                source_text = f"منبع {i+1}: {source.get('text', '')[:200]}..."
                sources_text.append(source_text)
            
            sources_text_combined = "\n\n".join(sources_text)
            
            # ارسال به LLM برای تشخیص
            prompt = self.error_detection_prompts["hallucination"].format(
                query=query,
                answer=answer,
                sources=sources_text_combined
            )
            
            if self.qwen_client:
                response = await self.qwen_client.generate_response(
                    prompt=prompt,
                    max_tokens=300,
                    temperature=0.1
                )
                
                # Parse JSON response
                try:
                    import json
                    # Extract text from GenerationResponse
                    response_text = response.text if hasattr(response, 'text') else str(response)
                    result = json.loads(response_text)
                    
                    is_hallucinated = result.get("is_hallucinated", False)
                    confidence = result.get("confidence", 0.5)
                    
                    severity = "high" if confidence > 0.8 else "medium" if confidence > 0.5 else "low"
                    
                    detection = ErrorDetection(
                        error_type=ErrorType.HALLUCINATION,
                        confidence=confidence,
                        severity=severity,
                        description="Hallucination detected" if is_hallucinated else "No hallucination detected",
                        evidence=result.get("evidence", []),
                        suggestions=result.get("suggestions", [])
                    )
                    
                except json.JSONDecodeError:
                    detection = ErrorDetection(
                        ErrorType.HALLUCINATION, 0.5, "medium", "JSON parsing failed", [], []
                    )
            else:
                detection = ErrorDetection(
                    ErrorType.HALLUCINATION, 0.5, "medium", "No LLM client", [], []
                )
            
            # ردیابی عملکرد
            detection_time = time.time() - start_time
            self._track_detection(detection_time)
            
            logger.debug(f"Hallucination detection: {detection.confidence:.3f}")
            return detection
            
        except Exception as e:
            logger.error(f"❌ Failed to detect hallucination: {e}")
            return ErrorDetection(
                ErrorType.HALLUCINATION, 0.5, "medium", str(e), [], []
            )
    
    async def detect_irrelevant_retrieval(
        self, 
        query: str, 
        retrieved_docs: List[Dict[str, Any]]
    ) -> ErrorDetection:
        """تشخیص اسناد نامرتبط"""
        if not self.enable_verification:
            return ErrorDetection(
                ErrorType.IRRELEVANT_RETRIEVAL, 0.0, "low", "Verification disabled", [], []
            )
        
        try:
            start_time = time.time()
            
            # آماده‌سازی اسناد
            docs_text = []
            for i, doc in enumerate(retrieved_docs[:5]):
                doc_text = f"سند {i+1}: {doc.get('text', '')[:150]}..."
                docs_text.append(doc_text)
            
            retrieved_docs_text = "\n\n".join(docs_text)
            
            # ارسال به LLM برای تشخیص
            prompt = self.error_detection_prompts["irrelevant_retrieval"].format(
                query=query,
                retrieved_docs=retrieved_docs_text
            )
            
            if self.qwen_client:
                response = await self.qwen_client.generate_response(
                    prompt=prompt,
                    max_tokens=300,
                    temperature=0.1
                )
                
                # Parse JSON response
                try:
                    import json
                    # Extract text from GenerationResponse
                    response_text = response.text if hasattr(response, 'text') else str(response)
                    result = json.loads(response_text)
                    
                    has_irrelevant = result.get("has_irrelevant_docs", False)
                    confidence = result.get("confidence", 0.5)
                    
                    severity = "high" if confidence > 0.8 else "medium" if confidence > 0.5 else "low"
                    
                    detection = ErrorDetection(
                        error_type=ErrorType.IRRELEVANT_RETRIEVAL,
                        confidence=confidence,
                        severity=severity,
                        description="Irrelevant documents detected" if has_irrelevant else "All documents relevant",
                        evidence=result.get("evidence", []),
                        suggestions=result.get("suggestions", [])
                    )
                    
                except json.JSONDecodeError:
                    detection = ErrorDetection(
                        ErrorType.IRRELEVANT_RETRIEVAL, 0.5, "medium", "JSON parsing failed", [], []
                    )
            else:
                detection = ErrorDetection(
                    ErrorType.IRRELEVANT_RETRIEVAL, 0.5, "medium", "No LLM client", [], []
                )
            
            # ردیابی عملکرد
            detection_time = time.time() - start_time
            self._track_detection(detection_time)
            
            logger.debug(f"Irrelevant retrieval detection: {detection.confidence:.3f}")
            return detection
            
        except Exception as e:
            logger.error(f"❌ Failed to detect irrelevant retrieval: {e}")
            return ErrorDetection(
                ErrorType.IRRELEVANT_RETRIEVAL, 0.5, "medium", str(e), [], []
            )
    
    async def detect_incomplete_answer(
        self, 
        query: str, 
        answer: str
    ) -> ErrorDetection:
        """تشخیص پاسخ ناقص"""
        if not self.enable_verification:
            return ErrorDetection(
                ErrorType.INCOMPLETE_ANSWER, 0.0, "low", "Verification disabled", [], []
            )
        
        try:
            start_time = time.time()
            
            # ارسال به LLM برای تشخیص
            prompt = self.error_detection_prompts["incomplete_answer"].format(
                query=query,
                answer=answer
            )
            
            if self.qwen_client:
                response = await self.qwen_client.generate_response(
                    prompt=prompt,
                    max_tokens=300,
                    temperature=0.1
                )
                
                # Parse JSON response
                try:
                    import json
                    # Extract text from GenerationResponse
                    response_text = response.text if hasattr(response, 'text') else str(response)
                    result = json.loads(response_text)
                    
                    is_incomplete = result.get("is_incomplete", False)
                    confidence = result.get("confidence", 0.5)
                    
                    severity = "high" if confidence > 0.8 else "medium" if confidence > 0.5 else "low"
                    
                    detection = ErrorDetection(
                        error_type=ErrorType.INCOMPLETE_ANSWER,
                        confidence=confidence,
                        severity=severity,
                        description="Incomplete answer detected" if is_incomplete else "Answer is complete",
                        evidence=result.get("evidence", []),
                        suggestions=result.get("suggestions", [])
                    )
                    
                except json.JSONDecodeError:
                    detection = ErrorDetection(
                        ErrorType.INCOMPLETE_ANSWER, 0.5, "medium", "JSON parsing failed", [], []
                    )
            else:
                detection = ErrorDetection(
                    ErrorType.INCOMPLETE_ANSWER, 0.5, "medium", "No LLM client", [], []
                )
            
            # ردیابی عملکرد
            detection_time = time.time() - start_time
            self._track_detection(detection_time)
            
            logger.debug(f"Incomplete answer detection: {detection.confidence:.3f}")
            return detection
            
        except Exception as e:
            logger.error(f"❌ Failed to detect incomplete answer: {e}")
            return ErrorDetection(
                ErrorType.INCOMPLETE_ANSWER, 0.5, "medium", str(e), [], []
            )
    
    async def detect_contradictory_information(
        self, 
        query: str, 
        answer: str, 
        sources: List[Dict[str, Any]]
    ) -> ErrorDetection:
        """تشخیص اطلاعات متناقض"""
        if not self.enable_verification:
            return ErrorDetection(
                ErrorType.CONTRADICTORY_INFORMATION, 0.0, "low", "Verification disabled", [], []
            )
        
        try:
            start_time = time.time()
            
            # آماده‌سازی منابع
            sources_text = []
            for i, source in enumerate(sources[:3]):
                source_text = f"منبع {i+1}: {source.get('text', '')[:200]}..."
                sources_text.append(source_text)
            
            sources_text_combined = "\n\n".join(sources_text)
            
            # ارسال به LLM برای تشخیص
            prompt = self.error_detection_prompts["contradictory_information"].format(
                query=query,
                answer=answer,
                sources=sources_text_combined
            )
            
            if self.qwen_client:
                response = await self.qwen_client.generate_response(
                    prompt=prompt,
                    max_tokens=300,
                    temperature=0.1
                )
                
                # Parse JSON response
                try:
                    import json
                    # Extract text from GenerationResponse
                    response_text = response.text if hasattr(response, 'text') else str(response)
                    result = json.loads(response_text)
                    
                    has_contradictions = result.get("has_contradictions", False)
                    confidence = result.get("confidence", 0.5)
                    
                    severity = "high" if confidence > 0.8 else "medium" if confidence > 0.5 else "low"
                    
                    detection = ErrorDetection(
                        error_type=ErrorType.CONTRADICTORY_INFORMATION,
                        confidence=confidence,
                        severity=severity,
                        description="Contradictory information detected" if has_contradictions else "No contradictions detected",
                        evidence=result.get("evidence", []),
                        suggestions=result.get("suggestions", [])
                    )
                    
                except json.JSONDecodeError:
                    detection = ErrorDetection(
                        ErrorType.CONTRADICTORY_INFORMATION, 0.5, "medium", "JSON parsing failed", [], []
                    )
            else:
                detection = ErrorDetection(
                    ErrorType.CONTRADICTORY_INFORMATION, 0.5, "medium", "No LLM client", [], []
                )
            
            # ردیابی عملکرد
            detection_time = time.time() - start_time
            self._track_detection(detection_time)
            
            logger.debug(f"Contradictory information detection: {detection.confidence:.3f}")
            return detection
            
        except Exception as e:
            logger.error(f"❌ Failed to detect contradictory information: {e}")
            return ErrorDetection(
                ErrorType.CONTRADICTORY_INFORMATION, 0.5, "medium", str(e), [], []
            )
    
    async def correct_answer(
        self, 
        query: str, 
        answer: str, 
        error_detections: List[ErrorDetection],
        sources: List[Dict[str, Any]]
    ) -> CorrectionResult:
        """تصحیح پاسخ بر اساس خطاهای تشخیص داده شده"""
        if not self.enable_correction or not error_detections:
            return CorrectionResult(
                original_answer=answer,
                corrected_answer=answer,
                corrections_applied=[],
                confidence=1.0,
                success=True
            )
        
        try:
            start_time = time.time()
            
            # فیلتر کردن خطاهای با اطمینان بالا
            high_confidence_errors = [
                error for error in error_detections 
                if error.confidence > self.error_threshold
            ]
            
            if not high_confidence_errors:
                return CorrectionResult(
                    original_answer=answer,
                    corrected_answer=answer,
                    corrections_applied=[],
                    confidence=1.0,
                    success=True
                )
            
            # ایجاد prompt تصحیح
            corrections_needed = []
            for error in high_confidence_errors:
                corrections_needed.append(f"- {error.error_type.value}: {error.description}")
            
            correction_prompt = f"""
            شما یک متخصص تصحیح پاسخ در سیستم‌های RAG هستید. لطفاً پاسخ زیر را بر اساس خطاهای تشخیص داده شده تصحیح کنید.

            سوال: {query}
            پاسخ اصلی: {answer}
            منابع: {sources[:2]}

            خطاهای تشخیص داده شده:
            {chr(10).join(corrections_needed)}

            لطفاً پاسخ تصحیح شده را ارائه دهید:
            """
            
            if self.qwen_client:
                response = await self.qwen_client.generate_response(
                    prompt=correction_prompt,
                    max_tokens=1000,
                    temperature=0.1
                )
                
                corrected_answer = response
                corrections_applied = [error.error_type.value for error in high_confidence_errors]
                
                result = CorrectionResult(
                    original_answer=answer,
                    corrected_answer=corrected_answer,
                    corrections_applied=corrections_applied,
                    confidence=0.8,  # اعتماد متوسط به تصحیح
                    success=True
                )
            else:
                result = CorrectionResult(
                    original_answer=answer,
                    corrected_answer=answer,
                    corrections_applied=[],
                    confidence=0.0,
                    success=False
                )
            
            # ردیابی عملکرد
            correction_time = time.time() - start_time
            self._track_correction(correction_time)
            
            logger.debug(f"Answer corrected: {len(result.corrections_applied)} corrections applied")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to correct answer: {e}")
            return CorrectionResult(
                original_answer=answer,
                corrected_answer=answer,
                corrections_applied=[],
                confidence=0.0,
                success=False
            )
    
    def _track_detection(self, detection_time: float):
        """ردیابی عملکرد detection"""
        self.error_detection_count += 1
        self.total_detection_time += detection_time
    
    def _track_correction(self, correction_time: float):
        """ردیابی عملکرد correction"""
        self.correction_count += 1
        self.total_correction_time += correction_time
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """آمار عملکرد"""
        avg_detection_time = self.total_detection_time / max(self.error_detection_count, 1)
        avg_correction_time = self.total_correction_time / max(self.correction_count, 1)
        
        return {
            'error_detection_count': self.error_detection_count,
            'correction_count': self.correction_count,
            'total_detection_time': self.total_detection_time,
            'total_correction_time': self.total_correction_time,
            'average_detection_time': avg_detection_time,
            'average_correction_time': avg_correction_time,
            'error_threshold': self.error_threshold,
            'enable_verification': self.enable_verification,
            'enable_correction': self.enable_correction
        }
    
    def reset_stats(self):
        """بازنشانی آمار"""
        self.error_detection_count = 0
        self.correction_count = 0
        self.total_detection_time = 0.0
        self.total_correction_time = 0.0
    
    async def detect_errors(
        self,
        query: str,
        answer: str,
        sources: List[Any]
    ) -> List[ErrorDetection]:
        """
        تشخیص تمام انواع خطا در یک پاسخ
        
        Args:
            query: سوال کاربر
            answer: پاسخ تولید شده
            sources: منابع استفاده شده
            
        Returns:
            لیست خطاهای شناسایی شده
        """
        if not self.enable_verification:
            return []
        
        errors = []
        
        try:
            # 1. تشخیص hallucination
            hallucination = await self.detect_hallucination(query, answer, sources)
            if hallucination:
                errors.append(hallucination)
        except Exception as e:
            logger.warning(f"Hallucination detection failed: {e}")
        
        try:
            # 2. تشخیص irrelevant retrieval
            irrelevant = await self.detect_irrelevant_retrieval(query, sources)
            if irrelevant:
                errors.append(irrelevant)
        except Exception as e:
            logger.warning(f"Irrelevant retrieval detection failed: {e}")
        
        try:
            # 3. تشخیص incomplete answer
            incomplete = await self.detect_incomplete_answer(query, answer)
            if incomplete:
                errors.append(incomplete)
        except Exception as e:
            logger.warning(f"Incomplete answer detection failed: {e}")
        
        try:
            # 4. تشخیص contradictory information
            contradictory = await self.detect_contradictory_information(query, answer, sources)
            if contradictory:
                errors.append(contradictory)
        except Exception as e:
            logger.warning(f"Contradictory information detection failed: {e}")
        
        return errors

