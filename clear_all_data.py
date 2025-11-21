"""
Clear all license and trial data for fresh start
"""
import winreg
import os

REGISTRY_PATH = r"Software\Valido\License"

def clear_registry():
    """Delete all Valido registry keys"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_ALL_ACCESS)
        winreg.DeleteKey(key, "")
        print("✓ Registry cleared")
    except FileNotFoundError:
        print("✓ Registry already clean")
    except Exception as e:
        print(f"✗ Registry error: {e}")

def clear_database():
    """Delete the local database"""
    db_path = "backend/data/valido.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        print("✓ Database deleted")
    else:
        print("✓ Database already clean")

if __name__ == "__main__":
    print("Clearing all license and trial data...")
    print("=" * 40)
    clear_registry()
    clear_database()
    print("\n✓ All data cleared - fresh start ready!")
