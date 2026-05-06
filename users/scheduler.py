"""Scheduled task service for daily report notifications."""

import logging
import hashlib
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from users.config import config
from users.schemas import NotificationTime
from users.email_service import get_email_service

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for scheduling daily report notifications."""

    def __init__(self):
        """Initialize scheduler service."""
        self.scheduler = BackgroundScheduler(
            timezone=config.scheduler_timezone,
            job_defaults={
                "coalesce": True,
                "max_instances": config.scheduler_max_instances,
                "misfire_grace_time": config.scheduler_misfire_grace_seconds,
            },
        )
        self.running = False
        self.morning_hour, self.morning_minute = self._parse_time(config.notification_time_morning)
        self.evening_hour, self.evening_minute = self._parse_time(config.notification_time_evening)

    def _parse_time(self, value: str) -> tuple[int, int]:
        """Parse HH:MM scheduler config."""
        hour, minute = value.split(":", maxsplit=1)
        return int(hour), int(minute)

    def start(self):
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler already running")
            return

        if not config.enable_scheduler:
            logger.info("Scheduler disabled by ENABLE_SCHEDULER=false")
            return

        logger.info("Starting scheduler service")

        self.scheduler.add_job(
            self._send_morning_reports,
            CronTrigger(hour=self.morning_hour, minute=self.morning_minute),
            id="morning_reports",
            name=f"Morning Reports ({config.notification_time_morning})",
            replace_existing=True
        )

        self.scheduler.add_job(
            self._send_evening_reports,
            CronTrigger(hour=self.evening_hour, minute=self.evening_minute),
            id="evening_reports",
            name=f"Evening Reports ({config.notification_time_evening})",
            replace_existing=True
        )

        self.scheduler.start()
        self.running = True

        logger.info(f"Scheduler started successfully with jobs: morning ({config.notification_time_morning}), evening ({config.notification_time_evening})")

    def stop(self):
        """Stop the scheduler."""
        if not self.running:
            return

        logger.info("Stopping scheduler service")
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
        self.running = False
        logger.info("Scheduler stopped")

    def _send_morning_reports(self):
        """Send morning reports at 8:00 AM."""
        trace_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        logger.info(f"[TRACE={trace_id}] Running morning reports job")

        email_service = get_email_service()
        results = email_service.send_reports_for_time(NotificationTime.MORNING)

        logger.info(f"[TRACE={trace_id}] Morning reports completed: {results}")

    def _send_evening_reports(self):
        """Send evening reports at 8:00 PM."""
        trace_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        logger.info(f"[TRACE={trace_id}] Running evening reports job")

        email_service = get_email_service()
        results = email_service.send_reports_for_time(NotificationTime.EVENING)

        logger.info(f"[TRACE={trace_id}] Evening reports completed: {results}")

    def trigger_morning_now(self):
        """Manually trigger morning reports (for testing)."""
        logger.info("Manually triggering morning reports")
        self._send_morning_reports()

    def trigger_evening_now(self):
        """Manually trigger evening reports (for testing)."""
        logger.info("Manually triggering evening reports")
        self._send_evening_reports()

    def get_jobs(self):
        """Get list of scheduled jobs."""
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None
            }
            for job in self.scheduler.get_jobs()
        ]


_scheduler_service: Optional[SchedulerService] = None


def get_scheduler_service() -> SchedulerService:
    """Get singleton scheduler service instance."""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service


def start_scheduler():
    """Start the global scheduler."""
    scheduler = get_scheduler_service()
    scheduler.start()


def stop_scheduler():
    """Stop the global scheduler."""
    scheduler = get_scheduler_service()
    scheduler.stop()