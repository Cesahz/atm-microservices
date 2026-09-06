#importar tipos y utilidades de precision numerica
from decimal import Decimal, InvalidOperation
#importar manejo de fechas y tiempos
from datetime import datetime, timezone
#importar anotaciones de tipo estrictas
from typing import Any, Dict, Optional, Tuple
#importar utilidades criptograficas jwt
import jwt
#importar cliente de peticiones http
import requests
#importar componentes del framework web flask
from flask import Flask, jsonify, request, Response

#importar configuracion interna y capa de persistencia
try:
    from .config import config
    from . import database
except ImportError:
    from config import config
    import database

#enviar evento de auditoria a logs_service de forma tolerante a fallos
def enviar_log_silencioso(
    mensaje: str,
    severidad: str = "INFO",
    logs_url: Optional[str] = None,
    token_logs: Optional[str] = None,
) -> None:
    #construir payload estructurado para telemetria
    url = logs_url or config.logs_url
    token = token_logs or config.token_logs
    log_data: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": config.service_name,
        "severity": severidad,
        "message": mensaje,
    }
    #intentar envio http con timeout defensivo
    try:
        requests.post(
            url,
            json=log_data,
            headers={"Authorization": f"Token {token}"},
            timeout=2.0,
        )
    except requests.exceptions.RequestException:
        pass


#extraer token bearer de la cabecera authorization
def extraer_token_de_cabecera(cabecera_auth: str) -> Optional[str]:
    #validar presencia de cabecera
    if not cabecera_auth:
        return None
    #dividir cabecera por espacios en blanco
    partes = cabecera_auth.strip().split()
    #verificar formato bearer con dos partes
    if len(partes) == 2 and partes[0].lower() == "bearer":
        return partes[1]
    #admitir token plano si solo viene una cadena
    if len(partes) == 1:
        return partes[0]
    return None


#validar firma y expiracion del token jwt
def validar_jwt(token: str, secret_key: str, logs_url: Optional[str] = None) -> Optional[int]:
    #retornar vacio si no se envio token
    if not token:
        return None
    #intentar decodificacion y verificacion de claims
    try:
        data = jwt.decode(
            token,
            secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "user_id"]},
        )
        return int(data["user_id"])
    #capturar expiracion del token y reportar
    except jwt.ExpiredSignatureError:
        enviar_log_silencioso("Token expirado presentado en account_service", "WARN", logs_url=logs_url)
        return None
    #capturar firma invalida o manipulacion
    except (jwt.InvalidTokenError, ValueError, KeyError):
        enviar_log_silencioso("Token invalido presentado en account_service", "ERROR", logs_url=logs_url)
        return None


#parsear y validar monto numerico como decimal positivo
def parsear_monto(valor: Any) -> Optional[Decimal]:
    #descartar valores nulos
    if valor is None:
        return None
    #intentar conversion exacta a tipo decimal
    try:
        monto = Decimal(str(valor).strip())
        #validar que no sea nan infinito o menor igual a cero
        if monto.is_nan() or monto.is_infinite() or monto <= Decimal(0):
            return None
        return monto
    except (InvalidOperation, ValueError, TypeError):
        return None


