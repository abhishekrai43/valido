"""
Test Script: Reset Trial to Active State
This script resets the trial to start now (full 90 days remaining).
"""
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import get_session
from app.models import User
from app.utils.trial_manager import set_trial_start_in_registry, TRIAL_DAYS
from sqlmodel import select

def reset_trial():
    """Reset trial to active (starts now)."""
    print("\n" + "="*60)
    print("RESETTING TRIAL TO ACTIVE STATE")
    print("="*60)
    
    # Calculate current time
    now = datetime.utcnow()
    print(f"Setting trial start to: {now}")
    print(f"Trial days: {TRIAL_DAYS}")
    
    # Update Registry
    print("\n1. Updating Windows Registry...")
    set_trial_start_in_registry(now)
    print("   ✓ Registry updated")
    
    # Update Database
    print("\n2. Updating Database...")
    with get_session() as db:
        statement = select(User).where(User.username == "default")
        user = db.exec(statement).first()
        if user:
            user.trial_start_date = now
            user.license_active = False
            user.license_key = None
            db.add(user)
            db.commit()
            print(f"   ✓ User '{user.username}' trial reset")
        else:
            # Create user with fresh trial
            user = User(username="default", trial_start_date=now)
            db.add(user)
            db.commit()
            print("   ✓ Created default user with fresh trial")
    
    print("\n" + "="*60)
    print("✓ TRIAL RESET SUCCESSFULLY")
    print("="*60)
    print(f"\nYou now have {TRIAL_DAYS} days of trial remaining.")
    print("Refresh your browser to continue using Valido.")
    print("\nTo expire trial again, run: python scripts/expire_trial.py")
    print("="*60 + "\n")


if __name__ == "__main__":
    reset_trial()
