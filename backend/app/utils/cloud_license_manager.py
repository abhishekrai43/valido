"""
Cloud License Manager - Validates licenses against Vercel API
Keeps Supabase credentials secure (never in desktop app)
"""
import requests
import hashlib
import platform
import uuid
import os
from typing import Optional, Dict, Any

# Your secure license API endpoint
LICENSE_API_URL = "https://license-fjj9rrwx5-abhishekrai43s-projects.vercel.app"


class CloudLicenseManager:
    """Manages license validation via cloud API"""
    
    @staticmethod
    def get_device_id() -> str:
        """Generate unique device identifier"""
        # Combine multiple hardware identifiers for uniqueness
        mac = hex(uuid.getnode())
        hostname = platform.node()
        system = platform.system()
        
        # Create hash of combined identifiers
        device_string = f"{mac}-{hostname}-{system}"
        device_hash = hashlib.sha256(device_string.encode()).hexdigest()[:32]
        
        return device_hash
    
    @staticmethod
    def validate_license(license_key: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Validate license key against cloud API
        
        Args:
            license_key: User's license key
            timeout: Request timeout in seconds
            
        Returns:
            {
                "valid": bool,
                "license_type": str (if valid),
                "message": str
            }
        """
        device_id = CloudLicenseManager.get_device_id()
        
        try:
            response = requests.get(
                f"{LICENSE_API_URL}/api/validate",
                params={
                    "license_key": license_key,
                    "device_id": device_id
                },
                timeout=timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "valid": False,
                    "message": f"API error: {response.status_code}"
                }
                
        except requests.Timeout:
            return {
                "valid": False,
                "message": "Connection timeout - please check your internet connection"
            }
        except requests.ConnectionError:
            return {
                "valid": False,
                "message": "Cannot connect to license server - check internet connection"
            }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Validation error: {str(e)}"
            }
    
    @staticmethod
    def check_for_updates(current_version: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """
        Check if a newer version is available
        
        Args:
            current_version: Current app version (e.g. "1.0.0")
            timeout: Request timeout in seconds
            
        Returns:
            {
                "latest_version": str,
                "download_url": str,
                "changelog": str,
                "is_required": bool
            } or None if no update available
        """
        try:
            response = requests.get(
                f"{LICENSE_API_URL}/api/version",
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if update is available
                if data.get("latest_version") and data["latest_version"] != current_version:
                    return data
                
            return None
            
        except Exception as e:
            print(f"Update check failed: {e}")
            return None


# Example usage
if __name__ == "__main__":
    # Test device ID generation
    device_id = CloudLicenseManager.get_device_id()
    print(f"Device ID: {device_id}")
    
    # Test license validation (with fake key)
    result = CloudLicenseManager.validate_license("TEST-LICENSE-KEY")
    print(f"\nLicense validation: {result}")
    
    # Test update check
    update = CloudLicenseManager.check_for_updates("1.0.0")
    if update:
        print(f"\nUpdate available: {update}")
    else:
        print("\nNo updates available")
