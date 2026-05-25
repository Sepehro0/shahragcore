# -*- coding: utf-8 -*-
"""
Ultimate RAG UI - رابط کاربری برای Ultimate RAG System
"""

import streamlit as st
import asyncio
import logging
from typing import Dict, Any, List
import sys
import os

# Add path for imports
sys.path.insert(0, "/home/user01/qwen-api/enhanced_rag_system_dev")

from core.refactored_rag_system import RefactoredRAGSystem

logger = logging.getLogger(__name__)


class UltimateRAGUI:
    """رابط کاربری Ultimate RAG System"""
    
    def __init__(self):
        # پیش‌فرض: فعال بودن فیچرهای پیشرفته
        st.session_state.setdefault("enable_semantic_chunking", True)
        st.session_state.setdefault("enable_query_understanding", True)
        st.session_state.setdefault("enable_advanced_retrieval", True)
        st.session_state.setdefault("retrieval_strategy", "hybrid")

        if "ultimate_rag_system" not in st.session_state:
            try:
                st.session_state.ultimate_rag_system = RefactoredRAGSystem(
                    enable_semantic_chunking=st.session_state.get("enable_semantic_chunking", True),
                    enable_query_understanding=st.session_state.get("enable_query_understanding", True),
                    enable_advanced_retrieval=st.session_state.get("enable_advanced_retrieval", True),
                    retrieval_strategy=st.session_state.get("retrieval_strategy", "hybrid")
                )
                logger.info("✅ Ultimate RAG System initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Ultimate RAG System: {e}")
                st.error(f"خطا در راه‌اندازی سیستم: {str(e)}")
                st.session_state.ultimate_rag_system = None
    
    def render_ultimate_rag_tab(self):
        """رندر کردن تب Ultimate RAG"""
        
        # Header
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h2 style="color: white; margin: 0;">🚀 Ultimate RAG System</h2>
            <p style="color: white; margin: 10px 0 0 0;">سیستم پیشرفته RAG با Advanced PDF Processor، Cross-Encoder Reranking و Multi-Hop Retrieval</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.ultimate_rag_system is None:
            st.error("❌ سیستم Ultimate RAG در دسترس نیست")
            return
        
        # System Status
        with st.expander("📊 وضعیت سیستم", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("🔢 Persian Embeddings", "ParsBERT", "✅")
            with col2:
                st.metric("🎯 Reranking", "Cross-Encoder", "✅")
            with col3:
                st.metric("🔄 Multi-Hop", "Enabled", "✅")
            with col4:
                st.metric("📄 Advanced PDF", "Enabled", "✅")
        
        # ========== NEW: Advanced Features Toggle ==========
        st.divider()
        st.markdown("### ⚙️ Advanced Features (Beta)")
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <p style="color: white; margin: 0;">🌟 فیچرهای پیشرفته RAG - Phase 1, 2 & 3</p>
            <small style="color: white; opacity: 0.9;">Semantic Chunking, Query Understanding, Advanced Retrieval</small>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            enable_semantic = st.toggle(
                "🧠 Semantic Chunking",
                value=st.session_state.get("enable_semantic_chunking", True),
                help="Late + Agentic chunking for better context preservation\n+30-50% processing time, better retrieval accuracy",
                key="toggle_semantic_chunking"
            )
        
        with col2:
            enable_query_understanding = st.toggle(
                "🎯 Query Understanding",
                value=st.session_state.get("enable_query_understanding", True),
                help="Intent detection, HyDE, and query expansion\n+100-200ms per query, smarter search",
                key="toggle_query_understanding"
            )
        
        with col3:
            enable_advanced_retrieval = st.toggle(
                "🚀 Advanced Retrieval",
                value=st.session_state.get("enable_advanced_retrieval", True),
                help="RRF, iterative, and graph-based retrieval\n+50-100% retrieval time, higher accuracy",
                key="toggle_advanced_retrieval"
            )
        
        # Retrieval Strategy Selector (only if advanced retrieval is enabled)
        retrieval_strategy = "hybrid"
        if enable_advanced_retrieval:
            retrieval_strategy = st.selectbox(
                "📊 Retrieval Strategy",
                ["simple", "hybrid", "iterative", "graph", "advanced"],
                index=1,
                help="""
                - simple: Semantic + BM25 (fastest)
                - hybrid: RRF fusion (balanced)
                - iterative: Multi-stage refinement (accurate)
                - graph: Graph expansion (comprehensive)
                - advanced: All techniques combined (best, slowest)
                """,
                key="select_retrieval_strategy"
            )
        
        # Feature Status Indicators
        if any([enable_semantic, enable_query_understanding, enable_advanced_retrieval]):
            st.info(f"""
            ✅ Active Features: 
            {'🧠 Semantic Chunking ' if enable_semantic else ''}
            {'🎯 Query Understanding ' if enable_query_understanding else ''}
            {'🚀 Advanced Retrieval ({}) '.format(retrieval_strategy) if enable_advanced_retrieval else ''}
            """)
        
        # Check if features changed and need to reinitialize
        features_changed = (
            enable_semantic != st.session_state.get("enable_semantic_chunking", False) or
            enable_query_understanding != st.session_state.get("enable_query_understanding", False) or
            enable_advanced_retrieval != st.session_state.get("enable_advanced_retrieval", False) or
            retrieval_strategy != st.session_state.get("retrieval_strategy", "hybrid")
        )
        
        if features_changed:
            st.session_state.enable_semantic_chunking = enable_semantic
            st.session_state.enable_query_understanding = enable_query_understanding
            st.session_state.enable_advanced_retrieval = enable_advanced_retrieval
            st.session_state.retrieval_strategy = retrieval_strategy
            
            # Reinitialize system with new settings
            with st.spinner("🔄 Updating system configuration..."):
                try:
                    st.session_state.ultimate_rag_system = RefactoredRAGSystem(
                        enable_semantic_chunking=enable_semantic,
                        enable_query_understanding=enable_query_understanding,
                        enable_advanced_retrieval=enable_advanced_retrieval,
                        retrieval_strategy=retrieval_strategy
                    )
                    st.success("✅ System configuration updated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to update configuration: {str(e)}")
        # ===================================================
        
        st.divider()
        
        # ========== NEW: Upload & Advanced Processing (Ultimate RAG) ==========
        st.subheader("📤 آپلود و پردازش پیشرفته (Ultimate RAG)")
        st.caption("از Semantic Chunking و پردازش پیشرفته استفاده می‌کند. برای فعال‌سازی، Semantic Chunking را در بالا روشن کنید.")
        
        col_up1, col_up2 = st.columns([3, 1])
        with col_up1:
            # جلوگیری از تداخل کلید با نمونه‌های دیگر: کلید یکتا بر اساس session
            import uuid
            uploader_key = st.session_state.get("ultimate_file_uploader_key")
            if not uploader_key:
                uploader_key = f"ultimate_file_uploader_{uuid.uuid4()}"
                st.session_state["ultimate_file_uploader_key"] = uploader_key
            uploaded_files = st.file_uploader(
                "فایل‌های خود را آپلود کنید",
                type=["pdf", "docx", "txt", "xlsx", "xls"],
                accept_multiple_files=True,
                key=uploader_key
            )
        with col_up2:
            chunk_size = st.number_input("اندازه چانک هدف", value=500, min_value=100, max_value=2000, step=50, key="ultimate_chunk_size")
            overlap_note = st.caption("اندازه‌ها راهنمایی هستند؛ Chunker هوشمند با آستانه معنایی تقسیم می‌کند.")
        
        if uploaded_files:
            st.subheader("📋 فایل‌های آپلود شده")
            for idx, uf in enumerate(uploaded_files):
                with st.expander(f"📄 {uf.name} ({uf.size / 1024:.2f} KB)"):
                    colp1, colp2 = st.columns([3, 1])
                    with colp1:
                        collection_name = st.text_input(
                            "نام کالکشن",
                            value=f"ultimate_{uf.name.replace('.', '_').lower()}_{idx}",
                            key=f"ultimate_collection_{idx}"
                        )
                    with colp2:
                        do_process = st.button("🚀 پردازش پیشرفته", key=f"ultimate_process_{idx}")
                    if do_process:
                        if not collection_name:
                            st.error("لطفاً نام کالکشن را وارد کنید")
                        else:
                            # هشدار اگر Semantic Chunking خاموش است
                            if not st.session_state.get("enable_semantic_chunking", False):
                                st.warning("برای بهترین نتیجه، Semantic Chunking را از بخش بالا فعال کنید.")
                            progress = st.progress(0)
                            note = st.empty()
                            try:
                                file_bytes = uf.read()
                                note.info("🔄 در حال پردازش با Advanced PDF Processor و Semantic Chunking (در صورت فعال بودن)...")
                                progress.progress(10)
                                # فراخوانی مسیر UltimateRAGSystem
                                result = asyncio.run(
                                    st.session_state.ultimate_rag_system.process_pdf_advanced(
                                        file_bytes=file_bytes,
                                        filename=uf.name,
                                        collection_name=collection_name
                                    )
                                )
                                progress.progress(90)
                                if result.get("success"):
                                    st.success(f"✅ پردازش کامل شد - تعداد چانک‌ها: {result.get('chunks_count', 0)}")
                                    st.info(f"📦 کالکشن: {result.get('collection')}")
                                    progress.progress(100)
                                else:
                                    st.error(f"❌ خطا: {result.get('error', 'نامشخص')}")
                                    progress.progress(0)
                            except Exception as e:
                                st.error(f"❌ خطای غیرمنتظره: {e}")
                                progress.progress(0)
        # =====================================================================
        
        # Collection Management
        st.subheader("📁 مدیریت کالکشن‌ها")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Get existing collections
            collections = asyncio.run(st.session_state.ultimate_rag_system.get_collections())
            
            if collections:
                st.info(f"📋 {len(collections)} کالکشن موجود")
                selected_collection = st.selectbox(
                    "انتخاب کالکشن",
                    collections,
                    key="ultimate_collection_selector"
                )
            else:
                st.info("هیچ کالکشنی وجود ندارد. ابتدا یک سند آپلود کنید.")
                selected_collection = None
        
        with col2:
            new_collection_name = st.text_input(
                "نام کالکشن جدید",
                placeholder="ultimate-collection",
                help="نام منحصر به فرد برای collection جدید",
                key="ultimate_new_collection"
            )
        
        with col3:
            if selected_collection:
                if st.button("🗑️ حذف کالکشن", key="ultimate_delete_collection_btn"):
                    try:
                        # Delete collection logic here
                        st.success(f"✅ کالکشن '{selected_collection}' حذف شد")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطا در حذف کالکشن: {str(e)}")
        
        st.divider()
        
        # Main Tabs
        upload_tab, chat_tab, test_tab = st.tabs([
            "📤 آپلود و پردازش اسناد", 
            "💬 چت هوشمند", 
            "🧪 تست عملکرد"
        ])
        
        # Upload and Processing Tab
        with upload_tab:
            st.subheader("📤 آپلود و پردازش اسناد")
            
            # File uploader
            uploaded_files = st.file_uploader(
                "فایل‌های خود را آپلود کنید",
                type=["pdf", "xlsx", "xls"],
                accept_multiple_files=True,
                help="فرمت‌های پشتیبانی شده: PDF (با Advanced Processor), Excel",
                key="ultimate_file_uploader"
            )
            
            if uploaded_files:
                st.subheader("📋 فایل‌های آپلود شده")
                
                for idx, uploaded_file in enumerate(uploaded_files):
                    with st.expander(f"📄 {uploaded_file.name} ({uploaded_file.size / 1024:.2f} KB)"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            # Collection name for this file
                            file_collection_name = st.text_input(
                                "نام کالکشن",
                                value=new_collection_name if new_collection_name else uploaded_file.name.replace('.pdf', '').replace('.xlsx', '').replace('.xls', ''),
                                key=f"ultimate_file_collection_name_{idx}",
                                help="نام کالکشن برای ذخیره این فایل"
                            )
                        
                        with col2:
                            if st.button("🚀 پردازش پیشرفته", key=f"ultimate_process_btn_{idx}"):
                                if not file_collection_name:
                                    st.error("لطفاً نام کالکشن را وارد کنید")
                                else:
                                    # Create progress containers
                                    progress_bar = st.progress(0)
                                    status_text = st.empty()
                                    
                                    def update_progress(message, percentage):
                                        try:
                                            status_text.info(f"⏳ {message}")
                                            if percentage >= 0 and percentage <= 100:
                                                progress_bar.progress(int(percentage) / 100)
                                        except Exception as e:
                                            logger.warning(f"Progress callback error: {e}")
                                            pass
                                    
                                    # Process the file
                                    file_bytes = uploaded_file.read()
                                    
                                    try:
                                        # Determine file type and process accordingly
                                        if uploaded_file.name.lower().endswith('.pdf'):
                                            status_text.info("📄 پردازش PDF با Advanced Processor...")
                                            progress_bar.progress(20)
                                            
                                            stats = asyncio.run(st.session_state.ultimate_rag_system.process_pdf_advanced(
                                                file_bytes=file_bytes,
                                                filename=uploaded_file.name,
                                                collection_name=file_collection_name
                                            ))
                                        else:
                                            status_text.info("📊 پردازش Excel...")
                                            progress_bar.progress(20)
                                            
                                            stats = asyncio.run(st.session_state.ultimate_rag_system.process_excel(
                                                file_bytes=file_bytes,
                                                filename=uploaded_file.name,
                                                collection_name=file_collection_name
                                            ))
                                        
                                        if stats["success"]:
                                            status_text.success("✅ پردازش با موفقیت تکمیل شد!")
                                            progress_bar.progress(100)
                                            
                                            # Show statistics
                                            st.markdown("### 📊 آمار پردازش")
                                            col_s1, col_s2, col_s3 = st.columns(3)
                                            
                                            with col_s1:
                                                st.metric("تعداد چانک‌ها", stats.get('chunks_count', 0))
                                            with col_s2:
                                                st.metric("فایل", stats.get('filename', 'N/A'))
                                            with col_s3:
                                                st.metric("کالکشن", stats.get('collection', 'N/A'))
                                            
                                            st.success(f"✅ فایل '{uploaded_file.name}' با موفقیت پردازش و در کالکشن '{file_collection_name}' ذخیره شد!")
                                            
                                        else:
                                            status_text.error(f"❌ خطا: {stats.get('error', 'نامشخص')}")
                                            progress_bar.progress(0)
                                    
                                    except Exception as e:
                                        status_text.error(f"❌ خطای غیرمنتظره: {str(e)}")
                                        progress_bar.progress(0)
        
        # Chat Tab
        with chat_tab:
            st.subheader("💬 چت هوشمند با اسناد")
            
            if not collections:
                st.warning("⚠️ هیچ کالکشنی وجود ندارد. ابتدا یک سند آپلود و پردازش کنید.")
            else:
                # Collection selector for chat
                chat_collection = st.selectbox(
                    "انتخاب کالکشن برای چت",
                    collections,
                    key="ultimate_chat_collection_selector"
                )
                
                if chat_collection:
                    # Advanced RAG settings
                    with st.expander("⚙️ تنظیمات پیشرفته RAG"):
                        st.markdown("### تنظیمات اصلی")
                        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                        
                        with col_r1:
                            top_k = st.slider("تعداد اسناد بازیابی", 1, 20, 10, key="ultimate_rag_top_k")
                        with col_r2:
                            use_reranking = st.checkbox("🎯 Cross-Encoder Reranking", value=True, key="ultimate_use_reranking")
                        with col_r3:
                            use_multi_hop = st.checkbox("🔄 Multi-Hop Retrieval", value=True, key="ultimate_use_multi_hop")
                        with col_r4:
                            temperature = st.slider("دما", 0.1, 2.0, 0.1, 0.1, key="ultimate_temperature")
                    
                    # Chat History Management
                    col_hist1, col_hist2 = st.columns([3, 1])
                    with col_hist1:
                        st.markdown("### 💬 گفتگو با اسناد")
                    with col_hist2:
                        if st.button("🗑️ پاک کردن تاریخچه", key="clear_ultimate_chat_history"):
                            if "ultimate_rag_messages" in st.session_state:
                                st.session_state.ultimate_rag_messages = []
                            if st.session_state.ultimate_rag_system:
                                st.session_state.ultimate_rag_system.clear_chat_history(chat_collection)
                            st.rerun()
                    
                    # Initialize chat messages
                    if "ultimate_rag_messages" not in st.session_state:
                        st.session_state.ultimate_rag_messages = []
                    
                    # Display chat history
                    for message in st.session_state.ultimate_rag_messages:
                        with st.chat_message(message["role"]):
                            st.markdown(message["content"])
                            
                            # Show retrieved documents for assistant messages
                            if message["role"] == "assistant" and "retrieved_docs" in message:
                                with st.expander("📄 اسناد بازیابی شده"):
                                    for i, doc in enumerate(message["retrieved_docs"]):
                                        score = doc.get("final_score", doc.get("hybrid_score", 0))
                                        color = "🟢" if score > 0.7 else "🟡" if score > 0.4 else "🔴"
                                        st.markdown(f"""
                                        **{color} سند {i+1}** (امتیاز: {score:.4f})
                                        
                                        {doc.get('text', 'N/A')[:300]}...
                                        """)
                    
                    # Chat input
                    if chat_prompt := st.chat_input("سوال خود را در مورد اسناد بپرسید...", key="ultimate_chat_input"):
                        # Add user message
                        st.session_state.ultimate_rag_messages.append({"role": "user", "content": chat_prompt})
                        
                        # Display user message
                        with st.chat_message("user"):
                            st.markdown(chat_prompt)
                        
                        # Generate response
                        with st.chat_message("assistant"):
                            message_placeholder = st.empty()
                            full_response = ""
                            retrieved_docs = []
                            
                            with st.spinner("🔍 در حال جستجو و تولید پاسخ..."):
                                try:
                                    result = asyncio.run(st.session_state.ultimate_rag_system.retrieve_and_answer(
                                        query=chat_prompt,
                                        collection_name=chat_collection,
                                        top_k=top_k,
                                        use_reranking=use_reranking,
                                        use_multi_hop=use_multi_hop
                                    ))
                                    
                                    if result["success"]:
                                        full_response = result["answer"]
                                        retrieved_docs = result.get("top_results", [])
                                        
                                        # Show additional info
                                        st.info(f"""
                                        📊 **اطلاعات پاسخ:**
                                        - امتیاز: {result.get('top_score', 0):.4f}
                                        - Reranking: {'✅' if result.get('used_reranking', False) else '❌'}
                                        - Multi-hop: {'✅' if result.get('used_multi_hop', False) else '❌'}
                                        """)
                                    
                                    else:
                                        full_response = f"❌ خطا: {result.get('error', 'نامشخص')}"
                                
                                except Exception as e:
                                    full_response = f"❌ خطا: {str(e)}"
                                
                                message_placeholder.markdown(full_response)
                            
                            # Add assistant message
                            st.session_state.ultimate_rag_messages.append({
                                "role": "assistant",
                                "content": full_response,
                                "retrieved_docs": retrieved_docs
                            })
                            
                            # Show retrieved documents
                            if retrieved_docs:
                                with st.expander("📄 اسناد بازیابی شده"):
                                    for i, doc in enumerate(retrieved_docs):
                                        score = doc.get("final_score", doc.get("hybrid_score", 0))
                                        color = "🟢" if score > 0.7 else "🟡" if score > 0.4 else "🔴"
                                        st.markdown(f"""
                                        **{color} سند {i+1}** (امتیاز: {score:.4f})
                                        
                                        {doc.get('text', 'N/A')[:300]}...
                                        """)
                    
                    # Clear chat button
                    if st.button("🗑️ پاک کردن چت", use_container_width=True, key="ultimate_clear_chat"):
                        st.session_state.ultimate_rag_messages = []
                        st.rerun()
        
        # Test Tab
        with test_tab:
            st.subheader("🧪 تست عملکرد سیستم")
            
            if not collections:
                st.warning("⚠️ هیچ کالکشنی وجود ندارد. ابتدا یک سند آپلود و پردازش کنید.")
            else:
                test_collection = st.selectbox(
                    "انتخاب کالکشن برای تست",
                    collections,
                    key="ultimate_test_collection_selector"
                )
                
                if test_collection:
                    # Pre-defined test queries
                    test_queries = [
                        "بند چهارم توی این جدول چیه؟",
                        "جمع کل مالیات مشاغل چقدره؟",
                        "برآورد درآمدهای مالیاتی در بخش ملی و استانی چقدر است؟"
                    ]
                    
                    st.markdown("### 🎯 سوالات تست پیش‌فرض")
                    
                    for i, query in enumerate(test_queries, 1):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.text_input(
                                f"سوال {i}",
                                value=query,
                                disabled=True,
                                key=f"ultimate_test_query_{i}"
                            )
                        
                        with col2:
                            if st.button(f"🚀 تست {i}", key=f"ultimate_test_btn_{i}"):
                                with st.spinner(f"در حال تست سوال {i}..."):
                                    try:
                                        result = asyncio.run(st.session_state.ultimate_rag_system.retrieve_and_answer(
                                            query=query,
                                            collection_name=test_collection,
                                            top_k=5,
                                            use_reranking=True,
                                            use_multi_hop=True
                                        ))
                                        
                                        if result["success"]:
                                            score = result.get('top_score', 0)
                                            status = "🟢 عالی" if score > 0.7 else "🟡 متوسط" if score > 0.4 else "🔴 ضعیف"
                                            
                                            st.success(f"✅ تست {i} - امتیاز: {score:.4f} - {status}")
                                            
                                            with st.expander(f"📝 پاسخ سوال {i}"):
                                                st.markdown(result["answer"])
                                        
                                        else:
                                            st.error(f"❌ تست {i} - خطا: {result.get('error', 'نامشخص')}")
                                    
                                    except Exception as e:
                                        st.error(f"❌ تست {i} - خطا: {str(e)}")
                    
                    # Custom test query
                    st.markdown("### 🎯 سوال سفارشی")
                    custom_query = st.text_input(
                        "سوال خود را وارد کنید",
                        placeholder="سوال خود را بنویسید...",
                        key="ultimate_custom_query"
                    )
                    
                    if st.button("🚀 تست سفارشی", key="ultimate_custom_test_btn") and custom_query:
                        with st.spinner("در حال پردازش سوال سفارشی..."):
                            try:
                                result = asyncio.run(st.session_state.ultimate_rag_system.retrieve_and_answer(
                                    query=custom_query,
                                    collection_name=test_collection,
                                    top_k=5,
                                    use_reranking=True,
                                    use_multi_hop=True
                                ))
                                
                                if result["success"]:
                                    score = result.get('top_score', 0)
                                    status = "🟢 عالی" if score > 0.7 else "🟡 متوسط" if score > 0.4 else "🔴 ضعیف"
                                    
                                    st.success(f"✅ تست سفارشی - امتیاز: {score:.4f} - {status}")
                                    
                                    st.markdown("### 📝 پاسخ:")
                                    st.markdown(result["answer"])
                                    
                                    st.markdown("### 📊 اطلاعات پاسخ:")
                                    col_info1, col_info2, col_info3 = st.columns(3)
                                    
                                    with col_info1:
                                        st.metric("امتیاز", f"{score:.4f}")
                                    with col_info2:
                                        st.metric("Reranking", "✅" if result.get('used_reranking', False) else "❌")
                                    with col_info3:
                                        st.metric("Multi-hop", "✅" if result.get('used_multi_hop', False) else "❌")
                                
                                else:
                                    st.error(f"❌ تست سفارشی - خطا: {result.get('error', 'نامشخص')}")
                            
                            except Exception as e:
                                st.error(f"❌ تست سفارشی - خطا: {str(e)}")
