import psycopg2
import os
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from tokens import TOKENS_VALIDOS

#se crea el objeto principal del proyecto
#name le da el contexto a flask de la ubicacion del modulo
app = Flask(__name__)
DB_URL = os.environ.get("DATABASE_URL", "postgresql://usuario:password@localhost:5432/logs_db")

#crear tabla si no existe
def inicializar_db():
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS logs (
                        id SERIAL PRIMARY KEY, 
                        service TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        received_at TEXT NOT NULL
                    )
                ''')

#extraer y validar  los tokens
def verificar_token():
    partes = request.headers.get("Authorization", "").split(" ")
    if len(partes) == 2 and partes[0] == "Token":
        return TOKENS_VALIDOS.get(partes[1])
    return None

#recibir uno o varios logs
@app.route("/logs", methods=["POST"])
def recibir_logs():
    #si verificar_token es none, se cumple la condicion y retorna el error
    if not verificar_token():
        return jsonify({"error": "Quien sos, bro?"}), 401

    #almacenar el body de la solicitud en formato json
    datos = request.get_json()
    if not datos:
        return jsonify({"error": "JSON invalido"}), 400

    #si viene un solo objeto lo convierte a lista para que el loop de abajo funcione igual
    if isinstance(datos, dict): datos = [datos]

    #los logs que se insertan a la db
    logs_a_insertar = []
    
    #momento en que se recibio
    recibido_en = datetime.now(timezone.utc).isoformat()

    for log in datos:
        
        #validar campos obligatorios por cada log
        if not all(k in log for k in ("timestamp", "service", "severity", "message")):
            return jsonify({"error": "Campos faltantes", "log": log}), 400
      
        #validar la severidad permitida
        if log["severity"] not in {"INFO", "DEBUG", "WARN", "ERROR", "FATAL"}:
            return jsonify({"error": "Severidad invalida"}), 400

        #si el log esta bien, se agrega en la lista de logs para insertar al db
        logs_a_insertar.append((
            log["service"], log["severity"],
            log["message"], log["timestamp"], recibido_en
        ))

    #insertar los logs en un solo proceso
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.executemany('''
                INSERT INTO logs (service, severity, message, timestamp, received_at)
                VALUES (%s, %s, %s, %s, %s)
            ''', logs_a_insertar)
            conn.commit()

    #si todo salio bien, retorna el estado ok y la cantidad de insertados
    return jsonify({"status": "ok", "insertados": len(logs_a_insertar)}), 201


#consultar logs con filtros opcionales por servicio, severidad y fecha
@app.route("/logs", methods=["GET"])
def consultar_logs():
    if not verificar_token(): 
        return jsonify({"error": "Quien sos, bro?"}), 401

    #construir las consultas que varia dependiendo segun los filtros
    query = "SELECT * FROM logs WHERE 1=1"
    params = []
    args = request.args

    #por cada filtro que se cumple se modifica la consulta
    if args.get("service"):         query += " AND service = %s";    params.append(args.get("service"))
    if args.get("severity"):        query += " AND severity = %s";   params.append(args.get("severity"))
    if args.get("timestamp_start"): query += " AND timestamp >= %s"; params.append(args.get("timestamp_start"))
    if args.get("timestamp_end"):   query += " AND timestamp <= %s"; params.append(args.get("timestamp_end"))
    
    query += " ORDER BY received_at DESC LIMIT %s"
    params.append(int(args.get("limit", 100)))

    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, tuple(params))
            logs = cur.fetchall()

    return jsonify({"total": len(logs), "logs": logs}), 200

#retornar conteo de logs por servicio y por severidad
@app.route("/stats", methods=["GET"])
def obtener_stats():
    if not verificar_token():
        return jsonify({"error": "Quien sos, bro?"}), 401

    #consultar la cantidad en la database
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            
            cur.execute('SELECT service, COUNT(*) as total FROM logs GROUP BY service')
            por_servicio = {f["service"]: f["total"] for f in cur.fetchall()}
            
            cur.execute('SELECT severity, COUNT(*) as total FROM logs GROUP BY severity')
            por_severidad = {f["severity"]: f["total"] for f in cur.fetchall()}

    return jsonify({"Por_servicio": por_servicio, "Por_severidad": por_severidad}), 200


if __name__ == "__main__":
    inicializar_db()
    print("Penguin Logger corriendo en http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)