"""
SmartV2X-CP Ultra — Authentication Routes
===========================================
POST /api/auth/register — Create a new user account
POST /api/auth/login    — Authenticate and retrieve JWT
POST /api/auth/google   — Google OAuth login/register
"""

import logging
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext

from edge_rsu.database.connection import get_db
from edge_rsu.auth.jwt_handler import create_access_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Schemas ───────────────────────────────────────────────
class UserRegisterRequest(BaseModel):
    username: str
    password: str
    name: Optional[str] = ""
    role: Optional[str] = "viewer"  # admin, operator, viewer

class LoginRequest(BaseModel):
    username: str
    password: str

class GoogleLoginRequest(BaseModel):
    id_token: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    name: str
    role: str

# ── Helpers ───────────────────────────────────────────────
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# ── Routes ────────────────────────────────────────────────
@router.post("/register")
async def register(req: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    from edge_rsu.database.models import User
    # Check existing
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Create user
    new_user = User(
        username=req.username,
        password_hash=get_password_hash(req.password),
        name=req.name,
        role=req.role,
        auth_provider="local"
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Generate token
    token = create_access_token({
        "sub": new_user.username,
        "role": new_user.role,
        "name": new_user.name
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "name": new_user.name,
        "role": new_user.role,
    }

@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT."""
    from edge_rsu.database.models import User
    # Check DB
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalars().first()

    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        # Fallback to demo users if not in DB (for backward compatibility/initial setup)
        from edge_rsu.auth.jwt_handler import DEMO_USERS
        demo_user = DEMO_USERS.get(req.username)
        if demo_user and demo_user["password"] == req.password:
            token = create_access_token({
                "sub": req.username,
                "role": demo_user["role"],
                "name": demo_user["name"]
            })
            return {
                "access_token": token,
                "token_type": "bearer",
                "name": demo_user["name"],
                "role": demo_user["role"],
            }
            
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Generate token
    token = create_access_token({
        "sub": user.username,
        "role": user.role,
        "name": user.name
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "name": user.name,
        "role": user.role,
    }


@router.post("/google")
async def google_login(req: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with Google OAuth. Auto-registers on first login."""
    from edge_rsu.database.models import User

    # Verify the Google ID token
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
        idinfo = google_id_token.verify_oauth2_token(
            req.id_token,
            google_requests.Request(),
        )
    except ImportError:
        # google-auth not installed — decode the JWT manually (for dev/testing)
        # In production, always use the google-auth library
        logger.warning("google-auth not installed — using fallback token decode")
        try:
            import json, base64
            parts = req.id_token.split(".")
            if len(parts) < 2:
                raise HTTPException(status_code=400, detail="Invalid Google token")
            # Add padding
            payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
            idinfo = json.loads(base64.urlsafe_b64decode(payload))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token"
        )

    email = idinfo.get("email", "")
    name = idinfo.get("name", email.split("@")[0] if email else "Google User")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token missing email"
        )

    # Check if user exists by email
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
        # Auto-register Google user
        username = email.split("@")[0]
        # Ensure unique username
        existing = await db.execute(select(User).where(User.username == username))
        if existing.scalars().first():
            import time
            username = f"{username}_{int(time.time()) % 10000}"

        user = User(
            username=username,
            email=email,
            name=name,
            auth_provider="google",
            role="viewer",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("New Google user registered: %s (%s)", user.username, email)
    else:
        logger.info("Google user logged in: %s (%s)", user.username, email)

    # Generate JWT
    token = create_access_token({
        "sub": user.username,
        "role": user.role,
        "name": user.name,
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "name": user.name,
        "role": user.role,
    }
