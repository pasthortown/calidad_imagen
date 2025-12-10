import bcrypt
import jwt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from app.config import config
from app.models.user import TokenData


def hash_password(password: str) -> str:
    """Hashea una contraseña usando bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def create_access_token(user_id: str, email: str) -> str:
    """Crea un token JWT de acceso."""
    expire = datetime.utcnow() + timedelta(
        minutes=config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "type": "access"
    }
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def create_refresh_token() -> Tuple[str, datetime]:
    """Crea un token de refresco y su fecha de expiración."""
    token = secrets.token_urlsafe(64)
    expires_at = datetime.utcnow() + timedelta(days=config.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    return token, expires_at


def decode_access_token(token: str) -> Optional[TokenData]:
    """Decodifica y valida un token JWT de acceso."""
    try:
        payload = jwt.decode(
            token,
            config.JWT_SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM]
        )
        if payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        email = payload.get("email")
        if user_id is None:
            return None
        return TokenData(user_id=user_id, email=email)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def create_token_pair(user_id: str, email: str) -> Tuple[str, str, datetime]:
    """Crea un par de tokens (access + refresh)."""
    access_token = create_access_token(user_id, email)
    refresh_token, expires_at = create_refresh_token()
    return access_token, refresh_token, expires_at