#definir fabrica de aplicacion flask para operaciones contables
def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    #instanciar app flask
    app = Flask(__name__)

    #sobreescribir configuraciones si es entorno de pruebas
    if test_config:
        app.config.update(test_config)

    #resolver variables de entorno y secretos
    db_url = app.config.get("DATABASE_URL", config.database_url)
    logs_url = app.config.get("LOGS_URL", config.logs_url)
    jwt_secret = app.config.get("JWT_SECRET", config.jwt_secret)
    token_logs = app.config.get("TOKEN_ACCOUNT", config.token_logs)

    #definir endpoint de salud del microservicio
    @app.route("/health", methods=["GET"])
    def health() -> Tuple[Response, int]:
        #retornar estado exitoso y metadata
        return jsonify({
            "status": "healthy",
            "service": config.service_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }), 200

    #definir endpoint para consultar saldo de la cuenta autenticada
    @app.route("/saldo", methods=["GET"])
    def consultar_saldo() -> Tuple[Response, int]:
        #extraer y verificar token jwt
        token = extraer_token_de_cabecera(request.headers.get("Authorization", ""))
        user_id = validar_jwt(token, jwt_secret, logs_url=logs_url)

        #rechazar si no esta autorizado
        if not user_id:
            return jsonify({"error": "No autorizado. Token invalido o expirado"}), 401

        #consultar saldo en la base de datos
        saldo = database.obtener_saldo(user_id, db_url=db_url)
        if saldo is None:
            return jsonify({"error": "Cuenta no encontrada"}), 404

        #retornar saldo formateado
        return jsonify({
            "user_id": user_id,
            "saldo": float(saldo),
        }), 200

    #definir endpoint para procesar retiro de efectivo
    @app.route("/retiro", methods=["POST"])
    def retirar() -> Tuple[Response, int]:
        #extraer y verificar credencial bearer
        token = extraer_token_de_cabecera(request.headers.get("Authorization", ""))
        user_id = validar_jwt(token, jwt_secret, logs_url=logs_url)

        #rechazar solicitud no autenticada
        if not user_id:
            enviar_log_silencioso(
                "Intento de retiro con token invalido o expirado",
                "WARN",
                logs_url=logs_url,
                token_logs=token_logs,
            )
            return jsonify({"error": "No autorizado. Token invalido"}), 401

        #verificar que la peticion contenga json
        if not request.is_json:
            return jsonify({"error": "El cuerpo de la solicitud debe ser un JSON válido"}), 400

        #extraer carga util del request
        datos = request.get_json(silent=True)
        if not isinstance(datos, dict) or "monto" not in datos:
            return jsonify({"error": "Especifique el monto"}), 400

        #validar monto numerico positivo
        monto = parsear_monto(datos.get("monto"))
        if monto is None:
            return jsonify({"error": "El monto debe ser un numero estrictamente positivo"}), 400

        #ejecutar logica de retiro transaccional
        exito, resultado = database.procesar_retiro(user_id, monto, db_url=db_url)

        #manejar caso de fondos insuficientes o fallo
        if not exito:
            enviar_log_silencioso(
                f"Fallo de retiro para user_id {user_id}: {resultado}",
                "ERROR",
                logs_url=logs_url,
                token_logs=token_logs,
            )
            return jsonify({"error": str(resultado)}), 400

        #notificar evento de retiro exitoso en logs
        nuevo_saldo = float(resultado)
        enviar_log_silencioso(
            f"Retiro exitoso de {float(monto)} para user_id {user_id}. Saldo restante: {nuevo_saldo}",
            "INFO",
            logs_url=logs_url,
            token_logs=token_logs,
        )

        #retornar confirmacion contable
        return jsonify({
            "mensaje": "Retiro exitoso",
            "monto_retirado": float(monto),
            "nuevo_saldo": nuevo_saldo,
        }), 200

    #definir endpoint para transferir fondos entre cuentas
    @app.route("/transferir", methods=["POST"])
    def transferir() -> Tuple[Response, int]:
        #extraer y verificar token del emisor
        token = extraer_token_de_cabecera(request.headers.get("Authorization", ""))
        emisor_id = validar_jwt(token, jwt_secret, logs_url=logs_url)

        #rechazar solicitud no autenticada
        if not emisor_id:
            enviar_log_silencioso(
                "Intento de transferencia no autorizada",
                "WARN",
                logs_url=logs_url,
                token_logs=token_logs,
            )
            return jsonify({"error": "No autorizado"}), 401

        #verificar formato json en la peticion
        if not request.is_json:
            return jsonify({"error": "El cuerpo de la solicitud debe ser un JSON válido"}), 400

        #extraer datos de la transferencia
        datos = request.get_json(silent=True)
        if not isinstance(datos, dict):
            return jsonify({"error": "Cuerpo de solicitud invalido"}), 400

        #obtener campos obligatorios
        receptor_raw = datos.get("receptor_id")
        monto_raw = datos.get("monto")

        if receptor_raw is None or monto_raw is None:
            return jsonify({"error": "Debe especificar receptor_id y monto"}), 400

        #validar identificador entero positivo del receptor
        try:
            receptor_id = int(receptor_raw)
            if receptor_id <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({"error": "El receptor_id debe ser un entero positivo valido"}), 400

        #validar importe a transferir
        monto = parsear_monto(monto_raw)
        if monto is None:
            return jsonify({"error": "El monto debe ser un numero estrictamente positivo"}), 400

        #ejecutar transferencia atomica en base de datos
        exito, mensaje = database.ejecutar_transferencia(
            emisor_id, receptor_id, monto, db_url=db_url
        )

        #reportar fallo en la transferencia
        if not exito:
            enviar_log_silencioso(
                f"Fallo de transferencia de {emisor_id} a {receptor_id}: {mensaje}",
                "ERROR",
                logs_url=logs_url,
                token_logs=token_logs,
            )
            return jsonify({"error": mensaje}), 400

        #notificar transferencia completada
        enviar_log_silencioso(
            f"Transferencia: {emisor_id} envio {float(monto)} a {receptor_id}",
            "INFO",
            logs_url=logs_url,
            token_logs=token_logs,
        )

        #retornar resultado positivo
        return jsonify({
            "mensaje": mensaje,
            "monto": float(monto),
        }), 200

    return app


#instanciar servidor para ejecucion directa
app = create_app()

#arrancar servicio si es modulo principal
if __name__ == "__main__":
    database.inicializar_db()
    app.run(host=config.host, port=config.port, debug=False)