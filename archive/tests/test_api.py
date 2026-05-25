# -*- coding: utf-8 -*-
"""
Ultimate RAG API Test Client
کلاینت تست برای Ultimate RAG API
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any, List
import os

class UltimateRAGAPIClient:
    """کلاینت API برای Ultimate RAG System"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 minutes timeout
    
    async def health_check(self) -> Dict[str, Any]:
        """بررسی سلامت سیستم"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def get_system_status(self) -> Dict[str, Any]:
        """دریافت وضعیت سیستم"""
        try:
            response = await self.client.get(f"{self.base_url}/status")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def upload_pdf(self, file_path: str, collection_name: str, 
                        chunk_size: int = 500, enable_multimodal: bool = True) -> Dict[str, Any]:
        """آپلود و پردازش فایل PDF"""
        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                data = {
                    "collection_name": collection_name,
                    "chunk_size": chunk_size,
                    "enable_multimodal": enable_multimodal
                }
                
                response = await self.client.post(
                    f"{self.base_url}/upload/pdf",
                    files=files,
                    data=data
                )
                return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def upload_excel(self, file_path: str, collection_name: str, 
                          chunk_size: int = 500) -> Dict[str, Any]:
        """آپلود و پردازش فایل Excel"""
        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                data = {
                    "collection_name": collection_name,
                    "chunk_size": chunk_size
                }
                
                response = await self.client.post(
                    f"{self.base_url}/upload/excel",
                    files=files,
                    data=data
                )
                return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def query(self, query: str, collection_name: str, 
                   top_k: int = 5, use_reranking: bool = True, 
                   use_multi_hop: bool = True, temperature: float = 0.1) -> Dict[str, Any]:
        """پرس و جو از سیستم"""
        try:
            data = {
                "query": query,
                "collection_name": collection_name,
                "top_k": top_k,
                "use_reranking": use_reranking,
                "use_multi_hop": use_multi_hop,
                "temperature": temperature,
                "stream": False
            }
            
            response = await self.client.post(
                f"{self.base_url}/query",
                json=data
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def get_collections(self) -> List[str]:
        """دریافت لیست کالکشن‌ها"""
        try:
            response = await self.client.get(f"{self.base_url}/collections")
            return response.json()
        except Exception as e:
            return []
    
    async def create_chat_session(self, collection_name: str) -> Dict[str, str]:
        """ایجاد جلسه چت"""
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/sessions",
                params={"collection_name": collection_name}
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def send_chat_message(self, session_id: str, message: str, 
                               collection_name: str, top_k: int = 5) -> Dict[str, Any]:
        """ارسال پیام در چت"""
        try:
            data = {
                "message": message,
                "query": {
                    "query": message,
                    "collection_name": collection_name,
                    "top_k": top_k,
                    "use_reranking": True,
                    "use_multi_hop": True
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/chat/sessions/{session_id}/messages",
                json=data
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def test_queries(self, collection_name: str, 
                          test_queries: List[str] = None) -> Dict[str, Any]:
        """تست پرس و جوها"""
        try:
            if test_queries is None:
                test_queries = [
                    "بند چهارم توی این جدول چیه؟",
                    "جمع کل مالیات مشاغل چقدره؟",
                    "برآورد درآمدهای مالیاتی در بخش ملی و استانی چقدر است؟"
                ]
            
            data = {
                "collection_name": collection_name,
                "test_queries": test_queries
            }
            
            response = await self.client.post(
                f"{self.base_url}/test/query",
                json=data
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def get_multimodal_status(self) -> Dict[str, Any]:
        """وضعیت multimodal processing"""
        try:
            response = await self.client.get(f"{self.base_url}/features/multimodal/status")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def get_self_rag_status(self) -> Dict[str, Any]:
        """وضعیت Self-RAG"""
        try:
            response = await self.client.get(f"{self.base_url}/features/self-rag/status")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def get_corrective_rag_status(self) -> Dict[str, Any]:
        """وضعیت Corrective RAG"""
        try:
            response = await self.client.get(f"{self.base_url}/features/corrective-rag/status")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def close(self):
        """بستن کلاینت"""
        await self.client.aclose()


async def test_complete_workflow():
    """تست کامل workflow سیستم"""
    print("🚀 Starting Ultimate RAG API Test...")
    
    client = UltimateRAGAPIClient()
    
    try:
        # 1. Health Check
        print("\n1️⃣ Health Check...")
        health = await client.health_check()
        print(f"Health Status: {health.get('status', 'unknown')}")
        
        # 2. System Status
        print("\n2️⃣ System Status...")
        status = await client.get_system_status()
        print(f"System Status: {status.get('status', 'unknown')}")
        print(f"Features: {status.get('features', {})}")
        
        # 3. Multimodal Status
        print("\n3️⃣ Multimodal Status...")
        multimodal = await client.get_multimodal_status()
        print(f"Multimodal Enabled: {multimodal.get('enabled', False)}")
        print(f"Processors: {multimodal.get('processors', {})}")
        
        # 4. Self-RAG Status
        print("\n4️⃣ Self-RAG Status...")
        self_rag = await client.get_self_rag_status()
        print(f"Self-RAG Enabled: {self_rag.get('enabled', False)}")
        print(f"Reflection Count: {self_rag.get('reflection_count', 0)}")
        
        # 5. Corrective RAG Status
        print("\n5️⃣ Corrective RAG Status...")
        corrective_rag = await client.get_corrective_rag_status()
        print(f"Corrective RAG Enabled: {corrective_rag.get('enabled', False)}")
        print(f"Error Detection Count: {corrective_rag.get('error_detection_count', 0)}")
        
        # 6. Get Collections
        print("\n6️⃣ Collections...")
        collections = await client.get_collections()
        print(f"Available Collections: {collections}")
        
        # 7. Test Query (if collections exist)
        if collections:
            collection_name = collections[0]
            print(f"\n7️⃣ Testing Query on Collection: {collection_name}")
            
            test_query = "بند چهارم توی این جدول چیه؟"
            print(f"Query: {test_query}")
            
            start_time = time.time()
            result = await client.query(
                query=test_query,
                collection_name=collection_name,
                top_k=5,
                use_reranking=True,
                use_multi_hop=True
            )
            processing_time = time.time() - start_time
            
            if result.get("success"):
                print(f"✅ Query successful!")
                print(f"Answer: {result.get('answer', 'N/A')[:100]}...")
                print(f"Confidence: {result.get('confidence', 0):.4f}")
                print(f"Processing Time: {processing_time:.2f}s")
                print(f"Used Features: {result.get('used_features', {})}")
            else:
                print(f"❌ Query failed: {result.get('error', 'Unknown error')}")
        
        # 8. Test Chat Session
        if collections:
            print(f"\n8️⃣ Testing Chat Session...")
            session = await client.create_chat_session(collections[0])
            if session.get("session_id"):
                print(f"Chat Session Created: {session['session_id']}")
                
                # Send a message
                chat_result = await client.send_chat_message(
                    session_id=session["session_id"],
                    message="سلام، چطور می‌تونم کمکتون کنم؟",
                    collection_name=collections[0]
                )
                
                if chat_result.get("success"):
                    print("✅ Chat message sent successfully!")
                else:
                    print(f"❌ Chat failed: {chat_result.get('error', 'Unknown error')}")
        
        print("\n🎉 Ultimate RAG API Test Completed Successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    finally:
        await client.close()


async def test_file_upload():
    """تست آپلود فایل"""
    print("📤 Testing File Upload...")
    
    client = UltimateRAGAPIClient()
    
    try:
        # Test PDF upload (if file exists)
        pdf_path = "/home/user01/qwen-api/enhanced_rag_system/jadval5-bodje.pdf"
        if os.path.exists(pdf_path):
            print(f"Uploading PDF: {pdf_path}")
            
            result = await client.upload_pdf(
                file_path=pdf_path,
                collection_name="test_collection",
                chunk_size=500,
                enable_multimodal=True
            )
            
            if result.get("success"):
                print(f"✅ PDF uploaded successfully!")
                print(f"Filename: {result.get('filename')}")
                print(f"Collection: {result.get('collection')}")
                print(f"Chunks: {result.get('chunks_count')}")
                print(f"Processing Time: {result.get('processing_time'):.2f}s")
            else:
                print(f"❌ PDF upload failed: {result.get('error')}")
        else:
            print("⚠️ PDF file not found for testing")
    
    except Exception as e:
        print(f"❌ File upload test failed: {e}")
    
    finally:
        await client.close()


if __name__ == "__main__":
    print("🧪 Ultimate RAG API Test Suite")
    print("=" * 50)
    
    # Run complete workflow test
    asyncio.run(test_complete_workflow())
    
    print("\n" + "=" * 50)
    
    # Run file upload test
    asyncio.run(test_file_upload())

