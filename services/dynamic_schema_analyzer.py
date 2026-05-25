# -*- coding: utf-8 -*-
"""
Dynamic Schema Analyzer
Intelligently analyzes Excel/data schemas to determine column roles and data types
Replaces hardcoded column mappings with dynamic detection
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import json

from services.qwen_client import QwenClient

logger = logging.getLogger(__name__)


class ColumnRole(str, Enum):
    """Roles that columns can play in the data"""
    QUESTION = "question"           # Contains questions (Q&A dataset)
    ANSWER = "answer"               # Contains answers (Q&A dataset)
    CODE = "code"                   # Contains codes/IDs
    TITLE = "title"                 # Contains titles/names
    NUMERIC = "numeric"             # Contains numeric values (amounts, counts)
    DATE = "date"                   # Contains dates
    CATEGORY = "category"           # Contains categorical values
    DESCRIPTION = "description"     # Contains long text descriptions
    ENTITY = "entity"               # Contains entity names (organizations, devices)
    YEAR = "year"                   # Contains year values
    UNKNOWN = "unknown"             # Unknown role


class DatasetType(str, Enum):
    """Types of datasets"""
    QA = "qa"                       # Question/Answer dataset
    FINANCIAL = "financial"         # Financial/budget data
    CATALOG = "catalog"             # Item catalog
    LEGAL = "legal"                 # Legal documents with articles
    GENERAL = "general"             # General tabular data


@dataclass
class ColumnInfo:
    """Information about a single column"""
    original_name: str
    normalized_name: str
    role: ColumnRole
    confidence: float
    data_type: str  # Python type name
    sample_values: List[str] = field(default_factory=list)
    null_ratio: float = 0.0
    unique_ratio: float = 0.0


@dataclass
class SchemaInfo:
    """Complete schema information for a dataset"""
    dataset_type: DatasetType
    columns: List[ColumnInfo]
    detected_language: str = "fa"  # Default to Persian
    row_count: int = 0
    confidence: float = 0.0
    
    def get_columns_by_role(self, role: ColumnRole) -> List[ColumnInfo]:
        """Get all columns with a specific role"""
        return [col for col in self.columns if col.role == role]
    
    def get_primary_column(self, role: ColumnRole) -> Optional[ColumnInfo]:
        """Get the primary (highest confidence) column for a role"""
        cols = self.get_columns_by_role(role)
        if not cols:
            return None
        return max(cols, key=lambda c: c.confidence)
    
    def to_column_mapping(self) -> Dict[str, str]:
        """Generate a column mapping dict (Persian -> English)"""
        mapping = {}
        role_to_english = {
            ColumnRole.QUESTION: "question",
            ColumnRole.ANSWER: "answer",
            ColumnRole.CODE: "code",
            ColumnRole.TITLE: "title",
            ColumnRole.NUMERIC: "value",
            ColumnRole.DATE: "date",
            ColumnRole.ENTITY: "entity",
            ColumnRole.YEAR: "year"
        }
        for col in self.columns:
            if col.role != ColumnRole.UNKNOWN:
                english_name = role_to_english.get(col.role, col.role.value)
                mapping[col.original_name] = english_name
        return mapping


class DynamicSchemaAnalyzer:
    """
    Analyzes data schemas dynamically to determine column roles.
    Replaces hardcoded column mappings with intelligent detection.
    """
    
    # Pattern-based column name detection
    COLUMN_PATTERNS = {
        ColumnRole.QUESTION: [
            r'سوال', r'پرسش', r'question', r'q\d*$', r'پرس'
        ],
        ColumnRole.ANSWER: [
            r'پاسخ', r'جواب', r'answer', r'a\d*$', r'توضیح'
        ],
        ColumnRole.CODE: [
            r'کد', r'شماره', r'code', r'id', r'شناسه', r'ردیف'
        ],
        ColumnRole.TITLE: [
            r'عنوان', r'نام', r'title', r'name', r'موضوع'
        ],
        ColumnRole.ENTITY: [
            r'دستگاه', r'سازمان', r'واحد', r'شرکت', r'نهاد', r'organization', r'entity'
        ],
        ColumnRole.YEAR: [
            r'سال', r'year', r'دوره'
        ],
        ColumnRole.NUMERIC: [
            r'مبلغ', r'مقدار', r'تعداد', r'amount', r'value', r'count', r'اعتبار', r'هزینه', r'درآمد', r'بودجه'
        ],
        ColumnRole.DATE: [
            r'تاریخ', r'date', r'زمان', r'time'
        ],
        ColumnRole.CATEGORY: [
            r'نوع', r'گروه', r'دسته', r'type', r'category', r'class'
        ]
    }
    
    # Financial column indicators
    FINANCIAL_INDICATORS = [
        'اعتبار', 'بودجه', 'هزینه', 'درآمد', 'مصارف', 'منابع',
        'تملک', 'سرمایه', 'جاری', 'عمرانی', 'ملی', 'استانی'
    ]
    
    def __init__(self, qwen_client: Optional[QwenClient] = None):
        self.qwen_client = qwen_client
    
    async def analyze_dataframe(
        self,
        df: pd.DataFrame,
        filename: Optional[str] = None,
        use_llm: bool = False
    ) -> SchemaInfo:
        """
        Analyze a DataFrame to determine its schema.
        
        Args:
            df: The DataFrame to analyze
            filename: Optional filename for context
            use_llm: Whether to use LLM for complex cases
            
        Returns:
            SchemaInfo with column roles and dataset type
        """
        if df.empty:
            return SchemaInfo(
                dataset_type=DatasetType.GENERAL,
                columns=[],
                confidence=0.0
            )
        
        columns_info = []
        
        for col in df.columns:
            col_info = self._analyze_column(df, col)
            columns_info.append(col_info)
        
        # Determine dataset type based on column roles
        dataset_type = self._detect_dataset_type(columns_info, filename)
        
        # Refine column roles based on dataset type
        columns_info = self._refine_roles_by_context(columns_info, dataset_type)
        
        # Use LLM for low-confidence cases if available
        if use_llm and self.qwen_client:
            low_confidence_cols = [c for c in columns_info if c.confidence < 0.6]
            if low_confidence_cols:
                columns_info = await self._llm_refine_roles(
                    df, columns_info, dataset_type
                )
        
        # Calculate overall confidence
        overall_confidence = sum(c.confidence for c in columns_info) / len(columns_info) if columns_info else 0.0
        
        return SchemaInfo(
            dataset_type=dataset_type,
            columns=columns_info,
            detected_language="fa",  # Default to Persian
            row_count=len(df),
            confidence=overall_confidence
        )
    
    def _analyze_column(self, df: pd.DataFrame, col_name: str) -> ColumnInfo:
        """Analyze a single column"""
        col_str = str(col_name)
        normalized = self._normalize_column_name(col_str)
        
        # Get sample values
        sample_values = []
        non_null = df[col_name].dropna()
        if len(non_null) > 0:
            sample_values = [str(v) for v in non_null.head(5).tolist()]
        
        # Calculate statistics
        null_ratio = df[col_name].isna().mean()
        unique_ratio = df[col_name].nunique() / len(df) if len(df) > 0 else 0
        
        # Detect data type
        data_type = self._detect_data_type(df[col_name])
        
        # Detect role based on column name patterns
        role, confidence = self._detect_role_by_name(normalized)
        
        # Refine role based on data content if name-based detection has low confidence
        if confidence < 0.7:
            content_role, content_conf = self._detect_role_by_content(
                df[col_name], sample_values, data_type
            )
            if content_conf > confidence:
                role = content_role
                confidence = content_conf
        
        return ColumnInfo(
            original_name=col_str,
            normalized_name=normalized,
            role=role,
            confidence=confidence,
            data_type=data_type,
            sample_values=sample_values,
            null_ratio=null_ratio,
            unique_ratio=unique_ratio
        )
    
    def _normalize_column_name(self, name: str) -> str:
        """Normalize column name for pattern matching"""
        if not name:
            return ""
        
        # Persian character normalization
        name = name.replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه')
        name = name.replace('‌', ' ')  # ZWNJ to space
        
        # Lowercase and strip
        name = name.lower().strip()
        
        return name
    
    def _detect_data_type(self, series: pd.Series) -> str:
        """Detect the data type of a column"""
        # Try numeric
        if pd.api.types.is_numeric_dtype(series):
            return "numeric"
        
        # Check string content
        sample = series.dropna().head(100)
        if len(sample) == 0:
            return "unknown"
        
        # Check if mostly numeric strings
        numeric_count = 0
        for val in sample:
            try:
                float(str(val).replace(',', '').replace('٬', ''))
                numeric_count += 1
            except:
                pass
        
        if numeric_count > len(sample) * 0.8:
            return "numeric_string"
        
        # Check string length for description vs short text
        avg_len = sample.astype(str).str.len().mean()
        if avg_len > 100:
            return "long_text"
        elif avg_len > 30:
            return "medium_text"
        else:
            return "short_text"
    
    def _detect_role_by_name(self, name: str) -> Tuple[ColumnRole, float]:
        """Detect column role based on column name patterns"""
        best_role = ColumnRole.UNKNOWN
        best_confidence = 0.0
        
        for role, patterns in self.COLUMN_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, name, re.IGNORECASE):
                    # Exact match gets higher confidence
                    if re.fullmatch(pattern, name, re.IGNORECASE):
                        confidence = 0.95
                    else:
                        confidence = 0.8
                    
                    if confidence > best_confidence:
                        best_role = role
                        best_confidence = confidence
        
        return best_role, best_confidence
    
    def _detect_role_by_content(
        self,
        series: pd.Series,
        sample_values: List[str],
        data_type: str
    ) -> Tuple[ColumnRole, float]:
        """Detect column role based on content analysis"""
        
        if data_type in ["numeric", "numeric_string"]:
            # Check for financial indicators in other columns' context
            return ColumnRole.NUMERIC, 0.7
        
        if data_type == "long_text":
            # Long text is likely description or answer
            return ColumnRole.ANSWER, 0.6
        
        # Check for question patterns in content
        question_indicators = ['؟', '?', 'چیست', 'چگونه', 'چرا', 'کجا', 'کدام']
        if any(ind in str(sample_values) for ind in question_indicators):
            return ColumnRole.QUESTION, 0.7
        
        # Check for year patterns
        year_pattern = re.compile(r'^1[34]\d{2}$|^[89][0-9]$|^0[0-4]$')
        if sample_values:
            year_matches = sum(1 for v in sample_values if year_pattern.match(str(v).strip()))
            if year_matches >= len(sample_values) * 0.5:
                return ColumnRole.YEAR, 0.8
        
        # Check for code patterns (short, alphanumeric)
        if data_type == "short_text" and sample_values:
            code_pattern = re.compile(r'^\d{2,10}$|^[A-Za-z0-9-_]+$')
            code_matches = sum(1 for v in sample_values if code_pattern.match(str(v).strip()))
            if code_matches >= len(sample_values) * 0.7:
                return ColumnRole.CODE, 0.7
        
        return ColumnRole.UNKNOWN, 0.3
    
    def _detect_dataset_type(
        self,
        columns: List[ColumnInfo],
        filename: Optional[str]
    ) -> DatasetType:
        """Detect the type of dataset based on columns"""
        
        # Check filename hints
        if filename:
            filename_lower = filename.lower()
            if any(kw in filename_lower for kw in ['qa', 'question', 'faq', 'پرسش', 'سوال']):
                return DatasetType.QA
            if any(kw in filename_lower for kw in ['budget', 'finance', 'بودجه', 'مالی', 'هزینه', 'درآمد', 'cost', 'income']):
                return DatasetType.FINANCIAL
            if any(kw in filename_lower for kw in ['law', 'legal', 'قانون', 'ماده', 'آیین']):
                return DatasetType.LEGAL
        
        # Check column roles
        roles = [c.role for c in columns]
        
        # Q&A dataset has question and answer columns
        if ColumnRole.QUESTION in roles and ColumnRole.ANSWER in roles:
            return DatasetType.QA
        
        # Financial dataset has numeric columns with financial indicators
        numeric_cols = [c for c in columns if c.role == ColumnRole.NUMERIC]
        if numeric_cols:
            financial_col_names = [c.original_name for c in columns]
            if any(ind in ' '.join(financial_col_names) for ind in self.FINANCIAL_INDICATORS):
                return DatasetType.FINANCIAL
        
        # Catalog has title and description
        if ColumnRole.TITLE in roles and ColumnRole.DESCRIPTION in roles:
            return DatasetType.CATALOG
        
        return DatasetType.GENERAL
    
    def _refine_roles_by_context(
        self,
        columns: List[ColumnInfo],
        dataset_type: DatasetType
    ) -> List[ColumnInfo]:
        """Refine column roles based on dataset context"""
        
        if dataset_type == DatasetType.FINANCIAL:
            # In financial datasets, unknown numeric columns are likely values
            for col in columns:
                if col.data_type in ["numeric", "numeric_string"] and col.role == ColumnRole.UNKNOWN:
                    col.role = ColumnRole.NUMERIC
                    col.confidence = max(col.confidence, 0.6)
        
        elif dataset_type == DatasetType.QA:
            # In Q&A datasets, prioritize question/answer detection
            has_question = any(c.role == ColumnRole.QUESTION for c in columns)
            has_answer = any(c.role == ColumnRole.ANSWER for c in columns)
            
            if not has_question:
                # Find best candidate for question
                for col in columns:
                    if col.data_type in ["medium_text", "short_text"] and col.role == ColumnRole.UNKNOWN:
                        col.role = ColumnRole.QUESTION
                        col.confidence = 0.5
                        break
            
            if not has_answer:
                # Find best candidate for answer
                for col in columns:
                    if col.data_type == "long_text" and col.role == ColumnRole.UNKNOWN:
                        col.role = ColumnRole.ANSWER
                        col.confidence = 0.5
                        break
        
        return columns
    
    async def _llm_refine_roles(
        self,
        df: pd.DataFrame,
        columns: List[ColumnInfo],
        dataset_type: DatasetType
    ) -> List[ColumnInfo]:
        """Use LLM to refine column roles for low-confidence cases"""
        
        if not self.qwen_client:
            return columns
        
        # Build prompt with column info
        columns_desc = []
        for col in columns:
            if col.confidence < 0.6:
                columns_desc.append(f"- {col.original_name}: samples={col.sample_values[:3]}")
        
        if not columns_desc:
            return columns
        
        prompt = f"""این ستون‌های داده را تحلیل کن و نقش هر کدام را مشخص کن:

