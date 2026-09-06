#importar tipado para diccionarios y opcionales
from typing import Dict, Optional

#definir diccionario estatico de tokens autorizados por servicio
TOKENS_VALIDOS: Dict[str, str] = {
    "TOKEN-ATM-001": "atm-cash-service",
    "TOKEN-AUTH-002": "atm-auth-service",
    "TOKEN-PAYMENTS-003": "atm-account-service",
    "TOKEN-WATCHDOG-004": "atm-hardware-service",
    "TOKEN-ADMIN-005": "admin",
}

#validar si el token corresponde a un servicio registrado
def validar_token_servicio(token_candidato: Optional[str]) -> Optional[str]:
    #descartar tokens ausentes o vacios
    if not token_candidato:
        return None
    #retornar nombre del servicio o none
    return TOKENS_VALIDOS.get(token_candidato.strip())