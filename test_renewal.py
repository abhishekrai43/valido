"""
Test License Renewal Flow
Tests that renewals update the expiration date correctly
"""
import os
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_renewal():
    print("\n" + "="*70)
    print("TESTING LICENSE RENEWAL FLOW")
    print("="*70)
    
    # Connect to Supabase
    conn = psycopg2.connect(
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        host=os.environ.get('DB_HOST'),
        port=os.environ.get('DB_PORT'),
        dbname=os.environ.get('DB_NAME')
    )
    cursor = conn.cursor()
    
    license_key = "RENEWAL-TEST-2025"
    email = "renewal@test.com"
    
    # STEP 1: Create initial monthly license (30 days)
    print("\n📅 STEP 1: Creating initial monthly license...")
    initial_expires = datetime.utcnow() + timedelta(days=30)
    
    cursor.execute("""
        INSERT INTO licenses (
            purchase_email, 
            license_key, 
            license_type, 
            is_active, 
            max_devices, 
            device_ids,
            expires_at,
            created_at,
            gumroad_sale_id
        ) VALUES (%s, %s, %s, %s, %s, ARRAY[]::text[], %s, NOW(), %s)
        ON CONFLICT (license_key) 
        DO UPDATE SET 
            purchase_email = EXCLUDED.purchase_email,
            is_active = EXCLUDED.is_active,
            expires_at = EXCLUDED.expires_at,
            gumroad_sale_id = EXCLUDED.gumroad_sale_id
    """, (email, license_key, 'monthly', True, 1, initial_expires, 'initial-sale-123'))
    
    conn.commit()
    
    # Verify initial state
    cursor.execute("SELECT expires_at FROM licenses WHERE license_key = %s", (license_key,))
    result = cursor.fetchone()
    print(f"✅ Initial license created")
    print(f"   License Key: {license_key}")
    print(f"   Initial Expires At: {result[0]}")
    
    # STEP 2: Simulate renewal (Gumroad webhook with same license_key)
    print("\n🔄 STEP 2: Simulating subscription renewal (30 days later)...")
    renewed_expires = datetime.utcnow() + timedelta(days=60)  # Extended another 30 days
    
    cursor.execute("""
        INSERT INTO licenses (
            purchase_email, 
            license_key, 
            license_type, 
            is_active, 
            max_devices, 
            device_ids,
            expires_at,
            created_at,
            gumroad_sale_id
        ) VALUES (%s, %s, %s, %s, %s, ARRAY[]::text[], %s, NOW(), %s)
        ON CONFLICT (license_key) 
        DO UPDATE SET 
            purchase_email = EXCLUDED.purchase_email,
            is_active = EXCLUDED.is_active,
            expires_at = EXCLUDED.expires_at,
            gumroad_sale_id = EXCLUDED.gumroad_sale_id
    """, (email, license_key, 'monthly', True, 1, renewed_expires, 'renewal-sale-456'))
    
    conn.commit()
    
    # Verify renewal state
    cursor.execute("SELECT expires_at FROM licenses WHERE license_key = %s", (license_key,))
    result = cursor.fetchone()
    print(f"✅ License renewed successfully")
    print(f"   New Expires At: {result[0]}")
    
    # STEP 3: Validate that expiration was extended
    print("\n✅ STEP 3: Verifying expiration was extended...")
    if result[0] > initial_expires:
        print(f"✅ SUCCESS! Expiration extended from {initial_expires} to {result[0]}")
        print(f"   Extension: ~{(result[0] - initial_expires).days} days")
    else:
        print(f"❌ FAILED! Expiration was NOT extended")
        print(f"   Initial: {initial_expires}")
        print(f"   Current: {result[0]}")
    
    # STEP 4: Test validation with renewed license
    print("\n🔍 STEP 4: Testing validation with renewed license...")
    from backend.app.utils.cloud_license_manager import CloudLicenseManager
    
    manager = CloudLicenseManager()
    validation = manager.validate_license(license_key, "TEST-DEVICE-123")
    
    print(f"Validation Result:")
    print(f"  Valid: {validation.get('valid')}")
    print(f"  Message: {validation.get('message', 'N/A')}")
    
    if validation.get('valid'):
        print("✅ RENEWAL VALIDATION PASSED - Renewed license is valid!")
    else:
        print("❌ RENEWAL VALIDATION FAILED")
    
    # Cleanup
    cursor.execute("DELETE FROM licenses WHERE license_key = %s", (license_key,))
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n" + "="*70)
    print("RENEWAL TEST COMPLETE")
    print("="*70)

if __name__ == "__main__":
    test_renewal()
