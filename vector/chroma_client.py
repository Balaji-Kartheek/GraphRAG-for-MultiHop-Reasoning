"""
ChromaDB client for vector storage and retrieval
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from vector.embeddings import EmbeddingGenerator
from config.settings import settings
from config.logger import log


class ChromaClient:
    """ChromaDB client for vector operations"""
    
    def __init__(self):
        """Initialize ChromaDB client"""
        # Initialize ChromaDB with persistent storage
        self.client = chromadb.Client(ChromaSettings(
            persist_directory=settings.chroma_persist_dir,
            anonymized_telemetry=False
        ))
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
        
        # Initialize embedding generator
        self.embedding_generator = EmbeddingGenerator()
        
        # MongoDB for article metadata
        self.mongo_client = MongoClient(settings.mongodb_uri)
        self.db = self.mongo_client[settings.mongodb_db]
        self.articles_collection = self.db[settings.mongodb_collection]
        
        log.info(f"ChromaDB initialized. Collection: {settings.chroma_collection}")
    
    def add_document_chunks(
        self, 
        chunks: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ):
        """
        Add document chunks to ChromaDB
        
        Args:
            chunks: List of text chunks
            embeddings: List of embedding vectors
            metadatas: List of metadata dicts
            ids: List of unique IDs for chunks
        """
        try:
            self.collection.add(
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            log.debug(f"Added {len(chunks)} chunks to ChromaDB")
        except Exception as e:
            log.error(f"Error adding chunks to ChromaDB: {e}")
            raise
    
    def embed_and_store_article(self, article_id: str) -> int:
        """
        Embed an article and store in ChromaDB
        
        Returns number of chunks created
        """
        # Get article from MongoDB
        article = self.articles_collection.find_one({"article_id": article_id})
        
        if not article:
            log.error(f"Article {article_id} not found")
            return 0
        
        # Check if already embedded
        if article.get("embedded", False):
            log.debug(f"Article {article_id} already embedded")
            return 0
        
        # Prepare text
        title = article.get("title", "")
        content = article.get("content", "")
        full_text = f"{title}. {content}"
        
        # Create metadata
        metadata = {
            "article_id": article_id,
            "source": article.get("source", "unknown"),
            "date": article.get("date", ""),
            "title": title[:100]  # Truncate for storage
        }
        
        # Generate embeddings
        chunk_data = self.embedding_generator.embed_article(
            full_text,
            article_id,
            metadata
        )
        
        if not chunk_data:
            return 0
        
        # Extract components
        chunks = [d["text"] for d in chunk_data]
        embeddings = [d["embedding"] for d in chunk_data]
        metadatas = [d["metadata"] for d in chunk_data]
        ids = [d["chunk_id"] for d in chunk_data]
        
        # Add to ChromaDB
        self.add_document_chunks(chunks, embeddings, metadatas, ids)
        
        # Mark as embedded in MongoDB
        self.articles_collection.update_one(
            {"article_id": article_id},
            {"$set": {"embedded": True}}
        )
        
        log.info(f"Embedded article {article_id}: {len(chunks)} chunks")
        return len(chunks)
    
    def embed_batch(self, limit: int = None) -> Dict[str, int]:
        """
        Embed all unembedded articles
        
        Returns statistics
        """
        query = {"embedded": {"$ne": True}}
        cursor = self.articles_collection.find(query, {"article_id": 1})
        
        if limit:
            cursor = cursor.limit(limit)
        
        articles = list(cursor)
        
        log.info(f"Embedding {len(articles)} articles")
        
        total_articles = 0
        total_chunks = 0
        
        for article in articles:
            try:
                chunks_created = self.embed_and_store_article(article["article_id"])
                if chunks_created > 0:
                    total_articles += 1
                    total_chunks += chunks_created
            except Exception as e:
                log.error(f"Error embedding article {article['article_id']}: {e}")
        
        stats = {
            "articles_embedded": total_articles,
            "total_chunks": total_chunks,
            "collection_size": self.collection.count()
        }
        
        log.info(f"Embedding complete: {stats}")
        return stats
    
    def query(
        self, 
        query_text: str, 
        n_results: int = None,
        where: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Query ChromaDB for similar documents
        
        Args:
            query_text: Query string
            n_results: Number of results to return
            where: Metadata filter
        
        Returns:
            Dict with documents, distances, and metadatas
        """
        n_results = n_results or settings.top_k_vector
        
        # Generate query embedding
        query_embedding = self.embedding_generator.generate_embedding(query_text)
        
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            where=where
        )
        
        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "ids": results["ids"][0] if results["ids"] else []
        }
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get ChromaDB collection statistics"""
        count = self.collection.count()
        
        # Get MongoDB stats
        total_articles = self.articles_collection.count_documents({})
        embedded_articles = self.articles_collection.count_documents({"embedded": True})
        
        return {
            "total_chunks": count,
            "total_articles": total_articles,
            "embedded_articles": embedded_articles,
            "pending_articles": total_articles - embedded_articles,
            "avg_chunks_per_article": count / embedded_articles if embedded_articles > 0 else 0
        }
    
    def clear_collection(self):
        """Clear all documents from collection"""
        self.client.delete_collection(settings.chroma_collection)
        self.collection = self.client.create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"}
        )
        log.warning("Cleared ChromaDB collection")
    
    def close(self):
        """Close connections"""
        self.mongo_client.close()


if __name__ == "__main__":
    # Example usage
    chroma_client = ChromaClient()
    
    # Embed articles
    stats = chroma_client.embed_batch(limit=5)
    print(f"Embedding stats: {stats}")
    
    # Test query
    query_results = chroma_client.query(
        "Microsoft investment in OpenAI",
        n_results=3
    )
    
    print(f"\nQuery results:")
    for i, (doc, distance, meta) in enumerate(zip(
        query_results["documents"],
        query_results["distances"],
        query_results["metadatas"]
    )):
        print(f"\n{i+1}. Distance: {distance:.4f}")
        print(f"   Article: {meta.get('article_id')}")
        print(f"   Text: {doc[:100]}...")
    
    # Get stats
    collection_stats = chroma_client.get_collection_stats()
    print(f"\nCollection stats: {collection_stats}")