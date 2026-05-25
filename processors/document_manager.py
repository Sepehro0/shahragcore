# -*- coding: utf-8 -*-
"""
Document Manager Module
مدیریت پردازش Excel و PDF documents
"""

import io
import json
import logging
from typing import Dict, Any, List, Optional
import pandas as pd

from services.dynamic_schema_analyzer import DynamicSchemaAnalyzer
from processors.document_domain_classifier import DocumentDomain
from processors.excel_to_database import ExcelToDatabaseProcessor
from processors.advanced_pdf_table_processor import AdvancedPDFTableProcessor
from processors.accurate_structure_analyzer import AccurateStructureAnalyzer
from processors.table_row_extractor import TableRowExtractor
from utils.text_utils import TextNormalizer

logger = logging.getLogger(__name__)

# Check PDF availability
try:
    import pdfplumber
    PDF_AVAILABLE = True
except:
    PDF_AVAILABLE = False


def _split_text_into_chunks(text: str, chunk_size: int = 500) -> List[str]:
    """تقسیم متن به chunks کوچک‌تر"""
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        word_length = len(word) + 1  # +1 for space
        if current_length + word_length > chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = word_length
        else:
            current_chunk.append(word)
            current_length += word_length
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks


class DocumentManager:
    """مدیریت پردازش documents (Excel و PDF)"""
    
    def __init__(
        self,
        qwen_client,
        domain_classifier,
        database_service=None,
        advanced_pdf_processor=None
    ):
        """
        Args:
            qwen_client: Qwen client instance
            domain_classifier: Document domain classifier
            database_service: Database service (optional)
            advanced_pdf_processor: Advanced PDF processor (optional)
        """
        self.qwen_client = qwen_client
        self.domain_classifier = domain_classifier
        self.database_service = database_service
        self.advanced_pdf_processor = advanced_pdf_processor
        self.text_normalizer = TextNormalizer()
    
    def detect_structured_headers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect header rows embedded in data"""
        try:
            if df.empty:
                return df
            
            # All columns unnamed => probable header row in first record
            if all(str(col).startswith("Unnamed") for col in df.columns):
                first_row = df.iloc[0].tolist()
                # Candidate headers are non-empty strings with reasonable length
                if all(isinstance(val, str) and 0 < len(val.strip()) <= 64 for val in first_row):
                    unique_ratio = len(set(first_row)) / len(first_row)
                    if unique_ratio > 0.6:
                        normalized_headers = [
                            self.text_normalizer.normalize_text(val) or f"column_{idx}"
                            for idx, val in enumerate(first_row)
                        ]
                        df = df.iloc[1:].reset_index(drop=True)
                        df.columns = normalized_headers
                        return df
            return df
        except Exception as header_error:
            logger.warning(f"Failed to detect structured headers: {header_error}")
            return df
    
    async def process_excel(
        self,
        file_bytes: bytes,
        filename: str,
        collection_name: str
    ) -> Dict[str, Any]:
        """پردازش و ذخیره Excel"""
        try:
            logger.info(f"📊 Processing Excel: {filename}...")
            
            excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
            chunks = []
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name)
                df = self.detect_structured_headers(df)
                
                if df.empty:
                    continue
                
                headers = [self.text_normalizer.normalize_text(str(col)) for col in df.columns]
                headers = [h for h in headers if h]
                
                # Dynamic Schema Analysis
                schema_analyzer = DynamicSchemaAnalyzer(self.qwen_client)
                try:
                    schema_info = await schema_analyzer.analyze_dataframe(
                        df=df,
                        filename=filename,
                        use_llm=False
                    )
                    column_mapping = schema_info.to_column_mapping()
                    dataset_type = schema_info.dataset_type.value
                    logger.info(f"📊 Dynamic schema detected: type={dataset_type}")
                except Exception as e:
                    logger.warning(f"Dynamic schema analysis failed: {e}")
                    column_mapping = {}
                    dataset_type = "general"
                
                # Process rows
                for idx, row in df.iterrows():
                    cells = [
                        self.text_normalizer.normalize_text(str(cell)) 
                        for cell in row 
                        if self.text_normalizer.normalize_text(str(cell))
                    ]
                    
                    if not cells:
                        continue
                    
                    row_data = {}
                    
                    if isinstance(row, pd.Series):
                        for col_name in df.columns:
                            value = row.get(col_name)
                            col_name_str = str(col_name).strip()
                            normalized_col = self.text_normalizer.normalize_text(col_name_str).lower().strip()
                            normalized_value = self.text_normalizer.normalize_text(value) if value else ""
                            
                            mapped_col = column_mapping.get(col_name_str)
                            
                            if not mapped_col:
                                for orig_col, english_col in column_mapping.items():
                                    if (orig_col in col_name_str or 
                                        col_name_str in orig_col or
                                        orig_col in normalized_col):
                                        mapped_col = english_col
                                        break
                            
                            if mapped_col:
                                if normalized_value:
                                    row_data[mapped_col] = normalized_value
                            elif normalized_col and normalized_value:
                                row_data[normalized_col] = normalized_value
                    
                    # Extract fields
                    question_field = row_data.get("question")
                    answer_field = row_data.get("answer")
                    code_field = row_data.get("code")
                    title_field = row_data.get("title")
                    entity_field = row_data.get("entity")
                    maddeh_id_field = row_data.get("maddeh_id")
                    zabete_title_field = row_data.get("zabete_title")
                    madde_title_field = row_data.get("madde_title")
                    
                    # Build text for embedding
                    text = f"Sheet: {sheet_name}\n"
                    if headers:
                        text += f"Headers: {' | '.join(headers)}\n"
                    text += f"Row {idx + 1}: {' | '.join(cells)}"
                    
                    if question_field:
                        text += f"\nسوال: {question_field}"
                    if answer_field:
                        text += f"\nپاسخ: {answer_field}"
                    if title_field:
                        text += f"\nعنوان: {title_field}"
                    
                    # Build metadata
                    metadata = {
                        "type": "excel_row",
                        "sheet_name": sheet_name,
                        "row_index": idx + 1,
                        "headers": " | ".join(headers) if headers else "",
                        "cells": " | ".join(cells),
                        "file_type": "excel",
                        "dataset_type": dataset_type
                    }
                    
                    # Add detected fields
                    if question_field:
                        metadata["question"] = question_field
                    if answer_field:
                        metadata["answer"] = answer_field
                    if code_field:
                        metadata["code"] = code_field
                    if title_field:
                        metadata["title"] = title_field
                    if entity_field:
                        metadata["entity"] = entity_field
                    if maddeh_id_field:
                        metadata["maddeh_id"] = maddeh_id_field
                    if zabete_title_field:
                        metadata["zabete_title"] = zabete_title_field
                    if madde_title_field:
                        metadata["madde_title"] = madde_title_field
                    
                    chunks.append({
                        "text": text,
                        "metadata": metadata
                    })
            
            if not chunks:
                return {"success": False, "error": "No data extracted"}
            
            logger.info(f"✅ Created {len(chunks)} chunks from Excel")
            
            # Domain Classification
            domain_info = None
            try:
                domain_info = await self.domain_classifier.classify_document(
                    chunks=chunks,
                    filename=filename,
                    use_llm=True
                )
                logger.info(f"✅ Domain detected: {domain_info['domain']}")
            except Exception as e:
                logger.warning(f"Domain classification failed: {e}")
                domain_info = {
                    'domain': DocumentDomain.GENERAL,
                    'confidence': 0.5,
                    'keywords': [],
                    'summary': 'سند عمومی',
                    'method': 'default'
                }
            
            return {
                "success": True,
                "chunks": chunks,
                "domain_info": domain_info,
                "chunks_count": len(chunks)
            }
            
        except Exception as e:
            logger.error(f"❌ Excel processing failed: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    async def process_pdf_advanced(
        self,
        file_bytes: bytes,
        filename: str,
        collection_name: str
    ) -> Dict[str, Any]:
        """پردازش PDF با Advanced Processor"""
        if not PDF_AVAILABLE:
            return {"success": False, "error": "PDF processing not available"}
        
        if not self.advanced_pdf_processor:
            return {"success": False, "error": "Advanced PDF processor not initialized"}
        
        try:
            logger.info(f"📄 Processing PDF: {filename}...")
            
            chunks = []
            
            # Extract tables
            logger.info("📊 Extracting tables...")
            tables_data = self.advanced_pdf_processor.extract_tables_advanced(file_bytes)
            
            if tables_data:
                table_chunks = self.advanced_pdf_processor.create_structured_chunks(tables_data)
                chunks.extend(table_chunks)
                logger.info(f"✅ Created {len(table_chunks)} table chunks")
            
            # Extract text
            logger.info("📝 Extracting text content...")
            try:
                pdf_file = io.BytesIO(file_bytes)
                text_chunks = []
                
                with pdfplumber.open(pdf_file) as pdf:
                    for page_num, page in enumerate(pdf.pages, 1):
                        text = page.extract_text()
                        if text and text.strip():
                            page_text_chunks = _split_text_into_chunks(text, chunk_size=500)
                            
                            for chunk_idx, chunk_text in enumerate(page_text_chunks):
                                if chunk_text.strip():
                                    chunk = {
                                        'text': chunk_text.strip(),
                                        'metadata': {
                                            'page': page_num,
                                            'chunk_index': chunk_idx,
                                            'source': 'pdf_text',
                                            'filename': filename,
                                            'type': 'text_content'
                                        }
                                    }
                                    text_chunks.append(chunk)
                
                if text_chunks:
                    chunks.extend(text_chunks)
                    logger.info(f"✅ Created {len(text_chunks)} text chunks")
                    
            except Exception as e:
                logger.error(f"❌ Text extraction failed: {str(e)}")
                if not chunks:
                    return {"success": False, "error": f"Text extraction failed: {str(e)}"}
            
            if not chunks:
                return {"success": False, "error": "No content extracted from PDF"}
            
            logger.info(f"✅ Total {len(chunks)} chunks created")
            
            # Document Structure Analysis
            try:
                structure_analyzer = AccurateStructureAnalyzer()
                doc_structure = structure_analyzer.analyze_document(chunks)
                
                enriched_chunks = []
                for chunk_idx, chunk in enumerate(chunks):
                    enriched_chunk = structure_analyzer.enrich_chunk_metadata(
                        chunk, doc_structure, chunk_idx
                    )
                    enriched_chunks.append(enriched_chunk)
                
                structure_summary_text = structure_analyzer.create_structure_summary_text(doc_structure)
                structure_summary_chunk = {
                    'text': structure_summary_text,
                    'metadata': {
                        'type': 'structure_summary',
                        'filename': filename,
                        'hierarchy_json': json.dumps(doc_structure, ensure_ascii=False)[:4000],
                        'total_parts': str(doc_structure.get('total_parts', 0)),
                        'total_sections': str(doc_structure.get('total_sections', 0)),
                        'total_clauses': str(doc_structure.get('total_clauses', 0)),
                        'total_items': str(doc_structure.get('total_items', 0))
                    }
                }
                
                enriched_chunks.insert(0, structure_summary_chunk)
                chunks = enriched_chunks
                
            except Exception as e:
                logger.warning(f"Structure analysis failed: {e}")
            
            # Separate Combined Table Rows
            try:
                row_extractor = TableRowExtractor()
                separated_chunks = row_extractor.split_combined_chunks(chunks)
                logger.info(f"✅ Separated into {len(separated_chunks)} individual row chunks")
                chunks = separated_chunks
            except Exception as e:
                logger.warning(f"Row separation failed: {e}")
            
            # Domain Classification
            domain_info = None
            try:
                domain_info = await self.domain_classifier.classify_document(
                    chunks=chunks,
                    filename=filename,
                    use_llm=True
                )
                logger.info(f"✅ Domain detected: {domain_info['domain']}")
            except Exception as e:
                logger.warning(f"Domain classification failed: {e}")
                domain_info = {
                    'domain': DocumentDomain.GENERAL,
                    'confidence': 0.5,
                    'keywords': [],
                    'summary': 'سند عمومی',
                    'method': 'default'
                }
            
            return {
                "success": True,
                "chunks": chunks,
                "domain_info": domain_info,
                "chunks_count": len(chunks)
            }
            
        except Exception as e:
            logger.error(f"❌ PDF processing failed: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