نوع دیتاست: {dataset_type.value}

ستون‌ها:
{chr(10).join(columns_desc)}

نقش‌های ممکن: question, answer, code, title, numeric, date, category, entity, year, description

به صورت JSON پاسخ بده:
{{"column_name": "role", ...}}
"""
        
        try:
            response = await self.qwen_client.generate_text(
                prompt=prompt,
                max_tokens=300,
                temperature=0.3
            )
            
            if response.success:
                # Extract JSON
                json_match = re.search(r'\{[^}]+\}', response.text, re.DOTALL)
                if json_match:
                    role_map = json.loads(json_match.group())
                    
                    # Update columns with LLM suggestions
                    for col in columns:
                        if col.original_name in role_map:
                            try:
                                new_role = ColumnRole(role_map[col.original_name])
                                col.role = new_role
                                col.confidence = max(col.confidence, 0.7)
                            except ValueError:
                                pass
        except Exception as e:
            logger.warning(f"LLM role refinement failed: {e}")
        
        return columns
    
    def generate_metadata_template(self, schema: SchemaInfo) -> Dict[str, Any]:
        """Generate a metadata template for storing data based on schema"""
        
        template = {
            "dataset_type": schema.dataset_type.value,
            "column_mapping": schema.to_column_mapping(),
            "primary_fields": {},
            "numeric_fields": [],
            "text_fields": []
        }
        
        # Identify primary fields
        for role in [ColumnRole.QUESTION, ColumnRole.ANSWER, ColumnRole.TITLE, ColumnRole.CODE]:
            col = schema.get_primary_column(role)
            if col:
                template["primary_fields"][role.value] = col.original_name
        
        # Categorize fields
        for col in schema.columns:
            if col.role == ColumnRole.NUMERIC:
                template["numeric_fields"].append(col.original_name)
            elif col.data_type in ["long_text", "medium_text"]:
                template["text_fields"].append(col.original_name)
        
        return template

