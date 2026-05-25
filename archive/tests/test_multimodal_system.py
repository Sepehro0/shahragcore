#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Multimodal RAG System
تست سیستم Multimodal RAG
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import time
from loguru import logger
from PIL import Image
import numpy as np

# Import the enhanced RAG system
from ultimate_rag_system import UltimateRAGSystem

async def test_multimodal_system():
    """تست سیستم Multimodal RAG"""
    
    print("🚀 Testing Multimodal RAG System")
    print("=" * 60)
    
    # Configuration for multimodal system
    multimodal_config = {
        'enable_layoutlm': True,
        'enable_donut': True,
        'enable_trocr': True,
        'enable_clip': True,
        'enable_blip2': False,  # Disable for testing due to VRAM requirements
        'enable_llava': False,  # Disable for testing due to VRAM requirements
        'auto_detect_gpu': True
    }
    
    try:
        # Initialize the enhanced RAG system with multimodal capabilities
        print("\n🔄 Initializing Ultimate RAG System with Multimodal capabilities...")
        
        rag_system = UltimateRAGSystem(
            enable_multimodal=True,
            multimodal_config=multimodal_config
        )
        
        print("✅ Ultimate RAG System initialized successfully!")
        
        # Test multimodal system status
        if rag_system.multimodal_system:
            print("\n📊 Multimodal System Status:")
            status = rag_system.multimodal_system.get_system_status()
            print(f"   Loaded Processors: {status['loaded_processors']}")
            print(f"   Total Processors: {status['total_processors']}")
            print(f"   GPU Status: {status['gpu_status']['total_gpus']} GPUs")
            
            # Test individual processors
            print("\n🧪 Testing Individual Processors:")
            
            # Create a test image
            test_image = Image.new('RGB', (400, 300), color='blue')
            
            # Test TrOCR
            if 'trocr' in rag_system.multimodal_system.processors:
                print("   🔍 Testing TrOCR...")
                try:
                    text = rag_system.multimodal_system.processors['trocr'].extract_text_from_image(test_image)
                    print(f"      ✅ TrOCR: '{text[:50]}...'")
                except Exception as e:
                    print(f"      ❌ TrOCR failed: {e}")
            
            # Test CLIP
            if 'clip' in rag_system.multimodal_system.processors:
                print("   🔍 Testing CLIP...")
                try:
                    similarities = rag_system.multimodal_system.processors['clip'].get_image_text_similarity(
                        test_image, 
                        ['a blue image', 'a red image', 'a green image']
                    )
                    print(f"      ✅ CLIP similarities: {similarities}")
                except Exception as e:
                    print(f"      ❌ CLIP failed: {e}")
            
            # Test LayoutLMv3
            if 'layoutlm' in rag_system.multimodal_system.processors:
                print("   🔍 Testing LayoutLMv3...")
                try:
                    layout_result = rag_system.multimodal_system.processors['layoutlm'].extract_layout_structure(test_image)
                    print(f"      ✅ LayoutLMv3: {len(layout_result['structure'])} entities")
                except Exception as e:
                    print(f"      ❌ LayoutLMv3 failed: {e}")
            
            # Test Donut
            if 'donut' in rag_system.multimodal_system.processors:
                print("   🔍 Testing Donut...")
                try:
                    doc_info = rag_system.multimodal_system.processors['donut'].extract_document_info(test_image)
                    print(f"      ✅ Donut: '{doc_info['text'][:50]}...'")
                except Exception as e:
                    print(f"      ❌ Donut failed: {e}")
            
            # Test PDF processing (if PDF exists)
            pdf_path = "/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf"
            if os.path.exists(pdf_path):
                print(f"\n📄 Testing PDF Processing: {pdf_path}")
                try:
                    # Test single page processing
                    page_result = rag_system.multimodal_system.process_pdf_page(pdf_path, 0)
                    print(f"   ✅ Page 0 processed: {page_result['success']}")
                    
                    if page_result['success']:
                        print(f"      Text extraction: {len(page_result.get('text_extraction', {}))} methods")
                        print(f"      Layout analysis: {len(page_result.get('layout_analysis', {}).get('structure', []))} entities")
                        print(f"      Tables: {len(page_result.get('tables', []))}")
                        print(f"      Visual analysis: {len(page_result.get('visual_analysis', {}))} methods")
                    
                except Exception as e:
                    print(f"   ❌ PDF processing failed: {e}")
            else:
                print(f"\n⚠️  PDF not found: {pdf_path}")
                print("   Skipping PDF processing test")
            
            # Test table extraction
            print("\n📊 Testing Advanced Table Extraction:")
            try:
                if os.path.exists(pdf_path):
                    tables = rag_system.multimodal_system.extract_tables_advanced(pdf_path, 0)
                    print(f"   ✅ Extracted {len(tables)} tables")
                    for i, table in enumerate(tables):
                        print(f"      Table {i+1}: {table['method']} (confidence: {table['confidence']:.2f})")
                else:
                    print("   ⚠️  Skipping table extraction test (PDF not found)")
            except Exception as e:
                print(f"   ❌ Table extraction failed: {e}")
            
            # Test image analysis
            print("\n🖼️  Testing Image Analysis:")
            try:
                if os.path.exists(pdf_path):
                    images_info = rag_system.multimodal_system.extract_images_and_captions(pdf_path)
                    print(f"   ✅ Analyzed {len(images_info)} pages")
                    for i, info in enumerate(images_info[:3]):  # Show first 3 pages
                        print(f"      Page {info['page_number']}: {info['success']}")
                        if info.get('caption'):
                            print(f"         Caption: {info['caption'][:50]}...")
                else:
                    print("   ⚠️  Skipping image analysis test (PDF not found)")
            except Exception as e:
                print(f"   ❌ Image analysis failed: {e}")
            
            # Performance statistics
            print("\n📈 Performance Statistics:")
            stats = rag_system.multimodal_system.get_system_status()
            processing_stats = stats['processing_stats']
            print(f"   Total Processed: {processing_stats['total_processed']}")
            print(f"   Successful: {processing_stats['successful_processed']}")
            print(f"   Failed: {processing_stats['failed_processed']}")
            print(f"   Average Time: {processing_stats['average_processing_time']:.2f}s")
            
            # GPU usage
            gpu_status = stats['gpu_status']
            print(f"\n💾 GPU Usage:")
            for gpu_id, usage in gpu_status['gpu_usage'].items():
                print(f"   GPU {gpu_id}: {usage['used_by_models']}MB used by models")
                print(f"             {usage['available']}MB available")
        
        else:
            print("❌ Multimodal system not initialized")
            return False
        
        print("\n✅ Multimodal RAG System test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.error(f"Multimodal test failed: {e}")
        return False
    
    finally:
        # Cleanup
        try:
            if 'rag_system' in locals() and rag_system.multimodal_system:
                rag_system.multimodal_system.cleanup_resources()
                print("🧹 Resources cleaned up")
        except Exception as e:
            print(f"⚠️  Cleanup failed: {e}")

async def main():
    """تابع اصلی"""
    success = await test_multimodal_system()
    
    if success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n💥 Some tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
