# -*- coding: utf-8 -*-
"""
Excel to Database Processor
پردازشگر تبدیل Excel به PostgreSQL
"""

import io
import logging
from typing import Dict, Any, List, Optional
import pandas as pd

from services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class ExcelToDatabaseProcessor:
    """پردازشگر تبدیل Excel به پایگاه داده"""
    
    def __init__(self, database_service: DatabaseService):
        self.database_service = database_service
    
    async def process_excel_file(
        self,
        file_bytes: bytes,
        filename: str,
        collection_name: str
    ) -> Dict[str, Any]:
        """پردازش فایل Excel و ذخیره در PostgreSQL"""
        try:
            logger.info(f"📊 Processing Excel file: {filename} for collection: {collection_name}")
            
            excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
            processed_tables = []
            
            for sheet_name in excel_file.sheet_names:
                logger.info(f"  Processing sheet: {sheet_name}")
                
                # خواندن DataFrame
                df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name)
                
                if df.empty:
                    logger.warning(f"  ⚠️ Sheet '{sheet_name}' is empty, skipping")
                    continue
                
                # نرمال‌سازی نام ستون‌ها
                df.columns = [self._normalize_column_name(col) for col in df.columns]
                
                # استخراج schema info
                schema_info = self._extract_schema_info(df)
                
                # ایجاد table name از sheet name و filename
                table_name = self._generate_table_name(filename, sheet_name)
                
                # ذخیره در پایگاه داده
                table = self.database_service.create_table_from_dataframe(
                    collection_name=collection_name,
                    table_name=table_name,
                    sheet_name=sheet_name,
                    source_file=filename,
                    dataframe=df,
                    schema_info=schema_info
                )
                
                processed_tables.append({
                    "table_name": table.table_name,
                    "sheet_name": sheet_name,
                    "row_count": table.row_count,
                    "column_count": table.column_count
                })
                
                logger.info(f"  ✅ Sheet '{sheet_name}' processed: {table.row_count} rows, {table.column_count} columns")
            
            return {
                "success": True,
                "collection_name": collection_name,
                "filename": filename,
                "tables": processed_tables,
                "total_tables": len(processed_tables)
            }
            
        except Exception as e:
            logger.error(f"❌ Excel processing failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _normalize_column_name(self, col_name: str) -> str:
        """نرمال‌سازی نام ستون"""
        # تبدیل به string و حذف فضاهای اضافی
        col_name = str(col_name).strip()
        
        # جایگزینی کاراکترهای غیرمجاز با underscore
        import re
        col_name = re.sub(r'[^\w\u0600-\u06FF]', '_', col_name)
        
        # حذف underscoreهای تکراری
        col_name = re.sub(r'_+', '_', col_name)
        
        # حذف underscore از ابتدا و انتها
        col_name = col_name.strip('_')
        
        # اگر خالی شد، نام پیش‌فرض
        if not col_name:
            col_name = "column"
        
        return col_name
    
    def _extract_schema_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        """استخراج اطلاعات schema"""
        schema_info = {
            "columns": {},
            "total_rows": int(len(df)),  # Convert to native int
            "total_columns": int(len(df.columns))  # Convert to native int
        }
        
        for col in df.columns:
            col_data = df[col]
            
            # آمار ستون - convert all pandas types to native Python types
            col_info = {
                "non_null_count": int(col_data.notna().sum()),
                "null_count": int(col_data.isna().sum()),
                "unique_count": int(col_data.nunique()),
                "dtype": str(col_data.dtype)
            }
            
            # نمونه داده‌ها (برای نمونه‌های عددی)
            if col_data.dtype in ['int64', 'float64', 'int32', 'float32']:
                if not col_data.empty:
                    col_info["min"] = float(col_data.min())
                    col_info["max"] = float(col_data.max())
                    col_info["mean"] = float(col_data.mean())
                else:
                    col_info["min"] = None
                    col_info["max"] = None
                    col_info["mean"] = None
            
            schema_info["columns"][str(col)] = col_info
        
        return schema_info
    
    def _generate_table_name(self, filename: str, sheet_name: str) -> str:
        """تولید نام table"""
        import re
        
        # استخراج نام فایل (بدون extension)
        file_basename = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # نرمال‌سازی
        file_basename = re.sub(r'[^\w\u0600-\u06FF]', '_', file_basename)
        sheet_name_clean = re.sub(r'[^\w\u0600-\u06FF]', '_', str(sheet_name))
        
        # ترکیب
        if file_basename.lower() == sheet_name_clean.lower():
            table_name = file_basename
        else:
            table_name = f"{file_basename}_{sheet_name_clean}"
        
        # حذف underscoreهای تکراری
        table_name = re.sub(r'_+', '_', table_name)
        table_name = table_name.strip('_').lower()
        
        return table_name if table_name else "table_1"

