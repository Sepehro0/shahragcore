# -*- coding: utf-8 -*-
"""
Collection Manager
Manages collection-specific configurations and metadata
"""

import logging
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class CollectionType(str, Enum):
    """Types of collections"""
    FINANCIAL = "financial"         # Budget, income, expenses
    QA = "qa"                       # Question/Answer datasets
    BOOKLET = "booklet"             # Legal documents with articles
    GENERAL = "general"             # General documents


@dataclass
class CollectionConfig:
    """Configuration for a collection"""
    name: str
    collection_type: CollectionType
    domain: str = "general"
    
    # Routing configuration
    use_database: bool = False
    use_rag: bool = True
    
    # Schema information
    schema_info: Dict[str, Any] = field(default_factory=dict)
    column_mapping: Dict[str, str] = field(default_factory=dict)
    
    # Processing configuration
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # Search configuration
    default_top_k: int = 5
    use_reranking: bool = True
    
    # Additional metadata
    created_at: Optional[str] = None
    document_count: int = 0
    total_chunks: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "collection_type": self.collection_type.value,
            "domain": self.domain,
            "use_database": self.use_database,
            "use_rag": self.use_rag,
            "schema_info": self.schema_info,
            "column_mapping": self.column_mapping,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "default_top_k": self.default_top_k,
            "use_reranking": self.use_reranking,
            "created_at": self.created_at,
            "document_count": self.document_count,
            "total_chunks": self.total_chunks
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollectionConfig":
        """Create from dictionary"""
        return cls(
            name=data.get("name", ""),
            collection_type=CollectionType(data.get("collection_type", "general")),
            domain=data.get("domain", "general"),
            use_database=data.get("use_database", False),
            use_rag=data.get("use_rag", True),
            schema_info=data.get("schema_info", {}),
            column_mapping=data.get("column_mapping", {}),
            chunk_size=data.get("chunk_size", 500),
            chunk_overlap=data.get("chunk_overlap", 50),
            default_top_k=data.get("default_top_k", 5),
            use_reranking=data.get("use_reranking", True),
            created_at=data.get("created_at"),
            document_count=data.get("document_count", 0),
            total_chunks=data.get("total_chunks", 0)
        )


