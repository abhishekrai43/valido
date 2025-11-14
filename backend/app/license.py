"""
license.py - Simple trial license management for Valido.
"""

import os
import json
import hashlib
import time
from typing import Dict, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

LICENSE_FILE = "valido.lic"
TRIAL_DAYS = 30


class LicenseManager:
    """Simple license manager for trial/demo purposes."""

    @staticmethod
    def get_license_info() -> Dict:
        """Get current license information."""
        license_path = os.path.join(os.getcwd(), LICENSE_FILE)

        if not os.path.exists(license_path):
            # Trial mode
            return {
                "type": "trial",
                "valid": True,
                "days_remaining": TRIAL_DAYS,
                "features": ["basic_validation", "web_interface"],
            }

        try:
            with open(license_path, 'r') as f:
                license_data = json.load(f)

            # Simple validation - in production, use proper license validation
            if license_data.get("valid", False):
                return {
                    "type": "licensed",
                    "valid": True,
                    "features": license_data.get("features", []),
                }
            else:
                return {
                    "type": "invalid",
                    "valid": False,
                    "error": "Invalid license",
                }
        except Exception as e:
            logger.error(f"License validation error: {e}")
            return {
                "type": "error",
                "valid": False,
                "error": str(e),
            }

    @staticmethod
    def is_feature_enabled(feature: str) -> bool:
        """Check if a feature is enabled."""
        license_info = LicenseManager.get_license_info()
        return feature in license_info.get("features", [])

    @staticmethod
    def create_trial_license():
        """Create a trial license file."""
        license_path = os.path.join(os.getcwd(), LICENSE_FILE)
        trial_data = {
            "type": "trial",
            "created": time.time(),
            "valid": True,
            "features": ["basic_validation", "web_interface", "api_access"],
        }

        with open(license_path, 'w') as f:
            json.dump(trial_data, f, indent=2)

        logger.info("Trial license created")


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