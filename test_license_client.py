"""Test license validation from desktop app"""
from backend.app.utils.cloud_license_manager import CloudLicenseManager, LICENSE_API_URL
import requests

print("Testing license validation with stable URL...")
print(f"API URL: {LICENSE_API_URL}")
print()

# Test direct API call first
device_id = CloudLicenseManager.get_device_id()
print(f"Device ID: {device_id}")
print()

print("Direct API test with requests...")
try:
    response = requests.get(
        f"{LICENSE_API_URL}/api/validate",
        params={
            "license_key": "NEW-TEST-KEY-2025",
            "device_id": device_id
        },
        timeout=10
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")

print()

# Test with the license we just created
result = CloudLicenseManager.validate_license('NEW-TEST-KEY-2025')

print("Validation Result:")
print(f"  Valid: {result.get('valid')}")
print(f"  License Type: {result.get('license_type')}")
print(f"  Message: {result.get('message')}")
print()

# Test with invalid license
print("Testing with invalid license key...")
result2 = CloudLicenseManager.validate_license('INVALID-KEY-999')

print("Validation Result:")
print(f"  Valid: {result2.get('valid')}")
print(f"  Message: {result2.get('message')}")
