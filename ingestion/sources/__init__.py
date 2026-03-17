"""
Dynamic article sources (RSS, News API).
Each fetcher returns a list of article dicts: title, content, source, date, url.
"""
from ingestion.sources.rss_fetcher import RSSFetcher
from ingestion.sources.newsapi_fetcher import NewsAPIFetcher

__all__ = ["RSSFetcher", "NewsAPIFetcher"]
