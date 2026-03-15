"""
Named Entity Recognition module using spaCy
Extracts entities from articles
"""
import spacy
from typing import List, Dict, Any, Set
from pymongo import MongoClient
from config.settings import settings
from config.logger import log
from config.models import Entity


class EntityExtractor:
    """Extract named entities from articles"""
    
    # TODO: Add more entity types, Implement the Scalability for the Entities
    # Relevant entity types for Tech/AI news
    RELEVANT_LABELS = {
        "ORG",      # Companies, organizations
        "PERSON",   # People, executives
        "PRODUCT",  # Products, technologies
        "GPE",      # Countries, cities
        "MONEY",    # Investment amounts
        "PERCENT",  # Percentages
        "DATE"      # Dates
    }
    
    def __init__(self):
        """Initialize spaCy NER"""
        try:
            self.nlp = spacy.load("en_core_web_sm")
            log.info("Loaded spaCy model for NER")
        except OSError:
            log.error("spaCy model not found. Run: python -m spacy download en_core_web_sm")
            raise
        
        self.client = MongoClient(settings.mongodb_uri)
        self.db = self.client[settings.mongodb_db]
        self.collection = self.db[settings.mongodb_collection]
    
    def extract_entities(self, text: str) -> List[Entity]:
        """
        Extract named entities from text
        
        Returns list of Entity objects
        """
        doc = self.nlp(text)
        
        entities = []
        for ent in doc.ents:
            if ent.label_ in self.RELEVANT_LABELS:
                entity = Entity(
                    text=ent.text,
                    label=ent.label_,
                    start_char=ent.start_char,
                    end_char=ent.end_char
                )
                entities.append(entity)
        
        return entities
    
    def normalize_entity(self, entity_text: str) -> str:
        """
        Normalize entity names
        
        - Remove common variations
        - Standardize company names
        """
        # Remove common suffixes
        suffixes = [" Inc", " Inc.", " LLC", " Ltd", " Corp", " Corporation"]
        normalized = entity_text
        
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
        
        # Standardize spacing
        normalized = " ".join(normalized.split())
        
        # Common company name variations
        replacements = {
            "Open AI": "OpenAI",
            "GPT": "GPT",
            "Chat GPT": "ChatGPT",
            "Meta Platforms": "Meta",
            "Alphabet Inc": "Google",
        }
        
        for old, new in replacements.items():
            if old.lower() in normalized.lower():
                normalized = new
        
        return normalized.strip()
    
    def get_unique_entities(self, entities: List[Entity]) -> Dict[str, Set[str]]:
        """
        Get unique entities grouped by type
        
        Returns dict: {entity_type: set_of_entity_names}
        """
        unique = {}
        
        for entity in entities:
            label = entity.label
            normalized_text = self.normalize_entity(entity.text)
            
            if label not in unique:
                unique[label] = set()
            
            unique[label].add(normalized_text)
        
        return unique
    
    def extract_from_article(self, article_id: str) -> Dict[str, List[str]]:
        """
        Extract entities from a specific article
        
        Returns dict of entities by type
        """
        article = self.collection.find_one({"article_id": article_id})
        
        if not article:
            log.error(f"Article {article_id} not found")
            return {}
        
        # Extract from title and content
        title_text = article.get("title", "")
        content_text = article.get("content", "")
        full_text = f"{title_text}. {content_text}"
        
        entities = self.extract_entities(full_text)
        unique_entities = self.get_unique_entities(entities)
        
        # Convert sets to lists for storage
        entity_dict = {
            label: list(entities) 
            for label, entities in unique_entities.items()
        }
        
        # Store in MongoDB
        self.collection.update_one(
            {"article_id": article_id},
            {"$set": {"entities": entity_dict}}
        )
        
        log.debug(f"Extracted {len(entities)} entities from article {article_id}")
        
        return entity_dict
    
    def extract_batch(self, limit: int = None) -> int:
        """
        Extract entities from all articles without entities
        
        Returns count of processed articles
        """
        query = {"$or": [{"entities": {"$exists": False}}, {"entities": None}]}
        articles = list(self.collection.find(query, {"article_id": 1}).limit(limit if limit else 0))
        
        log.info(f"Extracting entities from {len(articles)} articles")
        
        processed = 0
        for article in articles:
            try:
                self.extract_from_article(article["article_id"])
                processed += 1
            except Exception as e:
                log.error(f"Error extracting entities from {article['article_id']}: {e}")
        
        log.info(f"Extracted entities from {processed} articles")
        return processed
    
    def get_all_entities(self) -> Dict[str, Set[str]]:
        """
        Get all unique entities across all articles
        
        Returns dict: {entity_type: set_of_all_entities}
        """
        all_entities = {}
        
        articles = self.collection.find({"entities": {"$exists": True}}, {"entities": 1})
        
        for article in articles:
            entities_dict = article.get("entities") or {}
            
            for label, entities in entities_dict.items():
                if label not in all_entities:
                    all_entities[label] = set()
                
                all_entities[label].update(entities)
        
        return all_entities
    
    def get_entity_stats(self) -> Dict[str, Any]:
        """Get entity extraction statistics"""
        total = self.collection.count_documents({})
        with_entities = self.collection.count_documents({"entities": {"$exists": True}})
        
        all_entities = self.get_all_entities()
        entity_counts = {label: len(entities) for label, entities in all_entities.items()}
        
        return {
            "total_articles": total,
            "articles_with_entities": with_entities,
            "unique_entities_by_type": entity_counts,
            "total_unique_entities": sum(entity_counts.values())
        }
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()


if __name__ == "__main__":
    # Example usage
    extractor = EntityExtractor()
    
    # Extract entities from batch
    count = extractor.extract_batch(limit=10)
    print(f"Processed {count} articles")
    
    # Get stats
    stats = extractor.get_entity_stats()
    print(f"\nEntity Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Get all unique organizations
    all_entities = extractor.get_all_entities()
    if "ORG" in all_entities:
        print(f"\nSample Organizations: {list(all_entities['ORG'])[:10]}")