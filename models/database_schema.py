# -*- coding: utf-8 -*-
"""
Database Schema Models
مدل‌های پایگاه داده برای ذخیره داده‌های ساختاریافته
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, 
    Boolean, DateTime, ForeignKey, Index, MetaData, Table, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import os

# Check database type from environment or default to JSON for compatibility
# Use JSONB for PostgreSQL, JSON for SQLite
_db_type = os.getenv("DATABASE_TYPE", "").lower()
if _db_type == "postgresql" or _db_type == "postgres":
    try:
        from sqlalchemy.dialects.postgresql import JSONB
        JSON_TYPE = JSONB
        _is_postgresql = True
    except ImportError:
        JSON_TYPE = JSON  # Fallback
        _is_postgresql = False
else:
    JSON_TYPE = JSON  # Use JSON for SQLite compatibility
    _is_postgresql = False
from datetime import datetime
from typing import Optional, Dict, Any, List
try:
    import uuid
except:
    pass

Base = declarative_base()
metadata = MetaData()


class Collection(Base):
    """مدل Collection برای مدیریت مجموعه‌های داده"""
    __tablename__ = "collections"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tables = relationship("DataTable", back_populates="collection", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Collection(name='{self.name}')>"


class DataTable(Base):
    """مدل Table برای نگهداری جداول Excel"""
    __tablename__ = "data_tables"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=False, index=True)
    table_name = Column(String(255), nullable=False)
    sheet_name = Column(String(255), nullable=True)
    source_file = Column(String(500), nullable=True)
    
    # Schema information stored as JSON
    schema_info = Column(JSON_TYPE, nullable=True)
    
    # Metadata
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    collection = relationship("Collection", back_populates="tables")
    rows = relationship("TableRow", back_populates="table", cascade="all, delete-orphan")
    columns = relationship("TableColumn", back_populates="table", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_table_collection', 'collection_id', 'table_name'),
        Index('idx_table_source_file', 'source_file'),  # برای جستجوی سریع‌تر بر اساس فایل
    )
    
    def __repr__(self):
        return f"<DataTable(table_name='{self.table_name}', collection_id={self.collection_id})>"


class TableColumn(Base):
    """مدل Column برای نگهداری اطلاعات ستون‌ها"""
    __tablename__ = "table_columns"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_id = Column(Integer, ForeignKey("data_tables.id"), nullable=False, index=True)
    column_name = Column(String(255), nullable=False)
    column_index = Column(Integer, nullable=False)
    data_type = Column(String(50), nullable=True)  # string, integer, float, date, etc.
    
    # Relationships
    table = relationship("DataTable", back_populates="columns")
    
    # Indexes
    __table_args__ = (
        Index('idx_column_table', 'table_id', 'column_index'),
    )
    
    def __repr__(self):
        return f"<TableColumn(column_name='{self.column_name}', table_id={self.table_id})>"


class TableRow(Base):
    """مدل Row برای نگهداری سطرهای داده"""
    __tablename__ = "table_rows"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_id = Column(Integer, ForeignKey("data_tables.id"), nullable=False, index=True)
    row_index = Column(Integer, nullable=False)
    
    # Store row data as JSON for flexibility
    data = Column(JSON_TYPE, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    table = relationship("DataTable", back_populates="rows")
    
    # Indexes
    __table_args__ = (
        Index('idx_row_table_index', 'table_id', 'row_index'),
        Index('idx_row_created_at', 'created_at'),  # برای sorting و filtering بر اساس تاریخ
        # Note: GIN index for JSONB 'data' field will be created via migration script
    )
    
    def __repr__(self):
        return f"<TableRow(table_id={self.table_id}, row_index={self.row_index})>"


class QueryCache(Base):
    """کش برای پرس‌وجوهای SQL"""
    __tablename__ = "query_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query_text = Column(Text, nullable=False)
    sql_query = Column(Text, nullable=False)
    result_hash = Column(String(64), nullable=True)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=True)
    
    # Execution metadata
    execution_time = Column(Float, nullable=True)
    result_count = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_query_cache_collection', 'collection_id'),
        Index('idx_query_cache_expires', 'expires_at'),  # برای cleanup سریع‌تر
        Index('idx_query_cache_hash', 'result_hash'),  # برای lookup سریع‌تر
    )
    
    def __repr__(self):
        return f"<QueryCache(query_text='{self.query_text[:50]}...')>"


# Helper functions
def get_base():
    """دریافت Base برای migrations"""
    return Base

