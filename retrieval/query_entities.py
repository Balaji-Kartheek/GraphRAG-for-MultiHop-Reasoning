"""
Query entity detection
Extracts entities from user queries to enable graph traversal
"""
import spacy
<<<<<<< HEAD
from typing import List, Set
=======
from typing import Dict, List, Set
>>>>>>> 6523998fa036486181be393d9c199ceb5a51335e
from config.logger import log


class QueryEntityDetector:
    """Detect entities in user queries"""
    
    def __init__(self):
        """Initialize spaCy NER"""
        try:
            self.nlp = spacy.load("en_core_web_sm")
            log.info("Loaded spaCy for query entity detection")
        except OSError:
            log.error("spaCy model not found")
            raise
    
    def extract_entities(self, query: str) -> List[str]:
        """
        Extract entities from query text
        
        Returns list of entity names
        """
        doc = self.nlp(query)
        
        # Focus on ORG, PERSON, PRODUCT, GPE
        relevant_labels = {"ORG", "PERSON", "PRODUCT", "GPE"}
        
        entities = []
        for ent in doc.ents:
            if ent.label_ in relevant_labels:
                entities.append(ent.text)
        
        return entities
    
    def normalize_entities(self, entities: List[str]) -> List[str]:
        """
        Normalize entity names to match graph entities
        
        Handles common variations
        """
        normalized = []
        
        for entity in entities:
            # Remove extra whitespace
            clean = " ".join(entity.split())
            
            # Common replacements
            replacements = {
                "Open AI": "OpenAI",
                "Microsoft Corp": "Microsoft",
                "Meta Platforms": "Meta",
                "Alphabet": "Google",
            }
            
            for old, new in replacements.items():
                if old.lower() == clean.lower():
                    clean = new
                    break
            
            normalized.append(clean)
        
        return normalized
    
    def detect_query_entities(self, query: str) -> Dict[str, List[str]]:
        """
        Main method: detect and normalize entities from query
        
        Returns:
            Dict with raw and normalized entities
        """
        # Extract entities
        raw_entities = self.extract_entities(query)
        
        # Normalize
        normalized_entities = self.normalize_entities(raw_entities)
        
        # Remove duplicates while preserving order
        unique_entities = list(dict.fromkeys(normalized_entities))
        
        log.debug(f"Query: {query}")
        log.debug(f"Detected entities: {unique_entities}")
        
        return {
            "raw": raw_entities,
            "normalized": unique_entities,
            "count": len(unique_entities)
        }


if __name__ == "__main__":
    # Example usage
    detector = QueryEntityDetector()
    
    # Test queries
    queries = [
        "Which companies collaborate with organizations funded by Microsoft?",
        "What is the relationship between OpenAI and Nvidia?",
        "Who invested in Tesla recently?",
        "What partnerships does Google have with AI startups?"
    ]
    
    for query in queries:
        result = detector.detect_query_entities(query)
        print(f"\nQuery: {query}")
        print(f"Entities: {result['normalized']}")