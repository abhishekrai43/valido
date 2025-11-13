"""
Trial and License Management for Valido
Handles 14-day trial period and Gumroad license validation
Uses Registry + DB for persistence (survives DB deletion)
"""
import winreg
import hashlib
import uuid
import platform
from datetime import datetime, timedelta
from typing import Dict, Optional
from app.utils.logger import get_logger

logger = get_logger('trial_manager')

# Configuration
TEST_MODE = True  # Set to False for production
TRIAL_DAYS = 1 if TEST_MODE else 14  # 1 day for testing, 14 for production
TEST_LICENSE_KEY = "TEST-VALIDO-2024"  # Works in test mode only

# Registry paths
REGISTRY_PATH = r"Software\Valido\License"
REGISTRY_TRIAL_START = "TrialStartDate"
REGISTRY_HARDWARE_ID = "HardwareID"
REGISTRY_LICENSE_KEY = "LicenseKey"
REGISTRY_LICENSE_TYPE = "LicenseType"
REGISTRY_LICENSE_VALIDATED = "LastValidated"

# Gumroad configuration (will be set when you create products)
GUMROAD_PRODUCT_ID = None  # Set this after creating Gumroad product
GUMROAD_API_URL = "https://api.gumroad.com/v2/licenses/verify"
VALIDATION_GRACE_DAYS = 7  # Allow 7 days offline before forcing revalidation


def get_hardware_id() -> str:
    """
    Generate a unique hardware ID for this machine.
    Based on MAC address and other hardware identifiers.
    """
    try:
        # Get MAC address
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                       for elements in range(0, 2*6, 2)][::-1])
        
        # Get system info
        system_info = f"{platform.system()}{platform.node()}{mac}"
        
        # Hash it to create a stable ID
        hw_id = hashlib.sha256(system_info.encode()).hexdigest()[:32]
        return hw_id
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


def validate_license_key(license_key: str, license_type: Optional[str] = None) -> Dict:
    """
    Validate a license key with Gumroad API (with offline grace period).
    
    Args:
        license_key: The license key to validate
        license_type: Expected license type ('monthly' or 'annual')
        
    Returns:
        Dict with validation result
    """
    if not license_key:
        return {
            'valid': False,
            'error': 'No license key provided'
        }
    
    # Test mode - accept test key
    if TEST_MODE and license_key == TEST_LICENSE_KEY:
        logger.info(f"Test mode: Accepting test license key")
        # Store in registry for persistence
        set_registry_value(REGISTRY_LICENSE_KEY, license_key)
        set_registry_value(REGISTRY_LICENSE_TYPE, 'monthly')
        set_registry_value(REGISTRY_LICENSE_VALIDATED, datetime.utcnow().isoformat())
        return {
            'valid': True,
            'license_type': 'monthly',
            'customer_email': 'test@example.com',
            'customer_name': 'Test User',
            'test_mode': True
        }
    
    # Check if we have a cached validation (offline grace period)
    last_validated_str = get_registry_value(REGISTRY_LICENSE_VALIDATED)
    cached_key = get_registry_value(REGISTRY_LICENSE_KEY)
    
    if cached_key == license_key and last_validated_str:
        try:
            last_validated = datetime.fromisoformat(last_validated_str)
            days_since_validation = (datetime.utcnow() - last_validated).days
            
            if days_since_validation < VALIDATION_GRACE_DAYS:
                logger.info(f"Using cached validation ({days_since_validation} days old)")
                return {
                    'valid': True,
                    'license_type': get_registry_value(REGISTRY_LICENSE_TYPE) or license_type,
                    'cached': True,
                    'last_validated': last_validated.isoformat()
                }
        except:
            pass
    
    # Production mode - validate with Gumroad
    if not TEST_MODE:
        try:
            import requests
            
            if not GUMROAD_PRODUCT_ID:
                logger.error("Gumroad product ID not configured")
                return {
                    'valid': False,
                    'error': 'License validation not configured. Please contact support.'
                }
            
            # Verify with Gumroad API
            logger.info(f"Validating license with Gumroad API...")
            response = requests.post(
                GUMROAD_API_URL,
                data={
                    'product_id': GUMROAD_PRODUCT_ID,
                    'license_key': license_key,
                    'increment_uses_count': 'false'  # Don't count validation as a "use"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    purchase = data.get('purchase', {})
                    
                    # Check if subscription is still active
                    if purchase.get('subscription_cancelled_at') or purchase.get('subscription_failed_at'):
                        return {
                            'valid': False,
                            'error': 'Subscription cancelled or payment failed. Please renew your subscription.'
                        }
                    
                    # Valid! Store in registry for offline use
                    set_registry_value(REGISTRY_LICENSE_KEY, license_key)
                    set_registry_value(REGISTRY_LICENSE_TYPE, license_type or 'monthly')
                    set_registry_value(REGISTRY_LICENSE_VALIDATED, datetime.utcnow().isoformat())
                    
                    logger.info(f"License validated successfully with Gumroad")
                    return {
                        'valid': True,
                        'license_type': license_type or 'monthly',
                        'customer_email': purchase.get('email'),
                        'customer_name': purchase.get('full_name'),
                        'product_name': purchase.get('product_name'),
                        'sale_timestamp': purchase.get('sale_timestamp')
                    }
                else:
                    return {
                        'valid': False,
                        'error': data.get('message', 'Invalid license key')
                    }
            else:
                logger.error(f"Gumroad API error: {response.status_code}")
                # If we can't reach Gumroad but have a cached valid key, allow grace period
                if cached_key == license_key:
                    logger.warning(f"Gumroad unreachable, using cached validation")
                    return {
                        'valid': True,
                        'license_type': get_registry_value(REGISTRY_LICENSE_TYPE) or license_type,
                        'cached': True,
                        'warning': 'Could not validate with server. Using cached validation.'
                    }
                return {
                    'valid': False,
                    'error': 'Could not validate license. Please check your internet connection.'
                }
                
        except Exception as e:
            logger.error(f"License validation exception: {e}")
            # Offline fallback
            if cached_key == license_key:
                logger.warning(f"Validation failed, using cached result")
                return {
                    'valid': True,
                    'license_type': get_registry_value(REGISTRY_LICENSE_TYPE) or license_type,
                    'cached': True,
                    'warning': f'Validation error: {str(e)}. Using cached validation.'
                }
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}'
            }
    
    # If not test mode and not test key, reject
    return {
        'valid': False,
        'error': 'Invalid license key'
    }


def check_access(user) -> Dict:
    """
    Check if user has access (either trial active or valid license).
    
    Args:
        user: User model instance
        
    Returns:
        Dict with access status
    """
    # If user has active license, grant access
    if user.license_active and user.license_key:
        return {
            'has_access': True,
            'reason': 'active_license',
            'license_type': user.license_type,
            'message': f'Licensed ({user.license_type})'
        }
    
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
        'message': 'Trial expired. Please purchase a license to continue.',
        'purchase_url': 'https://gumroad.com/your-product-link'  # Update this
    }
