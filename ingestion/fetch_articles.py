"""
Article fetching and ingestion module
Loads Tech & AI news articles and stores them in MongoDB
"""
import pandas as pd
from pymongo import MongoClient
from typing import List, Dict, Any
import hashlib
from datetime import datetime
from config.settings import settings
from config.logger import log
from config.models import Article


class ArticleIngestion:
    """Handles article fetching and storage"""
    
    def __init__(self):
        """Initialize MongoDB connection"""
        self.client = MongoClient(settings.mongodb_uri)
        self.db = self.client[settings.mongodb_db]
        self.collection = self.db[settings.mongodb_collection]
        
        # Create indexes
        self.collection.create_index("article_id", unique=True)
        self.collection.create_index("processed")
        self.collection.create_index("source")
        
        log.info("ArticleIngestion initialized")
    
    def generate_article_id(self, title: str, source: str) -> str:
        """Generate unique article ID from title and source"""
        content = f"{title}_{source}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def load_from_csv(self, file_path: str, limit: int = None) -> int:
        """
        Load articles from CSV file
        
        Expected CSV columns: title, content, source, date, url
        """
        log.info(f"Loading articles from {file_path}")
        
        try:
            df = pd.read_csv(file_path)
            
            # Filter tech/AI related articles
            tech_keywords = [
                'ai', 'artificial intelligence', 'machine learning', 'openai',
                'microsoft', 'google', 'meta', 'amazon', 'nvidia', 'apple',
                'startup', 'tech', 'technology', 'software', 'cloud',
                'investment', 'acquisition', 'partnership', 'funding',
                'api', 'platform', 'chip', 'semiconductor', 'tesla'
            ]
            
            # Filter rows containing tech keywords
            mask = df['title'].str.lower().str.contains('|'.join(tech_keywords), na=False) | \
                   df['content'].str.lower().str.contains('|'.join(tech_keywords), na=False)
            
            df_filtered = df[mask]
            
            if limit:
                df_filtered = df_filtered.head(limit)
            
            log.info(f"Filtered {len(df_filtered)} tech/AI articles from {len(df)} total")
            
            # Insert articles
            inserted = 0
            for _, row in df_filtered.iterrows():
                article = self._create_article_from_row(row)
                if self.insert_article(article):
                    inserted += 1
            
            log.info(f"Inserted {inserted} new articles")
            return inserted
            
        except Exception as e:
            log.error(f"Error loading articles from CSV: {e}")
            raise
    
    def _create_article_from_row(self, row: pd.Series) -> Article:
        """Create Article object from DataFrame row"""
        title = str(row.get('title', ''))
        content = str(row.get('content', ''))
        source = str(row.get('source', 'unknown'))
        
        article_id = self.generate_article_id(title, source)
        
        return Article(
            article_id=article_id,
            title=title,
            content=content,
            source=source,
            date=row.get('date'),
            url=row.get('url'),
            processed=False
        )

    def _create_article_from_dict(self, d: Dict[str, Any]) -> Article:
        """Create Article object from fetcher dict (title, content, source, date, url)."""
        title = str(d.get("title", ""))
        content = str(d.get("content", ""))
        source = str(d.get("source", "unknown"))
        article_id = self.generate_article_id(title, source)
        return Article(
            article_id=article_id,
            title=title,
            content=content,
            source=source,
            date=d.get("date"),
            url=d.get("url"),
            processed=False,
        )

    def load_from_fetchers(self, limit: int = None) -> int:
        """
        Fetch articles from configured sources (currently Hacker News), apply tech filter, insert.
        Returns count of newly inserted articles.
        """
        from ingestion.sources import HackerNewsFetcher

        tech_keywords = [
            "ai", "artificial intelligence", "machine learning", "openai",
            "microsoft", "google", "meta", "amazon", "nvidia", "apple",
            "startup", "tech", "technology", "software", "cloud",
            "investment", "acquisition", "partnership", "funding",
            "api", "platform", "chip", "semiconductor", "tesla",
        ]
        cap = limit or getattr(settings, "fetch_limit_per_run", None) or 100
        all_items = []
        hn = HackerNewsFetcher()
        all_items.extend(hn.fetch(limit=cap))

        def has_tech(d):
            t, c = (d.get("title") or "").lower(), (d.get("content") or "").lower()
            return any(kw in t or kw in c for kw in tech_keywords)

        filtered = [x for x in all_items if has_tech(x)]
        if not filtered:
            filtered = all_items

        inserted = 0
        for d in filtered[:cap]:
            article = self._create_article_from_dict(d)
            if self.insert_article(article):
                inserted += 1
        total_fetched = len(filtered[:cap])
        log.info(
            f"load_from_fetchers: fetched {total_fetched} items, inserted {inserted} new articles "
            f"(duplicates skipped: {total_fetched - inserted})"
        )
        return inserted
    
    def insert_article(self, article: Article) -> bool:
        """Insert article into MongoDB, skip if exists"""
        try:
            self.collection.insert_one(article.model_dump(exclude_none=True))
            return True
        except Exception as e:
            if "duplicate key error" in str(e):
                log.debug(f"Article {article.article_id} already exists")
                return False
            else:
                log.error(f"Error inserting article: {e}")
                return False
    
    def get_unprocessed_articles(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get articles that haven't been processed yet"""
        query = {"processed": False}
        cursor = self.collection.find(query)
        
        if limit:
            cursor = cursor.limit(limit)
        
        return list(cursor)
    
    def mark_as_processed(self, article_id: str):
        """Mark article as processed"""
        self.collection.update_one(
            {"article_id": article_id},
            {"$set": {"processed": True}}
        )
    
    def get_article_by_id(self, article_id: str) -> Dict[str, Any]:
        """Get article by ID"""
        return self.collection.find_one({"article_id": article_id})
    
    def get_total_count(self) -> int:
        """Get total article count"""
        return self.collection.count_documents({})
    
    def get_processed_count(self) -> int:
        """Get processed article count"""
        return self.collection.count_documents({"processed": True})
    
    def update_entities(self, article_id: str, entities: List[str]):
        """Update extracted entities for an article"""
        self.collection.update_one(
            {"article_id": article_id},
            {"$set": {"entities": entities}}
        )
    
    def mark_triples_extracted(self, article_id: str):
        """Mark that triples have been extracted"""
        self.collection.update_one(
            {"article_id": article_id},
            {"$set": {"triples_extracted": True}}
        )
    
    def mark_embedded(self, article_id: str):
        """Mark that article has been embedded"""
        self.collection.update_one(
            {"article_id": article_id},
            {"$set": {"embedded": True}}
        )
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()


if __name__ == "__main__":
    # Example usage
    ingestion = ArticleIngestion()
    
    # Create sample data if CSV doesn't exist
    sample_data = pd.DataFrame([
        {
            "title": "Microsoft Invests $10 Billion in OpenAI",
            "content": "Microsoft announced a multi-billion dollar investment in OpenAI, strengthening their partnership in AI development.",
            "source": "TechCrunch",
            "date": "2023-01-23",
            "url": "https://example.com/ms-openai"
        },
        {
            "title": "OpenAI Partners with Nvidia for GPU Infrastructure",
            "content": "OpenAI has formed a strategic partnership with Nvidia to leverage their advanced GPU technology for AI model training.",
            "source": "VentureBeat",
            "date": "2023-03-15",
            "url": "https://example.com/openai-nvidia"
        }
    ])
    
    sample_data.to_csv("./data/sample_tech_news.csv", index=False)
    
    count = ingestion.load_from_csv("./data/sample_tech_news.csv")
    print(f"Loaded {count} articles")
    print(f"Total articles: {ingestion.get_total_count()}")