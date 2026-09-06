# Fuente única de la verdad. Mapeo estricto 1 a 1 por microservicio.
TOKENS_VALIDOS = {
    "TOKEN-AUTH-002":     "atm-auth-service",    # Usado por el Guardián (auth.py)
    "TOKEN-PAYMENTS-003": "atm-account-service", # Usado por el Operador (account.py)
    "TOKEN-ADMIN-005":    "admin",               # Tu pase VIP para leer los logs
}