#importar modulos de configuracion y tipado
import os
from dataclasses import dataclass
from dotenv import load_dotenv

#cargar variables de entorno locales desde archivo env
load_dotenv()

#definir estructura inmutable de configuracion de autenticacion
@dataclass(frozen=True)
class AuthConfig:
    #mapear url de conexion a postgresql para autenticacion
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://admin:password@localhost:5433/auth_db"
    )
    #mapear endpoint del servicio de registro de logs
    logs_url: str = os.getenv("LOGS_URL", "http://localhost:5000/logs")
    #obtener clave secreta compartida para firma de jwt
    jwt_secret: str = os.getenv("JWT_SECRET", "secreto_del_pinguino_aislado")
    #obtener token estatico de autenticacion ante logs
    token_auth: str = os.getenv("TOKEN_AUTH", "TOKEN-AUTH-002")
    #definir identificador del servicio guardian
    service_name: str = "atm-auth-service"
    #configurar ip de escucha del servidor
    host: str = os.getenv("HOST", "0.0.0.0")
    #configurar puerto de red para auth_service
    port: int = int(os.getenv("AUTH_PORT", "5001"))
    #definir tiempo de expiracion del token en minutos
    jwt_expiry_minutes: int = int(os.getenv("JWT_EXPIRY_MINUTES", "15"))

#instanciar configuracion global de autenticacion
config = AuthConfig()
