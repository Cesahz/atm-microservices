import os
import jwt
import requests
from dotenv import load_dotenv 
from datetime import datetime, timezone
from flask import Flask, request, jsonify
import database

load_dotenv() #cargar variables de entorno desde .env
#crear el objeto flask
app = Flask(__name__)

#variables globales
LOGS_URL = os.environ.get("LOGS_URL", "http://logs_service:5000/logs")
SECRET_KEY = os.environ.get("JWT_SECRET", "clave_de_emergencia")
TOKEN_LOGS = os.environ.get("TOKEN_LOGS_ACCOUNT", "TOKEN-DEFAULT")


#funcion para enviar logs con serverridad INFO por defecto
def enviar_log_silencioso(mensaje, severidad="INFO"):
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "atm-account-service",
        "severity": severidad,
        "message": mensaje
    }
    try:
        requests.post(LOGS_URL, json=log_data, headers={"Authorization": f"Token {TOKEN_LOGS}"}, timeout=2)
    except:
        pass

#funcion para validar el token JWT que manda el servicio auth
def validar_jwt(token):
    #intentar decodificar el token con la clave secreta
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return data["user_id"]
    
    #si el token expira
    except jwt.ExpiredSignatureError:
        enviar_log_silencioso("Token expirado", "WARN")
        return None
    
    #si el token es invalido
    except jwt.InvalidTokenError:
        enviar_log_silencioso("Token invalido/manipulado", "ERROR")
        return None


#endpoint para retirar dinero
@app.route("/retiro", methods=["POST"])
def retirar():
    #extraer y limpiar el token del header
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "") if "Bearer " in auth_header else ""
    
    user_id = validar_jwt(token)
    
    #si no hay token valido, no autorizado
    if not user_id:
        enviar_log_silencioso("Intento de retiro con token invalido o expirado", "WARN")
        return jsonify({"error": "No autorizado. Token invalido"}), 401

    datos = request.get_json()
    if not datos or "monto" not in datos:
        return jsonify({"error": "Especifique el monto"}), 400

    monto = float(datos["monto"])

    #procesar el retiro en la base de datos
    exito, resultado = database.procesar_retiro(user_id, monto)

    #evaluar resultado y reportar
    if not exito:
        enviar_log_silencioso(f"Fallo de retiro para user_id {user_id}: {resultado}", "ERROR")
        return jsonify({"error": resultado}), 400

    enviar_log_silencioso(f"Retiro exitoso de {monto} para user_id {user_id}. Saldo restante: {resultado}")
    return jsonify({
        "mensaje": "Retiro exitoso", 
        "monto_retirado": monto,
        "nuevo_saldo": float(resultado)
    }), 200


@app.route("/transferir", methods=["POST"])
def transferir():
    #extraer y limpiar el token del header
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "") if "Bearer " in auth_header else ""
    emisor_id = validar_jwt(token)
    
    #si no hay token valido, no autorizado
    if not emisor_id: 
        return jsonify({"error": "No autorizado"}), 401
    
    #recibe los datos y almacena
    datos = request.get_json()
    receptor_id = datos.get("receptor_id")
    monto = float(datos.get("monto", 0))

    #intentar transferencia y evaluar resultado
    exito, mensaje = database.ejecutar_transferencia(emisor_id, receptor_id, monto)
    if not exito: 
        return jsonify({"error": mensaje}), 400

    #loguear la transferencia
    enviar_log_silencioso(f"Transferencia: {emisor_id} envio {monto} a {receptor_id}")
    return jsonify({"mensaje": mensaje, "monto": monto}), 200


if __name__ == "__main__":
    database.inicializar_db()
    app.run(host="0.0.0.0", port=5002, debug=True)