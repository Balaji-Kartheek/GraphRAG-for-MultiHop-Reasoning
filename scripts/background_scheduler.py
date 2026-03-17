"""
In-process scheduler: run once and leave it running. It will run the pipeline
every N hours (e.g. 1 or 24) by itself. You do NOT run this script every day—
start it once (e.g. when you boot or start work) and it keeps fetching/updating
data at the interval. Use Ctrl+C only when you want to stop the scheduler.

Cross-platform (Windows, macOS, Linux). Configure via .env:
  SCHEDULER_INTERVAL_MINUTES=5  # every 5 minutes (testing)
  SCHEDULER_INTERVAL_HOURS=1    # every 1 hour (used if MINUTES is 0)
  SCHEDULER_INTERVAL_HOURS=24   # every 24 hours

Usage (from project root):
  python -m scripts.background_scheduler
"""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from apscheduler.schedulers.blocking import BlockingScheduler
from config.settings import settings
from config.logger import log


def run_pipeline_job():
    """Single run: fetch from HN and run full pipeline."""
    try:
        from scripts.run_pipeline import run_full_pipeline
        run_full_pipeline(source="fetch", limit=settings.fetch_limit_per_run)
    except Exception as e:
        log.error(f"Scheduled pipeline run failed: {e}")


if __name__ == "__main__":
    use_minutes = getattr(settings, "scheduler_interval_minutes", 0) or 0
    if use_minutes > 0:
        interval_val = use_minutes
        interval_unit = "minute(s)"
        job_kw = {"minutes": use_minutes}
    else:
        interval_val = settings.scheduler_interval_hours
        interval_unit = "hour(s)"
        job_kw = {"hours": interval_val}
    log.info(
        f"GraphRAG scheduler started. Pipeline will run every {interval_val} {interval_unit}. "
        f"Leave this process running; Ctrl+C only when you want to stop."
    )
    if getattr(settings, "scheduler_run_on_start", False):
        log.info("Running pipeline once at startup (SCHEDULER_RUN_ON_START=1).")
        run_pipeline_job()
    scheduler = BlockingScheduler()
    scheduler.add_job(run_pipeline_job, "interval", **job_kw)
    scheduler.start()
