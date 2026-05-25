# -*- coding: utf-8 -*-
"""
Advanced Conversation Memory Manager
سیستم پیشرفته مدیریت حافظه گفتگو

این ماژول یک سیستم حافظه گفتگوی پیشرفته پیاده‌سازی می‌کند که شامل:
1. Short-Term Memory (STM): حافظه کوتاه‌مدت برای context فوری
2. Long-Term Memory (LTM): حافظه بلندمدت برای entities و facts مهم
3. Semantic Memory: حافظه معنایی برای درک بهتر context
4. Entity Tracking: پیگیری entities مهم در گفتگو
5. Topic Tracking: پیگیری موضوعات و تغییرات آنها
6. Coreference Resolution: تشخیص ارجاعات (این، آن، اون و...)

معماری:
========
                    ┌─────────────────────────────────────┐
                    │       Conversation Memory           │
                    │              Manager                │
                    └───────────────┬─────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐         ┌─────────────────┐         ┌───────────────┐
│  Short-Term   │         │   Long-Term     │         │   Semantic    │
│   Memory      │         │    Memory       │         │   Memory      │
│  (STM)        │         │   (LTM)         │         │               │
└───────┬───────┘         └────────┬────────┘         └───────┬───────┘
        │                          │                          │
        ▼                          ▼                          ▼
  Recent turns             Extracted facts           Topic embeddings
  Active entities          User preferences          Entity embeddings
  Current topic            Important info            Semantic clusters

Author: AI Assistant
Version: 2.0.0
"""

import time
import json
import logging
import hashlib
import re
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ConversationTurn:
    """یک turn از گفتگو"""
    turn_id: str
    user_query: str
    assistant_response: str
    timestamp: float
    entities: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    intent: str = ""
    sentiment: str = "neutral"
    is_follow_up: bool = False
    context_dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationTurn':
        return cls(**data)


@dataclass
class Entity:
    """یک entity در گفتگو"""
    name: str
    entity_type: str  # e.g., 'fund', 'person', 'organization', 'concept'
    first_mentioned: float
    last_mentioned: float
    mention_count: int = 1
    attributes: Dict[str, Any] = field(default_factory=dict)
    aliases: List[str] = field(default_factory=list)
    related_entities: List[str] = field(default_factory=list)
    
    def update_mention(self, timestamp: float):
        self.last_mentioned = timestamp
        self.mention_count += 1


@dataclass
class Topic:
    """یک موضوع در گفتگو"""
    name: str
    keywords: List[str]
    first_discussed: float
    last_discussed: float
    discussion_count: int = 1
    sub_topics: List[str] = field(default_factory=list)
    related_entities: List[str] = field(default_factory=list)
    
    def update_discussion(self, timestamp: float):
        self.last_discussed = timestamp
        self.discussion_count += 1


@dataclass
class MemoryContext:
    """Context حاصل از حافظه برای یک query"""
    relevant_turns: List[ConversationTurn]
    active_entities: List[Entity]
    current_topic: Optional[Topic]
    topic_history: List[str]
    coreference_resolutions: Dict[str, str]  # e.g., {"این": "صندوق نوآور"}
    inferred_intent: str
    conversation_summary: str
    context_confidence: float


# =============================================================================
# Short-Term Memory (STM)
# =============================================================================

