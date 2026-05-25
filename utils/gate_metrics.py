# -*- coding: utf-8 -*-
"""
Gate Metrics
جمع‌آوری و تحلیل metrics از Gate ها برای monitoring
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


@dataclass
class GateDecisionLog:
    """لاگ یک تصمیم Gate"""
    timestamp: str
    collection_name: str
    gate_type: str  # intent_gate, relevance_gate
    query: str
    decision: str  # rejected, accepted
    reason: str
    confidence: float
    metadata: Dict[str, Any]


class GateMetrics:
    """
    جمع‌آوری و تحلیل metrics از Gate ها
    
    Features:
    - لاگ تصمیمات Gate ها
    - محاسبه rejection rate
    - تحلیل دلایل rejection
    - tracking عملکرد Gate ها
    """
    
    def __init__(self, log_file_path: Optional[str] = None):
        """
        Args:
            log_file_path: مسیر فایل لاگ (اختیاری)
        """
        self.log_file_path = log_file_path or "/home/user01/qwen-api/enhanced_rag_system_dev/gate_metrics.log"
        
        # In-memory storage برای آمار
        self.decisions: List[GateDecisionLog] = []
        self.stats = {
            # Phase 1 & 2
            'intent_gate': defaultdict(int),
            'relevance_gate': defaultdict(int),
            'answer_policy': defaultdict(int),
            # Phase 3 (NEW)
            'query_complexity': defaultdict(int),
            # Phase 4 (NEW)
            'pre_generation_guard': defaultdict(int),
            'semantic_alignment': defaultdict(int),
            'keyword_coverage': defaultdict(int),
            'context_contradiction': defaultdict(int),
            'intent_gate': defaultdict(int),
            'relevance_gate': defaultdict(int),
            'answer_policy': defaultdict(int)
        }
    
    def log_intent_gate_decision(
        self,
        collection_name: str,
        query: str,
        decision: str,
        reason: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        لاگ تصمیم Intent Gate
        
        Args:
            collection_name: نام collection
            query: سوال کاربر
            decision: نوع تصمیم (rejected, accepted)
            reason: دلیل تصمیم
            confidence: نمره اطمینان
            metadata: اطلاعات اضافی
        """
        log_entry = GateDecisionLog(
            timestamp=datetime.now().isoformat(),
            collection_name=collection_name,
            gate_type="intent_gate",
            query=query[:100],  # محدود کردن طول
            decision=decision,
            reason=reason,
            confidence=confidence,
            metadata=metadata or {}
        )
        
        # Add to in-memory storage
        self.decisions.append(log_entry)
        
        # Update stats
        self.stats['intent_gate'][decision] += 1
        self.stats['intent_gate'][f'reason_{reason}'] += 1
        
        # Log to file
        self._write_to_file(log_entry)
        
        logger.debug(
            f"📊 [METRICS] Intent Gate: {decision} "
            f"(reason={reason}, confidence={confidence:.2f})"
        )
    
    def log_relevance_gate_decision(
        self,
        collection_name: str,
        query: str,
        decision: str,
        reason: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        لاگ تصمیم Relevance Gate
        """
        log_entry = GateDecisionLog(
            timestamp=datetime.now().isoformat(),
            collection_name=collection_name,
            gate_type="relevance_gate",
            query=query[:100],
            decision=decision,
            reason=reason,
            confidence=confidence,
            metadata=metadata or {}
        )
        
        # Add to in-memory storage
        self.decisions.append(log_entry)
        
        # Update stats
        self.stats['relevance_gate'][decision] += 1
        self.stats['relevance_gate'][f'reason_{reason}'] += 1
        
        # Log to file
        self._write_to_file(log_entry)
        
        logger.debug(
            f"📊 [METRICS] Relevance Gate: {decision} "
            f"(reason={reason}, confidence={confidence:.2f})"
        )
    
    def log_answer_policy_decision(
        self,
        collection_name: str,
        query: str,
        strategy: str,
        reason: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        لاگ تصمیم Answer Policy
        """
        log_entry = GateDecisionLog(
            timestamp=datetime.now().isoformat(),
            collection_name=collection_name,
            gate_type="answer_policy",
            query=query[:100],
            decision=strategy,
            reason=reason,
            confidence=confidence,
            metadata=metadata or {}
        )
        
        # Add to in-memory storage
        self.decisions.append(log_entry)
        
        # Update stats
        self.stats['answer_policy'][strategy] += 1
        self.stats['answer_policy'][f'reason_{reason}'] += 1
        
        # Log to file
        self._write_to_file(log_entry)
        
        logger.debug(
            f"📊 [METRICS] Answer Policy: {strategy} "
            f"(reason={reason}, confidence={confidence:.2f})"
        )
    
    def _write_to_file(self, log_entry: GateDecisionLog):
        """
        نوشتن لاگ به فایل
        """
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(log_entry), ensure_ascii=False) + '\n')
        except Exception as e:
            logger.warning(f"⚠️ Failed to write gate metrics to file: {e}")
    
    def get_rejection_rate(
        self,
        gate_type: str,
        collection_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> float:
        """
        محاسبه نرخ rejection
        
        Args:
            gate_type: نوع gate (intent_gate, relevance_gate)
            collection_name: نام collection (اختیاری)
            time_window: بازه زمانی (اختیاری)
            
        Returns:
            نرخ rejection (0.0 تا 1.0)
        """
        # Filter decisions
        filtered_decisions = self.decisions
        
        if gate_type:
            filtered_decisions = [d for d in filtered_decisions if d.gate_type == gate_type]
        
        if collection_name:
            filtered_decisions = [d for d in filtered_decisions if d.collection_name == collection_name]
        
        if time_window:
            cutoff_time = datetime.now() - time_window
            filtered_decisions = [
                d for d in filtered_decisions 
                if datetime.fromisoformat(d.timestamp) > cutoff_time
            ]
        
        if not filtered_decisions:
            return 0.0
        
        rejected_count = sum(1 for d in filtered_decisions if d.decision == 'rejected')
        total_count = len(filtered_decisions)
        
        return rejected_count / total_count if total_count > 0 else 0.0
    
    def get_rejection_reasons(
        self,
        gate_type: str,
        collection_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, int]:
        """
        دریافت توزیع دلایل rejection
        
        Returns:
            Dict از reasons و تعداد آنها
        """
        # Filter decisions
        filtered_decisions = self.decisions
        
        if gate_type:
            filtered_decisions = [d for d in filtered_decisions if d.gate_type == gate_type]
        
        if collection_name:
            filtered_decisions = [d for d in filtered_decisions if d.collection_name == collection_name]
        
        if time_window:
            cutoff_time = datetime.now() - time_window
            filtered_decisions = [
                d for d in filtered_decisions 
                if datetime.fromisoformat(d.timestamp) > cutoff_time
            ]
        
        # Count reasons (only for rejected)
        reasons = defaultdict(int)
        for decision in filtered_decisions:
            if decision.decision == 'rejected':
                reasons[decision.reason] += 1
        
        return dict(reasons)
    
    def get_stats_summary(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """
        دریافت خلاصه آمار
        
        Returns:
            Dict حاوی آمار کامل
        """
        summary = {
            'total_decisions': len(self.decisions),
            'intent_gate': {
                'rejection_rate': self.get_rejection_rate('intent_gate', collection_name),
                'rejection_reasons': self.get_rejection_reasons('intent_gate', collection_name),
                'total': self.stats['intent_gate']['rejected'] + self.stats['intent_gate'].get('accepted', 0)
            },
            'relevance_gate': {
                'rejection_rate': self.get_rejection_rate('relevance_gate', collection_name),
                'rejection_reasons': self.get_rejection_reasons('relevance_gate', collection_name),
                'total': self.stats['relevance_gate']['rejected'] + self.stats['relevance_gate'].get('accepted', 0)
            },
            'answer_policy': {
                'strategies': dict(self.stats['answer_policy']),
                'total': sum(v for k, v in self.stats['answer_policy'].items() if not k.startswith('reason_'))
            }
        }
        
        return summary
    
    def print_stats(self, collection_name: Optional[str] = None):
        """
        نمایش آمار در console
        """
        summary = self.get_stats_summary(collection_name)
        
        logger.info("=" * 60)
        logger.info("📊 Gate Metrics Summary")
        if collection_name:
            logger.info(f"Collection: {collection_name}")
        logger.info("=" * 60)
        
        # Intent Gate
        logger.info("\n🚪 Intent Gate:")
        logger.info(f"  - Total: {summary['intent_gate']['total']}")
        logger.info(f"  - Rejection Rate: {summary['intent_gate']['rejection_rate']:.1%}")
        logger.info(f"  - Top Rejection Reasons:")
        for reason, count in sorted(
            summary['intent_gate']['rejection_reasons'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]:
            logger.info(f"    * {reason}: {count}")
        
        # Relevance Gate
        logger.info("\n🔍 Relevance Gate:")
        logger.info(f"  - Total: {summary['relevance_gate']['total']}")
        logger.info(f"  - Rejection Rate: {summary['relevance_gate']['rejection_rate']:.1%}")
        logger.info(f"  - Top Rejection Reasons:")
        for reason, count in sorted(
            summary['relevance_gate']['rejection_reasons'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]:
            logger.info(f"    * {reason}: {count}")
        
        # Answer Policy
        logger.info("\n📋 Answer Policy:")
        logger.info(f"  - Total: {summary['answer_policy']['total']}")
        logger.info(f"  - Strategy Distribution:")
        strategies = {k: v for k, v in summary['answer_policy']['strategies'].items() if not k.startswith('reason_')}
        for strategy, count in sorted(strategies.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"    * {strategy}: {count}")
        
        logger.info("=" * 60)


# Singleton instance
_gate_metrics_instance = None


def get_gate_metrics() -> GateMetrics:
    """
    دریافت instance سینگلتون GateMetrics
    """
    global _gate_metrics_instance
    if _gate_metrics_instance is None:
        _gate_metrics_instance = GateMetrics()
    return _gate_metrics_instance

