# -*- coding: utf-8 -*-
"""
Advanced Retrieval Strategies:
1. Reciprocal Rank Fusion (RRF) - ترکیب نتایج از sources مختلف
2. Iterative Retrieval - جستجوی تکرارشونده برای refine
3. Graph-based Retrieval - استفاده از روابط بین documents
4. Ensemble Reranking

محل قرارگیری: بعد از Query Understanding، قبل از Generation
"""

import numpy as np
from typing import List, Dict, Tuple, Set, Any
from dataclasses import dataclass
import networkx as nx
from collections import defaultdict
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """نتیجه یک retrieval"""
    doc_id: str
    text: str
    score: float
    source: str  # semantic, bm25, graph, etc.
    metadata: Dict
    relevance_reasoning: str = ""


class ReciprocalRankFusion:
    """
    Reciprocal Rank Fusion (RRF) - بهترین روش ترکیب نتایج
    بهتر از weighted average چون rank-based است
    """
    
    def __init__(self, k: int = 60):
        """
        Args:
            k: پارامتر RRF (معمولا 60)
        """
        self.k = k
    
    def fuse(
        self, 
        retrieval_results: Dict[str, List[RetrievalResult]]
    ) -> List[RetrievalResult]:
        """
        ترکیب نتایج از sources مختلف
        
        Args:
            retrieval_results: dict of {source_name: [results]}
            
        Formula: RRF(d) = Σ 1/(k + rank(d))
        """
        # محاسبه RRF score برای هر document
        doc_scores = defaultdict(float)
        doc_data = {}  # ذخیره اطلاعات document
        
        for source, results in retrieval_results.items():
            for rank, result in enumerate(results, start=1):
                rrf_score = 1.0 / (self.k + rank)
                doc_scores[result.doc_id] += rrf_score
                
                # ذخیره اطلاعات (از اولین occurrence)
                if result.doc_id not in doc_data:
                    doc_data[result.doc_id] = result
        
        # مرتب‌سازی بر اساس RRF score
        sorted_docs = sorted(
            doc_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # ساخت نتایج نهایی
        fused_results = []
        for doc_id, score in sorted_docs:
            result = doc_data[doc_id]
            result.score = score
            result.source = "RRF"
            fused_results.append(result)
        
        return fused_results


class IterativeRetriever:
    """
    Iterative Retrieval - جستجوی چند مرحله‌ای برای refine نتایج
    """
    
    def __init__(self, base_retriever, max_iterations: int = 3):
        self.base_retriever = base_retriever
        self.max_iterations = max_iterations
    
    async def retrieve_iteratively(
        self,
        query: str,
        collection_name: str,
        initial_k: int = 20
    ) -> List[Dict]:
        """
        جستجوی تکرارشونده:
        1. جستجوی اولیه
        2. استخراج terms کلیدی از نتایج
        3. query expansion و جستجوی مجدد
        4. تکرار تا convergence
        """
        all_results = []
        seen_docs = set()
        current_query = query
        
        for iteration in range(self.max_iterations):
            try:
                # جستجو با query فعلی
                results = await self.base_retriever.hybrid_search(
                    query=current_query,
                    collection_name=collection_name,
                    top_k=initial_k
                )
                
                # فیلتر کردن documents تکراری
                new_results = [
                    r for r in results 
                    if r.get('id') not in seen_docs
                ]
                
                if not new_results:
                    break  # convergence
                
                # اضافه کردن به نتایج
                all_results.extend(new_results)
                seen_docs.update(r.get('id') for r in new_results)
                
                # استخراج terms برای iteration بعدی
                if iteration < self.max_iterations - 1:
                    current_query = self._extract_refined_query(
                        original_query=query,
                        retrieved_docs=new_results[:5]  # top 5
                    )
            except Exception as e:
                logger.error(f"Error in iteration {iteration}: {e}")
                break
        
        return all_results
    
    def _extract_refined_query(
        self,
        original_query: str,
        retrieved_docs: List[Dict]
    ) -> str:
        """استخراج query بهبود یافته از documents"""
        # استخراج اسامی خاص و اعداد از top docs
        entities = set()
        for doc in retrieved_docs:
            text = doc.get('text', '')
            # استخراج entities (ساده‌سازی شده)
            numbers = set(re.findall(r'\d+', text))
            entities.update(numbers)
        
        # ترکیب با query اصلی
        if entities:
            refined = f"{original_query} {' '.join(list(entities)[:3])}"
            return refined
        
        return original_query


class GraphBasedRetriever:
    """
    Graph-based Retrieval - استفاده از روابط بین documents
    """
    
    def __init__(self):
        self.doc_graph = nx.DiGraph()  # گراف جهت‌دار
    
    def build_document_graph(
        self, 
        documents: List[Dict],
        embeddings: np.ndarray,
        similarity_threshold: float = 0.5
    ):
        """
        ساخت گراف از documents
        یال‌ها بر اساس مشابهت معنایی
        """
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            
            n = len(documents)
            
            # اضافه کردن nodes
            for i, doc in enumerate(documents):
                self.doc_graph.add_node(
                    i, 
                    text=doc.get("text", ""),
                    metadata=doc.get("metadata", {})
                )
            
            # محاسبه مشابهت و اضافه کردن edges
            similarities = cosine_similarity(embeddings)
            
            # اضافه کردن edges برای top-k مشابه‌ترین
            k = 5
            for i in range(n):
                # پیدا کردن k مشابه‌ترین (به غیر از خودش)
                similar_indices = np.argsort(similarities[i])[::-1][1:k+1]
                
                for j in similar_indices:
                    weight = float(similarities[i][j])
                    if weight > similarity_threshold:
                        self.doc_graph.add_edge(i, j, weight=weight)
            
            logger.info(f"Document graph built: {n} nodes, {self.doc_graph.number_of_edges()} edges")
        except Exception as e:
            logger.error(f"Error building document graph: {e}")
    
    def retrieve_with_graph(
        self,
        initial_results: List[Dict],
        top_k: int = 10
    ) -> List[Dict]:
        """
        توسعه نتایج اولیه با استفاده از گراف
        """
        try:
            # شناسایی node های initial results
            initial_nodes = set()
            node_to_result = {}
            
            for result in initial_results:
                result_text = result.get('text', '')
                # پیدا کردن node مربوطه
                for node, data in self.doc_graph.nodes(data=True):
                    if data["text"] == result_text:
                        initial_nodes.add(node)
                        node_to_result[node] = result
                        break
            
            # توسعه via graph
            expanded_nodes = self._expand_via_graph(initial_nodes, hops=2)
            
            # ساخت نتایج نهایی
            expanded_results = []
            for node in expanded_nodes:
                if node in node_to_result:
                    expanded_results.append(node_to_result[node])
                else:
                    # ساخت result جدید
                    data = self.doc_graph.nodes[node]
                    expanded_results.append({
                        'id': str(node),
                        'text': data["text"],
                        'score': 0.5,  # امتیاز graph-based
                        'metadata': data["metadata"],
                        'source': 'graph'
                    })
            
            return expanded_results[:top_k]
        except Exception as e:
            logger.error(f"Error in graph retrieval: {e}")
            return initial_results[:top_k]
    
    def _expand_via_graph(self, initial_nodes: Set[int], hops: int) -> List[int]:
        """توسعه با k-hop در گراف"""
        expanded = set(initial_nodes)
        current_layer = initial_nodes
        
        for _ in range(hops):
            next_layer = set()
            for node in current_layer:
                # اضافه کردن neighbors
                try:
                    neighbors = self.doc_graph.successors(node)
                    next_layer.update(neighbors)
                except:
                    pass
            
            expanded.update(next_layer)
            current_layer = next_layer
        
        return list(expanded)


class AdvancedRetrievalSystem:
    """
    سیستم کامل Retrieval با تمام تکنیک‌های پیشرفته
    """
    
    def __init__(
        self,
        base_retriever,
        use_rrf: bool = True,
        use_iterative: bool = True,
        use_graph: bool = True
    ):
        self.base_retriever = base_retriever
        
        # ماژول‌های مختلف
        self.rrf = ReciprocalRankFusion() if use_rrf else None
        self.iterative = IterativeRetriever(base_retriever) if use_iterative else None
        self.graph = GraphBasedRetriever() if use_graph else None
        
        logger.info(f"Advanced Retrieval initialized: RRF={use_rrf}, Iterative={use_iterative}, Graph={use_graph}")
    
    async def retrieve(
        self,
        query: str,
        collection_name: str,
        top_k: int = 10,
        strategy: str = "hybrid"
    ) -> List[Dict]:
        """
        Retrieval کامل با strategy انتخابی
        
        Strategies:
        - simple: فقط semantic + BM25
        - hybrid: RRF fusion
        - iterative: چند مرحله‌ای
        - graph: با graph expansion
        - advanced: ترکیب همه
        """
        
        if strategy == "simple":
            return await self._simple_retrieval(query, collection_name, top_k)
        
        elif strategy == "hybrid":
            return await self._hybrid_retrieval(query, collection_name, top_k)
        
        elif strategy == "iterative":
            return await self._iterative_retrieval(query, collection_name, top_k)
        
        elif strategy == "graph":
            return await self._graph_retrieval(query, collection_name, top_k)
        
        elif strategy == "advanced":
            return await self._advanced_retrieval(query, collection_name, top_k)
        
        else:
            logger.warning(f"Unknown strategy: {strategy}, using hybrid")
            return await self._hybrid_retrieval(query, collection_name, top_k)
    
    async def _simple_retrieval(self, query, collection, top_k):
        """جستجوی ساده"""
        try:
            return await self.base_retriever.hybrid_search(query, collection, top_k)
        except Exception as e:
            logger.error(f"Error in simple retrieval: {e}")
            return []
    
    async def _hybrid_retrieval(self, query, collection, top_k):
        """جستجوی ترکیبی با RRF"""
        try:
            # جستجو با hybrid search موجود
            results = await self.base_retriever.hybrid_search(query, collection, top_k * 2)
            
            # اگر RRF فعال است، نتایج را بهتر ترکیب کن
            if self.rrf and len(results) > 0:
                # گروه‌بندی بر اساس source
                grouped = defaultdict(list)
                for r in results:
                    source = r.get('source', 'unknown')
                    grouped[source].append(RetrievalResult(
                        doc_id=r.get('id', ''),
                        text=r.get('text', ''),
                        score=r.get('score', 0),
                        source=source,
                        metadata=r.get('metadata', {})
                    ))
                
                # ===== FIX: فقط وقتی RRF اعمال شود که چند source مختلف داشته باشیم =====
                # اگر فقط یک group باشد (همه با source یکسان)، RRF بی‌فایده است
                # و score های معنادار hybrid_search را نابود می‌کند (همه به ~1/61 می‌رسند).
                # در این حالت نتایج اصلی را برگردان و فقط متادیتا را همسان‌سازی کن.
                if len(grouped) <= 1:
                    logger.debug(f"RRF skipped: only {len(grouped)} source group(s); preserving original scores")
                    return results[:top_k]
                
                # ترکیب با RRF (وقتی حداقل 2 source وجود دارد)
                fused = self.rrf.fuse(grouped)
                
                # تبدیل به فرمت dict — حفظ متادیتا و scoreهای اصلی از doc_data
                out = []
                for r in fused[:top_k]:
                    # score اصلی hybrid_search را هم حفظ کن
                    original = next((res for res in results if res.get('id') == r.doc_id), None)
                    d = {
                        'id': r.doc_id,
                        'text': r.text,
                        'score': r.score,  # RRF score
                        'rrf_score': r.score,
                        'metadata': r.metadata,
                        'source': r.source,
                    }
                    if original:
                        # حفظ همه score fields از hybrid_search
                        for k in ('hybrid_score', 'dense_score', 'bm25_score',
                                  'keyword_score', 'matched_keywords', 'tag_hits',
                                  'original_score', 'final_score', 'match_type'):
                            if k in original:
                                d[k] = original[k]
                        # score را به hybrid_score هم fallback کن (برای downstream)
                        if 'hybrid_score' in original and original['hybrid_score'] > r.score:
                            d['score'] = original['hybrid_score']
                    out.append(d)
                return out
            
            return results[:top_k]
        except Exception as e:
            logger.error(f"Error in hybrid retrieval: {e}")
            return await self._simple_retrieval(query, collection, top_k)
    
    async def _iterative_retrieval(self, query, collection, top_k):
        """جستجوی تکرارشونده"""
        try:
            if self.iterative:
                results = await self.iterative.retrieve_iteratively(query, collection, top_k)
                return results[:top_k]
            else:
                return await self._hybrid_retrieval(query, collection, top_k)
        except Exception as e:
            logger.error(f"Error in iterative retrieval: {e}")
            return await self._hybrid_retrieval(query, collection, top_k)
    
    async def _graph_retrieval(self, query, collection, top_k):
        """جستجوی مبتنی بر گراف"""
        try:
            # جستجوی اولیه
            initial = await self._hybrid_retrieval(query, collection, top_k * 2)
            
            # توسعه با گراف
            if self.graph and len(initial) > 0:
                expanded = self.graph.retrieve_with_graph(initial, top_k)
                return expanded
            
            return initial[:top_k]
        except Exception as e:
            logger.error(f"Error in graph retrieval: {e}")
            return await self._hybrid_retrieval(query, collection, top_k)
    
    async def _advanced_retrieval(self, query, collection, top_k):
        """
        استراتژی پیشرفته: ترکیب همه تکنیک‌ها
        """
        try:
            # 1. Iterative retrieval
            if self.iterative:
                iterative_results = await self.iterative.retrieve_iteratively(
                    query, collection, top_k * 2
                )
            else:
                iterative_results = await self._hybrid_retrieval(query, collection, top_k * 2)
            
            # 2. Graph expansion
            if self.graph and len(iterative_results) > 0:
                graph_results = self.graph.retrieve_with_graph(iterative_results, top_k * 2)
            else:
                graph_results = iterative_results
            
            # 3. Fusion
            if self.rrf and len(graph_results) > 0:
                # گروه‌بندی بر اساس source
                grouped = {
                    "iterative": [RetrievalResult(
                        doc_id=r.get('id', ''),
                        text=r.get('text', ''),
                        score=r.get('score', 0),
                        source='iterative',
                        metadata=r.get('metadata', {})
                    ) for r in iterative_results],
                    "graph": [RetrievalResult(
                        doc_id=r.get('id', ''),
                        text=r.get('text', ''),
                        score=r.get('score', 0),
                        source='graph',
                        metadata=r.get('metadata', {})
                    ) for r in graph_results]
                }
                
                fused = self.rrf.fuse(grouped)
                
                return [
                    {
                        'id': r.doc_id,
                        'text': r.text,
                        'score': r.score,
                        'metadata': r.metadata,
                        'source': r.source
                    }
                    for r in fused[:top_k]
                ]
            
            return graph_results[:top_k]
        except Exception as e:
            logger.error(f"Error in advanced retrieval: {e}")
            return await self._hybrid_retrieval(query, collection, top_k)
    
    def build_graph_for_collection(self, documents: List[Dict], embeddings: np.ndarray):
        """ساخت گراف برای یک collection"""
        if self.graph:
            self.graph.build_document_graph(documents, embeddings)



