#importar utilidades del sistema operativo
import os
import sys

#permitir resolucion del modulo account_service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "services", "account_service"))

#importar componentes del servicio de cuentas
from services.account_service.account import app, create_app
from services.account_service.database import inicializar_db
from services.account_service.config import config

#arrancar servidor si es ejecutado como script principal
if __name__ == "__main__":
    #inicializar tablas y precarga de cuentas
    inicializar_db()
    #notificar puerto de escucha en consola
    print(f"Iniciando servicio financiero de cuentas en http://{config.host}:{config.port}")
    #levantar aplicacion flask
    app.run(host=config.host, port=config.port, debug=False)