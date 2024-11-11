from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging
from typing import Optional
from .transfer import AsRunTransfer
from .config import Config
import asyncio

logger = logging.getLogger(__name__)

class AsRunScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._is_running = False
        self.config = Config()
        self.transfer = AsRunTransfer(self.config)

    async def process_asrun_files(self):
        """Process AsRun files from configured source"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Starting scheduled AsRun processing at {current_time}")
            
            # Download new files
            downloaded_files = await asyncio.to_thread(
                self.transfer.process_new_files,
                hours_ago=1
            )
            
            logger.info(f"Downloaded {len(downloaded_files)} new files")
            
            # TODO: Process the downloaded files
            # This is where we'll add the file processing code
            
            logger.info(f"Completed scheduled processing at {current_time}")
            
        except Exception as e:
            logger.error(f"Error in scheduled processing: {str(e)}")
            logger.exception("Full traceback:")

    def start(self):
        """Start the scheduler"""
        if not self._is_running:
            try:
                # Schedule the job to run at the start of every hour
                self.scheduler.add_job(
                    self.process_asrun_files,
                    CronTrigger(minute=0),  # Run at the start of every hour
                    id='process_asrun_files',
                    name='Process AsRun Files',
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
            job = self.scheduler.get_job('process_asrun_files')
            return job.next_run_time if job else None
        return None