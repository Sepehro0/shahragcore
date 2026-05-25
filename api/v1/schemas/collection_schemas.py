# -*- coding: utf-8 -*-
"""
API Schemas for Collection Management
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator


class CollectionType(str, Enum):
    """نوع کالکشن"""
    QA = "qa"  # سوال و جواب
    SALES_SUPPORT = "sales_support"  # پشتیبانی فروش
    CUSTOMER_SUPPORT = "customer_support"  # پشتیبانی مشتری
    KNOWLEDGE_BASE = "knowledge_base"  # پایگاه دانش
    LEGAL = "legal"  # حقوقی
    FINANCIAL = "financial"  # مالی
    MEDICAL = "medical"  # پزشکی
    EDUCATION = "education"  # آموزشی
    GENERAL = "general"  # عمومی


class FileType(str, Enum):
    """نوع فایل"""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    TEXT = "text"
    WORD = "word"
    JSON = "json"


class ProcessingMode(str, Enum):
    """حالت پردازش"""
    DATABASE_FIRST = "database_first"  # اول از دیتابیس
    RAG_ONLY = "rag_only"  # فقط RAG
    HYBRID = "hybrid"  # ترکیبی


# ==================== CREATE COLLECTION ====================

class CreateCollectionRequest(BaseModel):
    """درخواست ساخت کالکشن جدید"""
    collection_name: str = Field(
        ...,
        description="نام کالکشن (باید یکتا باشد)",
        min_length=3,
        max_length=50,
        pattern="^[a-z0-9_]+$"
    )
    display_name: str = Field(
        ...,
        description="نام نمایشی کالکشن (فارسی/انگلیسی)",
        min_length=3,
        max_length=100
    )
    collection_type: CollectionType = Field(
        ...,
        description="نوع کالکشن"
    )
    processing_mode: ProcessingMode = Field(
        default=ProcessingMode.RAG_ONLY,
        description="حالت پردازش"
    )
    description: Optional[str] = Field(
        None,
        description="توضیحات کالکشن",
        max_length=500
    )
    system_prompt: Optional[str] = Field(
        None,
        description="پرامپت سیستم اولیه (اختیاری)",
        max_length=2000
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="متادیتای اضافی"
    )


class CreateCollectionResponse(BaseModel):
    """پاسخ ساخت کالکشن"""
    success: bool
    collection_id: str
    collection_name: str
    message: str
    created_at: str


# ==================== UPLOAD FILE ====================

class UploadFileRequest(BaseModel):
    """درخواست آپلود فایل"""
    collection_name: str = Field(
        ...,
        description="نام کالکشن"
    )
    file_type: FileType = Field(
        ...,
        description="نوع فایل"
    )
    chunk_size: Optional[int] = Field(
        default=500,
        description="اندازه chunk (برای متن)",
        ge=100,
        le=2000
    )
    chunk_overlap: Optional[int] = Field(
        default=50,
        description="همپوشانی chunk",
        ge=0,
        le=500
    )
    extract_tables: Optional[bool] = Field(
        default=True,
        description="استخراج جداول (برای PDF/Excel)"
    )
    extract_metadata: Optional[bool] = Field(
        default=True,
        description="استخراج متادیتا"
    )


class UploadFileResponse(BaseModel):
    """پاسخ آپلود فایل"""
    success: bool
    file_id: str
    filename: str
    collection_name: str
    file_size: int
    chunks_created: int
    processing_time: float
    message: str


# ==================== PROCESS FILE ====================

class ProcessFileRequest(BaseModel):
    """درخواست پردازش فایل"""
    file_id: str = Field(
        ...,
        description="شناسه فایل آپلود شده"
    )
    collection_name: str = Field(
        ...,
        description="نام کالکشن"
    )
    processing_options: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="تنظیمات پردازش"
    )


class ProcessFileResponse(BaseModel):
    """پاسخ پردازش فایل"""
    success: bool
    file_id: str
    collection_name: str
    documents_created: int
    embeddings_created: int
    processing_time: float
    status: str
    message: str


# ==================== UPDATE SYSTEM PROMPT ====================

class UpdateSystemPromptRequest(BaseModel):
    """درخواست بروزرسانی پرامپت سیستم"""
    collection_name: Optional[str] = Field(
        default=None,
        description="نام کالکشن (اختیاری؛ برای سازگاری با کلاینت‌های قدیمی - ترجیحاً از path parameter استفاده کنید)"
    )
    system_prompt: str = Field(
        ...,
        description="پرامپت سیستم جدید",
        min_length=10,
        max_length=2000
    )
    examples: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="مثال‌های سوال و جواب"
    )


class UpdateSystemPromptResponse(BaseModel):
    """پاسخ بروزرسانی پرامپت"""
    success: bool
    collection_name: str
    message: str
    updated_at: str


# ==================== UPDATE COLLECTION CONFIG ====================

class UpdateCollectionConfigRequest(BaseModel):
    """درخواست بروزرسانی تنظیمات کالکشن"""
    collection_name: Optional[str] = Field(
        default=None,
        description="نام کالکشن (اختیاری؛ برای سازگاری با کلاینت‌های قدیمی - ترجیحاً از path parameter استفاده کنید)"
    )
    display_name: Optional[str] = Field(
        None,
        description="نام نمایشی جدید"
    )
    description: Optional[str] = Field(
        None,
        description="توضیحات جدید"
    )
    system_prompt: Optional[str] = Field(
        None,
        description="پرامپت سیستم جدید"
    )
    out_of_scope_response: Optional[str] = Field(
        None,
        description="پیام پاسخ به سوالات خارج از حوزه",
    )
    retrieval_config: Optional[Dict[str, Any]] = Field(
        None,
        description="تنظیمات بازیابی (top_k, weights, ...)"
    )
    generation_config: Optional[Dict[str, Any]] = Field(
        None,
        description="تنظیمات تولید (temperature, max_tokens, ...)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="متادیتای اضافی"
    )
    aggregation_config: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "تنظیمات تجمیع چندبُعدی (برای کالکشن‌هایی با اقلام قابل‌تجمیع در "
            "بُعد زمانی/دسته‌ای مثل بودجه). ساختار: "
            "{enabled, grouping_field, temporal_field, value_fields, unit_label, "
            "temporal_kind (jalali_year|int), temporal_min, temporal_max, "
            "disable_classification_fastpath}. "
            "در صورت فعال بودن، سیستم به‌صورت خودکار برای کوئری‌های چندمقداری "
            "(مثل چندسالانه) داده‌های گمشده را از ChromaDB تکمیل می‌کند و جمع "
            "اعداد را با محاسبه قطعی از metadata اصلاح می‌کند."
        )
    )


class UpdateCollectionConfigResponse(BaseModel):
    """پاسخ بروزرسانی تنظیمات"""
    success: bool
    collection_name: str
    updated_fields: List[str]
    message: str


# ==================== QUERY COLLECTION ====================

class QueryCollectionRequest(BaseModel):
    """درخواست Query در کالکشن"""
    collection_name: Optional[str] = Field(
        default=None,
        description="نام کالکشن (اختیاری؛ برای سازگاری با کلاینت‌های قدیمی - ترجیحاً از path parameter استفاده کنید)"
    )
    query: str = Field(
        ...,
        description="سوال کاربر",
        min_length=3,
        max_length=500
    )
    top_k: Optional[int] = Field(
        default=5,
        description="تعداد نتایج",
        ge=1,
        le=20
    )
    use_reranking: Optional[bool] = Field(
        default=True,
        description="استفاده از reranking"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="فیلترهای متادیتا"
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="شناسه مکالمه"
    )


class QueryCollectionResponse(BaseModel):
    """پاسخ Query"""
    success: bool
    answer: str
    full_answer: Optional[str]
    sources: List[Dict[str, Any]]
    confidence: float
    processing_time: float
    metadata: Dict[str, Any]


# ==================== LIST COLLECTIONS ====================

class ListCollectionsResponse(BaseModel):
    """پاسخ لیست کالکشن‌ها"""
    success: bool
    collections: List[Dict[str, Any]]
    total_count: int


# ==================== GET COLLECTION INFO ====================

class GetCollectionInfoResponse(BaseModel):
    """پاسخ اطلاعات کالکشن"""
    success: bool
    collection_name: str
    display_name: str
    collection_type: str
    processing_mode: str
    description: Optional[str]
    system_prompt: Optional[str]
    documents_count: int
    created_at: str
    updated_at: str
    config: Dict[str, Any]
    metadata: Dict[str, Any]


# ==================== DELETE COLLECTION ====================

class DeleteCollectionRequest(BaseModel):
    """درخواست حذف کالکشن"""
    collection_name: str = Field(
        ...,
        description="نام کالکشن"
    )
    confirm: bool = Field(
        ...,
        description="تایید حذف"
    )


class DeleteCollectionResponse(BaseModel):
    """پاسخ حذف کالکشن"""
    success: bool
    collection_name: str
    message: str


# ==================== ADD DOCUMENTS ====================

class AddDocumentsRequest(BaseModel):
    """درخواست افزودن اسناد دستی"""
    collection_name: Optional[str] = Field(
        default=None,
        description="نام کالکشن (اختیاری؛ برای سازگاری با کلاینت‌های قدیمی - ترجیحاً از path parameter استفاده کنید)"
    )
    documents: List[str] = Field(
        ...,
        description="لیست متن اسناد",
        min_items=1
    )
    metadata_list: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="لیست متادیتا برای هر سند"
    )


class AddDocumentsResponse(BaseModel):
    """پاسخ افزودن اسناد"""
    success: bool
    collection_name: str
    documents_added: int
    message: str


# ==================== SEARCH DOCUMENTS ====================

class SearchDocumentsRequest(BaseModel):
    """درخواست جستجو در اسناد"""
    collection_name: Optional[str] = Field(
        default=None,
        description="نام کالکشن (اختیاری؛ برای سازگاری با کلاینت‌های قدیمی - ترجیحاً از path parameter استفاده کنید)"
    )
    query: str = Field(
        ...,
        description="جستجو",
        min_length=2
    )
    top_k: Optional[int] = Field(
        default=10,
        description="تعداد نتایج",
        ge=1,
        le=50
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="فیلترها"
    )


class SearchDocumentsResponse(BaseModel):
    """پاسخ جستجو"""
    success: bool
    results: List[Dict[str, Any]]
    total_found: int
    processing_time: float


# ==================== EXPORT COLLECTION ====================

class ExportCollectionRequest(BaseModel):
    """درخواست Export کالکشن"""
    collection_name: str = Field(
        ...,
        description="نام کالکشن"
    )
    export_format: str = Field(
        default="json",
        description="فرمت خروجی (json, csv, excel)"
    )
    include_embeddings: Optional[bool] = Field(
        default=False,
        description="شامل embeddings"
    )


class ExportCollectionResponse(BaseModel):
    """پاسخ Export"""
    success: bool
    collection_name: str
    export_url: str
    file_size: int
    message: str
