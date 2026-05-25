# -*- coding: utf-8 -*-
"""
Intelligent content chunking based on content type and domain
Enhanced with LangChain integration for better chunking strategies
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

# LangChain imports for enhanced chunking
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
    from langchain_core.documents import Document as LCDocument
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    RecursiveCharacterTextSplitter = None
    MarkdownHeaderTextSplitter = None
    LCDocument = None

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Content type enumeration"""
    LEGAL_DOCUMENT = "legal_document"
    MEDICAL_DOCUMENT = "medical_document"
    TECHNICAL_DOCUMENT = "technical_document"
    ACADEMIC_PAPER = "academic_paper"
    CODE_DOCUMENTATION = "code_documentation"
    CONVERSATIONAL = "conversational"
    BUSINESS_DOCUMENT = "business_document"
    MATHEMATICAL = "mathematical"
    FINANCIAL_DOCUMENT = "financial_document"  # New for Persian financial PDFs
    GENERAL = "general"


@dataclass
class Chunk:
    """Represents a content chunk"""
    content: str
    chunk_index: int
    title: Optional[str] = None
    section: Optional[str] = None
    page_number: Optional[int] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class IntelligentChunker:
    """Intelligent content chunking based on content type and domain"""
    
    def __init__(self, use_langchain: bool = True):
        self.use_langchain = use_langchain and HAS_LANGCHAIN
        
        # Initialize LangChain text splitters if available
        if self.use_langchain:
            self._init_langchain_splitters()
        
        # Content type detection patterns
        self.content_patterns = {
            ContentType.LEGAL_DOCUMENT: [
                r"ماده\s+\d+",
                r"تبصره\s+\d+",
                r"بند\s+\d+",
                r"قانون\s+",
                r"مقررات\s+"
            ],
            ContentType.MEDICAL_DOCUMENT: [
                r"تشخیص\s*:",
                r"درمان\s*:",
                r"علائم\s*:",
                r"دوز\s*:",
                r"مصرف\s*:"
            ],
            ContentType.TECHNICAL_DOCUMENT: [
                r"def\s+\w+\(",
                r"class\s+\w+",
                r"function\s+\w+",
                r"API\s+",
                r"endpoint\s+"
            ],
            ContentType.ACADEMIC_PAPER: [
                r"Abstract\s*:",
                r"Introduction\s*:",
                r"Methodology\s*:",
                r"Results\s*:",
                r"Conclusion\s*:",
                r"References\s*:"
            ],
            ContentType.CODE_DOCUMENTATION: [
                r"```\w+",
                r"def\s+\w+",
                r"class\s+\w+",
                r"import\s+\w+",
                r"from\s+\w+"
            ],
            ContentType.FINANCIAL_DOCUMENT: [
                r"جدول\s+\d+",
                r"بخش\s+\d+",
                r"فصل\s+\d+",
                r"مالیات\s+",
                r"بودجه\s+",
                r"درآمد\s+",
                r"هزینه\s+",
                r"میلیون\s*ریال",
                r"میلیارد\s*ریال"
            ]
        }
    
    def _init_langchain_splitters(self):
        """Initialize LangChain text splitters for different content types"""
        try:
            # General purpose splitter
            self.general_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
            )
            
            # Markdown splitter for structured documents
            self.markdown_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=[
                    ("#", "Header 1"),
                    ("##", "Header 2"),
                    ("###", "Header 3"),
                    ("####", "Header 4"),
                ]
            )
            
            # Specialized splitters for different content types
            self.splitters = {
                ContentType.LEGAL_DOCUMENT: RecursiveCharacterTextSplitter(
                    chunk_size=1500,
                    chunk_overlap=300,
                    separators=["\n\n", "ماده", "تبصره", "بند", "\n", ".", " "]
                ),
                ContentType.MEDICAL_DOCUMENT: RecursiveCharacterTextSplitter(
                    chunk_size=1200,
                    chunk_overlap=200,
                    separators=["\n\n", "تشخیص", "درمان", "علائم", "\n", ".", " "]
                ),
                ContentType.TECHNICAL_DOCUMENT: RecursiveCharacterTextSplitter(
                    chunk_size=800,
                    chunk_overlap=150,
                    separators=["\n\n", "```", "def ", "class ", "\n", ".", " "]
                ),
                ContentType.ACADEMIC_PAPER: RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200,
                    separators=["\n\n", "Abstract", "Introduction", "Methodology", "Results", "Conclusion", "\n", ".", " "]
                ),
                ContentType.CODE_DOCUMENTATION: RecursiveCharacterTextSplitter(
                    chunk_size=600,
                    chunk_overlap=100,
                    separators=["\n\n", "def ", "class ", "```", "\n", " ", ""]
                ),
                ContentType.MATHEMATICAL: RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200,
                    separators=["\n\n", "قضیه", "اثبات", "مثال", "تعریف", "\n", ".", " "]
                ),
                ContentType.FINANCIAL_DOCUMENT: RecursiveCharacterTextSplitter(
                    chunk_size=1200,
                    chunk_overlap=250,
                    separators=["\n\n", "جدول", "بخش", "فصل", "\n", ".", " "]
                )
            }
            
            logger.info("LangChain splitters initialized successfully")
            
        except Exception as e:
            logger.warning(f"Failed to initialize LangChain splitters: {e}")
            self.use_langchain = False
    
    def chunk_content(self, content: str, content_type: ContentType, 
                     domain_config: Dict[str, Any], metadata: Dict[str, Any] = None) -> List[Chunk]:
        """Chunk content based on type and configuration"""
        try:
            # Use LangChain if available and enabled
            if self.use_langchain:
                return self._chunk_with_langchain(content, content_type, domain_config, metadata)
            
            # Fallback to custom chunking methods
            if content_type == ContentType.LEGAL_DOCUMENT:
                return self._chunk_legal_document(content, domain_config, metadata)
            elif content_type == ContentType.MEDICAL_DOCUMENT:
                return self._chunk_medical_document(content, domain_config, metadata)
            elif content_type == ContentType.TECHNICAL_DOCUMENT:
                return self._chunk_technical_document(content, domain_config, metadata)
            elif content_type == ContentType.ACADEMIC_PAPER:
                return self._chunk_academic_paper(content, domain_config, metadata)
            elif content_type == ContentType.CODE_DOCUMENTATION:
                return self._chunk_code_documentation(content, domain_config, metadata)
            elif content_type == ContentType.CONVERSATIONAL:
                return self._chunk_conversational(content, domain_config, metadata)
            elif content_type == ContentType.MATHEMATICAL:
                return self._chunk_mathematical(content, domain_config, metadata)
            elif content_type == ContentType.FINANCIAL_DOCUMENT:
                return self._chunk_financial_document(content, domain_config, metadata)
            else:
                return self._chunk_general(content, domain_config, metadata)
                
        except Exception as e:
            logger.error(f"Chunking failed: {e}")
            return self._chunk_general(content, domain_config, metadata)
    
    def _chunk_with_langchain(self, content: str, content_type: ContentType, 
                             domain_config: Dict[str, Any], metadata: Dict[str, Any] = None) -> List[Chunk]:
        """Chunk content using LangChain splitters"""
        try:
            # Get appropriate splitter for content type
            if content_type in self.splitters:
                splitter = self.splitters[content_type]
            else:
                splitter = self.general_splitter
            
            # Create LangChain document
            lc_doc = LCDocument(page_content=content, metadata=metadata or {})
            
            # Split the document
            chunks = splitter.split_documents([lc_doc])
            
            # Convert to our Chunk format
            result_chunks = []
            for i, chunk in enumerate(chunks):
                # Analyze chunk characteristics
                characteristics = self.analyze_chunk_characteristics(
                    Chunk(content=chunk.page_content, chunk_index=i)
                )
                
                result_chunk = Chunk(
                    content=chunk.page_content,
                    chunk_index=i,
                    title=self._extract_title_from_chunk(chunk.page_content),
                    section=self._extract_section_from_chunk(chunk.page_content, content_type),
                    page_number=self._extract_page_number_from_metadata(chunk.metadata),
                    metadata={
                        **chunk.metadata,
                        **characteristics
                    }
                )
                result_chunks.append(result_chunk)
            
            logger.info(f"Chunked content using LangChain: {len(result_chunks)} chunks")
            return result_chunks
            
        except Exception as e:
            logger.error(f"LangChain chunking failed: {e}")
            # Fallback to custom chunking
            return self._chunk_general(content, domain_config, metadata)
    
    def _extract_title_from_chunk(self, content: str) -> Optional[str]:
        """Extract title from chunk content"""
        lines = content.split('\n')
        for line in lines[:3]:  # Check first 3 lines
            line = line.strip()
            if len(line) > 10 and len(line) < 100:
                # Check if it looks like a title
                if any(keyword in line.lower() for keyword in ['فصل', 'بخش', 'درس', 'مثال', 'تمرین', 'جدول']):
                    return line
        return None
    
    def _extract_section_from_chunk(self, content: str, content_type: ContentType) -> Optional[str]:
        """Extract section information from chunk content"""
        content_lower = content.lower()
        
        if content_type == ContentType.LEGAL_DOCUMENT:
            if 'ماده' in content_lower:
                return 'legal_article'
            elif 'تبصره' in content_lower:
                return 'legal_note'
        elif content_type == ContentType.MEDICAL_DOCUMENT:
            if 'تشخیص' in content_lower:
                return 'diagnosis'
            elif 'درمان' in content_lower:
                return 'treatment'
        elif content_type == ContentType.TECHNICAL_DOCUMENT:
            if 'def ' in content_lower or 'function' in content_lower:
                return 'function'
            elif 'class ' in content_lower:
                return 'class'
        elif content_type == ContentType.ACADEMIC_PAPER:
            if 'abstract' in content_lower:
                return 'abstract'
            elif 'introduction' in content_lower:
                return 'introduction'
            elif 'conclusion' in content_lower:
                return 'conclusion'
        elif content_type == ContentType.FINANCIAL_DOCUMENT:
            if 'جدول' in content_lower:
                return 'table'
            elif 'بخش' in content_lower:
                return 'section'
            elif 'فصل' in content_lower:
                return 'chapter'
        
        return 'content'
    
    def _extract_page_number_from_metadata(self, metadata: Dict[str, Any]) -> Optional[int]:
        """Extract page number from metadata"""
        return metadata.get('page_number') or metadata.get('page') or None
    
    def _chunk_financial_document(self, content: str, config: Dict[str, Any], metadata: Dict[str, Any]) -> List[Chunk]:
        """Chunk financial documents preserving table structure"""
        chunks = []
        chunk_size = config.get("chunk_size", 1200)
        chunk_overlap = config.get("chunk_overlap", 250)
        
        # Split by tables and sections
        table_pattern = r"(جدول\s+\d+[^\n]*(?:\n(?!جدول\s+\d+).*)*)"
        section_pattern = r"(بخش\s+\d+[^\n]*(?:\n(?!بخش\s+\d+).*)*)"
        
        tables = re.findall(table_pattern, content, re.MULTILINE | re.DOTALL)
        sections = re.findall(section_pattern, content, re.MULTILINE | re.DOTALL)
        
        all_sections = tables + sections
        
        if not all_sections:
            # Fallback to paragraph-based chunking
            return self._chunk_by_paragraphs(content, chunk_size, chunk_overlap, metadata)
        
        current_chunk = ""
        chunk_index = 0
        
        for section in all_sections:
            if len(current_chunk) + len(section) > chunk_size and current_chunk:
                # Save current chunk
                chunks.append(Chunk(
                    content=current_chunk.strip(),
                    chunk_index=chunk_index,
                    section="financial_section",
                    metadata=metadata or {}
                ))
                chunk_index += 1
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else ""
                current_chunk = overlap_text + "\n" + section
            else:
                current_chunk += "\n" + section if current_chunk else section
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(Chunk(
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                section="financial_section",
                metadata=metadata or {}
            ))
        
        return chunks
    
    def _chunk_legal_document(self, content: str, config: Dict[str, Any], metadata: Dict[str, Any]) -> List[Chunk]:
        """Chunk legal documents preserving article structure"""
        chunks = []
        chunk_size = config.get("chunk_size", 1500)
        chunk_overlap = config.get("chunk_overlap", 300)
        
        # Split by articles/sections
        article_pattern = r"(ماده\s+\d+[^\n]*(?:\n(?!ماده\s+\d+).*)*)"
        articles = re.findall(article_pattern, content, re.MULTILINE | re.DOTALL)
        
        if not articles:
            # Fallback to paragraph-based chunking
            return self._chunk_by_paragraphs(content, chunk_size, chunk_overlap, metadata)
        
        current_chunk = ""
        chunk_index = 0
        
        for article in articles:
            if len(current_chunk) + len(article) > chunk_size and current_chunk:
                # Save current chunk
                chunks.append(Chunk(
                    content=current_chunk.strip(),
                    chunk_index=chunk_index,
                    section="legal_article",
                    metadata=metadata or {}
                ))
                chunk_index += 1
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else ""
                current_chunk = overlap_text + "\n" + article
            else:
                current_chunk += "\n" + article if current_chunk else article
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(Chunk(
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                section="legal_article",
                metadata=metadata or {}
            ))
        
        return chunks
    
    def _chunk_medical_document(self, content: str, config: Dict[str, Any], metadata: Dict[str, Any]) -> List[Chunk]:
        """Chunk medical documents preserving diagnosis/treatment structure"""
        chunks = []
        chunk_size = config.get("chunk_size", 1200)
        chunk_overlap = config.get("chunk_overlap", 200)
        
        # Split by medical sections
        section_pattern = r"(تشخیص\s*:|درمان\s*:|علائم\s*:|دوز\s*:|مصرف\s*:[^\n]*(?:\n(?!تشخیص\s*:|درمان\s*:|علائم\s*:|دوز\s*:|مصرف\s*:).*)*)"
        sections = re.findall(section_pattern, content, re.MULTILINE | re.DOTALL)
        
        if not sections:
            return self._chunk_by_paragraphs(content, chunk_size, chunk_overlap, metadata)
        
        current_chunk = ""
        chunk_index = 0
        
        for section in sections:
            if len(current_chunk) + len(section) > chunk_size and current_chunk:
                chunks.append(Chunk(
                    content=current_chunk.strip(),
                    chunk_index=chunk_index,
                    section="medical_section",
                    metadata=metadata or {}
                ))
                chunk_index += 1
                current_chunk = section
            else:
                current_chunk += "\n" + section if current_chunk else section
        
        if current_chunk.strip():
            chunks.append(Chunk(
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                section="medical_section",
                metadata=metadata or {}
            ))
        
        return chunks
    
    def _chunk_technical_document(self, content: str, config: Dict[str, Any], metadata: Dict[str, Any]) -> List[Chunk]:
        """Chunk technical documents preserving code structure"""
        chunks = []
        chunk_size = config.get("chunk_size", 800)
        chunk_overlap = config.get("chunk_overlap", 150)
        
        # Split by code blocks and sections
        code_block_pattern = r"(```[\s\S]*?```)"
        sections = re.split(code_block_pattern, content)
        
        current_chunk = ""
        chunk_index = 0
        
        for section in sections:
            if not section.strip():
                continue
                
            if len(current_chunk) + len(section) > chunk_size and current_chunk:
                chunks.append(Chunk(
                    content=current_chunk.strip(),
                    chunk_index=chunk_index,
                    section="technical_section",
                    metadata=metadata or {}
                ))
                chunk_index += 1
                current_chunk = section
            else:
                current_chunk += section
        
        if current_chunk.strip():
            chunks.append(Chunk(
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                section="technical_section",
                metadata=metadata or {}
            ))
        
        return chunks
    
    def _chunk_academic_paper(self, content: str, config: Dict[str, Any], metadata: Dict[str, Any]) -> List[Chunk]:
        """Chunk academic papers preserving section structure"""
        chunks = []
        chunk_size = config.get("chunk_size", 1000)
        chunk_overlap = config.get("chunk_overlap", 200)
        
        # Academic paper sections
        section_pattern = r"(Abstract\s*:|Introduction\s*:|Methodology\s*:|Results\s*:|Discussion\s*:|Conclusion\s*:|References\s*:[^\n]*(?:\n(?!Abstract\s*:|Introduction\s*:|Methodology\s*:|Results\s*:|Discussion\s*:|Conclusion\s*:|References\s*:).*)*)"
        sections = re.findall(section_pattern, content, re.MULTILINE | re.DOTALL)
        
        if not sections:
            return self._chunk_by_paragraphs(content, chunk_size, chunk_overlap, metadata)
        
        current_chunk = ""
        chunk_index = 0
        
        for section in sections:
            if len(current_chunk) + len(section) > chunk_size and current_chunk:
                chunks.append(Chunk(
                    content=current_chunk.strip(),
                    chunk_index=chunk_index,
                    section="academic_section",
                    metadata=metadata or {}
                ))
                chunk_index += 1
                current_chunk = section
            else:
                current_chunk += "\n" + section if current_chunk else section
        
        if current_chunk.strip():
            chunks.append(Chunk(
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                section="academic_section",
                metadata=metadata or {}
            ))
        
        return chunks
    
    def _chunk_code_documentation(self, content: str, config: Dict[str, Any], metadata: Dict[str, Any]) -> List[Chunk]:
        """Chunk code documentation preserving function/class boundaries"""
        chunks = []
        chunk_size = config.get("chunk_size", 600)
        chunk_overlap = config.get("chunk_overlap", 100)
        
        # Split by functions and classes
        function_pattern = r"(def\s+\w+\([^)]*\):[\s\S]*?(?=\n\s*def|\n\s*class|\Z))"
        class_pattern = r"(class\s+\w+[^:]*:[\s\S]*?(?=\n\s*def|\n\s*class|\Z))"
        
        functions = re.findall(function_pattern, content, re.MULTILINE)
        classes = re.findall(class_pattern, content, re.MULTILINE)
        
        all_sections = functions + classes
        
        if not all_sections:
            return self._chunk_by_paragraphs(content, chunk_size, chunk_overlap, metadata)
        
        current_chunk = ""
        chunk_index = 0
        
        for section in all_sections:
            if len(current_chunk) + len(section) > chunk_size and current_chunk:
                chunks.append(Chunk(
                    content=current_chunk.strip(),
                    chunk_index=chunk_index,
                    section="code_section",
                    metadata=metadata or {}
                ))
                chunk_index += 1
                current_chunk = section
            else:
                current_chunk += "\n" + section if current_chunk else section
        
        if current_chunk.strip():
            chunks.append(Chunk(
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                section="code_section",
                metadata=metadata or {}
            ))
        
        return chunks
    
    def _chunk_conversational(self, content: str, config: Dict[str, Any], metadata: Dict[str, Any]) -> List[Chunk]:
        """Chunk conversational content by sentences"""
        chunks = []
        chunk_size = config.get("chunk_size", 500)
        chunk_overlap = config.get("chunk_overlap", 100)
        
        # Split by sentences
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        current_chunk = ""
        chunk_index = 0
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                chunks.append(Chunk(
                    content=current_chunk.strip(),
                    chunk_index=chunk_index,
                    section="conversational",
                    metadata=metadata or {}
                ))
                chunk_index += 1
                current_chunk = sentence
            else:
                current_chunk += ". " + sentence if current_chunk else sentence
        
        if current_chunk.strip():
            chunks.append(Chunk(
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                section="conversational",
                metadata=metadata or {}
            ))
        
        return chunks
    
    def _chunk_mathematical(self, content: str, config: Dict[str, Any], metadata: Dict[str, Any]) -> List[Chunk]:
        """Chunk mathematical content preserving formula context"""
        chunks = []
        chunk_size = config.get("chunk_size", 1000)
        chunk_overlap = config.get("chunk_overlap", 200)
        
        # Split by mathematical sections (theorems, proofs, examples)
        section_pattern = r"(قضیه\s*:|اثبات\s*:|مثال\s*:|تعریف\s*:|لم\s*:[^\n]*(?:\n(?!قضیه\s*:|اثبات\s*:|مثال\s*:|تعریف\s*:|لم\s*:).*)*)"
        sections = re.findall(section_pattern, content, re.MULTILINE | re.DOTALL)
        
        if not sections:
            return self._chunk_by_paragraphs(content, chunk_size, chunk_overlap, metadata)
        
        current_chunk = ""
        chunk_index = 0
        
        for section in sections:
            if len(current_chunk) + len(section) > chunk_size and current_chunk:
                chunks.append(Chunk(
                    content=current_chunk.strip(),
                    chunk_index=chunk_index,
                    section="mathematical_section",
                    metadata=metadata or {}
                ))
                chunk_index += 1
                current_chunk = section
            else:
                current_chunk += "\n" + section if current_chunk else section
        
        if current_chunk.strip():
            chunks.append(Chunk(
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                section="mathematical_section",
                metadata=metadata or {}
            ))
        
        return chunks
    
    def _chunk_general(self, content: str, config: Dict[str, Any], metadata: Dict[str, Any]) -> List[Chunk]:
        """General chunking strategy"""
        return self._chunk_by_paragraphs(
            content, 
            config.get("chunk_size", 1000), 
            config.get("chunk_overlap", 200), 
            metadata
        )
    
    def _chunk_by_paragraphs(self, content: str, chunk_size: int, chunk_overlap: int, metadata: Dict[str, Any]) -> List[Chunk]:
        """Chunk content by paragraphs with size limits"""
        chunks = []
        paragraphs = content.split('\n\n')
        
        current_chunk = ""
        chunk_index = 0
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
                
            if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
                chunks.append(Chunk(
                    content=current_chunk.strip(),
                    chunk_index=chunk_index,
                    metadata=metadata or {}
                ))
                chunk_index += 1
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else ""
                current_chunk = overlap_text + "\n\n" + paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        if current_chunk.strip():
            chunks.append(Chunk(
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                metadata=metadata or {}
            ))
        
        return chunks
    
    def detect_content_type(self, content: str) -> ContentType:
        """Detect content type based on patterns"""
        content_lower = content.lower()
        
        for content_type, patterns in self.content_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    return content_type
        
        return ContentType.GENERAL
    
    def analyze_chunk_characteristics(self, chunk: Chunk) -> Dict[str, Any]:
        """Analyze characteristics of a chunk"""
        content = chunk.content
        
        return {
            "has_formula": bool(re.search(r'[=+\-*/^()]', content)),
            "has_code": bool(re.search(r'```|def\s+|class\s+|import\s+', content)),
            "has_table": bool(re.search(r'\|.*\|', content)),
            "has_example": bool(re.search(r'مثال|example|مثلاً', content, re.IGNORECASE)),
            "has_question": bool(re.search(r'\?', content)),
            "has_numbered_list": bool(re.search(r'^\d+\.', content, re.MULTILINE)),
            "has_bullet_list": bool(re.search(r'^[-*•]', content, re.MULTILINE)),
            "word_count": len(content.split()),
            "char_count": len(content),
            "sentence_count": len(re.split(r'[.!?]+', content)),
            "has_persian_numbers": bool(re.search(r'[\u06F0-\u06F9]', content)),
            "has_currency": bool(re.search(r'ریال|تومان|دلار|یورو', content, re.IGNORECASE))
        }


# Global chunker instance
intelligent_chunker = IntelligentChunker()
