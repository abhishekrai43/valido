"""
Usage tracking for free tier limits.
Tracks PDF processing count in multiple locations to prevent easy bypass.
"""
import winreg
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger('usage_tracker')

# Free tier limit
FREE_TIER_LIMIT = 300  # PDFs per month

# Registry key location
REGISTRY_PATH = r"Software\Valido\Usage"
REGISTRY_KEY_COUNT = "MonthlyCount"
REGISTRY_KEY_MONTH = "CurrentMonth"


def get_current_month():
    """Get current month as YYYY-MM string."""
    return datetime.now().strftime("%Y-%m")


def get_registry_count():
    """Get PDF count from Windows Registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_READ)
        count, _ = winreg.QueryValueEx(key, REGISTRY_KEY_COUNT)
        month, _ = winreg.QueryValueEx(key, REGISTRY_KEY_MONTH)
        winreg.CloseKey(key)
        
        # Reset if month changed
        if month != get_current_month():
            set_registry_count(0)
            return 0
        
        return int(count)
    except FileNotFoundError:
        # Registry key doesn't exist yet
        return 0
    except Exception as e:
        logger.warning(f"Failed to read registry count: {e}")
        return 0


def set_registry_count(count):
    """Set PDF count in Windows Registry."""
    try:
        # Create or open registry key
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH)
        winreg.SetValueEx(key, REGISTRY_KEY_COUNT, 0, winreg.REG_DWORD, count)
        winreg.SetValueEx(key, REGISTRY_KEY_MONTH, 0, winreg.REG_SZ, get_current_month())
        winreg.CloseKey(key)
    except Exception as e:
        logger.warning(f"Failed to write registry count: {e}")


def get_db_count(db):
    """Get PDF count from database for current month."""
    from app.models import UsageRecord
    from sqlalchemy import func, extract
    
    current_date = datetime.now()
    
    try:
        # Sum all processed PDFs for current month
        result = db.query(func.sum(UsageRecord.pdf_count)).filter(
            extract('year', UsageRecord.processed_at) == current_date.year,
            extract('month', UsageRecord.processed_at) == current_date.month
        ).scalar()
        
        return result or 0
    except Exception as e:
        logger.warning(f"Failed to read database count: {e}")
        return 0


def record_usage(db, pdf_count: int):
    """
    Record PDF processing usage in both database and registry.
    
    Args:
        db: SQLAlchemy database session
        pdf_count: Number of PDFs processed
    """
    from app.models import UsageRecord
    
    # Record in database
    try:
        usage = UsageRecord(
            pdf_count=pdf_count,
            processed_at=datetime.now()
        )
        db.add(usage)
        db.commit()
        logger.info(f"Recorded usage: {pdf_count} PDFs")
    except Exception as e:
        logger.error(f"Failed to record usage in database: {e}")
        db.rollback()
    
    # Update registry counter
    try:
        current_registry = get_registry_count()
        set_registry_count(current_registry + pdf_count)
        logger.debug(f"Updated registry count: {current_registry + pdf_count}")
    except Exception as e:
        logger.error(f"Failed to update registry: {e}")


def check_usage_limit(db):
    """
    Check if user has exceeded free tier limit.
    
    Returns:
        dict with:
            - exceeded: bool - Whether limit is exceeded
            - count: int - Current usage count
            - limit: int - Free tier limit
            - remaining: int - PDFs remaining (0 if exceeded)
            - warning: bool - True if within 20 PDFs of limit
    """
    db_count = get_db_count(db)
    registry_count = get_registry_count()
    
    # Use the maximum of both counts (in case one was tampered with)
    current_count = max(db_count, registry_count)
    
    # Log mismatch as potential tampering
    if abs(db_count - registry_count) > 5:
        logger.warning(f"Usage count mismatch - DB: {db_count}, Registry: {registry_count}")
    
    remaining = max(0, FREE_TIER_LIMIT - current_count)
    exceeded = current_count >= FREE_TIER_LIMIT
    warning = remaining <= 20 and remaining > 0
    
    return {
        'exceeded': exceeded,
        'count': current_count,
        'limit': FREE_TIER_LIMIT,
        'remaining': remaining,
        'warning': warning
    }


def get_usage_display(db):
    """
    Get user-friendly usage display string.
    
    Returns:
        str: e.g. "150 / 300 PDFs this month (150 remaining)"
    """
    status = check_usage_limit(db)
    
    if status['exceeded']:
        return f"{status['count']} / {status['limit']} PDFs this month (Limit reached)"
    else:
        return f"{status['count']} / {status['limit']} PDFs this month ({status['remaining']} remaining)"
