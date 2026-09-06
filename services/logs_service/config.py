import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class LogsConfig:
    database_url: str = (
        os.getenv("DATABASE_URL")
        or os.getenv("DB_LOGS_URL")
        or "postgresql://admin:password@localhost:5435/logs_db"
    )
    service_name: str = "atm-logs-service"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("LOGS_PORT", "5000"))

config = LogsConfig()
