from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
import jwt
import requests
from flask import Flask, jsonify, request, Response

try:
    from .config import config
    from . import database
except ImportError:
    from config import config
    import database

def enviar_log_silencioso(
    mensaje: str,
    severidad: str = "INFO",
    logs_url: Optional[str] = None,
    token_logs: Optional[str] = None,
) -> None:
    """Envía un log de auditoría a logs_service con tolerancia total a fallos."""
    url = logs_url or config.logs_url
    token = token_logs or config.token_logs
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


def extraer_token_de_cabecera(cabecera_auth: str) -> Optional[str]:
    """Extrae el token Bearer de la cabecera Authorization respetando variaciones de formato."""
    if not cabecera_auth:
        return None
    partes = cabecera_auth.strip().split()
    if len(partes) == 2 and partes[0].lower() == "bearer":
        return partes[1]
    if len(partes) == 1:
        return partes[0]
    return None


def validar_jwt(token: str, secret_key: str, logs_url: Optional[str] = None) -> Optional[int]:
    """Valida la firma y expiración del JWT, devolviendo el user_id autenticado."""
    if not token:
        return None
    try:
        data = jwt.decode(
            token,
            secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "user_id"]},
        )
        return int(data["user_id"])
    except jwt.ExpiredSignatureError:
        enviar_log_silencioso("Token expirado presentado en account_service", "WARN", logs_url=logs_url)
        return None
    except (jwt.InvalidTokenError, ValueError, KeyError):
        enviar_log_silencioso("Token invalido presentado en account_service", "ERROR", logs_url=logs_url)
        return None


def parsear_monto(valor: Any) -> Optional[Decimal]:
    """Valida y parsea un monto monetario a Decimal positivo."""
    if valor is None:
        return None
    try:
        monto = Decimal(str(valor).strip())
        if monto.is_nan() or monto.is_infinite() or monto <= Decimal(0):
            return None
        return monto
    except (InvalidOperation, ValueError, TypeError):
        return None


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """Fábrica de aplicaciones Flask para el microservicio de operaciones de cuenta."""
    app = Flask(__name__)

    if test_config:
        app.config.update(test_config)

    db_url = app.config.get("DATABASE_URL", config.database_url)
    logs_url = app.config.get("LOGS_URL", config.logs_url)
    jwt_secret = app.config.get("JWT_SECRET", config.jwt_secret)
    token_logs = app.config.get("TOKEN_ACCOUNT", config.token_logs)

    @app.route("/health", methods=["GET"])
    def health() -> Tuple[Response, int]:
        """Endpoint de diagnóstico de salud del servicio."""
        return jsonify({
            "status": "healthy",
            "service": config.service_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }), 200

    @app.route("/saldo", methods=["GET"])
    def consultar_saldo() -> Tuple[Response, int]:
        """Consulta el saldo de la cuenta autenticada."""
        token = extraer_token_de_cabecera(request.headers.get("Authorization", ""))
        user_id = validar_jwt(token, jwt_secret, logs_url=logs_url)

        if not user_id:
            return jsonify({"error": "No autorizado. Token invalido o expirado"}), 401

        saldo = database.obtener_saldo(user_id, db_url=db_url)
        if saldo is None:
            return jsonify({"error": "Cuenta no encontrada"}), 404

        return jsonify({
            "user_id": user_id,
            "saldo": float(saldo),
        }), 200

    @app.route("/retiro", methods=["POST"])
    def retirar() -> Tuple[Response, int]:
        """Procesa una solicitud de retiro de fondos garantizando consistencia transaccional."""
        token = extraer_token_de_cabecera(request.headers.get("Authorization", ""))
        user_id = validar_jwt(token, jwt_secret, logs_url=logs_url)

        if not user_id:
            enviar_log_silencioso(
                "Intento de retiro con token invalido o expirado",
                "WARN",
                logs_url=logs_url,
                token_logs=token_logs,
            )
            return jsonify({"error": "No autorizado. Token invalido"}), 401

        if not request.is_json:
            return jsonify({"error": "El cuerpo de la solicitud debe ser un JSON válido"}), 400

        datos = request.get_json(silent=True)
        if not isinstance(datos, dict) or "monto" not in datos:
            return jsonify({"error": "Especifique el monto"}), 400

        monto = parsear_monto(datos.get("monto"))
        if monto is None:
            return jsonify({"error": "El monto debe ser un numero estrictamente positivo"}), 400

        exito, resultado = database.procesar_retiro(user_id, monto, db_url=db_url)

        if not exito:
            enviar_log_silencioso(
                f"Fallo de retiro para user_id {user_id}: {resultado}",
                "ERROR",
                logs_url=logs_url,
                token_logs=token_logs,
            )
            return jsonify({"error": str(resultado)}), 400

        nuevo_saldo = float(resultado)
        enviar_log_silencioso(
            f"Retiro exitoso de {float(monto)} para user_id {user_id}. Saldo restante: {nuevo_saldo}",
            "INFO",
            logs_url=logs_url,
            token_logs=token_logs,
        )

        return jsonify({
            "mensaje": "Retiro exitoso",
            "monto_retirado": float(monto),
            "nuevo_saldo": nuevo_saldo,
        }), 200

    @app.route("/transferir", methods=["POST"])
    def transferir() -> Tuple[Response, int]:
        """Ejecuta una transferencia intercuentas atómica libre de interbloqueos."""
        token = extraer_token_de_cabecera(request.headers.get("Authorization", ""))
        emisor_id = validar_jwt(token, jwt_secret, logs_url=logs_url)

        if not emisor_id:
            enviar_log_silencioso(
                "Intento de transferencia no autorizada",
                "WARN",
                logs_url=logs_url,
                token_logs=token_logs,
            )
            return jsonify({"error": "No autorizado"}), 401

        if not request.is_json:
            return jsonify({"error": "El cuerpo de la solicitud debe ser un JSON válido"}), 400

        datos = request.get_json(silent=True)
        if not isinstance(datos, dict):
            return jsonify({"error": "Cuerpo de solicitud invalido"}), 400

        receptor_raw = datos.get("receptor_id")
        monto_raw = datos.get("monto")

        if receptor_raw is None or monto_raw is None:
            return jsonify({"error": "Debe especificar receptor_id y monto"}), 400

        try:
            receptor_id = int(receptor_raw)
            if receptor_id <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({"error": "El receptor_id debe ser un entero positivo valido"}), 400

        monto = parsear_monto(monto_raw)
        if monto is None:
            return jsonify({"error": "El monto debe ser un numero estrictamente positivo"}), 400

        exito, mensaje = database.ejecutar_transferencia(
            emisor_id, receptor_id, monto, db_url=db_url
        )

        if not exito:
            enviar_log_silencioso(
                f"Fallo de transferencia de {emisor_id} a {receptor_id}: {mensaje}",
                "ERROR",
                logs_url=logs_url,
                token_logs=token_logs,
            )
            return jsonify({"error": mensaje}), 400

        enviar_log_silencioso(
            f"Transferencia: {emisor_id} envio {float(monto)} a {receptor_id}",
            "INFO",
            logs_url=logs_url,
            token_logs=token_logs,
        )

        return jsonify({
            "mensaje": mensaje,
            "monto": float(monto),
        }), 200

    return app


app = create_app()

if __name__ == "__main__":
    database.inicializar_db()
    app.run(host=config.host, port=config.port, debug=False)