"""
Script to initialize Supabase cloud database tables.
Run this once to create the tables in your Supabase database.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.cloud_db import create_cloud_tables, test_cloud_connection

def main():
    print("🔧 Testing Supabase connection...")
    
    if not test_cloud_connection():
        print("❌ Failed to connect to Supabase. Check your .env file.")
        print("   Make sure SUPABASE_URL is set correctly.")
        return
    
    print("✅ Supabase connection successful!")
    print("\n🔧 Creating cloud database tables...")
    
    try:
        create_cloud_tables()
        print("✅ Cloud tables created successfully!")
        print("\nTables created:")
        print("  - licenses (license key tracking, device limits)")
        print("  - app_versions (version checking, update notifications)")
        print("  - license_usage (usage analytics)")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
