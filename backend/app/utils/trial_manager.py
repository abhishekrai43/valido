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
TEST_MODE = False  # Set to False for production
TRIAL_DAYS = 1 if TEST_MODE else 14  # 1 day for testing, 14 for production

# Registry paths
REGISTRY_PATH = r"Software\Valido\License"
REGISTRY_TRIAL_START = "TrialStartDate"
REGISTRY_HARDWARE_ID = "HardwareID"
REGISTRY_NETWORK_ID = "NetworkID"
REGISTRY_PURCHASE_EMAIL = "PurchaseEmail"  # Store validated email
REGISTRY_LICENSE_TYPE = "LicenseType"
REGISTRY_LICENSE_VALIDATED = "LastValidated"

# Gumroad configuration
GUMROAD_ACCESS_TOKEN = "-exmGh2an_SU8wVqQhBW5f9-cat6iG4W2Q-ywWRPJ5E"
GUMROAD_MONTHLY_PRODUCT_PERMALINK = "bdspjn"
GUMROAD_ANNUAL_PRODUCT_PERMALINK = "eyuiy"
GUMROAD_API_URL = "https://api.gumroad.com/v2/sales"
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


def get_network_id() -> str:
    """
    Generate a network identifier to prevent trial abuse across multiple devices on same LAN.
    Uses combination of gateway MAC, network prefix, and domain name to identify the network.
    """
    try:
        import socket
        import subprocess
        
        # Get local IP address
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Get network prefix (first 3 octets)
        network_prefix = '.'.join(local_ip.split('.')[:3])
        
        # Try to get default gateway MAC address (router identifier)
        gateway_mac = "unknown"
        try:
            # Run arp -a to get gateway MAC
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Look for gateway in ARP table
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Gateway' in line or network_prefix in line:
                        parts = line.split()
                        for part in parts:
                            # MAC address pattern: xx-xx-xx-xx-xx-xx
                            if len(part.replace('-', '')) == 12 and '-' in part:
                                gateway_mac = part
                                break
                        if gateway_mac != "unknown":
                            break
        except:
            pass
        
        # Get Windows domain/workgroup name
        domain = "unknown"
        try:
            result = subprocess.run(['wmic', 'computersystem', 'get', 'domain'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    domain = lines[1].strip()
        except:
            pass
        
        # Combine all identifiers
        network_info = f"{network_prefix}|{gateway_mac}|{domain}"
        network_id = hashlib.sha256(network_info.encode()).hexdigest()[:32]
        
        logger.info(f"Network ID generated: {network_id} (prefix: {network_prefix}, gateway: {gateway_mac}, domain: {domain})")
        return network_id
    except Exception as e:
        logger.error(f"Failed to generate network ID: {e}")
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




def validate_license_email(purchase_email: str, license_type: str = 'monthly') -> Dict:
    """
    Validate a Gumroad purchase using customer's email (NEW METHOD).
    NOW WITH DEVICE TRACKING - prevents license sharing across devices/networks.
    
    Args:
        purchase_email: The email address used to purchase on Gumroad
        license_type: 'monthly' or 'annual'
        
    Returns:
        Dict with validation result
    """
    import requests
    from app.db import get_session
    from app.models import DeviceActivation
    from sqlmodel import select
    
    if not purchase_email or not purchase_email.strip():
        return {'valid': False, 'error': 'Email address is required'}
    
    purchase_email = purchase_email.strip().lower()
    
    # Get device identifiers
    hardware_id = get_hardware_id()
    network_id = get_network_id()
    computer_name = platform.node()
    
    # Test mode - accept test email
    if TEST_MODE and purchase_email == "test@valido.com":
        logger.info("Test mode: Accepting test email")
        set_registry_value(REGISTRY_PURCHASE_EMAIL, purchase_email)
        set_registry_value(REGISTRY_LICENSE_TYPE, license_type)
        set_registry_value(REGISTRY_HARDWARE_ID, hardware_id)
        set_registry_value(REGISTRY_NETWORK_ID, network_id)
        set_registry_value(REGISTRY_LICENSE_VALIDATED, datetime.utcnow().isoformat())
        return {
            'valid': True,
            'license_type': license_type,
            'customer_email': purchase_email,
            'test_mode': True,
            'message': 'Test license activated'
        }
    
    # Check if this device is already activated
    with get_session() as session:
        existing_activation = session.exec(
            select(DeviceActivation).where(
                DeviceActivation.purchase_email == purchase_email,
                DeviceActivation.hardware_id == hardware_id,
                DeviceActivation.is_active == True
            )
        ).first()
        
        if existing_activation:
            # This device is already activated - allow revalidation
            logger.info(f"Device already activated for {purchase_email}")
            existing_activation.last_validated = datetime.utcnow()
            session.add(existing_activation)
            session.commit()
            
            # Update registry
            set_registry_value(REGISTRY_PURCHASE_EMAIL, purchase_email)
            set_registry_value(REGISTRY_LICENSE_TYPE, license_type)
            set_registry_value(REGISTRY_HARDWARE_ID, hardware_id)
            set_registry_value(REGISTRY_NETWORK_ID, network_id)
            set_registry_value(REGISTRY_LICENSE_VALIDATED, datetime.utcnow().isoformat())
            
            return {
                'valid': True,
                'license_type': license_type,
                'customer_email': purchase_email,
                'cached': True,
                'message': 'License revalidated successfully'
            }
        
        # Check if another device/network is already activated with this email
        other_device_activation = session.exec(
            select(DeviceActivation).where(
                DeviceActivation.purchase_email == purchase_email,
                DeviceActivation.is_active == True
            )
        ).first()
        
        if other_device_activation:
            # Another device is already using this license!
            logger.warning(f"License {purchase_email} already activated on another device")
            
            # Check if it's on the same network
            same_network = other_device_activation.network_id == network_id
            other_computer = other_device_activation.computer_name or "another computer"
            
            if same_network:
                error_msg = f'⚠️ License already activated on "{other_computer}" (same network). Each license works on only ONE computer. To use on this computer, please deactivate the other installation first.'
            else:
                error_msg = f'⚠️ License already activated on "{other_computer}" at a different location. Each license works on only ONE computer. Please deactivate the other device or purchase an additional license.'
            
            return {
                'valid': False,
                'error': error_msg,
                'device_limit_reached': True,
                'same_network': same_network,
                'other_computer': other_computer
            }
    
    # New activation - validate with Gumroad
    try:
        product_permalink = GUMROAD_MONTHLY_PRODUCT_PERMALINK if license_type == 'monthly' else GUMROAD_ANNUAL_PRODUCT_PERMALINK
        
        logger.info(f"Validating new activation with Gumroad: {purchase_email}, type: {license_type}")
        
        response = requests.get(
            GUMROAD_API_URL,
            params={
                'access_token': GUMROAD_ACCESS_TOKEN,
                'email': purchase_email
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if not data.get('success'):
                return {'valid': False, 'error': 'Could not verify with Gumroad'}
            
            sales = data.get('sales', [])
            
            if not sales:
                return {'valid': False, 'error': 'No purchases found for this email'}
            
            # Find valid purchase
            for sale in sales:
                if sale.get('product_permalink') != product_permalink:
                    continue
                
                if sale.get('refunded') or sale.get('chargedback'):
                    continue
                
                if sale.get('subscription_id'):
                    if sale.get('cancelled') or sale.get('ended'):
                        continue
                
                # Valid purchase found! Register this device
                with get_session() as session:
                    new_activation = DeviceActivation(
                        purchase_email=purchase_email,
                        hardware_id=hardware_id,
                        network_id=network_id,
                        license_type=license_type,
                        computer_name=computer_name,
                        network_info=f"Network: {network_id[:8]}...",
                        is_active=True
                    )
                    session.add(new_activation)
                    session.commit()
                
                # Update registry
                set_registry_value(REGISTRY_PURCHASE_EMAIL, purchase_email)
                set_registry_value(REGISTRY_LICENSE_TYPE, license_type)
                set_registry_value(REGISTRY_HARDWARE_ID, hardware_id)
                set_registry_value(REGISTRY_NETWORK_ID, network_id)
                set_registry_value(REGISTRY_LICENSE_VALIDATED, datetime.utcnow().isoformat())
                
                logger.info(f"New device activated successfully for {purchase_email}")
                
                return {
                    'valid': True,
                    'license_type': license_type,
                    'customer_email': sale.get('email'),
                    'product_name': sale.get('product_name'),
                    'message': 'License activated successfully!'
                }
            
            return {'valid': False, 'error': f'No active {license_type} license found'}
        
        else:
            return {'valid': False, 'error': 'Could not connect to Gumroad server. Please check your internet connection.'}
    
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return {'valid': False, 'error': f'Validation failed: {str(e)}'}


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
        'purchase_url': 'https://rai89.gumroad.com/l/bdspjn'
    }
