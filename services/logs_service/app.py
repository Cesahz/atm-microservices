import os
from flask import Flask, request, jsonify
from datetime import datetime
from tokens import TOKENS_VALIDOS
import database

#iniciar el objeto flask
app = Flask(__name__)

#endpoint para recibir logs de otros servicios
@app.route("/logs", methods=["POST"])
def recibir_logs():
    #validacion del token
    auth_token = request.headers.get("Authorization", "").replace("Token ", "")
    if auth_token not in TOKENS_VALIDOS:
        return jsonify({"error": "No autorizado"}), 401

    #convertir a lista si es un solo log
    datos = request.get_json()
    if not isinstance(datos, list): datos = [datos]

    logs_procesados = []
    for log in datos:
        logs_procesados.append((
            log.get("service", "unknown"),
            log.get("severity", "INFO"),
            log.get("message", ""),
            log.get("timestamp", datetime.now().isoformat()),
            datetime.now().isoformat()
        ))
    
    #insertar los logs procesados en la base de datos
    database.insertar_logs(logs_procesados)
    return jsonify({"status": "logs guardados"}), 201


if __name__ == "__main__":
    print("Inicializando base de datos de logs...")
    database.inicializar_db()
    print("Servidor de Logs activo en el puerto 5000")
    app.run(host="0.0.0.0", port=5000)