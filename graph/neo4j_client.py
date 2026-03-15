"""
Neo4j client for knowledge graph operations
"""
from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional
from config.settings import settings
from config.logger import log


class Neo4jClient:
    """Neo4j database client"""
    
    def __init__(self):
        """Initialize Neo4j connection"""
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        
        log.info(f"Connected to Neo4j at {settings.neo4j_uri}")
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create indexes for better query performance"""
        with self.driver.session() as session:
            # Index on entity name
            session.run("CREATE INDEX entity_name IF NOT EXISTS FOR (n:Entity) ON (n.name)")
            # Index on entity type
            session.run("CREATE INDEX entity_type IF NOT EXISTS FOR (n:Entity) ON (n.type)")
            
        log.info("Created Neo4j indexes")
    
    def verify_connection(self) -> bool:
        """Verify Neo4j connection"""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS num")
                return result.single()["num"] == 1
        except Exception as e:
            log.error(f"Neo4j connection failed: {e}")
            return False
    
    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query
        
        Returns list of result records
        """
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def create_node(self, name: str, node_type: str = "Entity", properties: Dict[str, Any] = None) -> bool:
        """
        Create or merge a node in the graph
        
        Uses MERGE to avoid duplicates
        """
        query = """
        MERGE (n:Entity {name: $name})
        SET n.type = $node_type
        SET n += $properties
        RETURN n
        """
        
        try:
            self.execute_query(query, {
                "name": name,
                "node_type": node_type,
                "properties": properties or {}
            })
            return True
        except Exception as e:
            log.error(f"Error creating node {name}: {e}")
            return False
    
    def create_relationship(
        self, 
        subject: str, 
        relation: str, 
        obj: str,
        properties: Dict[str, Any] = None
    ) -> bool:
        """
        Create a relationship between two nodes
        
        Creates nodes if they don't exist
        """
        # Sanitize relation name (Neo4j requirement)
        relation_safe = relation.upper().replace(" ", "_").replace("-", "_")
        
        query = f"""
        MERGE (a:Entity {{name: $subject}})
        MERGE (b:Entity {{name: $object}})
        MERGE (a)-[r:{relation_safe}]->(b)
        SET r += $properties
        RETURN r
        """
        
        try:
            self.execute_query(query, {
                "subject": subject,
                "object": obj,
                "properties": properties or {}
            })
            return True
        except Exception as e:
            log.error(f"Error creating relationship {subject}->{relation}->{obj}: {e}")
            return False
    
    def get_node_neighbors(self, name: str, depth: int = 1) -> List[Dict[str, Any]]:
        """
        Get neighbors of a node within specified depth
        
        Returns list of connected nodes and relationships
        """
        query = f"""
        MATCH path = (n:Entity {{name: $name}})-[*1..{depth}]-(m:Entity)
        RETURN path
        LIMIT {settings.max_graph_paths}
        """
        
        return self.execute_query(query, {"name": name})
    
    def find_paths(
        self, 
        start_entity: str, 
        end_entity: Optional[str] = None,
        max_depth: int = 3
    ) -> List[List[str]]:
        """
        Find paths between entities
        
        If end_entity is None, returns all paths from start_entity
        """
        if end_entity:
            query = f"""
            MATCH path = (a:Entity {{name: $start}})-[*1..{max_depth}]-(b:Entity {{name: $end}})
            RETURN path
            LIMIT {settings.max_graph_paths}
            """
            params = {"start": start_entity, "end": end_entity}
        else:
            query = f"""
            MATCH path = (a:Entity {{name: $start}})-[*1..{max_depth}]-(b:Entity)
            RETURN path
            LIMIT {settings.max_graph_paths}
            """
            params = {"start": start_entity}
        
        results = self.execute_query(query, params)
        
        paths = []
        for result in results:
            if "path" in result:
                path = result["path"]
                # Extract node names from path
                node_names = [node["name"] for node in path.nodes]
                paths.append(node_names)
        
        return paths
    
    def get_graph_stats(self) -> Dict[str, int]:
        """Get knowledge graph statistics"""
        node_count_query = "MATCH (n:Entity) RETURN count(n) as count"
        relationship_count_query = "MATCH ()-[r]->() RETURN count(r) as count"
        
        node_result = self.execute_query(node_count_query)
        rel_result = self.execute_query(relationship_count_query)
        
        return {
            "total_nodes": node_result[0]["count"] if node_result else 0,
            "total_relationships": rel_result[0]["count"] if rel_result else 0
        }
    
    def clear_graph(self):
        """Clear all nodes and relationships (use with caution!)"""
        query = "MATCH (n) DETACH DELETE n"
        self.execute_query(query)
        log.warning("Cleared entire knowledge graph")
    
    def export_graph_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Export all nodes and relationships"""
        nodes_query = "MATCH (n:Entity) RETURN n.name as name, n.type as type"
        rels_query = """
        MATCH (a:Entity)-[r]->(b:Entity) 
        RETURN a.name as subject, type(r) as relation, b.name as object
        """
        
        nodes = self.execute_query(nodes_query)
        relationships = self.execute_query(rels_query)
        
        return {
            "nodes": nodes,
            "relationships": relationships
        }
    
    def close(self):
        """Close Neo4j connection"""
        self.driver.close()
        log.info("Closed Neo4j connection")


if __name__ == "__main__":
    # Example usage
    client = Neo4jClient()
    
    # Verify connection
    if client.verify_connection():
        print("✓ Neo4j connection successful")
    
    # Create sample nodes and relationships
    client.create_node("Microsoft", "COMPANY")
    client.create_node("OpenAI", "COMPANY")
    client.create_relationship("Microsoft", "INVESTED_IN", "OpenAI", {"amount": "$10B"})
    
    # Get stats
    stats = client.get_graph_stats()
    print(f"Graph stats: {stats}")
    
    client.close()