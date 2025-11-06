"""
Valido Agent - Scheduled Folder Processing

This agent runs on user's PC and processes folders on schedule.
Communicates with Valido server to submit batches and retrieve results.
"""

import os
import sys
import time
import json
import glob
import shutil
import requests
import schedule
from datetime import datetime
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('valido-agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ValidoAgent')


class ValidoAgent:
    """Main agent class for scheduled folder processing."""
    
    def __init__(self, config_path='agent_config.json'):
        self.config_path = config_path
        self.config = self.load_config()
        self.server_url = self.config.get('server_url', 'http://localhost:9090')
        self.watch_folders = []
        
        logger.info(f"Valido Agent initialized. Server: {self.server_url}")
    
    def load_config(self):
        """Load agent configuration from JSON file."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        else:
            # Default config
            return {
                'server_url': 'http://localhost:9090',
                'watch_folders': []
            }
    
    def save_config(self):
        """Save agent configuration to JSON file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
        logger.info("Configuration saved")
    
    def fetch_watch_folders(self):
        """Fetch watch folder configurations from server."""
        try:
            response = requests.get(f"{self.server_url}/api/v1/watch-folders/")
            response.raise_for_status()
            self.watch_folders = response.json()
            logger.info(f"Fetched {len(self.watch_folders)} watch folder configurations")
            return self.watch_folders
        except Exception as e:
            logger.error(f"Failed to fetch watch folders: {e}")
            return []
    
    def process_folder(self, watch_config):
        """Process a single watch folder."""
        folder_id = watch_config['id']
        folder_name = watch_config['name']
        input_path = watch_config['input_path']
        output_path = watch_config['output_path']
        ruleset_id = watch_config['ruleset_id']
        move_processed = watch_config.get('move_processed', True)
        processed_path = watch_config.get('processed_path')
        delete_after = watch_config.get('delete_after', False)
        
        logger.info(f"Processing folder: {folder_name} ({input_path})")
        
        # Check if folder exists
        if not os.path.exists(input_path):
            logger.warning(f"Input folder does not exist: {input_path}")
            return
        
        # Find all PDF files
        pdf_pattern = os.path.join(input_path, '*.pdf')
        pdf_files = glob.glob(pdf_pattern)
        
        if not pdf_files:
            logger.info(f"No PDF files found in {input_path}")
            return
        
        # Limit to 500 files per batch
        if len(pdf_files) > 500:
            logger.warning(f"Found {len(pdf_files)} files, processing first 500")
            pdf_files = pdf_files[:500]
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        # Fetch ruleset from server
        try:
            response = requests.get(f"{self.server_url}/api/v1/rulesets/{ruleset_id}")
            response.raise_for_status()
            ruleset = response.json()
            rules = ruleset['rules']
            logger.info(f"Using ruleset: {ruleset['name']}")
        except Exception as e:
            logger.error(f"Failed to fetch ruleset {ruleset_id}: {e}")
            return
        
        # Submit files to server
        try:
            files = []
            for pdf_path in pdf_files:
                files.append(('files', (os.path.basename(pdf_path), open(pdf_path, 'rb'), 'application/pdf')))
            
            data = {'rules': json.dumps(rules)}
            
            logger.info(f"Uploading {len(pdf_files)} files to server...")
            response = requests.post(
                f"{self.server_url}/api/v1/submit",
                files=files,
                data=data,
                timeout=300  # 5 minute timeout for upload
            )
            response.raise_for_status()
            
            # Close all file handles
            for _, (_, file_obj, _) in files:
                file_obj.close()
            
            task_id = response.json()['task_id']
            logger.info(f"Task submitted: {task_id}")
            
            # Poll for completion
            result = self.wait_for_task(task_id)
            
            if result['state'] == 'SUCCESS':
                logger.info(f"Processing complete for {folder_name}")
                
                # Download results
                self.download_results(task_id, output_path)
                
                # Update stats on server
                try:
                    requests.post(
                        f"{self.server_url}/api/v1/watch-folders/{folder_id}/update-stats",
                        params={'files_processed': len(pdf_files)}
                    )
                except Exception as e:
                    logger.warning(f"Failed to update stats: {e}")
                
                # Move or delete processed files
                if delete_after:
                    for pdf_path in pdf_files:
                        os.remove(pdf_path)
                        logger.info(f"Deleted: {pdf_path}")
                elif move_processed and processed_path:
                    os.makedirs(processed_path, exist_ok=True)
                    for pdf_path in pdf_files:
                        dest = os.path.join(processed_path, os.path.basename(pdf_path))
                        shutil.move(pdf_path, dest)
                        logger.info(f"Moved: {pdf_path} → {dest}")
            else:
                logger.error(f"Task failed: {result}")
        
        except Exception as e:
            logger.error(f"Error processing folder {folder_name}: {e}")
    
    def wait_for_task(self, task_id, timeout=600):
        """Poll task status until complete or timeout."""
        start_time = time.time()
        last_percent = -1
        
        while True:
            try:
                response = requests.get(f"{self.server_url}/api/v1/tasks/{task_id}")
                response.raise_for_status()
                result = response.json()
                
                state = result['state']
                info = result.get('info', {})
                
                if state == 'PENDING':
                    logger.info("Task pending...")
                elif state == 'PROGRESS':
                    percent = info.get('percent', 0)
                    if percent != last_percent:
                        current_file = info.get('current_file', '')
                        logger.info(f"Progress: {percent}% - {current_file}")
                        last_percent = percent
                elif state == 'SUCCESS':
                    logger.info("Task completed successfully")
                    return result
                elif state in ['FAILURE', 'REVOKED']:
                    logger.error(f"Task failed: {state}")
                    return result
                
                # Check timeout
                if time.time() - start_time > timeout:
                    logger.error("Task timeout")
                    return {'state': 'TIMEOUT', 'info': 'Task exceeded timeout'}
                
                time.sleep(2)  # Poll every 2 seconds
            
            except Exception as e:
                logger.error(f"Error polling task: {e}")
                time.sleep(5)
    
    def download_results(self, task_id, output_path):
        """Download CSV and JSON results from server."""
        os.makedirs(output_path, exist_ok=True)
        
        # Download ZIP file
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            zip_filename = f"results_{timestamp}.zip"
            zip_path = os.path.join(output_path, zip_filename)
            
            response = requests.get(f"{self.server_url}/api/v1/tasks/{task_id}/results.zip")
            response.raise_for_status()
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Results saved: {zip_path}")
        except Exception as e:
            logger.error(f"Failed to download results: {e}")
    
    def schedule_jobs(self):
        """Schedule all enabled watch folders."""
        self.fetch_watch_folders()
        
        for watch_config in self.watch_folders:
            if not watch_config.get('enabled', True):
                logger.info(f"Skipping disabled folder: {watch_config['name']}")
                continue
            
            schedule_times = watch_config.get('schedule_times')
            if schedule_times:
                try:
                    times = json.loads(schedule_times) if isinstance(schedule_times, str) else schedule_times
                    for time_str in times:
                        schedule.every().day.at(time_str).do(self.process_folder, watch_config)
                        logger.info(f"Scheduled '{watch_config['name']}' at {time_str}")
                except Exception as e:
                    logger.error(f"Failed to schedule {watch_config['name']}: {e}")
        
        logger.info(f"Scheduled {len(schedule.jobs)} jobs")
    
    def run(self):
        """Main run loop."""
        logger.info("Starting Valido Agent...")
        
        # Schedule jobs
        self.schedule_jobs()
        
        # Run scheduler loop
        logger.info("Agent running. Press Ctrl+C to stop.")
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Agent stopped by user")
        except Exception as e:
            logger.error(f"Agent error: {e}")


def main():
    """Entry point for agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Valido Agent - Scheduled PDF Processing')
    parser.add_argument('--server', default='http://localhost:9090', help='Valido server URL')
    parser.add_argument('--config', default='agent_config.json', help='Configuration file path')
    
    args = parser.parse_args()
    
    agent = ValidoAgent(config_path=args.config)
    agent.server_url = args.server
    agent.run()


if __name__ == '__main__':
    main()