class ShortTermMemory:
    """
    حافظه کوتاه‌مدت
    نگهداری آخرین turns گفتگو و entities فعال
    """
    
    def __init__(self, max_turns: int = 10, decay_rate: float = 0.1):
        self.max_turns = max_turns
        self.decay_rate = decay_rate
        self.turns: List[ConversationTurn] = []
        self.active_entities: Dict[str, Entity] = {}
        self.current_topic: Optional[Topic] = None
        self.topic_stack: List[str] = []  # برای پیگیری تغییر موضوع
    
    def add_turn(self, turn: ConversationTurn):
        """اضافه کردن یک turn جدید"""
        self.turns.append(turn)
        
        # حفظ حداکثر تعداد turns
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]
        
        # به‌روزرسانی entities فعال
        for entity_name in turn.entities:
            if entity_name in self.active_entities:
                self.active_entities[entity_name].update_mention(turn.timestamp)
            else:
                self.active_entities[entity_name] = Entity(
                    name=entity_name,
                    entity_type="unknown",
                    first_mentioned=turn.timestamp,
                    last_mentioned=turn.timestamp
                )
        
        # به‌روزرسانی topic
        if turn.topics:
            self._update_topic(turn.topics[0], turn.timestamp)
    
    def _update_topic(self, topic_name: str, timestamp: float):
        """به‌روزرسانی موضوع فعلی"""
        if self.current_topic and self.current_topic.name != topic_name:
            # تغییر موضوع
            self.topic_stack.append(self.current_topic.name)
            if len(self.topic_stack) > 5:
                self.topic_stack = self.topic_stack[-5:]
        
        if self.current_topic and self.current_topic.name == topic_name:
            self.current_topic.update_discussion(timestamp)
        else:
            self.current_topic = Topic(
                name=topic_name,
                keywords=[],
                first_discussed=timestamp,
                last_discussed=timestamp
            )
    
    def get_recent_turns(self, n: int = 5) -> List[ConversationTurn]:
        """دریافت آخرین n turn"""
        return self.turns[-n:]
    
    def get_active_entities(self, min_mentions: int = 1) -> List[Entity]:
        """دریافت entities فعال"""
        return [e for e in self.active_entities.values() 
                if e.mention_count >= min_mentions]
    
    def get_context_window(self) -> str:
        """دریافت context window متنی"""
        if not self.turns:
            return ""
        
        context_parts = []
        for turn in self.turns[-5:]:
            context_parts.append(f"کاربر: {turn.user_query}")
            if turn.assistant_response:
                # خلاصه پاسخ اگر خیلی طولانی باشد
                response = turn.assistant_response
                if len(response) > 300:
                    response = response[:300] + "..."
                context_parts.append(f"دستیار: {response}")
        
        return "\n".join(context_parts)
    
    def decay_entities(self):
        """کاهش اهمیت entities قدیمی"""
        current_time = time.time()
        entities_to_remove = []
        
        for name, entity in self.active_entities.items():
            age = current_time - entity.last_mentioned
            # اگر بیش از 5 دقیقه از آخرین mention گذشته
            if age > 300:
                entities_to_remove.append(name)
        
        for name in entities_to_remove:
            del self.active_entities[name]


# =============================================================================
# Long-Term Memory (LTM)
# =============================================================================

class LongTermMemory:
    """
    حافظه بلندمدت
    نگهداری facts مهم، preferences کاربر و اطلاعات استخراج‌شده
    """
    
    def __init__(self):
        self.facts: Dict[str, Dict[str, Any]] = {}  # key -> {fact, source, confidence, timestamp}
        self.user_preferences: Dict[str, Any] = {}
        self.entity_knowledge: Dict[str, Entity] = {}
        self.conversation_summaries: List[Dict] = []
    
    def store_fact(self, key: str, fact: str, source: str, confidence: float = 1.0):
        """ذخیره یک fact"""
        self.facts[key] = {
            'fact': fact,
            'source': source,
            'confidence': confidence,
            'timestamp': time.time()
        }
    
    def get_fact(self, key: str) -> Optional[str]:
        """دریافت یک fact"""
        if key in self.facts:
            return self.facts[key]['fact']
        return None
    
    def store_entity(self, entity: Entity):
        """ذخیره entity در حافظه بلندمدت"""
        self.entity_knowledge[entity.name] = entity
    
    def get_entity(self, name: str) -> Optional[Entity]:
        """دریافت entity"""
        return self.entity_knowledge.get(name)
    
    def update_user_preference(self, key: str, value: Any):
        """به‌روزرسانی preference کاربر"""
        self.user_preferences[key] = {
            'value': value,
            'timestamp': time.time()
        }
    
    def add_conversation_summary(self, summary: Dict):
        """اضافه کردن خلاصه گفتگو"""
        self.conversation_summaries.append({
            **summary,
            'timestamp': time.time()
        })
        
        # حفظ حداکثر 50 خلاصه
        if len(self.conversation_summaries) > 50:
            self.conversation_summaries = self.conversation_summaries[-50:]
    
    def search_relevant_facts(self, query: str, top_k: int = 5) -> List[Dict]:
        """جستجوی facts مرتبط با query"""
        relevant = []
        query_lower = query.lower()
        
        for key, fact_data in self.facts.items():
            if any(word in key.lower() or word in fact_data['fact'].lower() 
                   for word in query_lower.split()):
                relevant.append({
                    'key': key,
                    **fact_data
                })
        
        # مرتب‌سازی بر اساس confidence و timestamp
        relevant.sort(key=lambda x: (x['confidence'], x['timestamp']), reverse=True)
        return relevant[:top_k]


