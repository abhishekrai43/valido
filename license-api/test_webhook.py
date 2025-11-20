"""
Test Gumroad webhook manually
"""
import requests

# Your deployed webhook URL
WEBHOOK_URL = "https://license-47cn7dnzb-abhishekrai43s-projects.vercel.app/api/webhook/gumroad"

# Simulate Gumroad webhook data
test_data = {
    'email': 'testcustomer@example.com',
    'product_name': 'Valido - Monthly License',  # Change to "Annual" to test annual
    'sale_id': 'TEST-SALE-12345',
    'license_key': 'TEST-LICENSE-ABCD1234',
    'seller_id': 'your-seller-id',
    'product_id': 'your-product-id',
    'price': '14.99',
    'currency': 'USD'
}

print("Sending test webhook to:", WEBHOOK_URL)
print("Test data:", test_data)
print("-" * 50)

try:
    response = requests.post(WEBHOOK_URL, data=test_data, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        print("\n✅ SUCCESS! Check your Supabase database for the new license record.")
        print(f"Email: {test_data['email']}")
        print(f"License Key: {test_data['license_key']}")
        
        # Detect license type
        license_type = 'annual' if 'annual' in test_data['product_name'].lower() else 'monthly'
        print(f"License Type: {license_type}")
    else:
        print("\n❌ FAILED!")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
