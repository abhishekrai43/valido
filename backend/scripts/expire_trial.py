"""
Test Script: Expire Trial for Testing License Purchase Flow
This script sets the trial start date far enough in the past to expire the trial.
"""
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import get_session
from app.models import User
from app.utils.trial_manager import set_trial_start_in_registry
from sqlmodel import select

def expire_trial():
    """Set trial to expired (trial start far enough in the past)."""
    print("\n" + "="*60)
    print("EXPIRING TRIAL FOR TESTING")
    print("="*60)
    
    # Calculate expired date (91 days ago -> expired for a 90-day trial)
    expired_date = datetime.utcnow() - timedelta(days=91)
    print(f"Setting trial start to: {expired_date}")
    print(f"This is 91 days ago (trial is 90 days)")
    
    # Update Registry
    print("\n1. Updating Windows Registry...")
    set_trial_start_in_registry(expired_date)
    print("   ✓ Registry updated")
    
    # Update Database
    print("\n2. Updating Database...")
    with get_session() as db:
        statement = select(User).where(User.username == "default")
        user = db.exec(statement).first()
        if user:
            user.trial_start_date = expired_date
            db.add(user)
            db.commit()
            print(f"   ✓ User '{user.username}' trial_start_date updated")
        else:
            # Create user with expired trial
            user = User(username="default", trial_start_date=expired_date)
            db.add(user)
            db.commit()
            print("   ✓ Created default user with expired trial")
    
    print("\n" + "="*60)
    print("✓ TRIAL EXPIRED SUCCESSFULLY")
    print("="*60)
    print("\nNow refresh your browser and you should see:")
    print("  - License purchase modal blocking usage")
    print("  - 'Trial Expired' message")
    print("  - Purchase button to buy license")
    print("\nTo reset trial, run: python scripts/reset_trial.py")
    print("="*60 + "\n")


if __name__ == "__main__":
    expire_trial()
