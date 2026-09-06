#importar modulos del sistema y tipado
import os
from dataclasses import dataclass
from dotenv import load_dotenv

#cargar variables de entorno locales desde archivo env
load_dotenv()

#definir estructura inmutable de configuracion del operador contable
@dataclass(frozen=True)
class AccountConfig:
    #mapear url de base de datos con fallback a configuracion local
    database_url: str = (
        os.getenv("DATABASE_URL")
        or os.getenv("DB_ACCOUNT_URL")
        or "postgresql://admin:password@localhost:5434/operador_db"
    )
    #mapear endpoint centralizado de auditoria de logs
    logs_url: str = os.getenv("LOGS_URL", "http://localhost:5000/logs")
    #obtener clave secreta compartida para validar tokens jwt
    jwt_secret: str = os.getenv("JWT_SECRET", "secreto_del_pinguino_aislado")
    #mapear token estatico autorizado ante el servicio de logs
    token_logs: str = (
        os.getenv("TOKEN_ACCOUNT")
        or os.getenv("TOKEN_LOGS_ACCOUNT")
        or "TOKEN-PAYMENTS-003"
    )
    #establecer nombre del servicio para telemetria
    service_name: str = "atm-account-service"
    #configurar direccion ip de escucha
    host: str = os.getenv("HOST", "0.0.0.0")
    #configurar puerto de red del servicio de cuentas
    port: int = int(os.getenv("ACCOUNT_PORT", "5002"))

#instanciar objeto unico de configuracion para la aplicacion
config = AccountConfig()
