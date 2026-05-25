# -*- coding: utf-8 -*-
"""
Schema Analyzer
تحلیل‌گر schema برای Text-to-SQL
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class SchemaAnalyzer:
    """تحلیل‌گر schema پایگاه داده"""
    
    def __init__(self, database_service: DatabaseService):
        self.database_service = database_service
    
    def get_collection_schema_description(self, collection_name: str) -> str:
        """دریافت توضیحات schema یک collection به زبان فارسی"""
        schema_info = self.database_service.get_schema_description(collection_name)
        
        if not schema_info:
            return ""
        
        # بهبود فرمت
        description = f"# Schema برای Collection: {collection_name}\n\n"
        description += schema_info
        description += "\n\n# دستورالعمل‌های SQL:\n"
        description += "- برای جستجو در جداول از SELECT استفاده کنید\n"
        description += "- از WHERE برای فیلتر کردن داده‌ها استفاده کنید\n"
        description += "- از JOIN برای اتصال جداول استفاده کنید\n"
        description += "- از LIKE برای جستجوی متنی استفاده کنید (حساس به حروف کوچک/بزرگ نیست)\n"
        description += "- برای فارسی از ILIKE استفاده کنید\n"
        if self.database_service._is_booklet_collection(collection_name):
            description += "- ستون 'maddeh_id' فقط برای نمایش است؛ در پرس‌وجوی booklet_bo از آن استفاده نکنید\n"
        
        return description
    
    def get_table_schema(self, collection_name: str, table_name: str) -> Optional[Dict[str, Any]]:
        """دریافت schema یک table"""
        table = self.database_service.get_table(collection_name, table_name)
        if not table:
            return None
        
        with self.database_service.get_session() as session:
            from models.database_schema import TableColumn, TableRow
            
            columns = (
                session.query(TableColumn)
                .filter(TableColumn.table_id == table.id)
                .order_by(TableColumn.column_index)
                .all()
            )
            
            # نمونه داده‌ها برای درک بهتر
            sample_rows = (
                session.query(TableRow)
                .filter(TableRow.table_id == table.id)
                .limit(3)
                .all()
            )
            
            schema = {
                "table_name": table.table_name,
                "sheet_name": table.sheet_name,
                "columns": [
                    {
                        "name": col.column_name,
                        "type": col.data_type,
                        "index": col.column_index
                    }
                    for col in columns
                ],
                "row_count": table.row_count,
                "sample_data": [
                    row.data for row in sample_rows
                ]
            }
            
            return schema
    
    def validate_sql_query(self, sql_query: str, collection_name: str) -> Dict[str, Any]:
        """اعتبارسنجی SQL query"""
        errors = []
        warnings = []
        
        sql_lower = sql_query.lower().strip()
        
        # بررسی دستورات خطرناک
        dangerous_operations = ['drop', 'delete', 'truncate', 'alter', 'create', 'insert', 'update']
        for op in dangerous_operations:
            if f' {op} ' in f' {sql_lower} ':
                errors.append(f"عملیات خطرناک تشخیص داده شد: {op}")
        
        # بررسی اینکه فقط SELECT یا WITH (CTE) باشد
        if not (sql_lower.startswith('select') or sql_lower.startswith('with')):
            errors.append("فقط دستورات SELECT یا WITH (CTE) مجاز هستند")
        
        # بررسی وجود نام جداول collection
        tables = self.database_service.list_tables(collection_name)
        table_names = [t.table_name.lower() for t in tables]
        
        found_table = False
        for table_name in table_names:
            if table_name in sql_lower:
                found_table = True
                break
        
        if not found_table and tables:
            warnings.append("هیچ یک از جداول collection در query یافت نشد")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

