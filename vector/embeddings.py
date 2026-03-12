"""
Embedding generation using sentence-transformers
Creates vector embeddings for article chunks
"""
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import numpy as np
from config.settings import settings
from config.logger import log


class EmbeddingGenerator:
    """Generate embeddings for text"""
    
    def __init__(self):
        """Initialize sentence-transformers model"""
        log.info(f"Loading embedding model: {settings.embedding_model}")
        
        self.model = SentenceTransformer(settings.embedding_model)
        self.dimension = settings.embedding_dimension
        
        log.info(f"Embedding model loaded. Dimension: {self.dimension}")
    
    def chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Input text
            chunk_size: Words per chunk
            overlap: Overlapping words between chunks
        
        Returns:
            List of text chunks
        """
        chunk_size = chunk_size or settings.chunk_size
        overlap = overlap or settings.chunk_overlap
        
        words = text.split()
        chunks = []
        
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            start = end - overlap
        
        return chunks
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text
        
        Returns numpy array of shape (dimension,)
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding
    
    def generate_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts
        
        Returns numpy array of shape (n_texts, dimension)
        """
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=True,
            batch_size=32
        )
        return embeddings
    
    def embed_article(
        self, 
        article_text: str, 
        article_id: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Create embeddings for an article
        
        Chunks the article and generates embeddings
        
        Returns:
            List of dicts with chunk text, embedding, and metadata
        """
        # Chunk the text
        chunks = self.chunk_text(article_text)
        
        if not chunks:
            log.warning(f"No chunks created for article {article_id}")
            return []
        
        # Generate embeddings
        embeddings = self.generate_embeddings_batch(chunks)
        
        # Prepare results
        results = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            result = {
                "chunk_id": f"{article_id}_{i}",
                "text": chunk,
                "embedding": embedding.tolist(),
                "article_id": article_id,
                "chunk_index": i,
                "metadata": metadata or {}
            }
            results.append(result)
        
        log.debug(f"Created {len(results)} chunks for article {article_id}")
        return results
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings
        
        Returns similarity score (0 to 1)
        """
        # Normalize embeddings
        emb1_norm = embedding1 / np.linalg.norm(embedding1)
        emb2_norm = embedding2 / np.linalg.norm(embedding2)
        
        # Cosine similarity
        similarity = np.dot(emb1_norm, emb2_norm)
        
        return float(similarity)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get embedding model information"""
        return {
            "model_name": settings.embedding_model,
            "dimension": self.dimension,
            "max_seq_length": self.model.max_seq_length,
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap
        }


if __name__ == "__main__":
    # Example usage
    generator = EmbeddingGenerator()
    
    # Test embedding generation
    sample_text = """
    Microsoft announced a $10 billion investment in OpenAI, 
    strengthening their partnership in AI development. 
    This investment will help accelerate the development of 
    next-generation AI models.
    """
    
    # Generate embedding
    embedding = generator.generate_embedding(sample_text)
    print(f"Embedding shape: {embedding.shape}")
    print(f"First 5 values: {embedding[:5]}")
    
    # Test chunking
    chunks = generator.chunk_text(sample_text, chunk_size=10, overlap=2)
    print(f"\nCreated {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i}: {chunk[:50]}...")
    
    # Test article embedding
    article_data = generator.embed_article(
        sample_text, 
        "test_123",
        metadata={"source": "test"}
    )
    print(f"\nArticle embedding: {len(article_data)} chunks created")
    
    # Model info
    info = generator.get_model_info()
    print(f"\nModel info: {info}")