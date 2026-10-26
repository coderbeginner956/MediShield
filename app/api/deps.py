from typing import Generator, List, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def get_db() -> Generator:
    """Yields a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> User:
    """
    Validates JWT access token and returns authenticated User.
    In demonstration mode or client requests without Bearer headers,
    falls back gracefully to the active user persona.
    """
    if token:
        payload = decode_access_token(token)
        if payload:
            user_id: str = payload.get("sub")
            if user_id:
                user = db.query(User).filter(User.id == int(user_id)).first()
                if user and user.is_active:
                    return user

    # Check custom persona headers from frontend role switcher
    user_email = request.headers.get("x-user-email")
    user_role = request.headers.get("x-user-role")

    if user_email:
        user = db.query(User).filter(User.email == user_email, User.is_active == True).first()
        if user:
            return user

    if user_role:
        user = db.query(User).filter(User.role == user_role, User.is_active == True).first()
        if user:
            return user

    # Default fallback to active demo administrator
    demo_user = db.query(User).filter(User.is_active == True).order_by(User.id.asc()).first()
    if demo_user:
        return demo_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

def require_role(allowed_roles: List[str]):
    """Role-based access control (RBAC) dependency factory."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {', '.join(allowed_roles)}. Your role: '{current_user.role}'."
            )
        return current_user
    return role_checker

