"""
Data models for GraphRAG system
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class Article(BaseModel):
    """Article document model"""
    article_id: str
    title: str
    content: str
    source: str
    date: Optional[str] = None
    url: Optional[str] = None
    processed: bool = False
    entities: Optional[List[str]] = None
    triples_extracted: bool = False
    embedded: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Entity(BaseModel):
    """Named entity model"""
    text: str
    label: str  # ORG, PERSON, PRODUCT, etc.
    start_char: int
    end_char: int


class Triple(BaseModel):
    """Knowledge triple model"""
    subject: str
    relation: str
    object: str
    confidence: float
    article_id: Optional[str] = None
    source_text: Optional[str] = None


class GraphNode(BaseModel):
    """Knowledge graph node"""
    name: str
    type: str  # COMPANY, PERSON, PRODUCT, etc.
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphRelationship(BaseModel):
    """Knowledge graph relationship"""
    subject: str
    relation: str
    object: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class QueryResult(BaseModel):
    """Query result model"""
    answer: str
    reasoning_path: List[str]
    source_articles: List[Dict[str, str]]
    graph_paths: Optional[List[List[str]]] = None
    confidence_score: Optional[float] = None


class GraphPath(BaseModel):
    """Graph traversal path"""
    nodes: List[str]
    relationships: List[str]
    path_length: int


class DocumentChunk(BaseModel):
    """Document chunk for embedding"""
    chunk_id: str
    text: str
    article_id: str
    chunk_index: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalContext(BaseModel):
    """Combined retrieval context"""
    graph_paths: List[GraphPath]
    vector_results: List[DocumentChunk]
    entities_detected: List[str]