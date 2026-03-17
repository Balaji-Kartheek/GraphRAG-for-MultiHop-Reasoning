"""
Hacker News fetcher via Algolia API. Free; no API key required.
"""
from typing import List, Dict, Any
from datetime import datetime
import urllib.request
import urllib.parse
import json
import ssl
from config.logger import log

BASE_URL = "https://hn.algolia.com/api/v1/search_by_date"


class HackerNewsFetcher:
    """Fetch tech stories from Hacker News. Free; no API key."""

    def fetch(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Fetch recent HN stories. Returns list of dicts: title, content, source, date, url.
        Uses title + optional story_text as content (no scraping).
        """
        articles = []
        try:
            params = {"tags": "story", "hitsPerPage": min(limit or 50, 100)}
            url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"User-Agent": "GraphRAG/1.0"})
            # NOTE: On some local setups (e.g. macOS without updated certs),
            # SSL verification can fail. We fall back to an unverified context
            # so development still works. For production, you should fix system
            # certificates instead of disabling verification.
            context = ssl.create_default_context()
            try:
                resp = urllib.request.urlopen(req, timeout=15, context=context)
            except Exception:
                # Fallback: disable cert verification (dev-only safety valve)
                insecure_ctx = ssl._create_unverified_context()
                resp = urllib.request.urlopen(req, timeout=15, context=insecure_ctx)
            with resp:
                data = json.loads(resp.read().decode())
            for hit in data.get("hits", []):
                title = (hit.get("title") or "").strip()
                if not title:
                    continue
                # Use story_text if available, else title as content
                content = (hit.get("story_text") or hit.get("title") or "").strip()
                if not content:
                    content = title
                ts = hit.get("created_at_i")
                date_str = None
                if ts:
                    try:
                        date_str = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
                    except (ValueError, OSError):
                        pass
                articles.append({
                    "title": title,
                    "content": content[:50000],
                    "source": "Hacker News",
                    "date": date_str,
                    "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                })
                if limit and len(articles) >= limit:
                    break
        except Exception as e:
            log.warning(f"Hacker News fetch failed: {e}")
        log.info(f"Hacker News fetcher collected {len(articles)} entries")
        return articles[:limit] if limit else articles
