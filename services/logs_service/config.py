#importar dependencias de entorno y clases de datos
import os
from dataclasses import dataclass
from dotenv import load_dotenv

#cargar variables de entorno locales desde archivo env
load_dotenv()

#definir estructura inmutable de configuracion de logs
@dataclass(frozen=True)
class LogsConfig:
    #mapear url de base de datos para persistencia de logs
    database_url: str = (
        os.getenv("DATABASE_URL")
        or os.getenv("DB_LOGS_URL")
        or "postgresql://admin:password@localhost:5435/logs_db"
    )
    #definir nombre del servicio para auditoria
    service_name: str = "atm-logs-service"
    #configurar host del servidor
    host: str = os.getenv("HOST", "0.0.0.0")
    #configurar puerto de escucha de logs
    port: int = int(os.getenv("LOGS_PORT", "5000"))

#instanciar configuracion global de logs
config = LogsConfig()
