"""
Knowledge Graph Builder
Populates Neo4j from extracted triples
"""
from typing import List, Dict, Any
from pymongo import MongoClient
from graph.neo4j_client import Neo4jClient
from config.settings import settings
from config.logger import log
from config.models import Triple


class GraphBuilder:
    """Build knowledge graph from triples"""
    
    def __init__(self):
        """Initialize MongoDB and Neo4j connections"""
        self.mongo_client = MongoClient(settings.mongodb_uri)
        self.db = self.mongo_client[settings.mongodb_db]
        self.triples_collection = self.db["triples"]
        
        self.neo4j_client = Neo4jClient()
        
        log.info("GraphBuilder initialized")
    
    def normalize_entity_name(self, name: str) -> str:
        """
        Normalize entity names for consistency
        
        Handles common variations
        """
        # Remove extra whitespace
        normalized = " ".join(name.split())
        
        # Common company name standardizations
        replacements = {
            "Open AI": "OpenAI",
            "Microsoft Corporation": "Microsoft",
            "Meta Platforms": "Meta",
            "Alphabet Inc": "Google",
            "Amazon.com": "Amazon",
            "Tesla Inc": "Tesla",
            "NVIDIA Corporation": "Nvidia",
        }
        
        for old, new in replacements.items():
            if old.lower() == normalized.lower():
                normalized = new
                break
        
        return normalized
    
    def infer_node_type(self, entity_name: str) -> str:
        """
        Infer node type from entity name
        
        Simple heuristic-based classification
        """
        # Known companies
        companies = {
            "microsoft", "openai", "google", "meta", "amazon", "apple",
            "nvidia", "tesla", "salesforce", "oracle", "ibm", "intel",
            "amd", "qualcomm", "anthropic", "deepmind", "hugging face"
        }
        
        name_lower = entity_name.lower()
        
        if any(company in name_lower for company in companies):
            return "COMPANY"
        elif any(word in name_lower for word in ["ai", "gpt", "model", "api", "platform"]):
            return "PRODUCT"
        else:
            return "ENTITY"
    
    def add_triple_to_graph(self, triple: Triple) -> bool:
        """
        Add a single triple to the knowledge graph
        
        Creates nodes and relationship
        """
        # Normalize entity names
        subject = self.normalize_entity_name(triple.subject)
        obj = self.normalize_entity_name(triple.object)
        
        # Infer types
        subject_type = self.infer_node_type(subject)
        object_type = self.infer_node_type(obj)
        
        # Create nodes
        self.neo4j_client.create_node(subject, subject_type)
        self.neo4j_client.create_node(obj, object_type)
        
        # Create relationship
        properties = {
            "confidence": triple.confidence,
            "article_id": triple.article_id
        }
        
        success = self.neo4j_client.create_relationship(
            subject,
            triple.relation,
            obj,
            properties
        )
        
        return success
    
    def build_from_article(self, article_id: str) -> int:
        """
        Build graph from triples of a specific article
        
        Returns number of triples added
        """
        triple_doc = self.triples_collection.find_one({"article_id": article_id})
        
        if not triple_doc:
            log.debug(f"No triples found for article {article_id}")
            return 0
        
        triples = [Triple(**t) for t in triple_doc.get("triples", [])]
        
        added = 0
        for triple in triples:
            if self.add_triple_to_graph(triple):
                added += 1
        
        log.debug(f"Added {added} triples from article {article_id}")
        return added
    
    def build_full_graph(self, limit: int = None) -> Dict[str, int]:
        """
        Build complete knowledge graph from all triples
        
        Returns statistics
        """
        log.info("Building knowledge graph from all triples")
        
        # Get all triple documents
        cursor = self.triples_collection.find()
        if limit:
            cursor = cursor.limit(limit)
        
        triple_docs = list(cursor)
        
        total_articles = len(triple_docs)
        total_triples_added = 0
        
        for doc in triple_docs:
            article_id = doc["article_id"]
            added = self.build_from_article(article_id)
            total_triples_added += added
        
        # Get graph stats
        graph_stats = self.neo4j_client.get_graph_stats()
        
        result = {
            "articles_processed": total_articles,
            "triples_added": total_triples_added,
            "total_nodes": graph_stats["total_nodes"],
            "total_relationships": graph_stats["total_relationships"]
        }
        
        log.info(f"Graph built: {result}")
        return result
    
    def rebuild_graph(self):
        """
        Clear and rebuild entire graph
        
        Use with caution!
        """
        log.warning("Rebuilding entire knowledge graph")
        
        # Clear existing graph
        self.neo4j_client.clear_graph()
        
        # Build new graph
        stats = self.build_full_graph()
        
        return stats
    
    def get_entity_graph(self, entity_name: str, depth: int = 2) -> Dict[str, Any]:
        """
        Get subgraph around an entity
        
        Returns nodes and relationships
        """
        normalized_name = self.normalize_entity_name(entity_name)
        
        # Get paths from entity
        paths = self.neo4j_client.find_paths(normalized_name, max_depth=depth)
        
        # Extract unique nodes and relationships
        nodes = set()
        relationships = []
        
        for path in paths:
            nodes.update(path)
            # Create relationship pairs
            for i in range(len(path) - 1):
                relationships.append((path[i], path[i + 1]))
        
        return {
            "center_entity": normalized_name,
            "nodes": list(nodes),
            "relationships": relationships,
            "path_count": len(paths)
        }
    
    def close(self):
        """Close database connections"""
        self.mongo_client.close()
        self.neo4j_client.close()


if __name__ == "__main__":
    # Example usage
    builder = GraphBuilder()
    
    # Build graph from all triples
    stats = builder.build_full_graph(limit=10)
    print(f"Graph build stats: {stats}")
    
    # Get subgraph for an entity
    subgraph = builder.get_entity_graph("Microsoft", depth=2)
    print(f"\nMicrosoft subgraph: {subgraph}")
    
    builder.close()