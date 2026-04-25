from typing import List, Optional
from datetime import datetime
import json
from urllib import error as urllib_error
from urllib import request as urllib_request

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from app.db import get_session
from app.models import User
from app.utils.logger import get_logger
from app.utils.trial_manager import (
    calculate_trial_status, 
    start_trial, 
    validate_license_key,
    check_access
)

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    requests = None

logger = get_logger("UserRoutes")

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class UserCreate(BaseModel):
    username: str


class UserRead(BaseModel):
    id: int
    username: str
    trial_start_date: Optional[datetime]
    trial_expired: bool
    license_key: Optional[str]
    license_active: bool
    license_type: Optional[str]


@router.get("/", response_model=List[UserRead])
def list_users():
    logger.info("Listing users")
    with get_session() as session:
        stmt = select(User)
        results = session.exec(stmt).all()
        logger.info(f"Found {len(results)} users")
        return results


@router.post("/", response_model=UserRead)
def create_user(payload: UserCreate):
    logger.info(f"Creating user: {payload.username}")
    if not payload.username or len(payload.username.strip()) == 0:
        logger.warning("Empty username")
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    with get_session() as session:
        existing = session.exec(select(User).where(User.username == payload.username)).first()
        if existing:
            logger.warning(f"Duplicate username: {payload.username}")
            raise HTTPException(status_code=409, detail="user already exists")
        u = User(username=payload.username)
        session.add(u)
        session.commit()
        session.refresh(u)
        logger.info(f"User created: {u.id}")
        return u


# Trial and License Management Endpoints (MUST be before /{user_id} route)

@router.get("/trial-status")
def get_trial_status():
    """Get trial status for the default user."""
    with get_session() as session:
        user = session.exec(select(User).where(User.username == "default")).first()
        if not user:
            # Create default user with trial
            user = User(username="default")
            session.add(user)
            session.commit()
            session.refresh(user)
        
        trial_status = calculate_trial_status(user.trial_start_date)
        access_status = check_access(user)
        
        return {
            'trial': trial_status,
            'access': access_status,
            'license_active': user.license_active,
            'license_type': user.license_type
        }


@router.post("/start-trial")
def start_user_trial():
    """Start the trial period for the default user."""
    logger.info("Starting trial")
    with get_session() as session:
        user = session.exec(select(User).where(User.username == "default")).first()
        if not user:
            user = User(username="default")
            session.add(user)
        
        if user.trial_start_date:
            logger.warning("Trial already started")
            raise HTTPException(status_code=400, detail="Trial already started")
        
        user.trial_start_date = start_trial()
        session.commit()
        session.refresh(user)
        
        logger.info(f"Trial started for user at {user.trial_start_date}")
        return {
            'status': 'success',
            'trial_start_date': user.trial_start_date.isoformat(),
            'trial': calculate_trial_status(user.trial_start_date)
        }


class LicenseActivation(BaseModel):
    """License key activation"""
    license_key: str


class EmailLicenseActivation(BaseModel):
    """Email-based license activation"""
    purchase_email: str
    license_type: str = "monthly"


def _post_json(url: str, payload: dict, timeout: int = 10) -> tuple[int, dict]:
    if requests is not None:
        response = requests.post(url, json=payload, timeout=timeout)
        data = response.json() if response.text else {}
        return response.status_code, data

    req = urllib_request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8") or "{}"
            return response.getcode(), json.loads(body)
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8") or "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}
        return exc.code, data


