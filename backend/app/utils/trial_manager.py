"""app.utils.trial_manager

Trial and License Management for Valido.

Trial duration is controlled via :data:`TRIAL_DAYS`.
"""
import winreg
import hashlib
import uuid
import platform
from datetime import datetime, timedelta
from typing import Dict, Optional
from app.utils.logger import get_logger
from app.utils.cloud_license_manager import CloudLicenseManager

logger = get_logger('trial_manager')

# Configuration
TEST_MODE = False  # Set to False for production
# ~3 months trial in production (kept as days for simplicity/compat)
TRIAL_DAYS = 1 if TEST_MODE else 90  # 1 day for testing, 90 for production (~3 months)

# Registry paths
REGISTRY_PATH = r"Software\Valido\License"
REGISTRY_TRIAL_START = "TrialStartDate"
REGISTRY_HARDWARE_ID = "HardwareID"
REGISTRY_LICENSE_KEY = "LicenseKey"  # Store validated license key
REGISTRY_LICENSE_TYPE = "LicenseType"
REGISTRY_LICENSE_VALIDATED = "LastValidated"
VALIDATION_GRACE_DAYS = 7  # Allow 7 days offline before forcing revalidation


def get_hardware_id() -> str:
    """
    Generate a unique hardware ID for this machine.
    Uses CloudLicenseManager for consistency with API.
    """
    try:
        return CloudLicenseManager.get_device_id()
    except Exception as e:
        logger.error(f"Failed to generate hardware ID: {e}")
        return "unknown"


