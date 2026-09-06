import os
import sys

# Permitir importación del módulo interno logs_service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "services", "logs_service"))

from services.logs_service.app import app, create_app
from services.logs_service.database import inicializar_db
from services.logs_service.config import config

if __name__ == "__main__":
    inicializar_db()
    print(f"Iniciando servicio de auditoria y logs en http://{config.host}:{config.port}")
    app.run(host=config.host, port=config.port, debug=False)