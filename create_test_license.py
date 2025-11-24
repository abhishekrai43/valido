"""
Quick test: Create a license key and test activation
"""
import os
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def create_test_license():
    print("\n" + "="*70)
    print("CREATING TEST LICENSE FOR ACTIVATION")
    print("="*70)
    
    # Connect to Supabase
    conn = psycopg2.connect(
        user=os.environ.get('DB_USER', 'postgres.touhjzfmgznpgljocrvg'),
        password=os.environ.get('DB_PASSWORD', 'Dwayne43$#@!'),
        host=os.environ.get('DB_HOST', 'aws-1-eu-west-2.pooler.supabase.com'),
        port=os.environ.get('DB_PORT', '6543'),
        dbname=os.environ.get('DB_NAME', 'postgres')
    )
    cursor = conn.cursor()
    
    # Create a test license key (similar format to Gumroad)
    license_key = "TEST-ACTIVATION-2025"
    email = "test@activation.com"
    expires_at = datetime.utcnow() + timedelta(days=30)
    
    # Insert license
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
            device_ids = ARRAY[]::text[]
    """, (email, license_key, 'monthly', True, 1, expires_at, 'test-sale-123'))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n✅ Test license created successfully!")
    print(f"\n{'='*70}")
    print("COPY THIS LICENSE KEY:")
    print(f"{'='*70}")
    print(f"\n    {license_key}\n")
    print(f"{'='*70}")
    print("\nNOW TEST ACTIVATION:")
    print("1. Open Valido in your browser (http://localhost:5000)")
    print("2. Click 'Activate License' button")
    print(f"3. Enter the license key: {license_key}")
    print("4. Click 'Activate'")
    print("5. You should see: 'License activated successfully!'")
    print(f"\n{'='*70}")
    print("\nLicense Details:")
    print(f"  Email: {email}")
    print(f"  Type: Monthly")
    print(f"  Expires: {expires_at.strftime('%Y-%m-%d')}")
    print(f"  Max Devices: 1")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    create_test_license()