@router.post("/activate-license-email")
def activate_license_email(payload: EmailLicenseActivation):
    """Activate license using email (looks up license from Vercel API)."""
    from app.utils.cloud_license_manager import LICENSE_API_URL
    
    logger.info(f"Activating license via email: {payload.purchase_email}")
    
    try:
        # Call Vercel API to get license key
        status_code, data = _post_json(
            f"{LICENSE_API_URL}/api/activate",
            {
                "email": payload.purchase_email,
                "license_type": payload.license_type
            },
            timeout=10,
        )
        
        if status_code != 200:
            error_msg = data.get('message', 'License lookup failed')

            logger.warning(f"License lookup failed: {error_msg}")

            # If the license server is down (5xx), surface as 503 so the UI can show a retry message.
            if 500 <= status_code <= 599:
                raise HTTPException(
                    status_code=503,
                    detail="License server error (temporary). Please try again in a minute."
                )

            raise HTTPException(status_code=status_code, detail=error_msg)
        
        license_key = data.get('license_key')
        
        if not license_key:
            raise HTTPException(status_code=500, detail="No license key returned")
        
        # Now validate and activate the license key
        validation = validate_license_key(license_key)
        
        if not validation['valid']:
            logger.warning(f"License validation failed: {validation.get('error')}")
            if validation.get('transient'):
                raise HTTPException(
                    status_code=503,
                    detail=validation.get('error', 'License server temporarily unavailable. Please try again shortly.')
                )
            raise HTTPException(
                status_code=400,
                detail=validation.get('error', 'Could not validate license')
            )
        
        # Activate license for user
        with get_session() as session:
            user = session.exec(select(User).where(User.username == "default")).first()
            if not user:
                user = User(username="default")
                session.add(user)
            
            user.license_key = license_key
            user.license_active = True
            user.license_type = validation.get('license_type', 'monthly')
            user.license_activated_at = datetime.utcnow()
            user.trial_expired = False
            
            session.commit()
            session.refresh(user)
            
            logger.info(f"License activated successfully via email: {user.license_type}")
            return {
                'status': 'success',
                'message': 'License activated successfully!',
                'license_type': user.license_type,
                'activated_at': user.license_activated_at.isoformat()
            }
    
    except Exception as e:
        logger.error(f"Failed to contact license API: {e}")
        raise HTTPException(
            status_code=503,
            detail="Could not contact license server. Please check your internet connection."
        )


@router.post("/activate-license")
def activate_license(payload: LicenseActivation):
    """Activate license using license key (cloud-validated)."""
    logger.info(f"Activating license key: {payload.license_key[:8]}...")
    
    # Validate with cloud API
    validation = validate_license_key(payload.license_key)
    
    if not validation['valid']:
        logger.warning(f"License validation failed: {validation.get('error')}")
        if validation.get('transient'):
            raise HTTPException(
                status_code=503,
                detail=validation.get('error', 'License server temporarily unavailable. Please try again shortly.')
            )
        raise HTTPException(
            status_code=400,
            detail=validation.get('error', 'Could not validate license')
        )
    
    # Activate license for user
    with get_session() as session:
        user = session.exec(select(User).where(User.username == "default")).first()
        if not user:
            user = User(username="default")
            session.add(user)
        
        user.license_key = payload.license_key
        user.license_active = True
        user.license_type = validation.get('license_type', 'monthly')
        user.license_activated_at = datetime.utcnow()
        user.trial_expired = False
        
        session.commit()
        session.refresh(user)
        
        logger.info(f"License activated successfully: {user.license_type}")
        return {
            'status': 'success',
            'message': validation.get('message', 'License activated!'),
            'license_type': user.license_type,
            'activated_at': user.license_activated_at.isoformat(),
            'offline': validation.get('offline', False),
            'cached': validation.get('cached', False)
        }


@router.post("/deactivate-license")
def deactivate_license():
    """Deactivate license (for testing or cancellation)."""
    logger.info("Deactivating license")
    with get_session() as session:
        user = session.exec(select(User).where(User.username == "default")).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.license_key = None
        user.license_active = False
        user.license_type = None
        
        session.commit()
        
        logger.info("License deactivated")
        return {
            'status': 'success',
            'message': 'License deactivated'
        }


# User ID route MUST be last (catch-all pattern)
@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int):
    logger.info(f"Getting user: {user_id}")
    if user_id <= 0:
        logger.warning(f"Invalid user ID: {user_id}")
        raise HTTPException(status_code=400, detail="Invalid user ID")
    with get_session() as session:
        u = session.get(User, user_id)
        if not u:
            logger.warning(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="user not found")
        return u
