import os
import shutil
from datetime import datetime, timedelta
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _candidate_results_dirs():
    # Try a few likely locations for the `results` directory relative to cwd and this file
    cwd = os.getcwd()
    this_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(cwd, 'results'),
        os.path.join(cwd, '..', 'results'),
        os.path.join(cwd, '..', '..', 'results'),
        os.path.join(this_dir, '..', '..', '..', 'results'),
    ]
    # Normalize and dedupe
    seen = set()
    out = []
    for p in candidates:
        ab = os.path.abspath(p)
        if ab not in seen:
            seen.add(ab)
            out.append(ab)
    return out


def _remove_path(path: str):
    try:
        shutil.rmtree(path)
        return True
    except Exception:
        return False


def cleanup_old_results(days: int = 7) -> dict:
    """Delete result directories older than `days` days.

    This task is conservative: it only deletes directories directly under any
    discovered `results` directory whose last modification time is older than the cutoff.
    """
    logger.info(f"Starting cleanup of results older than {days} days")
    cutoff = datetime.utcnow() - timedelta(days=days)
    removed = []
    errors = []

    for results_root in _candidate_results_dirs():
        if not os.path.exists(results_root):
            continue
        try:
            for name in os.listdir(results_root):
                path = os.path.join(results_root, name)
                try:
                    mtime = datetime.utcfromtimestamp(os.path.getmtime(path))
                except Exception:
                    # If we can't stat, skip
                    continue

                if mtime < cutoff and os.path.isdir(path):
                    ok = _remove_path(path)
                    if ok:
                        removed.append(path)
                        logger.info(f"Removed old result directory: {path}")
                    else:
                        errors.append(path)
                        logger.warning(f"Failed to remove directory: {path}")
        except Exception as exc:
            errors.append(f"root-error:{results_root}:{exc}")
            logger.error(f"Error processing results root {results_root}: {exc}")

    result = {"removed": removed, "errors": errors, "cutoff": cutoff.isoformat()}
    logger.info(f"Cleanup completed: {len(removed)} removed, {len(errors)} errors")
    return result
