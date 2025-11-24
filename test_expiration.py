"""Test license expiration enforcement"""
import psycopg2
from datetime import datetime, timedelta
import os

# Connect to database
conn = psycopg2.connect(
    user=os.environ.get('DB_USER', 'postgres.touhjzfmgznpgljocrvg'),
    password=os.environ.get('DB_PASSWORD', 'Dwayne43$#@!'),
    host=os.environ.get('DB_HOST', 'aws-1-eu-west-2.pooler.supabase.com'),
    port=os.environ.get('DB_PORT', '6543'),
    dbname=os.environ.get('DB_NAME', 'postgres')
)

cursor = conn.cursor()

# Create an EXPIRED test license
expired_key = "EXPIRED-TEST-LICENSE-2025"
expired_date = datetime.utcnow() - timedelta(days=1)  # Expired yesterday

print("Creating expired test license...")
print(f"License Key: {expired_key}")
print(f"Expires At: {expired_date}")
print()

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
        expires_at = EXCLUDED.expires_at,
        is_active = EXCLUDED.is_active
""", ('expired@test.com', expired_key, 'monthly', True, 1, expired_date, 'TEST-EXPIRED'))

conn.commit()
cursor.close()
conn.close()

print("✅ Expired license created in database")
print()
print("Now testing validation...")

# Test with the desktop app
from backend.app.utils.cloud_license_manager import CloudLicenseManager

result = CloudLicenseManager.validate_license(expired_key)

print("Validation Result:")
print(f"  Valid: {result.get('valid')}")
print(f"  Message: {result.get('message')}")
print()

if result.get('valid') == False and 'expired' in result.get('message', '').lower():
    print("✅ EXPIRATION IS ENFORCED - Expired license correctly rejected!")
else:
    print("❌ ERROR - Expired license was NOT rejected!")
    print(f"   Full result: {result}")
