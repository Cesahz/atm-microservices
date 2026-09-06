from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from flask import Flask, jsonify, request, Response

from config import config
import database
from tokens import validar_token_servicio

SEVERIDADES_VALIDAS = {"INFO", "DEBUG", "WARN", "ERROR", "FATAL"}

def extraer_token(cabecera_auth: str) -> Optional[str]:
    """Extrae y normaliza el token estático desde la cabecera Authorization."""
    if not cabecera_auth:
        return None
    partes = cabecera_auth.strip().split()
    if len(partes) == 2 and partes[0].lower() in {"token", "bearer"}:
        return partes[1]
    if len(partes) == 1:
        return partes[0]
    return None

def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """Fábrica de aplicaciones Flask para el servicio de registro y auditoría."""
    app = Flask(__name__)

    if test_config:
        app.config.update(test_config)

    db_url = app.config.get("DATABASE_URL", config.database_url)

    def verificar_autorizacion() -> Tuple[bool, Optional[str]]:
        auth_header = request.headers.get("Authorization", "")
        token = extraer_token(auth_header)
        servicio = validar_token_servicio(token)
        if not servicio:
            return False, None
        return True, servicio

    @app.route("/health", methods=["GET"])
    def health() -> Tuple[Response, int]:
        """Endpoint de verificación de operatividad del servicio de logs."""
        return jsonify({
            "status": "healthy",
            "service": config.service_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }), 200

    @app.route("/logs", methods=["POST"])
    def recibir_logs() -> Tuple[Response, int]:
        """
        Recibe uno o varios eventos de auditoría y los persiste en la base de datos.
        """
        autorizado, _ = verificar_autorizacion()
        if not autorizado:
            return jsonify({"error": "No autorizado. Token de servicio ausente o invalido"}), 401

        if not request.is_json:
            return jsonify({"error": "El cuerpo de la solicitud debe ser un JSON válido"}), 400

        datos = request.get_json(silent=True)
        if datos is None:
            return jsonify({"error": "Payload JSON malformado"}), 400

        lista_logs = [datos] if isinstance(datos, dict) else datos
        if not isinstance(lista_logs, list) or len(lista_logs) == 0:
            return jsonify({"error": "Se requiere un objeto o una lista no vacia de logs"}), 400

        logs_a_insertar: List[Tuple[str, str, str, str, str]] = []
        recibido_en = datetime.now(timezone.utc).isoformat()

        for idx, item in enumerate(lista_logs):
            if not isinstance(item, dict):
                return jsonify({"error": f"El elemento en la posicion {idx} no es un objeto valido"}), 400

            servicio = item.get("service")
            severidad = str(item.get("severity", "INFO")).upper().strip()
            mensaje = item.get("message")
            ts = item.get("timestamp") or datetime.now(timezone.utc).isoformat()

            if not servicio or not mensaje:
                return jsonify({
                    "error": "Campos obligatorios faltantes ('service' y 'message')",
                    "elemento_invalido": idx,
                }), 400

            if severidad not in SEVERIDADES_VALIDAS:
                return jsonify({
                    "error": f"Severidad '{severidad}' no valida. Opciones: {sorted(list(SEVERIDADES_VALIDAS))}",
                    "elemento_invalido": idx,
                }), 400

            logs_a_insertar.append((
                str(servicio).strip(),
                severidad,
                str(mensaje).strip(),
                str(ts),
                recibido_en,
            ))

        total_insertados = database.insertar_logs(logs_a_insertar, db_url=db_url)
        return jsonify({
            "status": "logs guardados",
            "insertados": total_insertados,
        }), 201

    @app.route("/logs", methods=["GET"])
    def consultar_logs() -> Tuple[Response, int]:
        """
        Permite consultar eventos de log con filtros por servicio, severidad y rango de fechas.
        """
        autorizado, _ = verificar_autorizacion()
        if not autorizado:
            return jsonify({"error": "No autorizado. Token de servicio ausente o invalido"}), 401

        filtros: Dict[str, Any] = {
            "service": request.args.get("service"),
            "severity": request.args.get("severity"),
            "timestamp_start": request.args.get("timestamp_start"),
            "timestamp_end": request.args.get("timestamp_end"),
            "limit": request.args.get("limit", 100),
            "offset": request.args.get("offset", 0),
        }

        logs = database.consultar_logs(filtros, db_url=db_url)
        return jsonify({
            "total": len(logs),
            "logs": logs,
        }), 200

    @app.route("/stats", methods=["GET"])
    def obtener_stats() -> Tuple[Response, int]:
        """
        Retorna métricas cuantitativas agrupadas por servicio y severidad.
        """
        autorizado, _ = verificar_autorizacion()
        if not autorizado:
            return jsonify({"error": "No autorizado. Token de servicio ausente o invalido"}), 401

        estadisticas = database.obtener_estadisticas(db_url=db_url)
        return jsonify(estadisticas), 200

    return app


app = create_app()

if __name__ == "__main__":
    database.inicializar_db()
    app.run(host=config.host, port=config.port, debug=False)