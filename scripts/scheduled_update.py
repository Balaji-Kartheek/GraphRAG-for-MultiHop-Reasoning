"""
Scheduled knowledge update: runs full pipeline with --source fetch.
For cron (e.g. every 6 hours):
  0 */6 * * * cd /path/to/GraphRAG && .venv/bin/python -m scripts.scheduled_update
Exits 0 on success, non-zero on failure.
"""
import sys
from config.logger import log

if __name__ == "__main__":
    try:
        from scripts.run_pipeline import run_full_pipeline
        run_full_pipeline(source="fetch", limit=None)
        sys.exit(0)
    except Exception as e:
        log.error(f"Scheduled update failed: {e}")
        sys.exit(1)
