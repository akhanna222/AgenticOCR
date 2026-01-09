"""
Authentication and authorization system
JWT tokens, password hashing, API key management
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import get_db_session, get_tenant_context, set_tenant_context
from models import APIKey, User

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

# Security scheme
security = HTTPBearer()


# ==========================================
# PASSWORD HASHING
# ==========================================

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


# ==========================================
# JWT TOKEN MANAGEMENT
# ==========================================

def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token

    Args:
        user_id: User ID
        tenant_id: Tenant ID
        role: User role (admin, user, api)
        expires_delta: Optional expiration time

    Returns:
        JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def create_refresh_token(user_id: str, tenant_id: str) -> str:
    """Create JWT refresh token"""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_token(token: str) -> dict:
    """
    Decode and validate JWT token

    Returns:
        Token payload dict

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


# ==========================================
# API KEY MANAGEMENT
# ==========================================

def generate_api_key() -> tuple[str, str, str]:
    """
    Generate new API key

    Returns:
        Tuple of (full_key, key_prefix, key_hash)
    """
    prefix = "sk_live_"
    secret = secrets.token_urlsafe(32)
    full_key = f"{prefix}{secret}"

    # Hash for storage
    import hashlib
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    return full_key, prefix, key_hash


def verify_api_key(api_key: str, db: Session) -> Optional[APIKey]:
    """
    Verify API key and return APIKey object

    Args:
        api_key: API key string
        db: Database session

    Returns:
        APIKey object if valid, None otherwise
    """
    import hashlib

    # Extract prefix
    if not api_key.startswith("sk_"):
        return None

    # Hash the key
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    # Query database
    api_key_obj = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    ).first()

    if api_key_obj:
        # Update last used
        api_key_obj.last_used = datetime.utcnow()
        db.commit()

    return api_key_obj


# ==========================================
# AUTHENTICATION DEPENDENCIES
# ==========================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db_session)
) -> User:
    """
    Get current authenticated user from JWT token

    Usage:
        @app.get("/protected")
        async def protected_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.email}
    """
    token = credentials.credentials

    # Decode token
    payload = decode_token(token)

    # Get user from database
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user = db.query(User).filter(
        User.id == user_id,
        User.is_active == True
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Set tenant context
    set_tenant_context(tenant_id)

    return user


async def get_current_user_or_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db_session)
) -> tuple[Optional[User], Optional[APIKey]]:
    """
    Authenticate via JWT token OR API key

    Returns:
        Tuple of (User, APIKey) - one will be None
    """
    token = credentials.credentials

    # Try JWT first
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")

        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()

        if user:
            set_tenant_context(tenant_id)
            return user, None
    except HTTPException:
        pass

    # Try API key
    api_key_obj = verify_api_key(token, db)
    if api_key_obj:
        set_tenant_context(api_key_obj.tenant_id)
        user = db.query(User).filter(User.id == api_key_obj.user_id).first()
        return user, api_key_obj

    # Neither worked
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials"
    )


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require admin role

    Usage:
        @app.delete("/users/{user_id}")
        async def delete_user(admin: User = Depends(require_admin)):
            ...
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ==========================================
# USER AUTHENTICATION FUNCTIONS
# ==========================================

def authenticate_user(email: str, password: str, db: Session) -> Optional[User]:
    """
    Authenticate user with email and password

    Args:
        email: User email
        password: Plain text password
        db: Database session

    Returns:
        User object if authentication successful, None otherwise
    """
    user = db.query(User).filter(User.email == email).first()

    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    if not user.is_active:
        return None

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    return user


def create_user(
    email: str,
    password: str,
    tenant_id: str,
    full_name: Optional[str] = None,
    role: str = "user",
    db: Session = None
) -> User:
    """
    Create new user

    Args:
        email: User email
        password: Plain text password (will be hashed)
        tenant_id: Tenant ID
        full_name: Optional full name
        role: User role (default: user)
        db: Database session

    Returns:
        Created User object
    """
    # Check if user already exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise ValueError("User with this email already exists")

    # Hash password
    password_hash = hash_password(password)

    # Create user
    user = User(
        email=email,
        password_hash=password_hash,
        tenant_id=tenant_id,
        full_name=full_name,
        role=role,
        is_active=True,
        is_verified=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_password_hash(password: str) -> str:
    """Public alias for hash_password"""
    return hash_password(password)


def check_password(plain_password: str, hashed_password: str) -> bool:
    """Public alias for verify_password"""
    return verify_password(plain_password, hashed_password)
