# security.py  (or app/core/security.py)

from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict

from jose import JWTError, jwt
from pwdlib import PasswordHash

from schemas.user_schema import TokenData

# ----- Password hashing with pwdlib -----
password_hasher = PasswordHash.recommended()  # Argon2/Bcrypt with safe defaults

def hash_password(password: str) -> str:
    return password_hasher.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    
    return password_hasher.verify(plain_password, hashed_password)

# ----- JWT settings -----
SECRET_KEY = "CHANGE_ME_TO_A_LONG_RANDOM_SECRET"  # use env var in real app
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = now + expires_delta
    to_encode.update({"exp": expire, "iat": now})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Match your actual JWT structure:
        # sub     -> email
        # sub_id  -> user id
        user_id = payload.get("sub_id")
        email = payload.get("sub")

        if user_id is None or email is None:
            return None

        # ensure user_id is int for TokenData
        return TokenData(user_id=int(user_id), email=email)

    except JWTError:
        return None
    except JWTError:
        return None
