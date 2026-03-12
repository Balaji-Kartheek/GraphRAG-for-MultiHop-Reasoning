"""
Article preprocessing and cleaning module
"""
import re
import spacy
from typing import List, Dict, Any
from pymongo import MongoClient
from config.settings import settings
from config.logger import log


class ArticlePreprocessor:
    """Preprocesses and cleans articles"""
    
    def __init__(self):
        """Initialize spaCy and MongoDB"""
        try:
            self.nlp = spacy.load("en_core_web_sm")
            log.info("Loaded spaCy model: en_core_web_sm")
        except OSError:
            log.error("spaCy model not found. Run: python -m spacy download en_core_web_sm")
            raise
        
        self.client = MongoClient(settings.mongodb_uri)
        self.db = self.client[settings.mongodb_db]
        self.collection = self.db[settings.mongodb_collection]
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text
        
        - Remove HTML tags
        - Remove special characters
        - Normalize whitespace
        - Remove URLs
        """
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove URLs
        text = re.sub(r'http\S+|www\S+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:\-\(\)]', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def segment_sentences(self, text: str) -> List[str]:
        """Segment text into sentences using spaCy"""
        doc = self.nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents]
        return sentences
    
    def remove_duplicates(self) -> int:
        """
        Remove duplicate articles based on similar titles
        Uses simple title comparison
        """
        log.info("Checking for duplicate articles")
        
        articles = list(self.collection.find({}, {"article_id": 1, "title": 1}))
        
        seen_titles = {}
        duplicates = []
        
        for article in articles:
            title_normalized = article["title"].lower().strip()
            
            if title_normalized in seen_titles:
                duplicates.append(article["article_id"])
            else:
                seen_titles[title_normalized] = article["article_id"]
        
        if duplicates:
            result = self.collection.delete_many({"article_id": {"$in": duplicates}})
            log.info(f"Removed {result.deleted_count} duplicate articles")
            return result.deleted_count
        
        return 0
    
    def preprocess_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess a single article
        
        Returns cleaned article with sentences
        """
        article_id = article["article_id"]
        
        # Clean title and content
        cleaned_title = self.clean_text(article["title"])
        cleaned_content = self.clean_text(article["content"])
        
        # Segment into sentences
        sentences = self.segment_sentences(cleaned_content)
        
        # Update article in database
        self.collection.update_one(
            {"article_id": article_id},
            {
                "$set": {
                    "title": cleaned_title,
                    "content": cleaned_content,
                    "sentences": sentences,
                    "sentence_count": len(sentences)
                }
            }
        )
        
        log.debug(f"Preprocessed article {article_id}: {len(sentences)} sentences")
        
        return {
            "article_id": article_id,
            "title": cleaned_title,
            "content": cleaned_content,
            "sentences": sentences
        }
    
    def preprocess_batch(self, limit: int = None) -> int:
        """
        Preprocess all unprocessed articles
        
        Returns number of articles preprocessed
        """
        query = {"processed": False}
        articles = list(self.collection.find(query).limit(limit if limit else 0))
        
        log.info(f"Preprocessing {len(articles)} articles")
        
        processed_count = 0
        
        for article in articles:
            try:
                self.preprocess_article(article)
                processed_count += 1
            except Exception as e:
                log.error(f"Error preprocessing article {article['article_id']}: {e}")
        
        log.info(f"Preprocessed {processed_count} articles")
        return processed_count
    
    def get_article_stats(self) -> Dict[str, int]:
        """Get preprocessing statistics"""
        total = self.collection.count_documents({})
        processed = self.collection.count_documents({"sentences": {"$exists": True}})
        
        return {
            "total_articles": total,
            "preprocessed": processed,
            "pending": total - processed
        }
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()


if __name__ == "__main__":
    # Example usage
    preprocessor = ArticlePreprocessor()
    
    # Remove duplicates
    duplicates_removed = preprocessor.remove_duplicates()
    print(f"Removed {duplicates_removed} duplicates")
    
    # Preprocess articles
    count = preprocessor.preprocess_batch(limit=10)
    print(f"Preprocessed {count} articles")
    
    # Get stats
    stats = preprocessor.get_article_stats()
    print(f"Stats: {stats}")