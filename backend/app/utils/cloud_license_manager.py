"""
Cloud License Manager - Validates licenses against Vercel API
Keeps Supabase credentials secure (never in desktop app)
"""
import hashlib
import json
import platform
import uuid
import os
from typing import Optional, Dict, Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    requests = None

# Your secure license API endpoint - stable production URL
LICENSE_API_URL = "https://license-api-three-delta.vercel.app"


def _http_request(method: str, url: str, *, json_body: Optional[Dict[str, Any]] = None,
                  params: Optional[Dict[str, Any]] = None, timeout: int = 10) -> Dict[str, Any]:
    """Small fallback HTTP client used when requests is unavailable."""
    if params:
        url = f"{url}?{urllib_parse.urlencode(params)}"

    data = None
    headers = {"Accept": "application/json"}
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib_request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib_request.urlopen(req, timeout=timeout) as response:
            payload = response.read().decode("utf-8") or "{}"
            return {
                "status_code": response.getcode(),
                "json": json.loads(payload),
            }
    except urllib_error.HTTPError as exc:
        payload = exc.read().decode("utf-8") or "{}"
        try:
            parsed = json.loads(payload)
        except Exception:
            parsed = {}
        return {
            "status_code": exc.code,
            "json": parsed,
        }


def _post_json(url: str, payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    if requests is not None:
        response = requests.post(url, json=payload, timeout=timeout)
        return {"status_code": response.status_code, "json": response.json() if response.text else {}}
    return _http_request("POST", url, json_body=payload, timeout=timeout)


def _get_json(url: str, params: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    if requests is not None:
        response = requests.get(url, params=params, timeout=timeout)
        return {"status_code": response.status_code, "json": response.json() if response.text else {}}
    return _http_request("GET", url, params=params, timeout=timeout)


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
    def ping_usage(app_version: str, action: str = "app_open", details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send anonymous usage ping to track active users.
        
        Args:
            app_version: Current app version
            action: What action triggered the ping (app_open, validation, etc.)
            
        Returns:
            True if ping succeeded, False otherwise
        """
        device_id = CloudLicenseManager.get_device_id()
        
        try:
            payload: Dict[str, Any] = {
                "device_id": device_id,
                "app_version": app_version,
                "action": action,
                "platform": platform.system(),
            }
            if details is not None:
                payload["details"] = details

            response = _post_json(
                f"{LICENSE_API_URL}/api/ping",
                payload,
                timeout=5,  # Short timeout, non-blocking
            )
            return response["status_code"] == 200
        except:
            # Silently fail - usage tracking should never break the app
            return False
    
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
            response = _get_json(
                f"{LICENSE_API_URL}/api/validate",
                {
                    "license_key": license_key,
                    "device_id": device_id
                },
                timeout=timeout,
            )
            
            status_code = response["status_code"]
            if status_code == 200:
                return response["json"]

            # Treat server-side failures differently from user/input failures.
            # The desktop app should not blame the user for a server outage.
            if 500 <= status_code <= 599:
                return {
                    "valid": False,
                    "transient": True,
                    "status_code": status_code,
                    "message": "License server error (temporary). Please try again in a minute."
                }

            return {
                "valid": False,
                "status_code": status_code,
                "message": f"API error: {status_code}"
            }
                
        except Exception as e:
            err_name = type(e).__name__
            if err_name == "Timeout":
                return {
                    "valid": False,
                    "message": "Connection timeout - please check your internet connection"
                }
            if err_name == "ConnectionError":
                return {
                    "valid": False,
                    "message": "Cannot connect to license server - check internet connection"
                }
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
            response = _get_json(
                f"{LICENSE_API_URL}/api/version",
                {},
                timeout=timeout,
            )
            
            if response["status_code"] == 200:
                data = response["json"]
                
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
