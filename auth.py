#importar utilidades del sistema
import os
import sys

#permitir resolucion del modulo auth_service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "services", "auth_service"))

#importar componentes del servicio de autenticacion
from services.auth_service.auth import app, create_app
from services.auth_service.database import inicializar_db
from services.auth_service.config import config

#arrancar servidor si es ejecutado como script principal
if __name__ == "__main__":
    #inicializar tablas y credenciales precargadas
    inicializar_db()
    #notificar puerto de escucha en consola
    print(f"Iniciando servicio de autenticacion en http://{config.host}:{config.port}")
    #levantar aplicacion flask
    app.run(host=config.host, port=config.port, debug=False)