import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt

ITERATIONS = 100_000

def hash_pin(pin: str) -> str:
    """Deriva un hash criptográfico seguro para el PIN utilizando PBKDF2-HMAC-SHA256."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode("utf-8"),
        salt.encode("utf-8"),
        ITERATIONS
    )
    return f"pbkdf2:sha256:{ITERATIONS}${salt}${key.hex()}"

def verify_pin(pin: str, stored_hash: str) -> bool:
    """Verifica un PIN contra su hash almacenado en tiempo constante."""
    if not stored_hash or not pin:
        return False

    # Verificación estándar de hash PBKDF2
    if stored_hash.startswith("pbkdf2:sha256:"):
        try:
            algorithm_info, salt, expected_hash = stored_hash.split("$")
            iterations = int(algorithm_info.split(":")[2])
            derived_key = hashlib.pbkdf2_hmac(
                "sha256",
                pin.encode("utf-8"),
                salt.encode("utf-8"),
                iterations
            )
            return hmac.compare_digest(derived_key.hex(), expected_hash)
        except (ValueError, IndexError):
            return False

    # Compatibilidad retroactiva temporal para registros legados en texto plano
    return hmac.compare_digest(pin, stored_hash)

def create_access_token(user_id: int, secret_key: str, expiry_minutes: int = 15) -> str:
    """Genera un token JWT firmado criptográficamente con tiempo de expiración."""
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "user_id": user_id,
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=expiry_minutes)
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")

def decode_access_token(token: str, secret_key: str) -> Optional[Dict[str, Any]]:
    """Decodifica y valida la firma y expiración de un token JWT."""
    try:
        payload: Dict[str, Any] = jwt.decode(
            token,
            secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "user_id"]}
        )
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