# =============================================================================
# Semantic Memory
# =============================================================================

class SemanticMemory:
    """
    حافظه معنایی
    استفاده از embeddings برای درک بهتر context
    """
    
    def __init__(self, embedding_service=None):
        self.embedding_service = embedding_service
        self.topic_embeddings: Dict[str, np.ndarray] = {}
        self.entity_embeddings: Dict[str, np.ndarray] = {}
        self.turn_embeddings: List[Tuple[str, np.ndarray]] = []  # (turn_id, embedding)
    
    def compute_embedding(self, text: str) -> Optional[np.ndarray]:
        """محاسبه embedding برای متن"""
        if self.embedding_service:
            try:
                return self.embedding_service.get_embedding(text)
            except Exception as e:
                logger.warning(f"Failed to compute embedding: {e}")
        return None
    
    def store_turn_embedding(self, turn_id: str, text: str):
        """ذخیره embedding یک turn"""
        embedding = self.compute_embedding(text)
        if embedding is not None:
            self.turn_embeddings.append((turn_id, embedding))
            # حفظ حداکثر 100 embedding
            if len(self.turn_embeddings) > 100:
                self.turn_embeddings = self.turn_embeddings[-100:]
    
    def find_similar_turns(self, query: str, top_k: int = 3) -> List[str]:
        """یافتن turns مشابه با query"""
        if not self.turn_embeddings:
            return []
        
        query_embedding = self.compute_embedding(query)
        if query_embedding is None:
            return []
        
        # محاسبه similarity
        similarities = []
        for turn_id, turn_embedding in self.turn_embeddings:
            similarity = np.dot(query_embedding, turn_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(turn_embedding) + 1e-8
            )
            similarities.append((turn_id, similarity))
        
        # مرتب‌سازی و برگرداندن top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [turn_id for turn_id, _ in similarities[:top_k]]


# =============================================================================
# Entity Tracker
# =============================================================================

class EntityTracker:
    """
    پیگیری entities در گفتگو
    """
    
    def __init__(self):
        # تعریف entity types و patterns
        self.entity_patterns = {
            'fund': [
                (r'صندوق\s*(نوآور|باور|تبادل\s*فناوری)', 'صندوق {}'),
                (r'(نوآور|باور)\s*کپیتال', 'صندوق {}'),
                (r'(تبادل\s*فناوری)', 'صندوق تبادل فناوری'),
            ],
            'financial': [
                (r'(\d+)\s*(میلیون|میلیارد|تومان|ریال)', 'مبلغ {}'),
                (r'(بودجه|سرمایه|پرداخت)', '{}'),
            ],
            'process': [
                (r'(مرحله|فاز)\s*(\d+|اول|دوم|سوم)', '{} {}'),
                (r'(ثبت\s*نام|درخواست|ارسال)', '{}'),
            ],
            'concept': [
                (r'(ایده|طرح|پروژه|استارتاپ|شرکت)', '{}'),
                (r'(mvp|نمونه\s*اولیه|محصول)', '{}'),
            ],
        }
        
        # کلمات ارجاعی (pronouns/demonstratives)
        self.reference_words = {
            'این': 'this',
            'آن': 'that',
            'اون': 'that',
            'اینا': 'these',
            'اونا': 'those',
            'اینها': 'these',
            'آنها': 'those',
            'همین': 'this_same',
            'همون': 'that_same',
        }
    
    def extract_entities(self, text: str) -> List[Tuple[str, str]]:
        """استخراج entities از متن"""
        entities = []
        text_lower = text.lower()
        
        for entity_type, patterns in self.entity_patterns.items():
            for pattern, template in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        entity_name = template.format(*match)
                    else:
                        entity_name = template.format(match)
                    entities.append((entity_name, entity_type))
        
        return entities
    
    def detect_references(self, text: str) -> List[str]:
        """تشخیص کلمات ارجاعی در متن"""
        references = []
        for ref_word in self.reference_words:
            if ref_word in text:
                references.append(ref_word)
        return references
    
    def resolve_references(
        self, 
        text: str, 
        recent_entities: List[Entity]
    ) -> Dict[str, str]:
        """حل ارجاعات با استفاده از entities اخیر"""
        resolutions = {}
        references = self.detect_references(text)
        
        if not references or not recent_entities:
            return resolutions
        
        # مرتب‌سازی entities بر اساس آخرین mention
        sorted_entities = sorted(
            recent_entities, 
            key=lambda e: e.last_mentioned, 
            reverse=True
        )
        
        for ref in references:
            # ساده‌ترین استراتژی: آخرین entity مرتبط
            if sorted_entities:
                resolutions[ref] = sorted_entities[0].name
        
        return resolutions


