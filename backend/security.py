from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.hash import bcrypt
from config import settings

def hash_password(pwd: str) -> str:
    return bcrypt.hash(pwd)

def verify_password(pwd: str, hashed: str) -> bool:
    return bcrypt.verify(pwd, hashed)

def make_token(user_id: int, email: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRES_MIN)
    payload = {"sub": str(user_id), "email": email, "exp": exp}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
