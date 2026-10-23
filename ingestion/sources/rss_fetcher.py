"""
RSS fetcher for Tech/AI news feeds.
Uses feedparser; no API key required.
"""
from typing import List, Dict, Any
from datetime import datetime
import feedparser
from config.settings import settings
from config.logger import log

# Default Tech/AI RSS feeds when RSS_FEEDS is not set
DEFAULT_RSS_FEEDS = [
    "https://techcrunch.com/feed/",
    "https://feeds.feedburner.com/venturebeat/SZYF",
    "https://www.theverge.com/rss/index.xml",
    "https://feeds.wired.com/c/35185/f/661470/index.rss",
]


def _parse_date(entry: Any) -> str:
    """Extract date string from feed entry."""
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = getattr(entry, key, None)
        if parsed and len(parsed) >= 6:
            try:
                dt = datetime(parsed[0], parsed[1], parsed[2], parsed[3] if len(parsed) > 3 else 0, parsed[4] if len(parsed) > 4 else 0, parsed[5] if len(parsed) > 5 else 0)
                return dt.strftime("%Y-%m-%d")
            except (ValueError, IndexError):
                pass
    return ""


class RSSFetcher:
    """Fetch articles from RSS feeds. Free; no API key required."""

    def __init__(self, feed_urls: List[str] = None):
        self.feed_urls = feed_urls or getattr(settings, "rss_feeds", None) or DEFAULT_RSS_FEEDS

    def fetch(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Fetch entries from all configured RSS feeds.
        Returns list of dicts with keys: title, content, source, date, url.
        """
        articles = []
        for url in self.feed_urls:
            try:
                feed = feedparser.parse(url)
                source_name = feed.feed.get("title", url)
                for entry in feed.entries:
                    title = (entry.get("title") or "").strip()
                    if not title:
                        continue
                    link = entry.get("link", "")
                    content = (entry.get("summary") or entry.get("description") or "").strip()
                    if not content:
                        content = title
                    date_str = _parse_date(entry)
                    articles.append({
                        "title": title,
                        "content": content,
                        "source": source_name,
                        "date": date_str or None,
                        "url": link or None,
                    })
                    if limit and len(articles) >= limit:
                        break
            except Exception as e:
                log.warning(f"RSS fetch failed for {url}: {e}")
            if limit and len(articles) >= limit:
                break
        log.info(f"RSS fetcher collected {len(articles)} entries")
        return articles[:limit] if limit else articles
