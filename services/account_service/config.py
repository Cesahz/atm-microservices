import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class AccountConfig:
    database_url: str = (
        os.getenv("DATABASE_URL")
        or os.getenv("DB_ACCOUNT_URL")
        or "postgresql://admin:password@localhost:5434/operador_db"
    )
    logs_url: str = os.getenv("LOGS_URL", "http://localhost:5000/logs")
    jwt_secret: str = os.getenv("JWT_SECRET", "secreto_del_pinguino_aislado")
    token_logs: str = (
        os.getenv("TOKEN_ACCOUNT")
        or os.getenv("TOKEN_LOGS_ACCOUNT")
        or "TOKEN-PAYMENTS-003"
    )
    service_name: str = "atm-account-service"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("ACCOUNT_PORT", "5002"))

config = AccountConfig()
