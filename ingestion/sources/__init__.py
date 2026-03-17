"""
Dynamic article sources (Hacker News only).
Each fetcher returns a list of article dicts: title, content, source, date, url.
"""
from ingestion.sources.hackernews_fetcher import HackerNewsFetcher

__all__ = ["HackerNewsFetcher"]
