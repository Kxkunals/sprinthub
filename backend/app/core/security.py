from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db

_hasher = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


def check_password(plain: str, hashed: str) -> bool:
    return _hasher.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def _build_token(payload: dict, expires: timedelta, token_type: str) -> str:
    data = payload.copy()
    data.update({"exp": datetime.utcnow() + expires, "kind": token_type})
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def make_access_token(data: dict) -> str:
    return _build_token(data, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def make_refresh_token(data: dict) -> str:
    return _build_token(data, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), "refresh")


def parse_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    from app.models.core import Account
    raw = credentials.credentials
    payload = parse_token(raw)
    if not payload or payload.get("kind") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalid or expired")
    uid = payload.get("sub")
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")
    account = db.query(Account).filter(Account.id == int(uid)).first()
    if not account or not account.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found or disabled")
    return account


def require_admin(current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return current_user
