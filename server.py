#importar modulos de ruta del sistema
import os
import sys

#permitir resolucion del modulo logs_service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "services", "logs_service"))

#importar componentes del servicio de auditoria
from services.logs_service.app import app, create_app
from services.logs_service.database import inicializar_db
from services.logs_service.config import config

#arrancar servidor si es ejecutado como script principal
if __name__ == "__main__":
    #inicializar base de datos e indices de logs
    inicializar_db()
    #notificar puerto de escucha en consola
    print(f"Iniciando servicio de auditoria y logs en http://{config.host}:{config.port}")
    #levantar aplicacion flask
    app.run(host=config.host, port=config.port, debug=False)