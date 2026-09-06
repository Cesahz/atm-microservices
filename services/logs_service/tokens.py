from typing import Dict, Optional

TOKENS_VALIDOS: Dict[str, str] = {
    "TOKEN-ATM-001": "atm-cash-service",
    "TOKEN-AUTH-002": "atm-auth-service",
    "TOKEN-PAYMENTS-003": "atm-account-service",
    "TOKEN-WATCHDOG-004": "atm-hardware-service",
    "TOKEN-ADMIN-005": "admin",
}

def validar_token_servicio(token_candidato: Optional[str]) -> Optional[str]:
    """Valida si el token provisto corresponde a un servicio o rol autorizado."""
    if not token_candidato:
        return None
    return TOKENS_VALIDOS.get(token_candidato.strip())