# -*- coding: utf-8 -*-
"""
Collection Management Endpoints
"""

import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Request
from typing import Optional, TYPE_CHECKING

from api.v1.schemas.collection_schemas import (
    CreateCollectionRequest, CreateCollectionResponse,
    UpdateSystemPromptRequest, UpdateSystemPromptResponse,
    UpdateCollectionConfigRequest, UpdateCollectionConfigResponse,
    QueryCollectionRequest, QueryCollectionResponse,
    AddDocumentsRequest, AddDocumentsResponse,
    SearchDocumentsRequest, SearchDocumentsResponse,
    ListCollectionsResponse,
    GetCollectionInfoResponse,
    DeleteCollectionRequest, DeleteCollectionResponse,
    FileType
)

if TYPE_CHECKING:
    from api.v1.services.collection_manager import CollectionManager
    from api.v1.services.file_processor import FileProcessor
    from ultimate_rag_system import UltimateRAGSystem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collections", tags=["Collections API V1"])


# Dependency to get services
def get_collection_manager():
    """Get collection manager instance"""
    from api.v1.services.collection_manager import CollectionManager
    return CollectionManager()


def get_file_processor():
    """Get file processor instance"""
    from api.v1.services.file_processor import FileProcessor
    from api.v1.services.collection_manager import CollectionManager
    
    collection_manager = CollectionManager()
    return FileProcessor(collection_manager=collection_manager)


def get_rag_system():
    """Get the singleton RAG system from api_server (avoids loading a second heavy instance)."""
    try:
        import api_server
        return api_server.get_rag_system()
    except Exception:
        # Fallback: create a local instance if api_server isn't available
        from ultimate_rag_system import UltimateRAGSystem
        return UltimateRAGSystem()


# ==================== COLLECTION MANAGEMENT ====================

@router.post("", response_model=CreateCollectionResponse)
async def create_collection(
    request: CreateCollectionRequest,
    collection_manager = Depends(get_collection_manager)
):
    """
    ساخت کالکشن جدید
    
    - **collection_name**: نام یکتا کالکشن (lowercase, a-z, 0-9, _)
    - **display_name**: نام نمایشی (فارسی/انگلیسی)
    - **collection_type**: نوع کالکشن (qa, sales_support, ...)
    - **processing_mode**: حالت پردازش (rag_only, database_first, hybrid)
    - **system_prompt**: پرامپت سیستم (اختیاری)
    """
    try:
        result = collection_manager.create_collection(
            collection_name=request.collection_name,
            display_name=request.display_name,
            collection_type=request.collection_type.value,
            processing_mode=request.processing_mode.value,
            description=request.description,
            system_prompt=request.system_prompt,
            metadata=request.metadata
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to create collection"))
        
        return CreateCollectionResponse(**result)
        
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=ListCollectionsResponse)
async def list_collections(
    request: Request,
    collection_manager = Depends(get_collection_manager)
):
    """لیست تمام کالکشن‌ها"""
    try:
        result = collection_manager.list_collections()
        try:
            import api_server
            token_fp = getattr(request.state, "auth_token_fp", None)
            is_admin = bool(getattr(request.state, "is_admin", False))
            if api_server.REQUIRE_COLLECTION_ACL and token_fp and not is_admin:
                filtered = []
                for item in result.get("collections", []):
                    cname = item.get("collection_name")
                    if cname and api_server.acl_can_access_collection_by_fingerprint(
                        token_fp, cname, is_admin=False, allow_unowned=False
                    ):
                        filtered.append(item)
                result["collections"] = filtered
                result["total_count"] = len(filtered)
        except Exception:
            pass
        return ListCollectionsResponse(**result)
        
    except Exception as e:
        logger.error(f"Error listing collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{collection_name}", response_model=GetCollectionInfoResponse)
async def get_collection_info(
    collection_name: str,
    collection_manager = Depends(get_collection_manager)
):
    """اطلاعات کامل یک کالکشن"""
    try:
        result = collection_manager.get_collection_info(collection_name)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "Collection not found"))
        
        return GetCollectionInfoResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collection info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{collection_name}/system-prompt", response_model=UpdateSystemPromptResponse)
