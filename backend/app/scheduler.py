"""
Job Scheduler for Valido Automation
Handles automatic execution of watch folder jobs based on schedule
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from typing import Optional
import requests
from app.utils.logger import get_logger

logger = get_logger("Scheduler")

class JobScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logger.info("Job scheduler started")
    
    def schedule_job(self, watch_folder_id: int, schedule_times: str):
        """
        Schedule a watch folder job to run at specific times.
        schedule_times format: "13:00,18:30" (comma-separated HH:MM times)
        """
        if not schedule_times:
            logger.warning(f"No schedule times provided for watch folder {watch_folder_id}")
            return
        
        try:
            # Parse schedule times
            times = [t.strip() for t in schedule_times.split(',') if t.strip()]
            
            if not times:
                logger.warning(f"Empty schedule times for watch folder {watch_folder_id}")
                return
            
            # Remove any existing jobs for this watch folder
            self.remove_job(watch_folder_id)
            
            # Schedule for each time
            for time_str in times:
                try:
                    hour, minute = time_str.split(':')
                    hour = int(hour)
                    minute = int(minute)
                    
                    # Create cron trigger for daily execution
                    trigger = CronTrigger(hour=hour, minute=minute)
                    
                    # Add job
                    job_id = f"watch_folder_{watch_folder_id}_{time_str.replace(':', '')}"
                    self.scheduler.add_job(
                        func=self._execute_job,
                        trigger=trigger,
                        args=[watch_folder_id],
                        id=job_id,
                        name=f"Watch Folder {watch_folder_id} at {time_str}",
                        replace_existing=True
                    )
                    
                    logger.info(f"Scheduled watch folder {watch_folder_id} at {time_str} (job ID: {job_id})")
                    
                except Exception as e:
                    logger.error(f"Failed to schedule time {time_str} for watch folder {watch_folder_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to schedule watch folder {watch_folder_id}: {e}")
    
    def remove_job(self, watch_folder_id: int):
        """Remove all scheduled jobs for a watch folder"""
        try:
            # Get all jobs and remove those matching this watch folder
            jobs = self.scheduler.get_jobs()
            for job in jobs:
                if job.id.startswith(f"watch_folder_{watch_folder_id}_"):
                    self.scheduler.remove_job(job.id)
                    logger.info(f"Removed scheduled job: {job.id}")
        except Exception as e:
            logger.error(f"Failed to remove jobs for watch folder {watch_folder_id}: {e}")
    
    def _execute_job(self, watch_folder_id: int):
        """Execute a watch folder job"""
        try:
            logger.info(f"⏰ Scheduled execution triggered for watch folder {watch_folder_id}")
            
            # Call the /run endpoint to trigger the job
            url = f"http://localhost:8000/api/v1/watch-folders/{watch_folder_id}/run"
            response = requests.post(url)
            
            if response.ok:
                result = response.json()
                logger.info(f"✓ Scheduled job started successfully: {result.get('message')}")
            else:
                logger.error(f"✗ Scheduled job failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"✗ Failed to execute scheduled job for watch folder {watch_folder_id}: {e}")
    
    def reload_schedules(self):
        """Reload all schedules from database"""
        try:
            from app.db import engine
            from app.models import WatchFolder
            from sqlmodel import Session, select
            
            with Session(engine) as session:
                statement = select(WatchFolder).where(WatchFolder.enabled == True)
                watch_folders = session.exec(statement).all()
                
                logger.info(f"Reloading schedules for {len(watch_folders)} active watch folders")
                
                for wf in watch_folders:
                    if wf.schedule_times:
                        self.schedule_job(wf.id, wf.schedule_times)
                        
        except Exception as e:
            logger.error(f"Failed to reload schedules: {e}")
    
    def list_jobs(self):
        """List all scheduled jobs"""
        jobs = self.scheduler.get_jobs()
        logger.info(f"Currently scheduled jobs: {len(jobs)}")
        for job in jobs:
            logger.info(f"  - {job.name} (ID: {job.id}) - Next run: {job.next_run_time}")
        return jobs
    
    def shutdown(self):
        """Shutdown the scheduler"""
        logger.info("Shutting down job scheduler")
        self.scheduler.shutdown()


# Global scheduler instance
_scheduler: Optional[JobScheduler] = None

def get_scheduler() -> JobScheduler:
    """Get the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = JobScheduler()
    return _scheduler

def shutdown_scheduler():
    """Shutdown the global scheduler"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        _scheduler = None
