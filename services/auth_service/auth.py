from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
import requests
from flask import Flask, jsonify, request, Response

try:
    from .config import config
    from . import database
    from .security import create_access_token
except ImportError:
    from config import config
    import database
    from security import create_access_token

def enviar_log_silencioso(
    mensaje: str,
    severidad: str = "INFO",
    logs_url: Optional[str] = None,
    token_auth: Optional[str] = None
) -> None:
    """Envía un evento de auditoría a logs_service de forma tolerante a fallos."""
    url = logs_url or config.logs_url
    token = token_auth or config.token_auth
    log_data: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": config.service_name,
        "severity": severidad,
        "message": mensaje,
    }
    try:
        requests.post(
            url,
            json=log_data,
            headers={"Authorization": f"Token {token}"},
            timeout=2.0,
        )
    except requests.exceptions.RequestException:
        pass


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """Fábrica de aplicaciones Flask para el servicio de autenticación."""
    app = Flask(__name__)

    if test_config:
        app.config.update(test_config)

    db_url = app.config.get("DATABASE_URL", config.database_url)
    logs_url = app.config.get("LOGS_URL", config.logs_url)
    jwt_secret = app.config.get("JWT_SECRET", config.jwt_secret)
    token_auth = app.config.get("TOKEN_AUTH", config.token_auth)
    expiry_minutes = app.config.get("JWT_EXPIRY_MINUTES", config.jwt_expiry_minutes)

    @app.route("/health", methods=["GET"])
    def health() -> Tuple[Response, int]:
        """Endpoint de verificación de estado y conectividad."""
        return jsonify({
            "status": "healthy",
            "service": config.service_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }), 200

    @app.route("/login", methods=["POST"])
    def login() -> Tuple[Response, int]:
        """
        Autentica usuario y PIN, retornando un token JWT de acceso.
        """
        if not request.is_json:
            return jsonify({"error": "El cuerpo de la solicitud debe ser un JSON válido"}), 400

        datos = request.get_json(silent=True)
        if not isinstance(datos, dict):
            return jsonify({"error": "Formato de datos no válido"}), 400

        username = datos.get("username")
        pin = datos.get("pin")

        if not username or not pin:
            return jsonify({"error": "Faltan credenciales obligatorias (username y pin)"}), 400

        username_str = str(username).strip()
        pin_str = str(pin).strip()

        if not username_str or not pin_str:
            return jsonify({"error": "Las credenciales no pueden estar vacías"}), 400

        resultado = database.verificar_credenciales(username_str, pin_str, db_url=db_url)

        if resultado is not None:
            user_id, valid_username = resultado
            token = create_access_token(
                user_id=user_id,
                secret_key=jwt_secret,
                expiry_minutes=expiry_minutes,
            )
            enviar_log_silencioso(
                f"Login exitoso para usuario: {valid_username}",
                severidad="INFO",
                logs_url=logs_url,
                token_auth=token_auth,
            )
            return jsonify({"token": token}), 200

        enviar_log_silencioso(
            f"Intento de acceso denegado para usuario: {username_str}",
            severidad="WARN",
            logs_url=logs_url,
            token_auth=token_auth,
        )
        return jsonify({"error": "Credenciales invalidas"}), 401

    return app


app = create_app()

if __name__ == "__main__":
    database.inicializar_db()
    app.run(host=config.host, port=config.port, debug=False)