def get_registry_value(key_name: str) -> Optional[str]:
    """Get a value from Windows Registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, key_name)
        winreg.CloseKey(key)
        return value
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.warning(f"Failed to read registry key {key_name}: {e}")
        return None


def set_registry_value(key_name: str, value: str):
    """Set a value in Windows Registry."""
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH)
        winreg.SetValueEx(key, key_name, 0, winreg.REG_SZ, str(value))
        winreg.CloseKey(key)
    except Exception as e:
        logger.warning(f"Failed to write registry key {key_name}: {e}")


def get_trial_start_from_registry() -> Optional[datetime]:
    """Get trial start date from Registry (persists even if DB deleted)."""
    trial_start_str = get_registry_value(REGISTRY_TRIAL_START)
    if trial_start_str:
        try:
            return datetime.fromisoformat(trial_start_str)
        except:
            return None
    return None


def set_trial_start_in_registry(start_date: datetime):
    """Store trial start date in Registry."""
    set_registry_value(REGISTRY_TRIAL_START, start_date.isoformat())
    # Also store hardware ID to detect if trial is being moved between machines
    set_registry_value(REGISTRY_HARDWARE_ID, get_hardware_id())


def calculate_trial_status(trial_start_date: Optional[datetime]) -> Dict:
    """
    Calculate trial status based on start date.
    Checks both parameter and Registry (Registry takes precedence).
    
    Args:
        trial_start_date: When the trial started (None = not started yet)
        
    Returns:
        Dict with trial status information
    """
    # Check Registry first (more reliable than DB)
    registry_start = get_trial_start_from_registry()
    if registry_start:
        trial_start_date = registry_start
    
    if not trial_start_date:
        # Trial not started yet - will start on first use
        return {
            'status': 'not_started',
            'days_remaining': TRIAL_DAYS,
            'days_used': 0,
            'expired': False,
            'message': f'{TRIAL_DAYS}-day trial will begin on first use'
        }
    
    now = datetime.utcnow()
    days_used = (now - trial_start_date).days
    days_remaining = max(0, TRIAL_DAYS - days_used)
    expired = days_remaining == 0
    
    return {
        'status': 'active' if not expired else 'expired',
        'days_remaining': days_remaining,
        'days_used': days_used,
        'expired': expired,
        'trial_started': trial_start_date.isoformat(),
        'message': f'{days_remaining} days remaining' if not expired else 'Trial expired'
    }


def start_trial() -> datetime:
    """Start a new trial period. Returns the start datetime."""
    start_time = datetime.utcnow()
    
    # Store in Registry (survives DB deletion)
    set_trial_start_in_registry(start_time)
    
    logger.info(f"Trial started at {start_time} (stored in Registry)")
    return start_time


def validate_license_key(license_key: str) -> Dict:
    """
    Validate a license key via secure cloud API.
    Enforces device limits at the cloud level (prevents license sharing).
    
    Args:
        license_key: The license key to validate
        
    Returns:
        Dict with validation result
    """
    if not license_key or not license_key.strip():
        return {'valid': False, 'error': 'License key is required'}
    
    license_key = license_key.strip()
    
    # Test mode - accept test key
    if TEST_MODE and license_key == "TEST-LICENSE-KEY":
        logger.info("Test mode: Accepting test license key")
        set_registry_value(REGISTRY_LICENSE_KEY, license_key)
        set_registry_value(REGISTRY_LICENSE_TYPE, "monthly")
        set_registry_value(REGISTRY_HARDWARE_ID, get_hardware_id())
        set_registry_value(REGISTRY_LICENSE_VALIDATED, datetime.utcnow().isoformat())
        return {
            'valid': True,
            'license_type': 'monthly',
            'test_mode': True,
            'message': 'Test license activated'
        }
    
    # Check if we have recent validation in registry (grace period for offline use)
    last_validated_str = get_registry_value(REGISTRY_LICENSE_VALIDATED)
    cached_license_key = get_registry_value(REGISTRY_LICENSE_KEY)
    
    if cached_license_key == license_key and last_validated_str:
        try:
            last_validated = datetime.fromisoformat(last_validated_str)
            days_since_validation = (datetime.utcnow() - last_validated).days
            
            if days_since_validation < VALIDATION_GRACE_DAYS:
                # Use cached validation (offline grace period)
                cached_type = get_registry_value(REGISTRY_LICENSE_TYPE) or "monthly"
                logger.info(f"Using cached validation ({days_since_validation} days old)")
                return {
                    'valid': True,
                    'license_type': cached_type,
                    'cached': True,
                    'message': f'License valid (verified {days_since_validation} days ago)'
                }
        except:
            pass
    
    # Validate with cloud API
    logger.info(f"Validating license key with cloud API: {license_key[:8]}...")
    
    try:
        result = CloudLicenseManager.validate_license(license_key)
        
        if result.get('valid'):
            # Store in registry for offline grace period
            set_registry_value(REGISTRY_LICENSE_KEY, license_key)
            set_registry_value(REGISTRY_LICENSE_TYPE, result.get('license_type', 'monthly'))
            set_registry_value(REGISTRY_HARDWARE_ID, get_hardware_id())
            set_registry_value(REGISTRY_LICENSE_VALIDATED, datetime.utcnow().isoformat())
            
            logger.info(f"License validated successfully: {license_key[:8]}...")
            
            return {
                'valid': True,
                'license_type': result.get('license_type'),
                'message': result.get('message', 'License activated successfully!')
            }
        else:
            # Validation failed
            logger.warning(f"License validation failed: {result.get('message')}")
            error_payload = {
                'valid': False,
                'error': result.get('message', 'Invalid license key')
            }

            # If the server is failing (5xx), treat as transient so routes can return 503.
            if result.get('transient'):
                error_payload['transient'] = True
                error_payload['status_code'] = result.get('status_code')

            return error_payload
            
    except Exception as e:
        logger.error(f"License validation error: {e}")
        
        # If we have cached validation and API is unreachable, use cache
        if cached_license_key == license_key and last_validated_str:
            cached_type = get_registry_value(REGISTRY_LICENSE_TYPE) or "monthly"
            logger.info("API unreachable, using cached validation")
            return {
                'valid': True,
                'license_type': cached_type,
                'cached': True,
                'offline': True,
                'message': 'License valid (offline mode)'
            }
        
        return {
            'valid': False,
            'error': f'Could not validate license: {str(e)}'
        }


def check_access(user) -> Dict:
    """
    Check if user has access (either trial active or valid license).
    
    Args:
        user: User model instance
        
    Returns:
        Dict with access status
    """
    # If user has active license, check if it's still valid
    if user.license_active and user.license_key:
        # Validate license key (uses cache with grace period)
        validation = validate_license_key(user.license_key)
        
        if validation.get('valid'):
            return {
                'has_access': True,
                'reason': 'active_license',
                'license_type': validation.get('license_type'),
                'message': f"Licensed ({validation.get('license_type')})"
            }
        else:
            # License no longer valid
            logger.warning(f"License validation failed: {validation.get('error')}")
            user.license_active = False
            # Fall through to trial check
    
    # Check trial status
    trial_status = calculate_trial_status(user.trial_start_date)
    
    if not trial_status['expired']:
        return {
            'has_access': True,
            'reason': 'trial',
            'days_remaining': trial_status['days_remaining'],
            'message': f"Trial: {trial_status['days_remaining']} days remaining"
        }
    
    # No access
    return {
        'has_access': False,
        'reason': 'trial_expired',
        'message': 'Trial expired. Please enter a license key to continue.',
        'purchase_url': 'https://your-purchase-url.com'
    }