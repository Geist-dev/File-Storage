from datetime import datetime, timedelta, timezone
from jose import jwt
import bcrypt
from config import settings

def hash_password(pwd: str) -> str:
    return bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt()).decode('ascii')

def verify_password(pwd: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pwd.encode('utf-8'), hashed.encode('ascii'))
    except (ValueError, UnicodeError):
        return False

def make_token(user_id: int, email: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRES_MIN)
    payload = {"sub": str(user_id), "email": email, "exp": exp}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
