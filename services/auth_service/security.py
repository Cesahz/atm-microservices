#importar librerias criptograficas y de tiempo
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt

#definir iteraciones estandar para pbkdf2
ITERATIONS = 100_000

#derivar hash seguro para el pin mediante pbkdf2 hmac sha256
def hash_pin(pin: str) -> str:
    #generar sal criptografica aleatoria
    salt = secrets.token_hex(16)
    #derivar clave binaria mediante hashing seguro
    key = hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode("utf-8"),
        salt.encode("utf-8"),
        ITERATIONS
    )
    #retornar cadena formateada con metadata algoritmo sal y hash
    return f"pbkdf2:sha256:{ITERATIONS}${salt}${key.hex()}"

#verificar pin provisto contra hash almacenado en tiempo constante
def verify_pin(pin: str, stored_hash: str) -> bool:
    #descartar entradas nulas
    if not stored_hash or not pin:
        return False

    #verificacion de hash pbkdf2
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
            #comparar hashes en tiempo constante para evitar ataques de canal lateral
            return hmac.compare_digest(derived_key.hex(), expected_hash)
        except (ValueError, IndexError):
            return False

    #compatibilidad temporal para registros legados en texto plano
    return hmac.compare_digest(pin, stored_hash)

#generar token jwt firmado criptograficamente con expiracion
def create_access_token(user_id: int, secret_key: str, expiry_minutes: int = 15) -> str:
    #establecer marcas de tiempo utc
    now = datetime.now(timezone.utc)
    #construir payload con claims estandar
    payload: Dict[str, Any] = {
        "user_id": user_id,
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=expiry_minutes)
    }
    #firmar token con algoritmo hs256
    return jwt.encode(payload, secret_key, algorithm="HS256")

#decodificar y validar firma y vigencia del token jwt
def decode_access_token(token: str, secret_key: str) -> Optional[Dict[str, Any]]:
    #intentar decodificacion segura
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
