import time
from typing import Dict, Any, Optional
import jwt
from backend.platform.config.settings import settings

class AuthManager:
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[float] = None) -> str:
        to_encode = data.copy()
        expire = time.time() + (expires_delta or (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60))
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except jwt.PyJWTError:
            return None
