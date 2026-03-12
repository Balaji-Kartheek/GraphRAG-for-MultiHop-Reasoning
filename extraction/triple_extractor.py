"""
Triple extraction module using Gemini Flash API
Converts article text into structured knowledge triples
"""
import google.generativeai as genai
import json
from typing import List, Dict, Any
from pymongo import MongoClient
from tenacity import retry, stop_after_attempt, wait_exponential
from config.settings import settings
from config.logger import log
from config.models import Triple


class TripleExtractor:
    """Extract knowledge triples from text using Gemini"""
    
    def __init__(self):
        """Initialize Gemini API"""
        if not settings.gemini_api_key:
            log.warning("Gemini API key not set. Triple extraction will fail.")
        
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        
        self.client = MongoClient(settings.mongodb_uri)
        self.db = self.client[settings.mongodb_db]
        self.articles_collection = self.db[settings.mongodb_collection]
        self.triples_collection = self.db["triples"]
        
        # Create index
        self.triples_collection.create_index("article_id")
        
        log.info("TripleExtractor initialized with Gemini Flash")
    
    def create_extraction_prompt(self, text: str) -> str:
        """
        Create prompt for triple extraction
        
        Instructs Gemini to extract structured triples
        """
        prompt = f"""You are an expert knowledge graph builder for Tech & AI industry news.

Extract knowledge triples from the following text. Focus on:
- Company investments and funding
- Partnerships and collaborations
- Acquisitions and mergers
- Product launches and announcements
- Executive appointments
- Technology developments

Return ONLY a valid JSON array with this exact structure:
[
  {{
    "subject": "entity name",
    "relation": "relationship type",
    "object": "entity name",
    "confidence": 0.95
  }}
]

Rules:
1. Use clear, normalized entity names (e.g., "OpenAI" not "Open AI")
2. Use consistent relation types: INVESTED_IN, PARTNERED_WITH, ACQUIRED, LAUNCHED, APPOINTED, DEVELOPED, COLLABORATED_WITH
3. confidence should be 0.0 to 1.0 based on certainty
4. Only extract factual relationships explicitly stated in the text
5. Return empty array [] if no clear relationships found
6. DO NOT include any text before or after the JSON array

Text:
{text}

JSON Output:"""
        
        return prompt
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def extract_triples_from_text(self, text: str) -> List[Triple]:
        """
        Extract triples from text using Gemini API
        
        Returns list of Triple objects
        """
        prompt = self.create_extraction_prompt(text)
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            # Parse JSON
            triples_data = json.loads(response_text)
            
            # Convert to Triple objects and filter by confidence
            triples = []
            for triple_dict in triples_data:
                if triple_dict.get("confidence", 0) >= settings.confidence_threshold:
                    triple = Triple(
                        subject=triple_dict["subject"],
                        relation=triple_dict["relation"],
                        object=triple_dict["object"],
                        confidence=triple_dict["confidence"],
                        source_text=text[:500]  # Store snippet
                    )
                    triples.append(triple)
            
            return triples
            
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON response: {e}")
            log.debug(f"Response text: {response_text}")
            return []
        except Exception as e:
            log.error(f"Error extracting triples: {e}")
            raise
    
    def extract_from_article(self, article_id: str) -> List[Triple]:
        """
        Extract triples from a specific article
        
        Returns list of extracted triples
        """
        # Check if already extracted
        existing = self.triples_collection.find_one({"article_id": article_id})
        if existing:
            log.debug(f"Triples already extracted for article {article_id}")
            return [Triple(**t) for t in existing.get("triples", [])]
        
        # Get article
        article = self.articles_collection.find_one({"article_id": article_id})
        if not article:
            log.error(f"Article {article_id} not found")
            return []
        
        # Extract triples from content
        content = article.get("content", "")
        title = article.get("title", "")
        text = f"{title}. {content}"
        
        triples = self.extract_triples_from_text(text)
        
        # Add article_id to triples
        for triple in triples:
            triple.article_id = article_id
        
        # Store in database
        if triples:
            self.triples_collection.insert_one({
                "article_id": article_id,
                "triples": [t.model_dump() for t in triples],
                "count": len(triples)
            })
            
            self.articles_collection.update_one(
                {"article_id": article_id},
                {"$set": {"triples_extracted": True}}
            )
        
        log.info(f"Extracted {len(triples)} triples from article {article_id}")
        
        return triples
    
    def extract_batch(self, limit: int = None) -> int:
        """
        Extract triples from all articles without triples
        
        Returns count of processed articles
        """
        query = {"triples_extracted": {"$ne": True}}
        articles = list(
            self.articles_collection.find(query, {"article_id": 1})
            .limit(limit if limit else 0)
        )
        
        log.info(f"Extracting triples from {len(articles)} articles")
        
        processed = 0
        total_triples = 0
        
        for article in articles:
            try:
                triples = self.extract_from_article(article["article_id"])
                processed += 1
                total_triples += len(triples)
            except Exception as e:
                log.error(f"Error extracting triples from {article['article_id']}: {e}")
        
        log.info(f"Extracted {total_triples} triples from {processed} articles")
        return processed
    
    def get_all_triples(self) -> List[Triple]:
        """Get all extracted triples"""
        all_triples = []
        
        for doc in self.triples_collection.find():
            for triple_dict in doc.get("triples", []):
                all_triples.append(Triple(**triple_dict))
        
        return all_triples
    
    def get_triple_stats(self) -> Dict[str, Any]:
        """Get triple extraction statistics"""
        total_articles = self.articles_collection.count_documents({})
        articles_with_triples = self.articles_collection.count_documents(
            {"triples_extracted": True}
        )
        total_triples = sum(
            doc.get("count", 0) 
            for doc in self.triples_collection.find({}, {"count": 1})
        )
        
        # Get relation type distribution
        all_triples = self.get_all_triples()
        relation_counts = {}
        for triple in all_triples:
            relation_counts[triple.relation] = relation_counts.get(triple.relation, 0) + 1
        
        return {
            "total_articles": total_articles,
            "articles_with_triples": articles_with_triples,
            "total_triples": total_triples,
            "avg_triples_per_article": total_triples / articles_with_triples if articles_with_triples > 0 else 0,
            "relation_distribution": relation_counts
        }
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()


if __name__ == "__main__":
    # Example usage
    extractor = TripleExtractor()
    
    # Extract from batch (limited for testing)
    count = extractor.extract_batch(limit=5)
    print(f"Processed {count} articles")
    
    # Get stats
    stats = extractor.get_triple_stats()
    print(f"\nTriple Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")