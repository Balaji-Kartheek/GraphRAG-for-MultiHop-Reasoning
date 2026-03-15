"""
Configuration settings for GraphRAG system
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # MongoDB Configuration
    mongodb_uri: str = Field(default="mongodb://localhost:27017", env="MONGODB_URI")
    mongodb_db: str = Field(default="graphrag_news", env="MONGODB_DB")
    mongodb_collection: str = Field(default="articles", env="MONGODB_COLLECTION")
    
    # Neo4j Configuration
    neo4j_uri: str = Field(default="bolt://localhost:7687", env="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", env="NEO4J_USER")
    neo4j_password: str = Field(default="password", env="NEO4J_PASSWORD")
    
    # ChromaDB Configuration
    chroma_persist_dir: str = Field(default="./chroma_db", env="CHROMA_PERSIST_DIR")
    chroma_collection: str = Field(default="article_embeddings", env="CHROMA_COLLECTION")
    
    # Gemini API Configuration
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash", env="GEMINI_MODEL")
    
    # Embedding Model
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", 
        env="EMBEDDING_MODEL"
    )
    embedding_dimension: int = Field(default=384, env="EMBEDDING_DIMENSION")
    
    # Chunking Configuration
    chunk_size: int = Field(default=300, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, env="CHUNK_OVERLAP")
    
    # Retrieval Configuration
    top_k_vector: int = Field(default=5, env="TOP_K_VECTOR")
    graph_traversal_depth: int = Field(default=3, env="GRAPH_TRAVERSAL_DEPTH")
    max_graph_paths: int = Field(default=50, env="MAX_GRAPH_PATHS")
    
    # Triple Extraction
    confidence_threshold: float = Field(default=0.8, env="CONFIDENCE_THRESHOLD")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    
    # Streamlit Configuration
    streamlit_port: int = Field(default=8501, env="STREAMLIT_PORT")
    
    # Logging
    # TODO: Change the log level to INFO for production
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/graphrag.log", env="LOG_FILE")
    
    # Dataset
    dataset_path: str = Field(default="./data/tech_news.csv", env="DATASET_PATH")
    target_articles: int = Field(default=800, env="TARGET_ARTICLES")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings