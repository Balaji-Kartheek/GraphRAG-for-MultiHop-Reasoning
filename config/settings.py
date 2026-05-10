"""
Configuration settings for GraphRAG system
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional, List
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

    # LLM provider configuration
    llm_provider: str = Field(default="ollama", env="LLM_PROVIDER")
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.1:8b", env="OLLAMA_MODEL")
    
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
    # Delay in seconds between Gemini API calls to avoid 429 rate limit (free tier: ~20/day, low RPM).
    gemini_delay_seconds: int = Field(default=18, env="GEMINI_DELAY_SECONDS")
    gemini_max_calls_per_run: int = Field(default=10, env="GEMINI_MAX_CALLS_PER_RUN")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    
    # Streamlit Configuration
    streamlit_port: int = Field(default=8501, env="STREAMLIT_PORT")
    
    # Scheduled Entries Limit
    fetch_limit_per_run: int = Field(default=100, env="FETCH_LIMIT_PER_RUN")

    # In-process scheduler: interval for pipeline runs. Use minutes for testing (e.g. 5), hours for production.
    # If SCHEDULER_INTERVAL_MINUTES > 0, it takes precedence; else SCHEDULER_INTERVAL_HOURS is used.
    scheduler_interval_minutes: int = Field(default=0, env="SCHEDULER_INTERVAL_MINUTES")
    scheduler_interval_hours: float = Field(default=1.0, env="SCHEDULER_INTERVAL_HOURS")
    # Set SCHEDULER_RUN_ON_START=1 to run the pipeline once immediately when scheduler starts (good for testing).
    scheduler_run_on_start: bool = Field(default=False, env="SCHEDULER_RUN_ON_START")
    
    # Logging
    # TODO: Change the log level to INFO for production
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/graphrag.log", env="LOG_FILE")
    
    # Dataset
    dataset_path: str = Field(default="./data/tech_news.csv", env="DATASET_PATH")
    target_articles: int = Field(default=800, env="TARGET_ARTICLES")
    
    # Dynamic fetch (RSS / News API)
    news_api_key: str = Field(default="", env="NEWS_API_KEY")
    rss_feeds: List[str] = Field(default_factory=list, env="RSS_FEEDS")
    fetch_limit_per_run: Optional[int] = Field(default=100, env="FETCH_LIMIT_PER_RUN")
    
    @field_validator("rss_feeds", mode="before")
    @classmethod
    def parse_rss_feeds(cls, v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            if not v.strip():
                return []
            return [u.strip() for u in v.split(",") if u.strip()]
        return []
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings