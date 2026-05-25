# -*- coding: utf-8 -*-
"""
تست ساده برای بررسی اصلاحات
"""

import asyncio
import sys
import logging

sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system")

from ultimate_rag_system import UltimateRAGSystem

# تنظیم logging برای مشاهده همه چیز
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """تست ساده"""
    
    print("\n" + "=" * 80)
    print("🚀 SIMPLE TEST: Domain-Aware RAG")
    print("=" * 80 + "\n")
    
    # Initialize RAG
    rag = UltimateRAGSystem()
    
    # فایل تست
    pdf_path = "/home/user01/qwen-api/enhanced_rag_system/a-practical-guide-to-building-agents.pdf"
    collection_name = "test_simple_rag"
    
    try:
        # بارگذاری فایل
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        print(f"\n📄 File loaded: {len(pdf_bytes)} bytes\n")
        
        # حذف collection قدیمی
        try:
            rag.chroma_client.delete_collection(collection_name)
            print("🗑️  Old collection deleted\n")
        except:
            print("ℹ️  No old collection\n")
        
        # پردازش PDF
        print("=" * 80)
        print("STEP 1: PDF Processing")
        print("=" * 80 + "\n")
        
        result = await rag.process_pdf_advanced(
            file_bytes=pdf_bytes,
            filename="a-practical-guide-to-building-agents.pdf",
            collection_name=collection_name
        )
        
        if not result.get("success"):
            print(f"\n❌ Processing failed: {result.get('error')}\n")
            return
        
        print(f"\n✅ Document processed successfully!")
        print(f"   Total chunks: {result.get('chunks_count', 0)}\n")
        
        # بررسی نوع chunks
        print("=" * 80)
        print("STEP 2: Chunk Analysis")
        print("=" * 80 + "\n")
        
        col = rag.chroma_client.get_collection(collection_name)
        all_data = col.get()
        
        text_chunks = sum(1 for meta in all_data['metadatas'] if meta.get('type') == 'text_content')
        table_chunks = sum(1 for meta in all_data['metadatas'] if meta.get('type') != 'text_content')
        
        print(f"📊 Chunk Analysis:")
        print(f"   Total chunks: {len(all_data['ids'])}")
        print(f"   Text chunks: {text_chunks}")
        print(f"   Table/Structure chunks: {table_chunks}\n")
        
        if text_chunks > 0 and table_chunks > 0:
            print("✅ SUCCESS: Both text AND tables extracted!\n")
        elif text_chunks > 0:
            print("✅ SUCCESS: Text extracted (no tables in this PDF)\n")
        elif table_chunks > 0:
            print("⚠️  WARNING: Only tables extracted\n")
        else:
            print("❌ ERROR: No chunks extracted!\n")
        
        # Domain Detection
        print("=" * 80)
        print("STEP 3: Domain Detection")
        print("=" * 80 + "\n")
        
        domain_info = rag.get_collection_domain(collection_name)
        
        print(f"📂 Domain Information:")
        print(f"   Domain: {domain_info['domain']}")
        print(f"   Confidence: {domain_info['confidence']:.2f}")
        print(f"   Method: {domain_info['method']}")
        print(f"   Keywords: {', '.join(domain_info.get('keywords', [])[:5])}")
        print(f"   Summary: {domain_info.get('summary', 'N/A')[:150]}\n")
        
        if domain_info['domain'] in ['educational', 'technical']:
            print("✅ SUCCESS: Domain correctly detected!\n")
        elif domain_info['domain'] == 'general':
            print("⚠️  OK: Domain detected as 'general' (acceptable)\n")
        else:
            print(f"❌ ERROR: Domain incorrectly detected as '{domain_info['domain']}'\n")
        
        # تست یک Query ساده (بدون LLM)
        print("=" * 80)
        print("STEP 4: Simple Retrieval Test (No LLM)")
        print("=" * 80 + "\n")
        
        query = "agent چیست؟"
        print(f"Query: {query}\n")
        
        # فقط retrieval، بدون generation
        results = col.query(
            query_texts=[query],
            n_results=3
        )
        
        print(f"📊 Retrieved {len(results['documents'][0])} relevant chunks:\n")
        
        for i, (doc, meta) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
            print(f"   [{i}] Type: {meta.get('type', 'unknown')}")
            print(f"       Content: {doc[:100]}...\n")
        
        # خلاصه نهایی
        print("\n" + "=" * 80)
        print("FINAL SUMMARY")
        print("=" * 80 + "\n")
        
        status_items = []
        
        if result.get('success'):
            status_items.append("✅ PDF Processing: SUCCESS")
        else:
            status_items.append("❌ PDF Processing: FAILED")
        
        if text_chunks > 0:
            status_items.append("✅ Text Extraction: SUCCESS")
        else:
            status_items.append("❌ Text Extraction: FAILED")
        
        if domain_info['domain'] in ['educational', 'technical', 'general']:
            status_items.append(f"✅ Domain Detection: {domain_info['domain']} ({domain_info['method']})")
        else:
            status_items.append(f"❌ Domain Detection: {domain_info['domain']}")
        
        for item in status_items:
            print(f"   {item}")
        
        print("\n" + "=" * 80)
        print("✅ TEST COMPLETE")
        print("=" * 80 + "\n")
        
    except FileNotFoundError:
        print(f"\n❌ File not found: {pdf_path}\n")
    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

