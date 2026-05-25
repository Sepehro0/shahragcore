# -*- coding: utf-8 -*-
"""
Pattern Handler Module
مدیریت pattern detection و sequential queries
"""

import re
import logging
from typing import Dict, Any, List, Optional
import chromadb

from search.universal_pattern_detector import UniversalPatternDetector, PatternType
from search.universal_sequential_detector import UniversalSequentialDetector, SequenceType
from utils.text_utils import TextNormalizer

logger = logging.getLogger(__name__)


class PatternHandler:
    """مدیریت pattern detection"""
    
    def __init__(
        self,
        chroma_client: chromadb.Client,
        pattern_detector: UniversalPatternDetector = None,
        sequential_detector: UniversalSequentialDetector = None
    ):
        """
        Args:
            chroma_client: ChromaDB client instance
            pattern_detector: Universal pattern detector
            sequential_detector: Universal sequential detector
        """
        self.chroma_client = chroma_client
        self.pattern_detector = pattern_detector or UniversalPatternDetector()
        self.sequential_detector = sequential_detector or UniversalSequentialDetector()
        self.text_normalizer = TextNormalizer()
    
    def detect_row_number(self, query: str) -> Optional[int]:
        """شناسایی شماره ردیف"""
        query_lower = query.lower()
        
        row_patterns = {
            "اول": 1, "یکم": 1, "1": 1, "۱": 1,
            "دوم": 2, "2": 2, "۲": 2,
            "سوم": 3, "3": 3, "۳": 3,
            "چهارم": 4, "4": 4, "۴": 4,
            "پنجم": 5, "5": 5, "۵": 5,
        }
        
        for pattern, num in row_patterns.items():
            if pattern in query_lower:
                return num
        
        return None
    
    def extract_classification_number(
        self,
        query: str,
        dominant_pattern: Optional[str] = None
    ) -> Optional[str]:
        """استخراج شماره/کد/ID از سوال"""
        patterns = self.pattern_detector.detect_patterns(
            query,
            pattern_types=[PatternType.NUMERIC_ID, PatternType.CLASSIFICATION]
        )
        
        if patterns:
            if dominant_pattern:
                for p in patterns:
                    digits = re.sub(r'\D', '', p.value)
                    if dominant_pattern == f'{len(digits)}_digit':
                        return digits
            
            return re.sub(r'\D', '', patterns[0].value)
        
        return None
    
    def detect_sequential_query(
        self,
        query: str,
        collection_name: str = None,
        conversation_id: Optional[str] = None,
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """تشخیص سوالات متوالی"""
        if chat_history is None and collection_name:
            # Get chat history if not provided
            # Note: This requires chat_manager, but we'll handle it in the main class
            pass
        
        result = self.sequential_detector.detect_sequential_query(query, chat_history)
        
        if result:
            return {
                "type": result["type"],
                "number": result["value"],
                "contextual": result.get("contextual", False),
                "sequence_type": result.get("sequence_type", SequenceType.NUMBER).value
            }
        
        # Return default empty dict instead of None for consistency
        return {
            "type": None,
            "number": None,
            "contextual": False,
            "sequence_type": None
        }
    
    def extract_last_classification_number(
        self,
        collection_name: str,
        conversation_id: Optional[str] = None,
        chat_history: List[Dict[str, str]] = None
    ) -> Optional[str]:
        """استخراج آخرین شماره/کد/ID از chat history"""
        if chat_history is None:
            return None
        
        # جستجو در تاریخچه از آخر به اول
        for chat in reversed(chat_history):
            combined_text = chat.get("assistant", "") + " " + chat.get("user", "")
            
            patterns = self.pattern_detector.detect_patterns(
                combined_text,
                pattern_types=[PatternType.NUMERIC_ID, PatternType.CLASSIFICATION]
            )
            
            if patterns:
                return re.sub(r'\D', '', patterns[0].value)
        
        return None
    
    def detect_dominant_number_pattern(self, collection_name: str) -> Optional[str]:
        """تشخیص الگوی غالب اعداد در collection"""
        try:
            collection = self.chroma_client.get_collection(collection_name)
            all_docs = collection.get(include=["documents"], limit=100)
            
            if not all_docs or not all_docs.get("documents"):
                return None
            
            sample_text = " ".join(all_docs["documents"][:20])
            dominant = self.pattern_detector.detect_dominant_pattern(sample_text)
            
            logger.info(f"📊 Detected dominant pattern: {dominant}")
            return dominant
        
        except Exception as e:
            logger.error(f"Error detecting dominant pattern: {e}")
            return None
    
    async def get_sequential_classification(
        self,
        collection_name: str,
        current_number: str,
        direction: str
    ) -> Optional[Dict[str, Any]]:
        """دریافت شماره طبقه‌بندی قبلی یا بعدی"""
        try:
            collection = self.chroma_client.get_collection(collection_name)
            
            try:
                all_docs = collection.get(
                    include=["documents", "metadatas"],
                    limit=1000
                )
            except Exception as e:
                logger.warning(f"Failed to get all docs: {e}")
                return None
            
            if not all_docs or not all_docs.get("metadatas"):
                return None
            
            # Extract classification numbers
            classification_numbers = {}
            for idx, metadata in enumerate(all_docs.get("metadatas", [])):
                if not metadata:
                    continue
                
                class_num = None
                # Try different metadata fields
                for field in ['hierarchy_code', 'code', 'classification_number']:
                    if metadata.get(field):
                        class_num = str(metadata.get(field)).strip()
                        break
                
                if not class_num:
                    # Try extracting from text
                    doc_text = all_docs.get('documents', [])[idx] if idx < len(all_docs.get('documents', [])) else ""
                    patterns = self.pattern_detector.detect_patterns(
                        doc_text,
                        pattern_types=[PatternType.NUMERIC_ID, PatternType.CLASSIFICATION]
                    )
                    if patterns:
                        class_num = re.sub(r'\D', '', patterns[0].value)
                
                if class_num and class_num.isdigit():
                    if class_num not in classification_numbers:
                        classification_numbers[class_num] = {
                            'id': all_docs.get('ids', [])[idx] if idx < len(all_docs.get('ids', [])) else None,
                            'text': all_docs.get('documents', [])[idx] if idx < len(all_docs.get('documents', [])) else "",
                            'metadata': metadata
                        }
            
            if not classification_numbers:
                return None
            
            # Sort numbers
            sorted_numbers = sorted(classification_numbers.keys(), key=lambda x: int(x))
            
            try:
                current_idx = sorted_numbers.index(current_number)
            except ValueError:
                return None
            
            # Get previous or next
            if direction == "previous" and current_idx > 0:
                target_number = sorted_numbers[current_idx - 1]
            elif direction == "next" and current_idx < len(sorted_numbers) - 1:
                target_number = sorted_numbers[current_idx + 1]
            else:
                return None
            
            result = classification_numbers[target_number]
            return {
                'classification_number': target_number,
                'id': result['id'],
                'text': result['text'],
                'metadata': result['metadata']
            }
            
        except Exception as e:
            logger.error(f"Error in get_sequential_classification: {e}")
            return None