class CollectionManager:
    """
    Manages collection configurations and provides collection-specific behaviors.
    """
    
    # Patterns for auto-detecting collection types
    TYPE_PATTERNS = {
        CollectionType.FINANCIAL: [
            "finance", "budget", "بودجه", "مالی", "هزینه", "درآمد", 
            "cost", "income", "expense"
        ],
        CollectionType.QA: [
            "qa", "question", "faq", "پرسش", "سوال", "پاسخ"
        ],
        CollectionType.BOOKLET: [
            "booklet", "law", "legal", "قانون", "ماده", "آیین",
            "regulation", "rule"
        ]
    }
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the CollectionManager.
        
        Args:
            config_dir: Directory to store collection configurations
        """
        self.config_dir = Path(config_dir) if config_dir else None
        self.collections: Dict[str, CollectionConfig] = {}
        
        # Load existing configurations
        if self.config_dir and self.config_dir.exists():
            self._load_configs()
    
    def _load_configs(self):
        """Load collection configurations from disk"""
        if not self.config_dir:
            return
        
        config_file = self.config_dir / "collections.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for name, config_data in data.items():
                        self.collections[name] = CollectionConfig.from_dict(config_data)
                logger.info(f"Loaded {len(self.collections)} collection configurations")
            except Exception as e:
                logger.warning(f"Failed to load collection configs: {e}")
    
    def _save_configs(self):
        """Save collection configurations to disk"""
        if not self.config_dir:
            return
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        config_file = self.config_dir / "collections.json"
        
        try:
            data = {name: config.to_dict() for name, config in self.collections.items()}
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save collection configs: {e}")
    
    def get_collection_domain(self, collection_name: str) -> Dict[str, Any]:
        """
        Get domain info for a collection
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dict with domain info
        """
        # Default domain info
        domain_map = {
            'zabete_qa': {'domain': 'legal', 'confidence': 1.0},
            'karbaran_omomi': {'domain': 'educational', 'confidence': 1.0},
            'zinaf_dakheli': {'domain': 'educational', 'confidence': 1.0},
            'budget_financial': {'domain': 'financial', 'confidence': 1.0},
            'budget_tables': {'domain': 'financial', 'confidence': 1.0},
            'qovve_new': {'domain': 'legal', 'confidence': 1.0},
        }
        
        return domain_map.get(collection_name, {'domain': 'general', 'confidence': 0.5})
    
    def detect_collection_type(self, collection_name: str) -> CollectionType:
        """
        Auto-detect collection type based on name patterns.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Detected CollectionType
        """
        name_lower = collection_name.lower()
        
        for coll_type, patterns in self.TYPE_PATTERNS.items():
            if any(pattern in name_lower for pattern in patterns):
                return coll_type
        
        return CollectionType.GENERAL
    
    def get_or_create_config(
        self,
        collection_name: str,
        **kwargs
    ) -> CollectionConfig:
        """
        Get existing config or create a new one.
        
        Args:
            collection_name: Name of the collection
            **kwargs: Additional configuration options
            
        Returns:
            CollectionConfig for the collection
        """
        if collection_name in self.collections:
            config = self.collections[collection_name]
            # Update with any new kwargs
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            return config
        
        # Create new config
        collection_type = kwargs.get(
            'collection_type',
            self.detect_collection_type(collection_name)
        )
        
        config = CollectionConfig(
            name=collection_name,
            collection_type=collection_type,
            domain=self._get_domain_for_type(collection_type),
            use_database=collection_type == CollectionType.FINANCIAL,
            use_rag=True,
            **{k: v for k, v in kwargs.items() if k not in ['collection_type']}
        )
        
        self.collections[collection_name] = config
        self._save_configs()
        
        logger.info(f"Created config for collection '{collection_name}': type={collection_type.value}")
        return config
    
    def _get_domain_for_type(self, collection_type: CollectionType) -> str:
        """Get domain name for collection type"""
        type_to_domain = {
            CollectionType.FINANCIAL: "financial",
            CollectionType.QA: "qa",
            CollectionType.BOOKLET: "legal",
            CollectionType.GENERAL: "general"
        }
        return type_to_domain.get(collection_type, "general")
    
    def update_config(
        self,
        collection_name: str,
        **updates
    ) -> Optional[CollectionConfig]:
        """
        Update an existing collection configuration.
        
        Args:
            collection_name: Name of the collection
            **updates: Fields to update
            
        Returns:
            Updated CollectionConfig or None if not found
        """
        if collection_name not in self.collections:
            logger.warning(f"Collection '{collection_name}' not found")
            return None
        
        config = self.collections[collection_name]
        
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        self._save_configs()
        return config
    
    def set_schema_info(
        self,
        collection_name: str,
        schema_info: Dict[str, Any],
        column_mapping: Dict[str, str]
    ):
        """
        Set schema information for a collection.
        
        Args:
            collection_name: Name of the collection
            schema_info: Schema analysis result
            column_mapping: Column name mapping
        """
        if collection_name in self.collections:
            config = self.collections[collection_name]
            config.schema_info = schema_info
            config.column_mapping = column_mapping
            self._save_configs()
    
    def get_config(self, collection_name: str) -> Optional[CollectionConfig]:
        """
        Get configuration for a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            CollectionConfig or None if not found
        """
        return self.collections.get(collection_name)
    
    def should_use_database(self, collection_name: str) -> bool:
        """
        Check if a collection should use database queries.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            True if database should be used
        """
        config = self.get_config(collection_name)
        if config:
            return config.use_database
        
        # Default based on auto-detection
        collection_type = self.detect_collection_type(collection_name)
        return collection_type == CollectionType.FINANCIAL
    
    def get_routing_strategy(
        self,
        collection_name: str
    ) -> Dict[str, Any]:
        """
        Get the routing strategy for a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dictionary with routing strategy
        """
        config = self.get_or_create_config(collection_name)
        
        return {
            "collection_type": config.collection_type.value,
            "use_database": config.use_database,
            "use_rag": config.use_rag,
            "domain": config.domain,
            "default_top_k": config.default_top_k,
            "use_reranking": config.use_reranking
        }
    
    def list_collections(self) -> List[str]:
        """List all configured collections"""
        return list(self.collections.keys())
    
    def delete_config(self, collection_name: str) -> bool:
        """
        Delete a collection configuration.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            True if deleted, False if not found
        """
        if collection_name in self.collections:
            del self.collections[collection_name]
            self._save_configs()
            return True
        return False

