# -*- coding: utf-8 -*-
"""
OCR Engine for Multimodal RAG System
موتور OCR برای استخراج متن و bounding boxes از تصاویر
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from PIL import Image
import torch
from loguru import logger

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logger.warning("EasyOCR not available. Install with: pip install easyocr")

try:
    import paddleocr
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    logger.warning("PaddleOCR not available. Install with: pip install paddlepaddle paddleocr")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("Tesseract not available. Install with: pip install pytesseract")

class OCREngine:
    """موتور OCR برای استخراج متن و bounding boxes"""
    
    def __init__(
        self,
        engine: str = "auto",  # "easyocr", "paddleocr", "tesseract", "auto"
        languages: List[str] = None,
        use_gpu: bool = True,
        confidence_threshold: float = 0.5
    ):
        self.engine = engine
        self.languages = languages or ["en", "fa"]  # English and Persian
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.confidence_threshold = confidence_threshold
        
        # Initialize OCR engines
        self.easyocr_reader = None
        self.paddleocr_reader = None
        
        self._initialize_engines()
    
    def _initialize_engines(self):
        """مقداردهی اولیه موتورهای OCR"""
        try:
            if self.engine == "auto":
                # Auto-select best available engine
                if EASYOCR_AVAILABLE and self.use_gpu:
                    self.engine = "easyocr"
                    self._init_easyocr()
                elif PADDLEOCR_AVAILABLE:
                    self.engine = "paddleocr"
                    self._init_paddleocr()
                elif TESSERACT_AVAILABLE:
                    self.engine = "tesseract"
                else:
                    raise RuntimeError("No OCR engine available")
            
            elif self.engine == "easyocr" and EASYOCR_AVAILABLE:
                self._init_easyocr()
            elif self.engine == "paddleocr" and PADDLEOCR_AVAILABLE:
                self._init_paddleocr()
            elif self.engine == "tesseract" and TESSERACT_AVAILABLE:
                pass  # Tesseract doesn't need initialization
            else:
                raise RuntimeError(f"OCR engine '{self.engine}' not available")
            
            logger.info(f"✅ OCR Engine initialized: {self.engine}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize OCR engine: {e}")
            raise
    
    def _init_easyocr(self):
        """مقداردهی EasyOCR"""
        try:
            self.easyocr_reader = easyocr.Reader(
                self.languages,
                gpu=self.use_gpu,
                verbose=False
            )
            logger.info("✅ EasyOCR initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize EasyOCR: {e}")
            raise
    
    def _init_paddleocr(self):
        """مقداردهی PaddleOCR"""
        try:
            self.paddleocr_reader = paddleocr.PaddleOCR(
                use_angle_cls=True,
                lang='en',
                use_gpu=self.use_gpu,
                show_log=False
            )
            logger.info("✅ PaddleOCR initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize PaddleOCR: {e}")
            raise
    
    def extract_text_and_boxes(
        self, 
        image: Union[Image.Image, str, np.ndarray]
    ) -> Tuple[List[str], List[List[int]]]:
        """استخراج متن و bounding boxes از تصویر"""
        try:
            # Convert image to numpy array
            if isinstance(image, str):
                image = Image.open(image)
            elif isinstance(image, Image.Image):
                image = np.array(image)
            elif not isinstance(image, np.ndarray):
                raise ValueError(f"Unsupported image type: {type(image)}")
            
            # Ensure image is in RGB format
            if len(image.shape) == 3 and image.shape[2] == 3:
                # Convert RGB to BGR for OpenCV compatibility
                try:
                    if hasattr(cv2, 'cvtColor'):
                        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                    else:
                        # Fallback: manual conversion
                        image = image[:, :, ::-1]
                except Exception as e:
                    logger.warning(f"OpenCV color conversion failed: {e}, using manual conversion")
                    image = image[:, :, ::-1]  # Manual RGB to BGR conversion
            
            # Extract text and boxes based on engine
            if self.engine == "easyocr":
                return self._extract_with_easyocr(image)
            elif self.engine == "paddleocr":
                return self._extract_with_paddleocr(image)
            elif self.engine == "tesseract":
                return self._extract_with_tesseract(image)
            else:
                raise RuntimeError(f"Unknown OCR engine: {self.engine}")
                
        except Exception as e:
            logger.error(f"❌ Failed to extract text and boxes: {e}")
            return [], []
    
    def _extract_with_easyocr(self, image: np.ndarray) -> Tuple[List[str], List[List[int]]]:
        """استخراج با EasyOCR"""
        try:
            results = self.easyocr_reader.readtext(image)
            
            words = []
            boxes = []
            
            for (bbox, text, confidence) in results:
                if confidence >= self.confidence_threshold:
                    # Convert bbox to [x1, y1, x2, y2] format
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                    
                    box = [
                        int(min(x_coords)),  # x1
                        int(min(y_coords)),  # y1
                        int(max(x_coords)),  # x2
                        int(max(y_coords))   # y2
                    ]
                    
                    words.append(text.strip())
                    boxes.append(box)
            
            logger.debug(f"EasyOCR extracted {len(words)} words")
            return words, boxes
            
        except Exception as e:
            logger.error(f"❌ EasyOCR extraction failed: {e}")
            return [], []
    
    def _extract_with_paddleocr(self, image: np.ndarray) -> Tuple[List[str], List[List[int]]]:
        """استخراج با PaddleOCR"""
        try:
            results = self.paddleocr_reader.ocr(image, cls=True)
            
            words = []
            boxes = []
            
            if results and results[0]:
                for line in results[0]:
                    if line and len(line) >= 2:
                        bbox = line[0]
                        text_info = line[1]
                        
                        if len(text_info) >= 2:
                            text = text_info[0]
                            confidence = text_info[1]
                            
                            if confidence >= self.confidence_threshold:
                                # Convert bbox to [x1, y1, x2, y2] format
                                x_coords = [point[0] for point in bbox]
                                y_coords = [point[1] for point in bbox]
                                
                                box = [
                                    int(min(x_coords)),  # x1
                                    int(min(y_coords)),  # y1
                                    int(max(x_coords)),  # x2
                                    int(max(y_coords))   # y2
                                ]
                                
                                words.append(text.strip())
                                boxes.append(box)
            
            logger.debug(f"PaddleOCR extracted {len(words)} words")
            return words, boxes
            
        except Exception as e:
            logger.error(f"❌ PaddleOCR extraction failed: {e}")
            return [], []
    
    def _extract_with_tesseract(self, image: np.ndarray) -> Tuple[List[str], List[List[int]]]:
        """استخراج با Tesseract"""
        try:
            # Get detailed data from Tesseract
            data = pytesseract.image_to_data(
                image, 
                output_type=pytesseract.Output.DICT,
                lang='eng+fas'  # English + Persian
            )
            
            words = []
            boxes = []
            
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                text = data['text'][i].strip()
                conf = int(data['conf'][i])
                
                if conf > self.confidence_threshold * 100 and text:  # Tesseract confidence is 0-100
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    
                    box = [x, y, x + w, y + h]
                    
                    words.append(text)
                    boxes.append(box)
            
            logger.debug(f"Tesseract extracted {len(words)} words")
            return words, boxes
            
        except Exception as e:
            logger.error(f"❌ Tesseract extraction failed: {e}")
            return [], []
    
    def extract_text_only(self, image: Union[Image.Image, str, np.ndarray]) -> str:
        """استخراج فقط متن بدون bounding boxes"""
        words, _ = self.extract_text_and_boxes(image)
        return " ".join(words)
    
    def get_engine_info(self) -> Dict:
        """اطلاعات موتور OCR"""
        return {
            'engine': self.engine,
            'languages': self.languages,
            'use_gpu': self.use_gpu,
            'confidence_threshold': self.confidence_threshold,
            'available_engines': {
                'easyocr': EASYOCR_AVAILABLE,
                'paddleocr': PADDLEOCR_AVAILABLE,
                'tesseract': TESSERACT_AVAILABLE
            }
        }
    
    def test_engine(self) -> bool:
        """تست عملکرد موتور OCR"""
        try:
            # Create a simple test image
            test_image = np.ones((100, 300, 3), dtype=np.uint8) * 255
            cv2.putText(test_image, "Test Text", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            
            words, boxes = self.extract_text_and_boxes(test_image)
            
            logger.info(f"✅ OCR Engine test completed. Extracted: {words}")
            return len(words) > 0
            
        except Exception as e:
            logger.error(f"❌ OCR Engine test failed: {e}")
            return False

# Global instance
ocr_engine = OCREngine()

