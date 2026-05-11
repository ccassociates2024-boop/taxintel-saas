from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.repositories import TenantRepository, UserRepository, audit
from app.schemas import AuthRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    if repo.by_email(payload.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    # Auto-create a tenant for this CA firm; place_of_supply defaults to Delhi (07)
    tenant = TenantRepository(db).create(
        legal_name=getattr(payload, "legal_name", None) or payload.full_name,
        trade_name=getattr(payload, "trade_name", None) or payload.full_name,
        billing_email=payload.email,
    )
    user = repo.create(payload.email, payload.password, payload.full_name, payload.role, tenant.id)
    db.commit()

    audit(db, user.id, "USER_REGISTERED", "user", str(user.id), tenant_id=tenant.id)
    token = create_access_token(str(user.id), user.role, str(tenant.id), tenant.trade_name)
    return TokenResponse(access_token=token, user=user)


@router.post("/login", response_model=TokenResponse)
def login(payload: AuthRequest, db: Session = Depends(get_db)):
    user = UserRepository(db).by_email(payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    audit(db, user.id, "USER_LOGIN", "user", str(user.id), tenant_id=user.tenant_id)
    token = create_access_token(str(user.id), user.role, str(user.tenant_id), user.tenant.trade_name)
    return TokenResponse(access_token=token, user=user)
