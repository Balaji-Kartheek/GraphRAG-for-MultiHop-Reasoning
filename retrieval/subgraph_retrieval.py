"""
Subgraph retrieval from Neo4j
Retrieves relevant graph paths based on query entities
"""
from typing import List, Dict, Any, Optional
from graph.neo4j_client import Neo4jClient
from config.settings import settings
from config.logger import log
from config.models import GraphPath


def _get_node_name(n) -> str:
    """Extract name from Neo4j Node (handles both raw object and serialized dict)"""
    if isinstance(n, dict):
        return n.get("name") or (n.get("properties") or {}).get("name", "")
    return getattr(n, "get", lambda k: None)("name") or ""


def _get_rel_type(r) -> str:
    """Extract type from Neo4j Relationship"""
    if isinstance(r, dict):
        return r.get("type", "")
    return getattr(r, "type", str(r) if r else "")


class SubgraphRetriever:
    """Retrieve relevant subgraphs from knowledge graph"""
    
    def __init__(self):
        """Initialize Neo4j client"""
        self.neo4j_client = Neo4jClient()
        log.info("SubgraphRetriever initialized")
    
    def retrieve_entity_neighborhood(
        self, 
        entity: str, 
        depth: int = None
    ) -> List[GraphPath]:
        """
        Retrieve neighborhood around an entity
        
        Args:
            entity: Entity name
            depth: Traversal depth (default from settings)
        
        Returns:
            List of GraphPath objects
        """
        depth = depth or settings.graph_traversal_depth
        
        # Query for paths - return nodes() and relationships() to avoid Path serialization issues
        query = f"""
        MATCH path = (n:Entity {{name: $entity}})-[*1..{depth}]-(m:Entity)
        RETURN nodes(path) as nodes, relationships(path) as rels
        LIMIT {settings.max_graph_paths}
        """
        
        try:
            results = self.neo4j_client.execute_query(query, {"entity": entity})
            
            paths = []
            for result in results:
                if "nodes" in result and "rels" in result:
                    nodes_list = result["nodes"]
                    rels_list = result["rels"]
                    nodes = [_get_node_name(n) for n in nodes_list]
                    relationships = [_get_rel_type(r) for r in rels_list]
                    
                    graph_path = GraphPath(
                        nodes=nodes,
                        relationships=relationships,
                        path_length=len(nodes) - 1
                    )
                    paths.append(graph_path)
            
            log.debug(f"Retrieved {len(paths)} paths for entity: {entity}")
            return paths
            
        except Exception as e:
            log.error(f"Error retrieving subgraph for {entity}: {e}")
            return []
    
    def retrieve_multi_entity_paths(
        self, 
        entities: List[str],
        depth: int = None
    ) -> Dict[str, List[GraphPath]]:
        """
        Retrieve paths for multiple entities
        
        Returns:
            Dict mapping entity names to their paths
        """
        all_paths = {}
        
        for entity in entities:
            paths = self.retrieve_entity_neighborhood(entity, depth)
            if paths:
                all_paths[entity] = paths
        
        return all_paths
    
    def find_connecting_paths(
        self, 
        entity1: str, 
        entity2: str,
        max_depth: int = None
    ) -> List[GraphPath]:
        """
        Find paths connecting two entities
        
        Args:
            entity1: First entity
            entity2: Second entity
            max_depth: Maximum path length
        
        Returns:
            List of connecting paths
        """
        max_depth = max_depth or settings.graph_traversal_depth
        
        query = f"""
        MATCH path = (a:Entity {{name: $entity1}})-[*1..{max_depth}]-(b:Entity {{name: $entity2}})
        RETURN nodes(path) as nodes, relationships(path) as rels
        LIMIT {settings.max_graph_paths}
        """
        
        try:
            results = self.neo4j_client.execute_query(query, {
                "entity1": entity1,
                "entity2": entity2
            })
            
            paths = []
            for result in results:
                if "nodes" in result and "rels" in result:
                    nodes_list = result["nodes"]
                    rels_list = result["rels"]
                    nodes = [_get_node_name(n) for n in nodes_list]
                    relationships = [_get_rel_type(r) for r in rels_list]
                    
                    graph_path = GraphPath(
                        nodes=nodes,
                        relationships=relationships,
                        path_length=len(nodes) - 1
                    )
                    paths.append(graph_path)
            
            log.debug(f"Found {len(paths)} paths between {entity1} and {entity2}")
            return paths
            
        except Exception as e:
            log.error(f"Error finding paths: {e}")
            return []
    
    def retrieve_query_subgraph(
        self, 
        query_entities: List[str],
        depth: int = None
    ) -> Dict[str, Any]:
        """
        Main retrieval method: get subgraph for query entities
        
        Returns:
            Dict with paths and statistics
        """
        if not query_entities:
            log.warning("No query entities provided")
            return {
                "entities": [],
                "paths": [],
                "total_paths": 0
            }
        
        # Get paths for each entity
        entity_paths = self.retrieve_multi_entity_paths(query_entities, depth)
        
        # Flatten all paths
        all_paths = []
        for entity, paths in entity_paths.items():
            all_paths.extend(paths)
        
        # If multiple entities, also find connecting paths
        connecting_paths = []
        if len(query_entities) >= 2:
            for i in range(len(query_entities)):
                for j in range(i + 1, len(query_entities)):
                    paths = self.find_connecting_paths(
                        query_entities[i],
                        query_entities[j],
                        depth
                    )
                    connecting_paths.extend(paths)
        
        all_paths.extend(connecting_paths)
        
        # Remove duplicates
        unique_paths = self._deduplicate_paths(all_paths)
        
        result = {
            "query_entities": query_entities,
            "entity_paths": entity_paths,
            "connecting_paths": connecting_paths,
            "all_paths": unique_paths,
            "total_paths": len(unique_paths)
        }
        
        log.info(f"Retrieved {len(unique_paths)} unique paths for query entities")
        return result
    
    def _deduplicate_paths(self, paths: List[GraphPath]) -> List[GraphPath]:
        """Remove duplicate paths"""
        seen = set()
        unique = []
        
        for path in paths:
            # Create a tuple representation for comparison
            path_signature = tuple(path.nodes)
            
            if path_signature not in seen:
                seen.add(path_signature)
                unique.append(path)
        
        return unique
    
    def format_paths_for_llm(self, paths: List[GraphPath]) -> str:
        """
        Format graph paths for LLM context
        
        Returns human-readable string representation
        """
        if not paths:
            return "No graph paths found."
        
        formatted = "Graph Paths:\n"
        
        for i, path in enumerate(paths[:10], 1):  # Limit to top 10
            # Format: Entity1 -[RELATION]-> Entity2 -[RELATION]-> Entity3
            path_str = path.nodes[0]
            
            for j in range(len(path.relationships)):
                relation = path.relationships[j]
                next_node = path.nodes[j + 1]
                path_str += f" -[{relation}]-> {next_node}"
            
            formatted += f"{i}. {path_str}\n"
        
        return formatted
    
    def close(self):
        """Close Neo4j connection"""
        self.neo4j_client.close()


if __name__ == "__main__":
    # Example usage
    retriever = SubgraphRetriever()
    
    # Test with single entity
    paths = retriever.retrieve_entity_neighborhood("Microsoft", depth=2)
    print(f"Found {len(paths)} paths for Microsoft")
    
    # Test with multiple entities
    result = retriever.retrieve_query_subgraph(["Microsoft", "OpenAI"], depth=2)
    print(f"\nQuery subgraph: {result['total_paths']} total paths")
    
    # Format for LLM
    formatted = retriever.format_paths_for_llm(result["all_paths"])
    print(f"\nFormatted paths:\n{formatted}")
    
    retriever.close()