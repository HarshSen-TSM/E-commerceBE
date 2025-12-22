from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from database import get_db
from models.user_model import User
from schemas.user_schema import TokenData

# ===============================
# Password Hashing
# ===============================

password_hasher = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hasher.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hasher.verify(plain_password, hashed_password)


# ===============================
# JWT Config
# ===============================

SECRET_KEY = "CHANGE_ME_TO_A_LONG_RANDOM_SECRET"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ===============================
# JWT Creation
# ===============================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = now + expires_delta
    to_encode.update({"exp": expire, "iat": now})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ===============================
# JWT Decode
# ===============================

def decode_access_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id = payload.get("sub_id")
        email = payload.get("sub")

        if user_id is None or email is None:
            return None

        return TokenData(
            user_id=int(user_id),
            email=email
        )

    except JWTError:
        return None


# ===============================
# AUTHENTICATION
# ===============================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    token_data = decode_access_token(token)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = db.query(User).filter(User.id == token_data.user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


# ===============================
# AUTHORIZATION (OPTIONAL)
# ===============================

def admin_required(
    user: User = Depends(get_current_user)
):
    if not getattr(user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user
