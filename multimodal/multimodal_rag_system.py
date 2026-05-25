# -*- coding: utf-8 -*-
"""
Multimodal RAG System
سیستم Multimodal RAG برای پردازش پیشرفته اسناد
"""

import time
from typing import Dict, List, Optional, Union, Any
from PIL import Image
import numpy as np
from loguru import logger

from .gpu_resource_manager import gpu_resource_manager
from .base_multimodal_processor import BaseMultimodalProcessor

# Import processors
from .document_understanding.trocr_processor import TrOCRHandler
from .document_understanding.layoutlmv3_processor import LayoutLMv3Handler
from .document_understanding.donut_processor import DonutHandler
from .vision_language.clip_processor import CLIPHandler
from .vision_language.blip2_processor import BLIP2Handler
from .vision_language.llava_processor import LLaVAHandler

class MultimodalRAGSystem:
    """سیستم Multimodal RAG برای پردازش پیشرفته اسناد"""
    
    def __init__(
        self,
        base_rag_system,
        enable_layoutlm: bool = True,
        enable_donut: bool = True,
        enable_trocr: bool = True,
        enable_clip: bool = True,
        enable_blip2: bool = False,
        enable_llava: bool = False,
        auto_detect_gpu: bool = True,
        model_config: Dict = None
    ):
        self.base_rag = base_rag_system
        self.gpu_manager = gpu_resource_manager
        
        # Configuration
        self.enable_layoutlm = enable_layoutlm
        self.enable_donut = enable_donut
        self.enable_trocr = enable_trocr
        self.enable_clip = enable_clip
        self.enable_blip2 = enable_blip2
        self.enable_llava = enable_llava
        self.auto_detect_gpu = auto_detect_gpu
        self.model_config = model_config or {}
        
        # Processors
        self.processors = {}
        self.loaded_models = []
        
        # Performance tracking
        self.processing_stats = {
            'total_processed': 0,
            'successful_processed': 0,
            'failed_processed': 0,
            'average_processing_time': 0.0
        }
        
        # Multimodal-enhanced collections
        self.multimodal_collections = {}
        
        # Initialize processors
        self._initialize_processors()
    
    def _initialize_processors(self):
        """مقداردهی اولیه پردازشگرها"""
        logger.info("🚀 Initializing Multimodal RAG System...")
        
        # بررسی GPU و VRAM
        if self.auto_detect_gpu:
            self._auto_configure_models()
        
        # بارگذاری پردازشگرها بر اساس اولویت
        self._load_processors_by_priority()
        
        logger.info(f"✅ Multimodal RAG System initialized with {len(self.processors)} processors")
    
    def _auto_configure_models(self):
        """پیکربندی خودکار مدل‌ها بر اساس GPU"""
        try:
            # بررسی VRAM موجود
            vram_info = self.gpu_manager.check_vram_availability()
            total_vram_gb = vram_info['total_available_gb']
            
            logger.info(f"💾 Available VRAM: {total_vram_gb:.1f}GB")
            logger.info(f"📊 GPU Details: {vram_info['gpu_details']}")
            logger.info(f"💡 Recommendations: {vram_info['recommendations']}")
            
            # غیرفعال کردن مدل‌های سنگین در صورت کمبود VRAM
            if total_vram_gb < 10:
                self.enable_blip2 = False
                self.enable_llava = False
                logger.warning("⚠️  Disabled BLIP-2 and LLaVA due to insufficient VRAM")
            
            if total_vram_gb < 6:
                self.enable_donut = False
                logger.warning("⚠️  Disabled Donut due to insufficient VRAM")
            
            if total_vram_gb < 4:
                self.enable_layoutlm = False
                logger.warning("⚠️  Disabled LayoutLMv3 due to insufficient VRAM")
            
            # نمایش مدل‌های قابل بارگذاری
            if vram_info['can_load_models']:
                logger.info("✅ Models that can be loaded:")
                for model_info in vram_info['can_load_models']:
                    logger.info(f"   - {model_info['model']} ({model_info['required_gb']}GB) - {model_info['priority']}")
            
        except Exception as e:
            logger.error(f"❌ Failed to auto-configure models: {e}")
    
    def _load_processors_by_priority(self):
        """بارگذاری پردازشگرها بر اساس اولویت - فقط 3 مدل اول"""
        # اولویت 1: TrOCR (سبک‌ترین)
        if self.enable_trocr:
            self._load_processor('trocr', TrOCRHandler, 'document_understanding')
        
        # اولویت 2: LayoutLMv3 (متوسط)
        if self.enable_layoutlm:
            self._load_processor('layoutlm', LayoutLMv3Handler, 'document_understanding')
        
        # اولویت 3: Donut (سنگین‌ترین از 3 مدل)
        if self.enable_donut:
            self._load_processor('donut', DonutHandler, 'document_understanding')
        
        # غیرفعال کردن مدل‌های سنگین برای پایداری
        logger.info("⚠️  Heavy models (CLIP, BLIP-2, LLaVA) disabled for stability")
    
    def _load_processor(self, name: str, handler_class, category: str):
        """بارگذاری یک پردازشگر"""
        try:
            logger.info(f"🔄 Loading {name} processor...")
            
            # تنظیمات مدل
            model_config = self.model_config.get(name, {})
            
            # ایجاد handler
            handler = handler_class(**model_config)
            
            # بارگذاری مدل
            if handler.load_model():
                self.processors[name] = handler
                self.loaded_models.append(name)
                logger.info(f"✅ {name} processor loaded successfully")
            else:
                logger.warning(f"⚠️  Failed to load {name} processor")
                
        except Exception as e:
            logger.error(f"❌ Failed to load {name} processor: {e}")
    
    def process_pdf_multimodal(self, pdf_path: str) -> Dict:
        """پردازش PDF با قابلیت‌های multimodal"""
        try:
            start_time = time.time()
            logger.info(f"📄 Processing PDF with multimodal capabilities: {pdf_path}")
            
            # استخراج صفحات PDF
            pages = self._extract_pdf_pages(pdf_path)
            
            results = {
                'pdf_path': pdf_path,
                'total_pages': len(pages),
                'pages': [],
                'processing_time': 0.0,
                'success': True
            }
            
            # پردازش هر صفحه
            for page_num, page_image in enumerate(pages):
                try:
                    page_result = self.process_pdf_page(pdf_path, page_num)
                    results['pages'].append(page_result)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process page {page_num}: {e}")
                    results['pages'].append({
                        'page_number': page_num,
                        'success': False,
                        'error': str(e)
                    })
            
            # محاسبه زمان پردازش
            processing_time = time.time() - start_time
            results['processing_time'] = processing_time
            
            # به‌روزرسانی آمار
            self._update_processing_stats(True, processing_time)
            
            logger.info(f"✅ PDF processing completed in {processing_time:.2f}s")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to process PDF: {e}")
            self._update_processing_stats(False, 0.0)
            return {
                'pdf_path': pdf_path,
                'success': False,
                'error': str(e),
                'processing_time': 0.0
            }
    
    def process_pdf_page(self, pdf_path: str, page_num: int) -> Dict:
        """پردازش یک صفحه PDF"""
        try:
            # استخراج تصویر صفحه
            page_image = self._extract_pdf_page_image(pdf_path, page_num)
            
            page_result = {
                'page_number': page_num,
                'success': True,
                'text_extraction': {},
                'layout_analysis': {},
                'visual_analysis': {},
                'tables': [],
                'images': []
            }
            
            # 1. استخراج متن با TrOCR
            if 'trocr' in self.processors:
                try:
                    text = self.processors['trocr'].extract_text_from_image(page_image)
                    page_result['text_extraction']['trocr'] = {
                        'text': text,
                        'success': bool(text)
                    }
                except Exception as e:
                    logger.warning(f"TrOCR failed for page {page_num}: {e}")
                    page_result['text_extraction']['trocr'] = {'text': '', 'success': False}
            
            # 2. تحلیل layout با LayoutLMv3
            if 'layoutlm' in self.processors:
                try:
                    layout_result = self.processors['layoutlm'].extract_layout_structure(page_image)
                    page_result['layout_analysis'] = layout_result
                except Exception as e:
                    logger.warning(f"LayoutLMv3 failed for page {page_num}: {e}")
                    page_result['layout_analysis'] = {'structure': [], 'confidence': 0.0}
            
            # 3. استخراج جداول با Donut
            if 'donut' in self.processors:
                try:
                    table_data = self.processors['donut'].extract_table_data(page_image)
                    page_result['tables'] = [table_data] if table_data['table_data'] else []
                except Exception as e:
                    logger.warning(f"Donut failed for page {page_num}: {e}")
                    page_result['tables'] = []
            
            # 4. تحلیل بصری با CLIP
            if 'clip' in self.processors:
                try:
                    # تحلیل محتوای بصری
                    visual_analysis = self._analyze_page_visual_content(page_image)
                    page_result['visual_analysis']['clip'] = visual_analysis
                except Exception as e:
                    logger.warning(f"CLIP failed for page {page_num}: {e}")
                    page_result['visual_analysis']['clip'] = {}
            
            # 5. تحلیل با BLIP-2 (اگر فعال باشد)
            if 'blip2' in self.processors:
                try:
                    caption = self.processors['blip2'].generate_caption(page_image)
                    page_result['visual_analysis']['blip2'] = {
                        'caption': caption,
                        'success': bool(caption)
                    }
                except Exception as e:
                    logger.warning(f"BLIP-2 failed for page {page_num}: {e}")
                    page_result['visual_analysis']['blip2'] = {'caption': '', 'success': False}
            
            # 6. تحلیل با LLaVA (اگر فعال باشد)
            if 'llava' in self.processors:
                try:
                    analysis = self.processors['llava'].analyze_document(page_image)
                    page_result['visual_analysis']['llava'] = analysis
                except Exception as e:
                    logger.warning(f"LLaVA failed for page {page_num}: {e}")
                    page_result['visual_analysis']['llava'] = {'analysis': '', 'confidence': 0.0}
            
            return page_result
            
        except Exception as e:
            logger.error(f"❌ Failed to process page {page_num}: {e}")
            return {
                'page_number': page_num,
                'success': False,
                'error': str(e)
            }
    
    def _analyze_page_visual_content(self, page_image: Image.Image) -> Dict:
        """تحلیل محتوای بصری صفحه"""
        try:
            # سوالات تحلیل بصری
            analysis_questions = [
                "What type of document is this?",
                "Are there any tables or charts?",
                "What is the main content?",
                "Are there any images or diagrams?",
                "What is the layout structure?"
            ]
            
            # تحلیل با CLIP
            if 'clip' in self.processors:
                classifications = {}
                for question in analysis_questions:
                    result = self.processors['clip'].classify_image(
                        page_image, 
                        [question], 
                        threshold=0.1
                    )
                    classifications[question] = result
                
                return {
                    'classifications': classifications,
                    'processor': 'clip'
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze visual content: {e}")
            return {}
    
    def extract_tables_advanced(self, pdf_path: str, page_num: int) -> List[Dict]:
        """استخراج جداول با استفاده از LayoutLM + Donut"""
        try:
            # استخراج تصویر صفحه
            page_image = self._extract_pdf_page_image(pdf_path, page_num)
            
            tables = []
            
            # استخراج با LayoutLMv3
            if 'layoutlm' in self.processors:
                try:
                    layout_tables = self.processors['layoutlm'].extract_tables(page_image)
                    for table in layout_tables:
                        tables.append({
                            'method': 'layoutlm',
                            'data': table,
                            'confidence': table.get('confidence', 0.0)
                        })
                except Exception as e:
                    logger.warning(f"LayoutLMv3 table extraction failed: {e}")
            
            # استخراج با Donut
            if 'donut' in self.processors:
                try:
                    donut_result = self.processors['donut'].extract_table_data(page_image)
                    if donut_result['table_data']:
                        tables.append({
                            'method': 'donut',
                            'data': donut_result,
                            'confidence': donut_result.get('confidence', 0.0)
                        })
                except Exception as e:
                    logger.warning(f"Donut table extraction failed: {e}")
            
            return tables
            
        except Exception as e:
            logger.error(f"❌ Failed to extract tables: {e}")
            return []
    
    def extract_images_and_captions(self, pdf_path: str) -> List[Dict]:
        """استخراج تصاویر و تولید caption با BLIP-2"""
        try:
            # استخراج صفحات PDF
            pages = self._extract_pdf_pages(pdf_path)
            
            images_info = []
            
            for page_num, page_image in enumerate(pages):
                try:
                    # تحلیل با BLIP-2
                    if 'blip2' in self.processors:
                        caption = self.processors['blip2'].generate_caption(page_image)
                        analysis = self.processors['blip2'].analyze_image_content(page_image)
                        
                        images_info.append({
                            'page_number': page_num,
                            'caption': caption,
                            'analysis': analysis,
                            'success': True
                        })
                    else:
                        # استفاده از CLIP به عنوان جایگزین
                        if 'clip' in self.processors:
                            visual_analysis = self._analyze_page_visual_content(page_image)
                            images_info.append({
                                'page_number': page_num,
                                'caption': '',
                                'analysis': visual_analysis,
                                'success': True
                            })
                        
                except Exception as e:
                    logger.warning(f"Failed to process page {page_num}: {e}")
                    images_info.append({
                        'page_number': page_num,
                        'caption': '',
                        'analysis': {},
                        'success': False,
                        'error': str(e)
                    })
            
            return images_info
            
        except Exception as e:
            logger.error(f"❌ Failed to extract images and captions: {e}")
            return []
    
    def _extract_pdf_pages(self, pdf_path: str) -> List[Image.Image]:
        """استخراج صفحات PDF"""
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(pdf_path)
            pages = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                img_data = pix.tobytes("png")
                
                from PIL import Image
                import io
                page_image = Image.open(io.BytesIO(img_data))
                pages.append(page_image)
            
            doc.close()
            return pages
            
        except Exception as e:
            logger.error(f"❌ Failed to extract PDF pages: {e}")
            return []
    
    def _extract_pdf_page_image(self, pdf_path: str, page_num: int) -> Image.Image:
        """استخراج تصویر یک صفحه PDF"""
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
            img_data = pix.tobytes("png")
            
            from PIL import Image
            import io
            page_image = Image.open(io.BytesIO(img_data))
            
            doc.close()
            return page_image
            
        except Exception as e:
            logger.error(f"❌ Failed to extract page {page_num}: {e}")
            return Image.new('RGB', (400, 600), color='white')  # تصویر خالی
    
    def _update_processing_stats(self, success: bool, processing_time: float):
        """به‌روزرسانی آمار پردازش"""
        self.processing_stats['total_processed'] += 1
        
        if success:
            self.processing_stats['successful_processed'] += 1
        else:
            self.processing_stats['failed_processed'] += 1
        
        # محاسبه میانگین زمان پردازش
        total_time = self.processing_stats['average_processing_time'] * (self.processing_stats['total_processed'] - 1)
        self.processing_stats['average_processing_time'] = (total_time + processing_time) / self.processing_stats['total_processed']
    
    def get_system_status(self) -> Dict:
        """وضعیت سیستم"""
        return {
            'loaded_processors': list(self.processors.keys()),
            'total_processors': len(self.processors),
            'gpu_status': self.gpu_manager.get_memory_usage_summary(),
            'processing_stats': self.processing_stats,
            'configuration': {
                'enable_layoutlm': self.enable_layoutlm,
                'enable_donut': self.enable_donut,
                'enable_trocr': self.enable_trocr,
                'enable_clip': self.enable_clip,
                'enable_blip2': self.enable_blip2,
                'enable_llava': self.enable_llava
            }
        }
    
    def cleanup_resources(self):
        """پاک‌سازی منابع"""
        try:
            # حذف پردازشگرها
            for name, processor in self.processors.items():
                try:
                    processor.unload_model()
                    logger.info(f"✅ Unloaded {name} processor")
                except Exception as e:
                    logger.warning(f"Failed to unload {name} processor: {e}")
            
            self.processors.clear()
            self.loaded_models.clear()
            
            # پاک‌سازی حافظه GPU
            self.gpu_manager.cleanup_unused_models()
            
            logger.info("✅ Multimodal RAG System resources cleaned up")
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup resources: {e}")
    
    # ========== NEW: Query and Retrieval Methods ==========
    
    async def retrieve_and_answer(self, query: str, collection_name: str, 
                                top_k: int = 5, use_reranking: bool = True,
                                use_multi_hop: bool = True) -> Dict[str, Any]:
        """
        جستجو و پاسخ‌دهی با استفاده از قابلیت‌های Legacy RAG + Multimodal
        """
        try:
            logger.info(f"🔍 Multimodal Query: {query}")
            
            # استفاده از base RAG system برای جستجو و پاسخ
            result = await self.base_rag.retrieve_and_answer(
                query=query,
                collection_name=collection_name,
                top_k=top_k,
                use_reranking=use_reranking,
                use_multi_hop=use_multi_hop
            )
            
            # افزودن اطلاعات multimodal به نتیجه
            if result.get('success'):
                result['multimodal_enhanced'] = True
                result['multimodal_processors'] = list(self.processors.keys())
                result['processing_stats'] = self.processing_stats
                
                # اگر collection multimodal است، اطلاعات اضافی اضافه کن
                if collection_name in self.multimodal_collections:
                    result['multimodal_collection_info'] = self.multimodal_collections[collection_name]
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Multimodal query failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def hybrid_search(self, query: str, collection_name: str, 
                          top_k: int = 10) -> List[Dict[str, Any]]:
        """
        جستجوی ترکیبی با استفاده از Legacy RAG + Multimodal
        """
        try:
            # استفاده از base RAG system برای جستجو
            results = await self.base_rag.hybrid_search(
                query=query,
                collection_name=collection_name,
                top_k=top_k
            )
            
            # افزودن اطلاعات multimodal به نتایج
            for result in results:
                result['multimodal_enhanced'] = True
                result['multimodal_processors'] = list(self.processors.keys())
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Multimodal hybrid search failed: {e}")
            return []
    
    async def process_document_multimodal(self, file_bytes: bytes, filename: str, 
                                        collection_name: str) -> Dict[str, Any]:
        """
        پردازش سند با قابلیت‌های multimodal + Legacy RAG
        """
        try:
            logger.info(f"📄 Processing document with multimodal capabilities: {filename}")
            
            # ابتدا با Legacy RAG پردازش کن
            legacy_result = await self.base_rag.process_pdf_advanced(
                file_bytes=file_bytes,
                filename=filename,
                collection_name=collection_name
            )
            
            if not legacy_result.get('success'):
                return legacy_result
            
            # سپس پردازش multimodal اضافه کن
            multimodal_enhancements = await self._enhance_with_multimodal(
                file_bytes=file_bytes,
                filename=filename,
                collection_name=collection_name
            )
            
            # ترکیب نتایج
            enhanced_result = legacy_result.copy()
            enhanced_result['multimodal_enhancements'] = multimodal_enhancements
            enhanced_result['multimodal_enhanced'] = True
            
            # Ensure chunks are included in result
            if 'chunks' not in enhanced_result:
                enhanced_result['chunks'] = legacy_result.get('chunks', [])
            
            # ذخیره اطلاعات multimodal collection
            self.multimodal_collections[collection_name] = {
                'filename': filename,
                'processors_used': list(self.processors.keys()),
                'enhancements': multimodal_enhancements,
                'processing_time': enhanced_result.get('processing_time', 0)
            }
            
            logger.info(f"✅ Document processed with multimodal enhancements")
            return enhanced_result
            
        except Exception as e:
            logger.error(f"❌ Multimodal document processing failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _enhance_with_multimodal(self, file_bytes: bytes, filename: str, 
                                     collection_name: str) -> Dict[str, Any]:
        """
        افزودن قابلیت‌های multimodal به سند پردازش شده
        """
        try:
            enhancements = {
                'visual_analysis': {},
                'layout_analysis': {},
                'tables_extracted': [],
                'images_analyzed': [],
                'text_extraction_enhanced': {}
            }
            
            # اگر PDF است، پردازش multimodal انجام بده
            if filename.lower().endswith('.pdf'):
                # استخراج صفحات PDF
                pages = self._extract_pdf_pages_from_bytes(file_bytes)
                
                for page_num, page_image in enumerate(pages):
                    page_enhancements = await self._process_page_multimodal(
                        page_image, page_num, filename
                    )
                    
                    # ترکیب نتایج
                    for key, value in page_enhancements.items():
                        if key in enhancements:
                            if isinstance(enhancements[key], list):
                                enhancements[key].append(value)
                            else:
                                enhancements[key][f'page_{page_num}'] = value
            
            return enhancements
            
        except Exception as e:
            logger.error(f"❌ Multimodal enhancement failed: {e}")
            return {}
    
    async def _process_page_multimodal(self, page_image: Image.Image, 
                                     page_num: int, filename: str) -> Dict[str, Any]:
        """
        پردازش یک صفحه با قابلیت‌های multimodal
        """
        try:
            page_enhancements = {
                'visual_analysis': {},
                'layout_analysis': {},
                'tables_extracted': [],
                'text_extraction_enhanced': {}
            }
            
            # 1. استخراج متن با TrOCR
            if 'trocr' in self.processors:
                try:
                    text = self.processors['trocr'].extract_text_from_image(page_image)
                    page_enhancements['text_extraction_enhanced']['trocr'] = text
                except Exception as e:
                    logger.warning(f"TrOCR failed for page {page_num}: {e}")
            
            # 2. تحلیل layout با LayoutLMv3
            if 'layoutlm' in self.processors:
                try:
                    layout_result = self.processors['layoutlm'].extract_layout_structure(page_image)
                    page_enhancements['layout_analysis'] = layout_result
                except Exception as e:
                    logger.warning(f"LayoutLMv3 failed for page {page_num}: {e}")
            
            # 3. استخراج جداول با Donut
            if 'donut' in self.processors:
                try:
                    table_data = self.processors['donut'].extract_table_data(page_image)
                    if table_data.get('table_data'):
                        page_enhancements['tables_extracted'].append(table_data)
                except Exception as e:
                    logger.warning(f"Donut failed for page {page_num}: {e}")
            
            # 4. تحلیل بصری با CLIP
            if 'clip' in self.processors:
                try:
                    visual_analysis = self._analyze_page_visual_content(page_image)
                    page_enhancements['visual_analysis']['clip'] = visual_analysis
                except Exception as e:
                    logger.warning(f"CLIP failed for page {page_num}: {e}")
            
            return page_enhancements
            
        except Exception as e:
            logger.error(f"❌ Failed to process page {page_num} with multimodal: {e}")
            return {}
    
    def _extract_pdf_pages_from_bytes(self, file_bytes: bytes) -> List[Image.Image]:
        """استخراج صفحات PDF از bytes"""
        try:
            import fitz  # PyMuPDF
            import io
            
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            pages = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                img_data = pix.tobytes("png")
                
                page_image = Image.open(io.BytesIO(img_data))
                pages.append(page_image)
            
            doc.close()
            return pages
            
        except Exception as e:
            logger.error(f"❌ Failed to extract PDF pages from bytes: {e}")
            return []
    
    def get_multimodal_collections(self) -> List[str]:
        """لیست collections با قابلیت‌های multimodal"""
        return list(self.multimodal_collections.keys())
    
    def get_collection_multimodal_info(self, collection_name: str) -> Dict[str, Any]:
        """اطلاعات multimodal یک collection"""
        return self.multimodal_collections.get(collection_name, {})
    
    # ========================================================
    
    def __del__(self):
        """Destructor"""
        try:
            self.cleanup_resources()
        except:
            pass
