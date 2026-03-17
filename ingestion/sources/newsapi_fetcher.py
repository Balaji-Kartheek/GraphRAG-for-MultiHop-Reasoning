"""
News API fetcher for Tech/AI news.
Requires NEWS_API_KEY (free tier at newsapi.org). Skip if key not set.
"""
from typing import List, Dict, Any
import requests
from config.settings import settings
from config.logger import log

NEWSAPI_URL = "https://newsapi.org/v2/everything"


class NewsAPIFetcher:
    """Fetch articles from News API. Optional; requires API key."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, "news_api_key", None) or ""

    def fetch(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Fetch articles from News API (tech/AI query).
        Returns list of dicts with keys: title, content, source, date, url.
        """
        if not self.api_key:
            log.debug("News API key not set; skipping News API fetcher")
            return []
        limit = limit or 50
        try:
            resp = requests.get(
                NEWSAPI_URL,
                params={
                    "apiKey": self.api_key,
                    "q": "AI OR artificial intelligence OR OpenAI OR Microsoft OR Google OR tech",
                    "language": "en",
                    "pageSize": min(limit, 100),
                    "sortBy": "publishedAt",
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.warning(f"News API request failed: {e}")
            return []
        articles = []
        for item in data.get("articles", []):
            title = (item.get("title") or "").strip()
            if not title or title == " [Removed]":
                continue
            source_name = (item.get("source") or {}).get("name", "NewsAPI")
            content = (item.get("description") or item.get("content") or title).strip()
            if isinstance(content, dict):
                content = content.get("content", "") or title
            date_str = item.get("publishedAt", "")[:10] if item.get("publishedAt") else None
            url = item.get("url")
            articles.append({
                "title": title,
                "content": content,
                "source": source_name,
                "date": date_str,
                "url": url,
            })
        log.info(f"News API fetcher collected {len(articles)} articles")
        return articles
