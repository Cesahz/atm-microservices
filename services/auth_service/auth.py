import os
import jwt
import requests
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify
import database

#iniciar el objeto flask
app = Flask(__name__)

#variables globales
LOGS_URL = os.environ.get("LOGS_URL", "http://logs_service:5000/logs")
SECRET_KEY = os.environ.get("JWT_SECRET", "secreto_del_pinguino_aislado")
TOKEN_LOGS = os.environ.get("TOKEN_AUTH", "TOKEN-AUTH-002") 


def enviar_log_silencioso(mensaje, severidad="INFO"):
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "atm-auth-service",
        "severity": severidad,
        "message": mensaje
    }
    try:
        #si el servicio de logs no responde, sigue sin problemas
        requests.post(LOGS_URL, json=log_data, headers={"Authorization": f"Token {TOKEN_LOGS}"}, timeout=2)
    except:
        pass 

#endpoint para login, recibe username y pin, devuelve token JWT si es correcto
@app.route("/login", methods=["POST"])
def login():
    datos = request.get_json()
    if not datos or not "username" in datos or not "pin" in datos:
        return jsonify({"error": "Faltan credenciales"}), 400

    username = datos["username"]
    pin = datos["pin"]

    usuario = database.verificar_credenciales(username, pin)

    #verificar si el usuario existe y el pin es correcto
    if usuario:
        #si existe, genera un token JWT con el user_id que expira en 15 minutos
        token = jwt.encode(
            {
            "user_id": usuario[0],
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15)
            },  #carga del token
            SECRET_KEY, #clave secreta para firmar el token
            algorithm="HS256") #tipo de encriptacion
        
        enviar_log_silencioso(f"Login exitoso para usuario: {username}")
        return jsonify({"token": token}), 200
    else:
        enviar_log_silencioso(f"Intento de acceso denegado: {username}", "WARN")
        return jsonify({"error": "Credenciales invalidas"}), 401

if __name__ == "__main__":
    database.inicializar_db()
    app.run(host="0.0.0.0", port=5001, debug=True)