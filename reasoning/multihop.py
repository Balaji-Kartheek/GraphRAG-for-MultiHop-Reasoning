"""
Multi-hop reasoning module
Combines graph traversal and vector retrieval for complex queries
"""
import re
from typing import List, Dict, Any, Optional
from retrieval.query_entities import QueryEntityDetector
from retrieval.subgraph_retrieval import SubgraphRetriever
from retrieval.vector_retrieval import VectorRetriever
from config.logger import log
from config.models import RetrievalContext


class MultiHopReasoner:
    """Combine graph and vector retrieval for multi-hop reasoning"""
    
    def __init__(self):
        """Initialize all retrieval components"""
        self.entity_detector = QueryEntityDetector()
        self.graph_retriever = SubgraphRetriever()
        self.vector_retriever = VectorRetriever()
        
        log.info("MultiHopReasoner initialized")

    @staticmethod
    def _chunk_get(chunk: Any, key: str, default=None):
        """Read field from either dict chunk or Pydantic model chunk."""
        if isinstance(chunk, dict):
            return chunk.get(key, default)
        return getattr(chunk, key, default)

    def _chunk_source(self, chunk: Any) -> str:
        """Resolve source from top-level field or metadata fallback."""
        source = self._chunk_get(chunk, "source")
        if source:
            return source
        metadata = self._chunk_get(chunk, "metadata", {}) or {}
        return metadata.get("source", "Unknown")
    
    def retrieve_context(
        self, 
        query: str,
        graph_depth: int = None,
        top_k_vector: int = None
    ) -> RetrievalContext:
        """
        Main retrieval method: combine graph and vector retrieval
        
        Args:
            query: User query
            graph_depth: Graph traversal depth
            top_k_vector: Number of vector results
        
        Returns:
            RetrievalContext with graph paths and vector chunks
        """
        log.info(f"Retrieving context for query: {query}")
        
        # Step 1: Detect entities in query
        entity_result = self.entity_detector.detect_query_entities(query)
        query_entities = entity_result["normalized"]
        
        log.info(f"Detected entities: {query_entities}")
        
        # Parse query intent/constraints for better retrieval.
        source_filter = self._extract_source_filter(query)
        relation_hints = self._extract_relation_hints(query)

        # Step 2: Retrieve graph paths
        graph_result = self.graph_retriever.retrieve_query_subgraph(
            query_entities,
            depth=graph_depth
        )
        graph_paths = graph_result.get("all_paths", [])
        if query_entities and not graph_paths:
            log.info("Detected entities produced no graph paths; retrying with fallback global subgraph")
            graph_result = self.graph_retriever.retrieve_query_subgraph(
                [],
                depth=graph_depth
            )
            graph_paths = graph_result.get("all_paths", [])
        if relation_hints:
            graph_paths = self._filter_graph_paths_by_relations(graph_paths, relation_hints)
        if graph_result.get("fallback_mode"):
            log.info("Graph retrieval is running in fallback mode (no explicit entities detected)")
        
        log.info(f"Retrieved {len(graph_paths)} graph paths")
        
        # Step 3: Retrieve similar documents
        vector_chunks = self.vector_retriever.retrieve_similar_chunks(
            query,
            top_k=top_k_vector,
            metadata_filter=source_filter,
        )
        
        log.info(f"Retrieved {len(vector_chunks)} vector chunks")
        
        # Create retrieval context
        context = RetrievalContext(
            graph_paths=graph_paths,
            vector_results=vector_chunks,
            entities_detected=query_entities
        )
        
        return context

    @staticmethod
    def _extract_source_filter(query: str) -> Optional[Dict[str, Any]]:
        """
        Detect source constraints from query text.
        Example: "published by Wired" -> {"source": "Wired"}
        """
        query_stripped = query.strip()
        patterns = [
            r"\bpublished by\s+([a-zA-Z0-9&\-\.\s]+?)(?:[\?\.,]|$)",
            r"\bfrom\s+([a-zA-Z0-9&\-\.\s]+?)(?:[\?\.,]|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, query_stripped, flags=re.IGNORECASE)
            if match:
                source = " ".join(match.group(1).split()).strip(" ?.,")
                if source:
                    return {"source": source}
        return None

    @staticmethod
    def _extract_relation_hints(query: str) -> List[str]:
        """Map query wording to relation-type hints."""
        q = query.lower()
        hints = []
        if any(k in q for k in ["collaborat", "partnership", "partnered", "worked with"]):
            hints.extend(["COLLABORATED_WITH", "PARTNERED_WITH"])
        if any(k in q for k in ["invest", "funded", "funding"]):
            hints.append("INVESTED_IN")
        if any(k in q for k in ["acquire", "acquisition", "bought"]):
            hints.append("ACQUIRED")
        return list(dict.fromkeys(hints))

    @staticmethod
    def _filter_graph_paths_by_relations(paths, relation_hints: List[str]):
        """Keep only paths containing at least one hinted relation."""
        if not relation_hints:
            return paths
        hint_set = set(relation_hints)
        filtered = []
        for path in paths:
            rels = set(path.relationships or [])
            if rels.intersection(hint_set):
                filtered.append(path)
        return filtered
    
    def format_context_for_llm(self, context: RetrievalContext) -> str:
        """
        Format combined context for LLM
        
        Returns formatted string with graph paths and documents
        """
        formatted = "=" * 80 + "\n"
        formatted += "RETRIEVAL CONTEXT\n"
        formatted += "=" * 80 + "\n\n"
        
        # Detected entities
        formatted += "Detected Query Entities:\n"
        formatted += ", ".join(context.entities_detected) if context.entities_detected else "None"
        formatted += "\n\n"
        
        # Graph paths
        formatted += "=" * 80 + "\n"
        formatted += "KNOWLEDGE GRAPH PATHS\n"
        formatted += "=" * 80 + "\n\n"
        
        if context.graph_paths:
            for i, path in enumerate(context.graph_paths[:15], 1):  # Limit to 15 paths
                # Format: Entity1 -[RELATION]-> Entity2 -[RELATION]-> Entity3
                path_str = path.nodes[0]
                
                for j in range(len(path.relationships)):
                    relation = path.relationships[j]
                    next_node = path.nodes[j + 1]
                    path_str += f" -[{relation}]-> {next_node}"
                
                formatted += f"{i}. {path_str}\n"
        else:
            formatted += "No graph paths found.\n"
        
        formatted += "\n"
        
        # Vector documents
        formatted += "=" * 80 + "\n"
        formatted += "RELEVANT DOCUMENTS (Vector Retrieval)\n"
        formatted += "=" * 80 + "\n\n"
        
        if context.vector_results:
            for i, chunk in enumerate(context.vector_results, 1):
                metadata = self._chunk_get(chunk, "metadata", {}) or {}
                formatted += f"Document {i}:\n"
                formatted += f"  Source: {self._chunk_source(chunk)}\n"
                formatted += f"  Article ID: {self._chunk_get(chunk, 'article_id', 'Unknown')}\n"
                formatted += f"  Similarity: {self._chunk_get(chunk, 'similarity', 0):.3f}\n"
                formatted += f"  Content: {self._chunk_get(chunk, 'text', '')}\n"
                formatted += "-" * 80 + "\n\n"
        else:
            formatted += "No relevant documents found.\n"
        
        return formatted
    
    def extract_source_articles(self, context: RetrievalContext) -> List[Dict[str, str]]:
        """
        Extract unique source articles from context
        
        Returns list of article metadata
        """
        articles = {}
        
        # From vector results
        for chunk in context.vector_results:
            article_id = self._chunk_get(chunk, "article_id")
            if article_id and article_id not in articles:
                articles[article_id] = {
                    "article_id": article_id,
                    "source": self._chunk_source(chunk),
                    "title": self._chunk_get(chunk, "metadata", {}).get("title", "")
                }
        
        return list(articles.values())
    
    def analyze_reasoning_complexity(self, context: RetrievalContext) -> Dict[str, Any]:
        """
        Analyze the reasoning complexity of the query
        
        Returns metrics about multi-hop reasoning
        """
        # Analyze path lengths
        path_lengths = [path.path_length for path in context.graph_paths]
        
        if path_lengths:
            avg_path_length = sum(path_lengths) / len(path_lengths)
            max_path_length = max(path_lengths)
            multi_hop_paths = sum(1 for length in path_lengths if length >= 2)
        else:
            avg_path_length = 0
            max_path_length = 0
            multi_hop_paths = 0
        
        # Count unique entities in graph
        all_entities = set()
        for path in context.graph_paths:
            all_entities.update(path.nodes)
        
        return {
            "num_detected_entities": len(context.entities_detected),
            "num_graph_paths": len(context.graph_paths),
            "num_vector_results": len(context.vector_results),
            "avg_path_length": avg_path_length,
            "max_path_length": max_path_length,
            "multi_hop_paths": multi_hop_paths,
            "unique_graph_entities": len(all_entities),
            "requires_multi_hop": max_path_length >= 2
        }
    
    def close(self):
        """Close all connections"""
        self.graph_retriever.close()
        self.vector_retriever.close()


if __name__ == "__main__":
    # Example usage
    reasoner = MultiHopReasoner()
    
    # Test query
    query = "Which companies collaborate with organizations funded by Microsoft?"
    
    print(f"Query: {query}\n")
    
    # Retrieve context
    context = reasoner.retrieve_context(query)
    
    # Analyze complexity
    complexity = reasoner.analyze_reasoning_complexity(context)
    print(f"Reasoning Complexity: {complexity}\n")
    
    # Format for LLM
    formatted = reasoner.format_context_for_llm(context)
    print(f"Formatted Context:\n{formatted[:1000]}...\n")
    
    # Extract sources
    sources = reasoner.extract_source_articles(context)
    print(f"Source Articles: {len(sources)}")
    
    reasoner.close()