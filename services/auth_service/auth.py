#importar utilidades de fechas y tiempos
from datetime import datetime, timezone
#importar tipado estricto
from typing import Any, Dict, Optional, Tuple
#importar cliente http
import requests
#importar componentes del framework flask
from flask import Flask, jsonify, request, Response

#importar configuracion interna capa de datos y seguridad
try:
    from .config import config
    from . import database
    from .security import create_access_token
except ImportError:
    from config import config
    import database
    from security import create_access_token

#enviar evento de auditoria a logs_service de forma tolerante a fallos
def enviar_log_silencioso(
    mensaje: str,
    severidad: str = "INFO",
    logs_url: Optional[str] = None,
    token_auth: Optional[str] = None
) -> None:
    url = logs_url or config.logs_url
    token = token_auth or config.token_auth
    #construir estructura del registro
    log_data: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": config.service_name,
        "severity": severidad,
        "message": mensaje,
    }
    #enviar log con timeout defensivo
    try:
        requests.post(
            url,
            json=log_data,
            headers={"Authorization": f"Token {token}"},
            timeout=2.0,
        )
    except requests.exceptions.RequestException:
        pass

#definir fabrica de aplicacion flask para autenticacion
def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    #instanciar app flask
    app = Flask(__name__)

    #aplicar configuracion de prueba si se proporciona
    if test_config:
        app.config.update(test_config)

    #resolver configuraciones y secretos
    db_url = app.config.get("DATABASE_URL", config.database_url)
    logs_url = app.config.get("LOGS_URL", config.logs_url)
    jwt_secret = app.config.get("JWT_SECRET", config.jwt_secret)
    token_auth = app.config.get("TOKEN_AUTH", config.token_auth)
    expiry_minutes = app.config.get("JWT_EXPIRY_MINUTES", config.jwt_expiry_minutes)

    #definir endpoint de salud del servicio
    @app.route("/health", methods=["GET"])
    def health() -> Tuple[Response, int]:
        return jsonify({
            "status": "healthy",
            "service": config.service_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }), 200

    #definir endpoint de login para emision de tokens jwt
    @app.route("/login", methods=["POST"])
    def login() -> Tuple[Response, int]:
        #verificar formato json en la peticion
        if not request.is_json:
            return jsonify({"error": "El cuerpo de la solicitud debe ser un JSON válido"}), 400

        #extraer y validar objeto json
        datos = request.get_json(silent=True)
        if not isinstance(datos, dict):
            return jsonify({"error": "Formato de datos no válido"}), 400

        username = datos.get("username")
        pin = datos.get("pin")

        #validar campos obligatorios
        if not username or not pin:
            return jsonify({"error": "Faltan credenciales obligatorias (username y pin)"}), 400

        username_str = str(username).strip()
        pin_str = str(pin).strip()

        #descartar valores vacios
        if not username_str or not pin_str:
            return jsonify({"error": "Las credenciales no pueden estar vacías"}), 400

        #validar credenciales en base de datos
        resultado = database.verificar_credenciales(username_str, pin_str, db_url=db_url)

        #generar token si el login es exitoso
        if resultado is not None:
            user_id, valid_username = resultado
            token = create_access_token(
                user_id=user_id,
                secret_key=jwt_secret,
                expiry_minutes=expiry_minutes,
            )
            #notificar acceso exitoso en logs
            enviar_log_silencioso(
                f"Login exitoso para usuario: {valid_username}",
                severidad="INFO",
                logs_url=logs_url,
                token_auth=token_auth,
            )
            return jsonify({"token": token}), 200

        #notificar intento fallido en logs
        enviar_log_silencioso(
            f"Intento de acceso denegado para usuario: {username_str}",
            severidad="WARN",
            logs_url=logs_url,
            token_auth=token_auth,
        )
        return jsonify({"error": "Credenciales invalidas"}), 401

    return app

#instanciar app para servidor
app = create_app()

#ejecutar servidor si es script principal
if __name__ == "__main__":
    database.inicializar_db()
    app.run(host=config.host, port=config.port, debug=False)