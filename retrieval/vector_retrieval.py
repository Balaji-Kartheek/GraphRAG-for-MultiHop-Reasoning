"""
Vector retrieval from ChromaDB
Semantic search over article chunks
"""
from typing import List, Dict, Any
from vector.chroma_client import ChromaClient
from config.settings import settings
from config.logger import log


class VectorRetriever:
    """Retrieve relevant documents using vector similarity"""
    
    def __init__(self):
        """Initialize ChromaDB client"""
        self.chroma_client = ChromaClient()
        log.info("VectorRetriever initialized")
    
    def retrieve_similar_chunks(
        self, 
        query: str,
        top_k: int = None,
        metadata_filter: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve semantically similar document chunks
        
        Args:
            query: Query string
            top_k: Number of results
            metadata_filter: Filter by metadata
        
        Returns:
            List of relevant chunks with metadata
        """
        top_k = top_k or settings.top_k_vector
        
        # Query ChromaDB
        results = self.chroma_client.query(
            query_text=query,
            n_results=top_k,
            where=metadata_filter
        )
        
        # Format results
        chunks = []
        for i in range(len(results["documents"])):
            chunk = {
                "text": results["documents"][i],
                "distance": results["distances"][i],
                "similarity": 1 - results["distances"][i],  # Convert distance to similarity
                "metadata": results["metadatas"][i],
                "chunk_id": results["ids"][i],
                "article_id": results["metadatas"][i].get("article_id"),
                "source": results["metadatas"][i].get("source")
            }
            chunks.append(chunk)
        
        log.debug(f"Retrieved {len(chunks)} similar chunks for query")
        return chunks
    
    def format_chunks_for_llm(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Format retrieved chunks for LLM context
        
        Returns formatted string
        """
        if not chunks:
            return "No relevant documents found."
        
        formatted = "Relevant Documents:\n\n"
        
        for i, chunk in enumerate(chunks, 1):
            formatted += f"Document {i}:\n"
            formatted += f"Source: {chunk.get('source', 'Unknown')}\n"
            formatted += f"Article ID: {chunk.get('article_id', 'Unknown')}\n"
            formatted += f"Similarity: {chunk.get('similarity', 0):.3f}\n"
            formatted += f"Content: {chunk['text']}\n"
            formatted += "-" * 80 + "\n\n"
        
        return formatted
    
    def get_unique_articles(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """
        Get unique article IDs from retrieved chunks
        
        Returns list of article IDs
        """
        article_ids = set()
        for chunk in chunks:
            if chunk.get("article_id"):
                article_ids.add(chunk["article_id"])
        
        return list(article_ids)
    
    def close(self):
        """Close ChromaDB connection"""
        self.chroma_client.close()


if __name__ == "__main__":
    # Example usage
    retriever = VectorRetriever()
    
    # Test retrieval
    query = "Microsoft investment in artificial intelligence companies"
    
    chunks = retriever.retrieve_similar_chunks(query, top_k=5)
    print(f"Retrieved {len(chunks)} chunks\n")
    
    for i, chunk in enumerate(chunks, 1):
        print(f"\n{i}. Similarity: {chunk['similarity']:.3f}")
        print(f"   Article: {chunk['article_id']}")
        print(f"   Text: {chunk['text'][:100]}...")
    
    # Format for LLM
    formatted = retriever.format_chunks_for_llm(chunks)
    print(f"\n{'='*80}\nFormatted for LLM:\n{'='*80}\n{formatted[:500]}...")
    
    retriever.close()