async def update_system_prompt(
    collection_name: str,
    request: UpdateSystemPromptRequest,
    collection_manager = Depends(get_collection_manager)
):
    """بروزرسانی پرامپت سیستم کالکشن"""
    try:
        result = collection_manager.update_system_prompt(
            collection_name=collection_name,
            system_prompt=request.system_prompt,
            examples=request.examples
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to update system prompt"))
        
        return UpdateSystemPromptResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating system prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{collection_name}/config", response_model=UpdateCollectionConfigResponse)
async def update_collection_config(
    collection_name: str,
    request: UpdateCollectionConfigRequest,
    collection_manager = Depends(get_collection_manager)
):
    """بروزرسانی تنظیمات کالکشن"""
    try:
        result = collection_manager.update_collection_config(
            collection_name=collection_name,
            display_name=request.display_name,
            description=request.description,
            system_prompt=request.system_prompt,
            out_of_scope_response=request.out_of_scope_response,
            retrieval_config=request.retrieval_config,
            generation_config=request.generation_config,
            metadata=request.metadata,
            aggregation_config=request.aggregation_config,
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to update config"))
        
        return UpdateCollectionConfigResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{collection_name}", response_model=DeleteCollectionResponse)
async def delete_collection(
    collection_name: str,
    request: DeleteCollectionRequest,
    collection_manager = Depends(get_collection_manager)
):
    """حذف کالکشن"""
    try:
        result = collection_manager.delete_collection(
            collection_name=collection_name,
            confirm=request.confirm
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to delete collection"))
        
        return DeleteCollectionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== FILE UPLOAD & PROCESSING ====================

@router.post("/{collection_name}/upload")
async def upload_file(
    collection_name: str,
    file: UploadFile = File(...),
    file_type: FileType = Form(...),
    chunk_size: int = Form(500),
    chunk_overlap: int = Form(50),
    extract_tables: bool = Form(True),
    system_prompt: Optional[str] = Form(None),
    display_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
):
    """
    آپلود و پردازش فایل (async job queue)

    پردازش در پس‌زمینه انجام می‌شود. از job_id برگشتی برای poll وضعیت در
    /jobs/{job_id} استفاده کنید.

    - **file**: فایل برای آپلود
    - **file_type**: نوع فایل (pdf, excel, csv, text, word, json)
    - **chunk_size**: اندازه chunk (100-2000)
    - **chunk_overlap**: همپوشانی chunk (0-500)
    - **extract_tables**: استخراج جداول (برای PDF/Excel)
    """
    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        filename = file.filename or "upload"
        ftype = file_type.value

        # ── Enqueue the job (returns immediately) ────────────────────────
        try:
            # Access the shared queue that api_server.py registered
            from api.shared_job_queue import get_queue, get_job_store, register_job
            queue = get_queue()
            job_store = get_job_store()
            estimate_time = max(10, len(file_bytes) // 50_000)   # rough estimate
            job_id = register_job(
                collection=collection_name,
                filenames=[filename],
                queue_length=queue.qsize(),
                estimate_time=estimate_time,
            )
        except Exception as queue_err:
            logger.warning(f"Shared queue unavailable, falling back to sync processing: {queue_err}")
            job_id = None
            queue = None
            job_store = None

        if queue is not None:
            _captured_bytes = file_bytes
            _captured_filename = filename
            _captured_collection = collection_name
            _captured_ftype = ftype

            async def _file_handler():
                try:
                    if _captured_ftype == "pdf":
                        from processors.smart_persian_pdf_processor import SmartPersianPDFProcessor
                        processor = SmartPersianPDFProcessor(
                            chunk_size=chunk_size,
                            chunk_overlap=chunk_overlap,
                        )
                        result = processor.build_collection_from_files(
                            pdf_files=[{"bytes": _captured_bytes, "filename": _captured_filename, "metadata": {}}],
                            collection_name=_captured_collection,
                            collection_metadata={
                                **({"display_name": display_name} if display_name else {}),
                                **({"description": description} if description else {}),
                            },
                            overwrite=False,
                            append=True,
                        )
                    else:
                        # Non-PDF: use FileProcessor (now async)
                        import tempfile, os
                        from api.v1.services.file_processor import FileProcessor
                        from api.v1.services.collection_manager import CollectionManager
                        fp = FileProcessor(collection_manager=CollectionManager())
                        with tempfile.NamedTemporaryFile(suffix=f".{_captured_ftype}", delete=False) as tmp:
                            tmp.write(_captured_bytes)
                            tmp_path = tmp.name
                        try:
                            proc_result = await fp.process_file(
                                file_id=os.path.basename(tmp_path),
                                collection_name=_captured_collection,
                                file_type=_captured_ftype,
                                chunk_size=chunk_size,
                                chunk_overlap=chunk_overlap,
                            )
                            result = proc_result
                        finally:
                            os.unlink(tmp_path)

                    # Save dynamic config if needed
                    if system_prompt or display_name or description:
                        from config.dynamic_collection_store import save_collection_config
                        save_collection_config(
                            collection_name=_captured_collection,
                            system_prompt=system_prompt,
                            display_name=display_name,
                            description=description,
                        )

                    if result.get("success"):
                        return {
                            "success": True,
                            "collection": _captured_collection,
                            "filename": _captured_filename,
                            "chunks_count": result.get("total_chunks", result.get("documents_created", 0)),
                        }
                    else:
                        raise Exception(result.get("error", "Processing failed"))

                except Exception as proc_err:
                    logger.error(f"File processing error in job {job_id}: {proc_err}")
                    raise

            await queue.put({"job_id": job_id, "handler": _file_handler})
            logger.info(f"📥 File job {job_id} queued: '{filename}' -> '{collection_name}'")

            return {
                "success": True,
                "job_id": job_id,
                "status": "queued",
                "filename": filename,
                "collection_name": collection_name,
                "file_size": len(file_bytes),
                "chunks_created": 0,
                "message": f"فایل در صف پردازش قرار گرفت. برای دریافت نتیجه از /jobs/{job_id} استفاده کنید.",
                "poll_url": f"/jobs/{job_id}",
                "estimate_time": estimate_time,
            }

        # ── Fallback: small non-PDF files processed synchronously ────────
        raise HTTPException(status_code=503, detail="Processing queue unavailable. Please try again.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{collection_name}/documents", response_model=AddDocumentsResponse)
async def add_documents(
    collection_name: str,
    request: AddDocumentsRequest,
    collection_manager = Depends(get_collection_manager)
):
    """افزودن اسناد به صورت دستی"""
    try:
        result = await collection_manager.add_documents(
            collection_name=collection_name,
            documents=request.documents,
            metadata_list=request.metadata_list
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to add documents"))
        
        return AddDocumentsResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== QUERY & SEARCH ====================

@router.post("/{collection_name}/query", response_model=QueryCollectionResponse)
async def query_collection(
    collection_name: str,
    request: QueryCollectionRequest,
    rag_system = Depends(get_rag_system)
):
    """پرس و جو در کالکشن"""
    try:
        # Use existing RAG system (note: retrieve_and_answer doesn't accept 'filters')
        result = await rag_system.retrieve_and_answer(
            query=request.query,
            collection_name=collection_name,
            top_k=request.top_k,
            use_reranking=request.use_reranking,
        )
        
        return QueryCollectionResponse(
            success=result.get("success", False),
            answer=result.get("answer", ""),
            full_answer=result.get("full_answer"),
            sources=result.get("sources", []),
            confidence=result.get("confidence", 0.0),
            processing_time=result.get("processing_time", 0.0),
            metadata=result.get("metadata", {})
        )
        
    except Exception as e:
        logger.error(f"Error querying collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{collection_name}/search", response_model=SearchDocumentsResponse)
async def search_documents(
    collection_name: str,
    request: SearchDocumentsRequest,
    collection_manager = Depends(get_collection_manager)
):
    """جستجو در اسناد (بدون LLM)"""
    try:
        import time
        start_time = time.time()
        
        # Get collection
        collection = collection_manager.chroma_client.get_collection(collection_name)
        
        # Generate embedding for query
        if collection_manager.embedding_service:
            query_embedding = await collection_manager.embedding_service.generate_embedding(request.query)
        else:
            raise HTTPException(status_code=503, detail="Embedding service not available")
        
        # Search
        search_result = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.top_k,
            where=request.filters
        )
        
        # Format results
        results = []
        if search_result["documents"]:
            for i, doc in enumerate(search_result["documents"][0]):
                results.append({
                    "document": doc,
                    "metadata": search_result["metadatas"][0][i] if search_result["metadatas"] else {},
                    "score": 1.0 - search_result["distances"][0][i] if search_result["distances"] else 0.0
                })
        
        processing_time = time.time() - start_time
        
        return SearchDocumentsResponse(
            success=True,
            results=results,
            total_found=len(results),
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
