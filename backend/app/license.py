"""
license.py - License banner display for Valido UI.
Uses trial_manager.py for actual trial/license logic.
"""

from typing import Optional, Dict
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_license_banner() -> Optional[Dict]:
    """Get license banner text for UI display."""
    from app.db import get_session
    from app.models import User
    from sqlmodel import select
    from app.utils.trial_manager import calculate_trial_status, check_access
    
    try:
        with get_session() as session:
            user = session.exec(select(User).where(User.username == "default")).first()
            if not user:
                # No user yet - show trial info
                return {
                    "type": "trial",
                    "message": "14-day trial will begin on first use",
                    "details": "Full features available during trial",
                    "link": None,
                    "linkText": None
                }
            
            access_status = check_access(user)
            
            if user.license_active:
                # Licensed user
                return {
                    "type": "licensed",
                    "message": f"Licensed ({user.license_type})",
                    "details": "Thank you for your support!",
                    "link": None,
                    "linkText": None
                }
            
            # Trial user
            trial_status = calculate_trial_status(user.trial_start_date)
            if not trial_status['expired']:
                return {
                    "type": "trial",
                    "message": f"Trial: {trial_status['days_remaining']} days remaining",
                    "details": "Enjoying Valido? Purchase a license to continue",
                    "link": "https://rai89.gumroad.com/l/bdspjn",
                    "linkText": "Buy Now"
                }
            else:
                # Trial expired
                return {
                    "type": "expired",
                    "message": "Trial expired",
                    "details": "Purchase a license to continue using Valido",
                    "link": "https://rai89.gumroad.com/l/bdspjn",
                    "linkText": "Purchase License"
                }
    except Exception as e:
        logger.error(f"Error getting license banner: {e}")
        return None