import os
import jwt
import psycopg2
import requests
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_URL = os.environ.get("DATABASE_URL", "postgresql://usuario:password@localhost:5433/auth_db")
LOGS_URL = os.environ.get("LOGS_URL", "http://localhost:5000/logs")
SECRET_KEY = "secreto_del_pinguino_super_seguro"
TOKEN_LOGS = "TOKEN-AUTH-002"

def inicializar_db():
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, pin TEXT NOT NULL
                )
            ''')
            # Insertar usuario de prueba si no existe
            cur.execute("INSERT INTO usuarios (username, pin) VALUES ('pinguino1', '1234') ON CONFLICT DO NOTHING")
        conn.commit()

def enviar_log(mensaje, severidad="INFO"):
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "atm-auth-service",
        "severity": severidad,
        "message": mensaje
    }
    try:
        requests.post(LOGS_URL, json=log_data, headers={"Authorization": f"Token {TOKEN_LOGS}"}, timeout=2)
    except:
        pass # Tolerancia a fallos: si el server de logs cae, la auth sigue viva

@app.route("/login", methods=["POST"])
def login():
    datos = request.get_json()
    username = datos.get("username")
    pin = datos.get("pin")

    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM usuarios WHERE username = %s AND pin = %s", (username, pin))
            usuario = cur.fetchone()

    if usuario:
        # Generar JWT válido por 15 minutos
        token = jwt.encode({
            "user_id": usuario[0],
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15)
        }, SECRET_KEY, algorithm="HS256")
        
        enviar_log(f"Login exitoso para {username}")
        return jsonify({"token": token}), 200
    else:
        enviar_log(f"Intento fallido para {username}", "WARN")
        return jsonify({"error": "Credenciales invalidas"}), 401

if __name__ == "__main__":
    inicializar_db()
    app.run(host="0.0.0.0", port=5001)