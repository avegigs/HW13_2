import jwt
from datetime import datetime, timedelta
from typing import Optional
import os

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
VERIFICATION_TOKEN_EXPIRE_MINUTES = 60


def generate_verification_token(email: str) -> str:
    expiration = datetime.utcnow() + timedelta(
        minutes=VERIFICATION_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": email, "exp": expiration}
    verification_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return verification_token


def verify_verification_token(email: str, token: str) -> bool:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload["sub"] == email:
            return True
    except jwt.ExpiredSignatureError:
        pass
    except jwt.PyJWTError:
        pass
    return False
