from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone
import logging
from typing import Optional
import pytz
import paramiko
import os

logger = logging.getLogger(__name__)

class AsRunScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._is_running = False
        self.alaska_tz = pytz.timezone('America/Anchorage')

    async def check_asrun_files(self):
        """Check for missing AsRun files and handle alerts/restarts"""
        try:
            current_time = datetime.now(self.alaska_tz)
            logger.info(f"Running scheduled AsRun file check at {current_time}")
            
            # Import here to avoid circular imports
            from .main import check_latest_file
            
            # Run the check
            result = await check_latest_file()
            
            if result["status"] == "success" and result.get("days_behind", 0) > 0:
                logger.warning(f"Missing AsRun files detected: {result['warning']}")
                await self.handle_missing_files(result)
            
        except Exception as e:
            logger.error(f"Error in scheduled file check: {str(e)}")
            logger.exception("Full traceback:")

    async def handle_missing_files(self, check_result):
        """Handle missing files by sending alerts and optionally restarting traffic module"""
        try:
            # Prepare alert message
            message = (
                f"AsRun File Alert\n"
                f"Missing files detected at {check_result['current_time_alaska']}\n"
                f"Last successful file: {check_result['latest_file']['date']}\n"
                f"Missing dates: {', '.join(check_result['missing_dates'])}\n"
                f"Days behind: {check_result['days_behind']}"
            )
            
            # Log the alert
            logger.warning(message)
            
            # TODO: Add email notification here
            # await self.send_email_alert(message)
            
            # TODO: Add traffic module restart logic here
            # if check_result['days_behind'] >= 1:
            #     await self.restart_traffic_module()
            
        except Exception as e:
            logger.error(f"Error handling missing files: {str(e)}")

    def start(self):
        """Start the scheduler"""
        if not self._is_running:
            try:
                # Schedule the file check for 6:05 AM Alaska time
                self.scheduler.add_job(
                    self.check_asrun_files,
                    CronTrigger(
                        hour=6,
                        minute=5,
                        timezone=self.alaska_tz
                    ),
                    id='check_asrun_files',
                    name='Check AsRun Files',
                    replace_existing=True
                )
                
                self.scheduler.start()
                self._is_running = True
                logger.info("Scheduler started successfully")
            except Exception as e:
                logger.error(f"Error starting scheduler: {str(e)}")
                raise

    def stop(self):
        """Stop the scheduler"""
        if self._is_running:
            try:
                self.scheduler.shutdown()
                self._is_running = False
                logger.info("Scheduler stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping scheduler: {str(e)}")
                raise

    @property
    def is_running(self) -> bool:
        return self._is_running

    def get_next_run_time(self) -> Optional[datetime]:
        """Get the next scheduled run time"""
        if self._is_running:
            job = self.scheduler.get_job('check_asrun_files')
            return job.next_run_time if job else None
        return None