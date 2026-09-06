import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class AuthConfig:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://admin:password@localhost:5433/auth_db"
    )
    logs_url: str = os.getenv("LOGS_URL", "http://localhost:5000/logs")
    jwt_secret: str = os.getenv("JWT_SECRET", "secreto_del_pinguino_aislado")
    token_auth: str = os.getenv("TOKEN_AUTH", "TOKEN-AUTH-002")
    service_name: str = "atm-auth-service"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("AUTH_PORT", "5001"))
    jwt_expiry_minutes: int = int(os.getenv("JWT_EXPIRY_MINUTES", "15"))

config = AuthConfig()
