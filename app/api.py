"""
FastAPI application for GraphRAG system
Provides REST API for querying and system management
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn

from reasoning.multihop import MultiHopReasoner
from generation.answer_generator import AnswerGenerator
from ingestion.fetch_articles import ArticleIngestion
from ingestion.preprocess import ArticlePreprocessor
from extraction.ner import EntityExtractor
from extraction.triple_extractor import TripleExtractor
from graph.graph_builder import GraphBuilder
from vector.chroma_client import ChromaClient
from config.settings import settings
from config.logger import log

# Initialize FastAPI app
app = FastAPI(
    title="GraphRAG API",
    description="Multi-hop reasoning over Tech & AI news using Knowledge Graphs",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
reasoner = MultiHopReasoner()
generator = AnswerGenerator()


# Request/Response Models
class QueryRequest(BaseModel):
    query: str
    graph_depth: Optional[int] = None
    top_k_vector: Optional[int] = None


class QueryResponse(BaseModel):
    answer: str
    reasoning_path: List[str]
    source_articles: List[Dict[str, str]]
    graph_paths: Optional[List[List[str]]] = None
    insufficient_context: bool = False


class SystemStatsResponse(BaseModel):
    total_articles: int
    processed_articles: int
    total_entities: int
    total_triples: int
    graph_nodes: int
    graph_relationships: int
    vector_chunks: int


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "GraphRAG API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Main query endpoint
    
    Performs multi-hop reasoning and returns answer
    """
    try:
        log.info(f"Received query: {request.query}")
        
        # Retrieve context
        context = reasoner.retrieve_context(
            request.query,
            graph_depth=request.graph_depth,
            top_k_vector=request.top_k_vector
        )
        
        # Format context
        formatted_context = reasoner.format_context_for_llm(context)
        
        # Generate answer
        result = generator.generate_query_result(
            request.query,
            context,
            formatted_context
        )
        
        return QueryResponse(
            answer=result.answer,
            reasoning_path=result.reasoning_path,
            source_articles=result.source_articles,
            graph_paths=result.graph_paths,
            insufficient_context=result.insufficient_context
        )
        
    except Exception as e:
        log.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=SystemStatsResponse)
async def get_stats():
    """Get system statistics"""
    try:
        # Initialize clients
        ingestion = ArticleIngestion()
        extractor = EntityExtractor()
        triple_extractor = TripleExtractor()
        graph_builder = GraphBuilder()
        chroma_client = ChromaClient()
        
        # Get stats
        article_stats = {
            "total": ingestion.get_total_count(),
            "processed": ingestion.get_processed_count()
        }
        
        entity_stats = extractor.get_entity_stats()
        triple_stats = triple_extractor.get_triple_stats()
        graph_stats = graph_builder.neo4j_client.get_graph_stats()
        vector_stats = chroma_client.get_collection_stats()
        
        # Close connections
        ingestion.close()
        extractor.close()
        triple_extractor.close()
        graph_builder.close()
        chroma_client.close()
        
        return SystemStatsResponse(
            total_articles=article_stats["total"],
            processed_articles=article_stats["processed"],
            total_entities=entity_stats.get("total_unique_entities", 0),
            total_triples=triple_stats.get("total_triples", 0),
            graph_nodes=graph_stats["total_nodes"],
            graph_relationships=graph_stats["total_relationships"],
            vector_chunks=vector_stats["total_chunks"]
        )
        
    except Exception as e:
        log.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
async def ingest_articles(csv_path: str, limit: Optional[int] = None):
    """Ingest articles from CSV"""
    try:
        ingestion = ArticleIngestion()
        count = ingestion.load_from_csv(csv_path, limit)
        ingestion.close()
        
        return {"status": "success", "articles_ingested": count}
        
    except Exception as e:
        log.error(f"Error ingesting articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/fetch")
async def ingest_from_fetchers(limit: Optional[int] = None):
    """Fetch and ingest articles from RSS/News API. Returns count of newly ingested articles."""
    try:
        ingestion = ArticleIngestion()
        count = ingestion.load_from_fetchers(limit)
        ingestion.close()
        return {"status": "success", "articles_ingested": count}
    except Exception as e:
        log.error(f"Error fetching/ingesting articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/preprocess")
async def preprocess_articles(limit: Optional[int] = None):
    """Preprocess articles"""
    try:
        preprocessor = ArticlePreprocessor()
        count = preprocessor.preprocess_batch(limit)
        preprocessor.close()
        
        return {"status": "success", "articles_preprocessed": count}
        
    except Exception as e:
        log.error(f"Error preprocessing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/extract-entities")
async def extract_entities(limit: Optional[int] = None):
    """Extract entities from articles"""
    try:
        extractor = EntityExtractor()
        count = extractor.extract_batch(limit)
        extractor.close()
        
        return {"status": "success", "articles_processed": count}
        
    except Exception as e:
        log.error(f"Error extracting entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/extract-triples")
async def extract_triples(limit: Optional[int] = None):
    """Extract triples from articles"""
    try:
        extractor = TripleExtractor()
        count = extractor.extract_batch(limit)
        extractor.close()
        
        return {"status": "success", "articles_processed": count}
        
    except Exception as e:
        log.error(f"Error extracting triples: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/build-graph")
async def build_graph(limit: Optional[int] = None):
    """Build knowledge graph"""
    try:
        builder = GraphBuilder()
        stats = builder.build_full_graph(limit)
        builder.close()
        
        return {"status": "success", "stats": stats}
        
    except Exception as e:
        log.error(f"Error building graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/embed")
async def embed_articles(limit: Optional[int] = None):
    """Embed articles into vector database"""
    try:
        chroma_client = ChromaClient()
        stats = chroma_client.embed_batch(limit)
        chroma_client.close()
        
        return {"status": "success", "stats": stats}
        
    except Exception as e:
        log.error(f"Error embedding articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    reasoner.close()
    log.info("API shutdown complete")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower()
    )