# =============================================================================
# Topic Tracker
# =============================================================================

class TopicTracker:
    """
    پیگیری موضوعات در گفتگو
    """
    
    def __init__(self):
        # تعریف موضوعات و کلمات کلیدی
        self.topic_keywords = {
            'صندوق_نوآور': ['نوآور', 'noavar', 'ایده خام', 'mvp', 'نمونه اولیه', 'ایده اولیه'],
            'صندوق_باور': ['باور', 'bavar', 'سرمایه‌گذاری', 'استارتاپ', 'شرکت', 'سهام'],
            'صندوق_تبادل_فناوری': ['تبادل فناوری', 'rfp', 'فراخوان', 'نیاز فناورانه', 'پروژه صنعتی'],
            'پرداخت_مالی': ['پرداخت', 'پول', 'مبلغ', 'بودجه', 'تومان', 'ریال', 'هزینه', 'مالی'],
            'مراحل_همکاری': ['مرحله', 'فاز', 'مراحل', 'فرآیند', 'روند', 'گام'],
            'ثبت_نام': ['ثبت نام', 'درخواست', 'ارسال', 'اپلای', 'apply'],
            'ارزیابی': ['ارزیابی', 'داوری', 'بررسی', 'تایید', 'رد'],
            'مدارک': ['مدارک', 'مستندات', 'فرم', 'پروپوزال', 'طرح'],
            'تیم': ['تیم', 'اعضا', 'همکار', 'شریک'],
        }
    
    def detect_topic(self, text: str) -> Optional[str]:
        """تشخیص موضوع از متن"""
        text_lower = text.lower()
        topic_scores = {}
        
        for topic, keywords in self.topic_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                topic_scores[topic] = score
        
        if topic_scores:
            return max(topic_scores, key=topic_scores.get)
        return None
    
    def detect_topic_change(
        self, 
        current_topic: Optional[str], 
        new_text: str
    ) -> Tuple[bool, Optional[str]]:
        """تشخیص تغییر موضوع"""
        new_topic = self.detect_topic(new_text)
        
        if new_topic and new_topic != current_topic:
            return True, new_topic
        return False, current_topic


# =============================================================================
# Conversation Memory Manager (Main Class)
# =============================================================================

class ConversationMemoryManager:
    """
    مدیریت کننده اصلی حافظه گفتگو
    ترکیب تمام components برای ارائه context هوشمند
    """
    
    def __init__(self, embedding_service=None):
        # Initialize components
        self.stm = ShortTermMemory(max_turns=10)
        self.ltm = LongTermMemory()
        self.semantic_memory = SemanticMemory(embedding_service)
        self.entity_tracker = EntityTracker()
        self.topic_tracker = TopicTracker()
        
        # Conversation sessions
        self.sessions: Dict[str, Dict] = {}
        
        logger.info("🧠 ConversationMemoryManager initialized")
    
    def get_or_create_session(self, conversation_id: str) -> Dict:
        """دریافت یا ایجاد session جدید"""
        if conversation_id not in self.sessions:
            self.sessions[conversation_id] = {
                'stm': ShortTermMemory(max_turns=10),
                'created_at': time.time(),
                'last_activity': time.time(),
                'turn_count': 0
            }
            logger.info(f"📝 New conversation session created: {conversation_id}")
        
        self.sessions[conversation_id]['last_activity'] = time.time()
        return self.sessions[conversation_id]
    
    def process_turn(
        self,
        conversation_id: str,
        user_query: str,
        assistant_response: str
    ) -> ConversationTurn:
        """پردازش یک turn جدید از گفتگو"""
        session = self.get_or_create_session(conversation_id)
        stm = session['stm']
        
        # Generate turn ID
        turn_id = f"{conversation_id}_{session['turn_count']}"
        session['turn_count'] += 1
        
        # Extract entities
        user_entities = self.entity_tracker.extract_entities(user_query)
        response_entities = self.entity_tracker.extract_entities(assistant_response)
        all_entities = list(set([e[0] for e in user_entities + response_entities]))
        
        # Detect topic
        topic = self.topic_tracker.detect_topic(user_query + " " + assistant_response)
        topics = [topic] if topic else []
        
        # Detect if follow-up
        is_follow_up = self._is_follow_up(user_query, stm)
        
        # Detect context dependencies
        references = self.entity_tracker.detect_references(user_query)
        
        # Create turn
        turn = ConversationTurn(
            turn_id=turn_id,
            user_query=user_query,
            assistant_response=assistant_response,
            timestamp=time.time(),
            entities=all_entities,
            topics=topics,
            is_follow_up=is_follow_up,
            context_dependencies=references
        )
        
        # Add to STM
        stm.add_turn(turn)
        
        # Store embedding
        combined_text = f"{user_query} {assistant_response}"
        self.semantic_memory.store_turn_embedding(turn_id, combined_text)
        
        # Extract and store facts
        self._extract_and_store_facts(turn)
        
        logger.info(f"💬 Turn processed: {turn_id}, entities: {all_entities}, topic: {topic}")
        
        return turn
    
    def _is_follow_up(self, query: str, stm: ShortTermMemory) -> bool:
        """تشخیص اینکه آیا query یک follow-up است"""
        if not stm.turns:
            return False
        
        query_lower = query.lower().strip()
        
        # کلمات نشان‌دهنده follow-up
        follow_up_indicators = [
            'این', 'آن', 'اون', 'اینا', 'اونا', 'اینها', 'آنها',
            'خب', 'پس', 'بعد', 'بعدش',
            'کدوم', 'کدام', 'کدومش',
            'چطور', 'چجور', 'چرا',
        ]
        
        for indicator in follow_up_indicators:
            if indicator in query_lower:
                return True
        
        # سوالات خیلی کوتاه معمولاً follow-up هستند
        if len(query.split()) <= 4:
            return True
        
        return False
    
    def _extract_and_store_facts(self, turn: ConversationTurn):
        """استخراج و ذخیره facts از turn"""
        # استخراج facts از پاسخ assistant
        response = turn.assistant_response
        
        # الگوهای fact
        fact_patterns = [
            (r'صندوق\s+(\S+)\s+(هیچ\s+)?پیش\s*پرداختی\s+(نمی\s*دهد|ندارد)', 
             'پیش_پرداخت_{}', 'صندوق {} پیش‌پرداختی ندارد'),
            (r'بعد\s+از\s+تحویل\s+.*?مرحله.*?پرداخت', 
             'نحوه_پرداخت', 'پرداخت بعد از تحویل هر مرحله انجام می‌شود'),
        ]
        
        for pattern, key_template, fact_template in fact_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                groups = match.groups()
                if groups:
                    key = key_template.format(groups[0] if groups[0] else '')
                    fact = fact_template.format(groups[0] if groups[0] else '')
                else:
                    key = key_template
                    fact = fact_template
                
                self.ltm.store_fact(key, fact, turn.turn_id)
    
    def get_context_for_query(
        self,
        conversation_id: str,
        query: str
    ) -> MemoryContext:
        """
        دریافت context کامل برای یک query جدید
        این متد اصلی‌ترین API برای استفاده در RAG pipeline است
        """
        session = self.get_or_create_session(conversation_id)
        stm = session['stm']
        
        # دریافت turns اخیر
        recent_turns = stm.get_recent_turns(5)
        
        # دریافت entities فعال
        active_entities = stm.get_active_entities()
        
        # تشخیص موضوع فعلی
        current_topic = stm.current_topic
        topic_history = stm.topic_stack.copy()
        
        # حل ارجاعات
        coreference_resolutions = self.entity_tracker.resolve_references(
            query, active_entities
        )
        
        # تشخیص intent
        inferred_intent = self._infer_intent(query, recent_turns)
        
        # ساخت خلاصه گفتگو
        conversation_summary = self._build_conversation_summary(recent_turns, current_topic)
        
        # محاسبه confidence
        context_confidence = self._calculate_context_confidence(
            query, recent_turns, active_entities, current_topic
        )
        
        return MemoryContext(
            relevant_turns=recent_turns,
            active_entities=active_entities,
            current_topic=current_topic,
            topic_history=topic_history,
            coreference_resolutions=coreference_resolutions,
            inferred_intent=inferred_intent,
            conversation_summary=conversation_summary,
            context_confidence=context_confidence
        )
    
    def _infer_intent(
        self, 
        query: str, 
        recent_turns: List[ConversationTurn]
    ) -> str:
        """استنتاج intent از query و context"""
        query_lower = query.lower()
        
        # الگوهای intent
        intent_patterns = {
            'ask_amount': [r'چقدر', r'چند', r'مبلغ', r'مقدار'],
            'ask_process': [r'چطور', r'چجور', r'مراحل', r'روند'],
            'ask_requirements': [r'مدارک', r'شرایط', r'چی لازم'],
            'ask_eligibility': [r'آیا می‌توانم', r'شرایط', r'واجد شرایط'],
            'ask_comparison': [r'فرق', r'تفاوت', r'مقایسه', r'بهتر'],
            'follow_up': [r'^خب', r'^پس', r'^بعد'],
            'clarification': [r'^یعنی', r'^منظور'],
        }
        
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent
        
        # اگر follow-up است
        if recent_turns and len(query.split()) <= 4:
            return 'follow_up'
        
        return 'general_question'
    
    def _build_conversation_summary(
        self,
        recent_turns: List[ConversationTurn],
        current_topic: Optional[Topic]
    ) -> str:
        """ساخت خلاصه گفتگو"""
        if not recent_turns:
            return ""
        
        parts = []
        
        # موضوع فعلی
        if current_topic:
            parts.append(f"موضوع فعلی گفتگو: {current_topic.name}")
        
        # تعداد turns
        parts.append(f"تعداد پیام‌های اخیر: {len(recent_turns)}")
        
        # آخرین سوال
        if recent_turns:
            last_query = recent_turns[-1].user_query
            if len(last_query) > 50:
                last_query = last_query[:50] + "..."
            parts.append(f"آخرین سوال: {last_query}")
        
        # entities فعال
        all_entities = set()
        for turn in recent_turns:
            all_entities.update(turn.entities)
        if all_entities:
            parts.append(f"موضوعات مطرح‌شده: {', '.join(list(all_entities)[:5])}")
        
        return " | ".join(parts)
    
    def _calculate_context_confidence(
        self,
        query: str,
        recent_turns: List[ConversationTurn],
        active_entities: List[Entity],
        current_topic: Optional[Topic]
    ) -> float:
        """محاسبه confidence برای context"""
        confidence = 0.5  # Base confidence
        
        # اگر turns اخیر داریم
        if recent_turns:
            confidence += 0.1 * min(len(recent_turns), 5) / 5
        
        # اگر entities فعال داریم
        if active_entities:
            confidence += 0.1
        
        # اگر موضوع مشخص است
        if current_topic:
            confidence += 0.1
        
        # اگر query خیلی کوتاه است و context داریم
        if len(query.split()) <= 4 and recent_turns:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def enrich_query_with_context(
        self,
        conversation_id: str,
        query: str
    ) -> Dict[str, Any]:
        """
        غنی‌سازی query با context از حافظه
        """
        context = self.get_context_for_query(conversation_id, query)
        
        enriched_query = query
        context_additions = []
        
        # حل ارجاعات
        if context.coreference_resolutions:
            for ref, resolution in context.coreference_resolutions.items():
                if ref in query:
                    enriched_query = enriched_query.replace(ref, f"{ref} ({resolution})")
                    context_additions.append(f"'{ref}' → '{resolution}'")
        
        # اضافه کردن context موضوع
        if context.current_topic and len(query.split()) <= 4:
            topic_name = context.current_topic.name.replace('_', ' ')
            if topic_name not in query.lower():
                enriched_query = f"{query} (در مورد {topic_name})"
                context_additions.append(f"topic: {topic_name}")
        
        # اگر سوال در مورد پول/پرداخت است و صندوق مشخص است
        if any(kw in query.lower() for kw in ['پول', 'پرداخت', 'چقدر', 'مبلغ']):
            for entity in context.active_entities:
                if 'صندوق' in entity.name.lower():
                    if entity.name not in enriched_query:
                        enriched_query = f"در {entity.name}، {query}"
                        context_additions.append(f"entity: {entity.name}")
                    break
        
        logger.info(f"🔄 Query enrichment: '{query}' → '{enriched_query}'")
        if context_additions:
            logger.info(f"   Context additions: {context_additions}")
        
        return {
            'original_query': query,
            'enriched_query': enriched_query,
            'context': context,
            'context_additions': context_additions,
            'context_confidence': context.context_confidence
        }
    
    def get_prompt_context(
        self,
        conversation_id: str,
        query: str
    ) -> str:
        """
        دریافت context برای اضافه کردن به prompt
        """
        context = self.get_context_for_query(conversation_id, query)
        
        if not context.relevant_turns:
            return ""
        
        prompt_parts = []
        
        # Header
        prompt_parts.append("\n\n📜 **بافت گفتگوی قبلی:**")
        
        # موضوع فعلی
        if context.current_topic:
            topic_name = context.current_topic.name.replace('_', ' ')
            prompt_parts.append(f"🎯 **موضوع فعلی**: {topic_name}")
        
        # ارجاعات
        if context.coreference_resolutions:
            refs = [f"'{k}' = '{v}'" for k, v in context.coreference_resolutions.items()]
            prompt_parts.append(f"🔗 **ارجاعات**: {', '.join(refs)}")
        
        # Intent
        if context.inferred_intent:
            prompt_parts.append(f"💡 **نوع سوال**: {context.inferred_intent}")
        
        # تاریخچه
        prompt_parts.append("\n**گفتگوی اخیر:**")
        for i, turn in enumerate(context.relevant_turns[-3:], 1):
            user_q = turn.user_query
            if len(user_q) > 100:
                user_q = user_q[:100] + "..."
            prompt_parts.append(f"  {i}. کاربر: {user_q}")
            
            if turn.assistant_response:
                resp = turn.assistant_response
                if len(resp) > 200:
                    resp = resp[:200] + "..."
                prompt_parts.append(f"     دستیار: {resp}")
        
        # دستورالعمل
        prompt_parts.append("\n⚠️ **توجه**: سوال فعلی در ادامه گفتگوی بالا است. از context استفاده کن.")
        
        return "\n".join(prompt_parts)
    
    def cleanup_old_sessions(self, max_age_seconds: int = 3600):
        """پاک‌سازی sessions قدیمی"""
        current_time = time.time()
        sessions_to_remove = []
        
        for session_id, session in self.sessions.items():
            age = current_time - session['last_activity']
            if age > max_age_seconds:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
            logger.info(f"🗑️ Cleaned up old session: {session_id}")
        
        return len(sessions_to_remove)


# =============================================================================
# Factory Function
# =============================================================================

def create_conversation_memory_manager(embedding_service=None) -> ConversationMemoryManager:
    """Factory function برای ایجاد ConversationMemoryManager"""
    return ConversationMemoryManager(embedding_service)


# =============================================================================
# Test
# =============================================================================

if __name__ == "__main__":
    # تست ساده
    logging.basicConfig(level=logging.INFO)
    
    manager = ConversationMemoryManager()
    conv_id = "test_conv_1"
    
    # شبیه‌سازی گفتگو
    turns = [
        ("سلام من یه طرح بسیار جذاب دارم چیکار کنم؟", 
         "برای ارسال طرح، ابتدا باید نوع ایده را مشخص کنید. اگر ایده شما خام است، صندوق نوآور مناسب شماست."),
        ("ایده م خیلی خامه",
         "عالی! صندوق نوآور ایده‌های خام را می‌پذیرد و به شما کمک می‌کند تا آن را به MVP تبدیل کنید."),
        ("خب مرحله به مرحله بگو چیکار کنم؟",
         "مراحل کار با صندوق نوآور: 1. ثبت‌نام در سامانه 2. ارسال پروپوزال 3. ارزیابی 4. عقد قرارداد"),
        ("چقدر پول میدید؟",
         "صندوق هیچ پیش پرداختی نمی دهد. پرداخت بعد از تحویل هر مرحله انجام می‌شود.")
    ]
    
    for user_q, assistant_r in turns:
        turn = manager.process_turn(conv_id, user_q, assistant_r)
        print(f"\n✅ Processed: {turn.turn_id}")
        print(f"   Entities: {turn.entities}")
        print(f"   Topics: {turn.topics}")
        print(f"   Is follow-up: {turn.is_follow_up}")
    
    # تست context
    print("\n" + "="*60)
    print("Testing context for new query...")
    
    enrichment = manager.enrich_query_with_context(conv_id, "این چقدر طول میکشه؟")
    print(f"\nEnriched query: {enrichment['enriched_query']}")
    print(f"Context confidence: {enrichment['context_confidence']:.2f}")
    
    prompt_context = manager.get_prompt_context(conv_id, "این چقدر طول میکشه؟")
    print(f"\nPrompt context:\n{prompt_context}")

