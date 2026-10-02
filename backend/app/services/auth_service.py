from datetime import datetime, timedelta, timezone
from hashlib import sha256

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.models.parent import Parent
from app.models.refresh_token import RefreshToken


def register_parent(db: Session, name: str, phone: str, email: str, password: str) -> Parent:
    existing = db.query(Parent).filter((Parent.email == email) | (Parent.phone == phone)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent already exists")

    parent = Parent(name=name.strip(), phone=phone.strip(), email=email.strip().lower(), password_hash=hash_password(password))
    db.add(parent)
    db.commit()
    db.refresh(parent)
    return parent


def login_parent(db: Session, email: str, password: str) -> tuple[str, str, int, int]:
    parent = db.query(Parent).filter(Parent.email == email.lower()).first()
    if not parent or not verify_password(password, parent.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access = create_access_token(str(parent.id))
    refresh = create_refresh_token(str(parent.id))
    expiry = datetime.now(timezone.utc) + timedelta(days=30)
    db.add(RefreshToken(parent_id=parent.id, token_hash=sha256(refresh.encode("utf-8")).hexdigest(), expires_at=expiry, revoked=False))
    db.commit()
    return access, refresh, 30, 30


def refresh_token_pair(db: Session, refresh_token: str) -> tuple[str, str]:
    from jose import JWTError

    try:
        from app.core.security import decode_token

        payload = decode_token(refresh_token)
    except HTTPException as exc:
        raise exc
    except JWTError as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token type invalid")

    parent_id = int(payload.get("sub"))
    token_hash = sha256(refresh_token.encode("utf-8")).hexdigest()
    token_record = db.query(RefreshToken).filter(RefreshToken.parent_id == parent_id, RefreshToken.token_hash == token_hash).first()
    if token_record is None or token_record.revoked or token_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked or expired")

    token_record.revoked = True
    new_access = create_access_token(str(parent_id))
    new_refresh = create_refresh_token(str(parent_id))
    db.add(RefreshToken(parent_id=parent_id, token_hash=sha256(new_refresh.encode("utf-8")).hexdigest(), expires_at=datetime.now(timezone.utc) + timedelta(days=30), revoked=False))
    db.commit()
    return new_access, new_refresh


def logout_parent(db: Session, parent_id: int, refresh_token: str | None = None) -> None:
    if refresh_token:
        db.query(RefreshToken).filter(
            RefreshToken.parent_id == parent_id,
            RefreshToken.token_hash == sha256(refresh_token.encode("utf-8")).hexdigest(),
        ).update({"revoked": True})
    db.query(RefreshToken).filter(RefreshToken.parent_id == parent_id).update({"revoked": True})
    db.commit()
