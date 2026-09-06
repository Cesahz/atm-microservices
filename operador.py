import os
import sys

# Permitir importación del módulo interno account_service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "services", "account_service"))

from services.account_service.account import app, create_app
from services.account_service.database import inicializar_db
from services.account_service.config import config

if __name__ == "__main__":
    inicializar_db()
    print(f"Iniciando servicio financiero de cuentas en http://{config.host}:{config.port}")
    app.run(host=config.host, port=config.port, debug=False)