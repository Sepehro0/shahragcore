# -*- coding: utf-8 -*-
"""
Enhanced Search for zabete_qa Collection — backward-compatible wrapper.

تمام منطق اصلی به CollectionEnhancedSearch منتقل شده.
این فایل فقط backward compatibility را حفظ می‌کند.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher

from core.collection_enhanced_search import CollectionEnhancedSearch

logger = logging.getLogger(__name__)


class ZabeteEnhancedSearch(CollectionEnhancedSearch):
    """
    Backward-compatible wrapper.
    تمام functionality از CollectionEnhancedSearch ارث‌بری می‌شود.
    متدهای خاص zabete_qa (find_exact_match, find_all_material_matches) اینجا هستند.
    """

    def _calculate_keyword_score(
        self,
        query: str,
        metadata: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        return self.calculate_keyword_score(query, metadata)

    def find_all_material_matches(self, query: str, material_number: str) -> List[Dict[str, Any]]:
        all_docs = self._get_all_docs()
        if not all_docs or not all_docs.get('metadatas'):
            return []

        matches = []
        for idx, metadata in enumerate(all_docs['metadatas']):
            answer = str(metadata.get('answer', ''))
            answer_normalized = self.normalize_text(answer) if answer else ''
            if not answer_normalized:
                continue

            material_patterns = [
                f'ماده {material_number}',
                f'ماده({material_number})',
                f'ماده{material_number}',
                f'ماده ({material_number})',
            ]
            found = any(p in answer_normalized for p in material_patterns)
            if not found:
                found = bool(re.search(rf'ماده\s*\(?{material_number}\)?', answer_normalized))

            if found:
                question = self.normalize_text(str(metadata.get('question', '')))
                query_normalized = self.normalize_text(query)
                question_similarity = SequenceMatcher(None, query_normalized, question).ratio()
                question_has_material = bool(re.search(rf'ماده\s*{material_number}', question))

                matches.append({
                    'id': all_docs['ids'][idx],
                    'text': all_docs['documents'][idx],
                    'metadata': metadata,
                    'score': 0.98,
                    'match_type': 'exact_answer',
                    'question_similarity': question_similarity,
                    'answer_similarity': 0.98,
                    'priority_score': 1000 if question_has_material else 0,
                    'question_has_material': question_has_material,
                })

        matches.sort(key=lambda x: (x['priority_score'], x['question_similarity']), reverse=True)
        return matches

    def find_exact_match(self, query: str) -> Optional[Dict[str, Any]]:
        query_normalized = self.normalize_text(query)
        all_docs = self._get_all_docs()
        if not all_docs or not all_docs.get('metadatas'):
            return None

        material_number_match = re.search(r'ماده\s*(\d+)', query_normalized)
        material_number = material_number_match.group(1) if material_number_match else None

        best_match = None
        best_similarity = 0.0

        for idx, metadata in enumerate(all_docs['metadatas']):
            question = self.normalize_text(str(metadata.get('question', '')))
            answer_normalized = self.normalize_text(str(metadata.get('answer', '')))

            question_similarity = SequenceMatcher(None, query_normalized, question).ratio()
            answer_similarity = 0.0
            if answer_normalized and material_number:
                if re.search(rf'ماده\s*\(?{material_number}\)?', answer_normalized):
                    answer_similarity = 0.98

            max_sim = max(question_similarity, answer_similarity)
            match_type = 'exact_question' if question_similarity > answer_similarity else 'exact_answer'

            if max_sim > 0.75 and max_sim > best_similarity:
                best_similarity = max_sim
                best_match = {
                    'id': all_docs['ids'][idx],
                    'text': all_docs['documents'][idx] if all_docs.get('documents') else '',
                    'metadata': metadata,
                    'score': max_sim,
                    'match_type': match_type,
                    'question_similarity': question_similarity,
                    'answer_similarity': answer_similarity,
                }

        if best_match:
            logger.info(f"✅ [ZabeteSearch] Exact match: type={best_match['match_type']}, sim={best_similarity:.2f}")
        return best_match


def apply_zabete_enhanced_search(
    query: str,
    collection_name: str,
    semantic_results: List[Dict[str, Any]],
    chroma_collection
) -> List[Dict[str, Any]]:
    if collection_name != 'zabete_qa':
        return semantic_results

    searcher = ZabeteEnhancedSearch(chroma_collection)
    exact_match = searcher.find_exact_match(query)
    if exact_match:
        return [exact_match] + [r for r in semantic_results if r.get('id') != exact_match['id']]

    enhanced = searcher.enhanced_search(query, semantic_results)
    if not enhanced or (enhanced[0].get('hybrid_score', 0) < 0.5):
        keyword_results = searcher.keyword_only_search(query, top_k=5)
        if keyword_results:
            merged = keyword_results + enhanced
            seen_ids: set = set()
            unique = []
            for r in merged:
                rid = r.get('id')
                if rid not in seen_ids:
                    seen_ids.add(rid)
                    unique.append(r)
            return unique[:10]

    return enhanced
