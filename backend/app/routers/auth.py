import random
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    check_password, hash_password,
    make_access_token, make_refresh_token,
    parse_token, get_current_user,
)
from app.models.core import Account
from app.schemas.schemas import (
    SignUpRequest, SignInRequest, AuthTokens,
    TokenRefreshRequest, AccountOut, AccountPatch, OkResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

BADGE_PALETTE = [
    "#7c3aed", "#9333ea", "#db2777", "#d97706",
    "#059669", "#2563eb", "#dc2626", "#0d9488",
]


@router.post("/register", response_model=AuthTokens, status_code=status.HTTP_201_CREATED)
def register(payload: SignUpRequest, db: Session = Depends(get_db)):
    if db.query(Account).filter(Account.email == payload.email).first():
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    account = Account(
        display_name=payload.display_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        badge_color=random.choice(BADGE_PALETTE),
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    return AuthTokens(
        access_token=make_access_token({"sub": str(account.id)}),
        refresh_token=make_refresh_token({"sub": str(account.id)}),
    )


@router.post("/login", response_model=AuthTokens)
def login(payload: SignInRequest, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.email == payload.email).first()
    if not account or not check_password(payload.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not account.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated")

    return AuthTokens(
        access_token=make_access_token({"sub": str(account.id)}),
        refresh_token=make_refresh_token({"sub": str(account.id)}),
    )


@router.post("/refresh", response_model=AuthTokens)
def refresh(payload: TokenRefreshRequest, db: Session = Depends(get_db)):
    claims = parse_token(payload.refresh_token)
    if not claims or claims.get("kind") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token is invalid")
    account = db.query(Account).filter(Account.id == int(claims["sub"])).first()
    if not account:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    return AuthTokens(
        access_token=make_access_token({"sub": str(account.id)}),
        refresh_token=make_refresh_token({"sub": str(account.id)}),
    )


@router.get("/me", response_model=AccountOut)
def me(current_user=Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=AccountOut)
def update_me(
    payload: AccountPatch,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if payload.display_name:
        current_user.display_name = payload.display_name
    if payload.badge_color:
        current_user.badge_color = payload.badge_color
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Returns all active accounts (for member assignment, etc.)"""
    return db.query(Account).filter(Account.is_active == True).all()
