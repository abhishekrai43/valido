"""
Fix schedule_times format in database
Converts JSON format ["18:00"] to comma-separated format "18:00"
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlmodel import Session, select
from app.db import engine
from app.models import WatchFolder
import json

def fix_schedule_times():
    """Fix schedule_times format for all watch folders"""
    with Session(engine) as session:
        folders = session.exec(select(WatchFolder)).all()
        
        for folder in folders:
            if folder.schedule_times:
                try:
                    # Try to parse as JSON
                    times_array = json.loads(folder.schedule_times)
                    if isinstance(times_array, list):
                        # Convert to comma-separated string
                        folder.schedule_times = ','.join(times_array)
                        session.add(folder)
                        print(f"Fixed watch folder {folder.id}: {folder.schedule_times}")
                except json.JSONDecodeError:
                    # Already in correct format
                    print(f"Watch folder {folder.id} already in correct format: {folder.schedule_times}")
        
        session.commit()
        print("\nAll watch folders fixed!")

if __name__ == "__main__":
    fix_schedule_times()
