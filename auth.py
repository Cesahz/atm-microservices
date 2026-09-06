import os
import sys

# Permitir importación del módulo interno auth_service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "services", "auth_service"))

from services.auth_service.auth import app, create_app
from services.auth_service.database import inicializar_db
from services.auth_service.config import config

if __name__ == "__main__":
    inicializar_db()
    print(f"Iniciando servicio de autenticacion en http://{config.host}:{config.port}")
    app.run(host=config.host, port=config.port, debug=False)