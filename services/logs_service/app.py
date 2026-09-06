#importar utilidades de fechas y zonas horarias
from datetime import datetime, timezone
#importar anotaciones de tipado estricto
from typing import Any, Dict, List, Optional, Tuple
#importar componentes del framework flask
from flask import Flask, jsonify, request, Response

#importar configuracion interna capa de datos y tokens
try:
    from .config import config
    from . import database
    from .tokens import validar_token_servicio
except ImportError:
    from config import config
    import database
    from tokens import validar_token_servicio

#definir conjunto inmutable de severidades admitidas
SEVERIDADES_VALIDAS = {"INFO", "DEBUG", "WARN", "ERROR", "FATAL"}

#extraer y sanitizar token de servicio desde la cabecera
def extraer_token(cabecera_auth: str) -> Optional[str]:
    #descartar cabeceras vacias
    if not cabecera_auth:
        return None
    partes = cabecera_auth.strip().split()
    #identificar prefijo token o bearer
    if len(partes) == 2 and partes[0].lower() in {"token", "bearer"}:
        return partes[1]
    #admitir token plano
    if len(partes) == 1:
        return partes[0]
    return None

#definir fabrica de aplicacion flask para servicio de logs
def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    #instanciar app flask
    app = Flask(__name__)

    #aplicar configuracion de prueba si se proporciona
    if test_config:
        app.config.update(test_config)

    #resolver cadena de conexion
    db_url = app.config.get("DATABASE_URL", config.database_url)

    #verificar autorizacion con token estatico registrado
    def verificar_autorizacion() -> Tuple[bool, Optional[str]]:
        auth_header = request.headers.get("Authorization", "")
        token = extraer_token(auth_header)
        servicio = validar_token_servicio(token)
        if not servicio:
            return False, None
        return True, servicio

    #definir ruta de comprobacion de salud
    @app.route("/health", methods=["GET"])
    def health() -> Tuple[Response, int]:
        return jsonify({
            "status": "healthy",
            "service": config.service_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }), 200

    #definir ruta para recepcion e insercion de logs
    @app.route("/logs", methods=["POST"])
    def recibir_logs() -> Tuple[Response, int]:
        #validar credencial de servicio autorizado
        autorizado, _ = verificar_autorizacion()
        if not autorizado:
            return jsonify({"error": "No autorizado. Token de servicio ausente o invalido"}), 401

        #verificar que la solicitud contenga formato json
        if not request.is_json:
            return jsonify({"error": "El cuerpo de la solicitud debe ser un JSON válido"}), 400

        #extraer datos de la solicitud
        datos = request.get_json(silent=True)
        if datos is None:
            return jsonify({"error": "Payload JSON malformado"}), 400

        #normalizar objeto unico a lista para procesamiento unificado
        lista_logs = [datos] if isinstance(datos, dict) else datos
        if not isinstance(lista_logs, list) or len(lista_logs) == 0:
            return jsonify({"error": "Se requiere un objeto o una lista no vacia de logs"}), 400

        logs_a_insertar: List[Tuple[str, str, str, str, str]] = []
        recibido_en = datetime.now(timezone.utc).isoformat()

        #validar cada elemento de la lista
        for idx, item in enumerate(lista_logs):
            if not isinstance(item, dict):
                return jsonify({"error": f"El elemento en la posicion {idx} no es un objeto valido"}), 400

            servicio = item.get("service")
            severidad = str(item.get("severity", "INFO")).upper().strip()
            mensaje = item.get("message")
            ts = item.get("timestamp") or datetime.now(timezone.utc).isoformat()

            #comprobar campos mandatorios
            if not servicio or not mensaje:
                return jsonify({
                    "error": "Campos obligatorios faltantes ('service' y 'message')",
                    "elemento_invalido": idx,
                }), 400

            #validar nivel de severidad permitido
            if severidad not in SEVERIDADES_VALIDAS:
                return jsonify({
                    "error": f"Severidad '{severidad}' no valida. Opciones: {sorted(list(SEVERIDADES_VALIDAS))}",
                    "elemento_invalido": idx,
                }), 400

            #acumular tupla para insercion masiva
            logs_a_insertar.append((
                str(servicio).strip(),
                severidad,
                str(mensaje).strip(),
                str(ts),
                recibido_en,
            ))

        #persistir registros en base de datos
        total_insertados = database.insertar_logs(logs_a_insertar, db_url=db_url)
        return jsonify({
            "status": "logs guardados",
            "insertados": total_insertados,
        }), 201

    #definir ruta para consulta de logs con filtros parametrizados
    @app.route("/logs", methods=["GET"])
    def consultar_logs() -> Tuple[Response, int]:
        #validar autorizacion
        autorizado, _ = verificar_autorizacion()
        if not autorizado:
            return jsonify({"error": "No autorizado. Token de servicio ausente o invalido"}), 401

        #extraer parametros de consulta
        filtros: Dict[str, Any] = {
            "service": request.args.get("service"),
            "severity": request.args.get("severity"),
            "timestamp_start": request.args.get("timestamp_start"),
            "timestamp_end": request.args.get("timestamp_end"),
            "limit": request.args.get("limit", 100),
            "offset": request.args.get("offset", 0),
        }

        #ejecutar consulta filtrada
        logs = database.consultar_logs(filtros, db_url=db_url)
        return jsonify({
            "total": len(logs),
            "logs": logs,
        }), 200

    #definir ruta para generacion de estadisticas agrupadas
    @app.route("/stats", methods=["GET"])
    def obtener_stats() -> Tuple[Response, int]:
        #validar autorizacion
        autorizado, _ = verificar_autorizacion()
        if not autorizado:
            return jsonify({"error": "No autorizado. Token de servicio ausente o invalido"}), 401

        #obtener metricas agregadas
        estadisticas = database.obtener_estadisticas(db_url=db_url)
        return jsonify(estadisticas), 200

    return app

#instanciar servidor de logs
app = create_app()

#arrancar servidor si es script principal
if __name__ == "__main__":
    database.inicializar_db()
    app.run(host=config.host, port=config.port, debug=False)