import os
import jwt
import psycopg2
import requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_URL = os.environ.get("DATABASE_URL", "postgresql://usuario:password@localhost:5434/operador_db")
LOGS_URL = os.environ.get("LOGS_URL", "http://localhost:5000/logs")
SECRET_KEY = "secreto_del_pinguino_super_seguro" # Debe ser la misma que en auth.py
TOKEN_LOGS = "TOKEN-PAYMENTS-003"

def inicializar_db():
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS cuentas (
                    user_id INTEGER PRIMARY KEY, saldo NUMERIC NOT NULL
                )
            ''')
            # Insertar saldo de prueba para el user_id 1
            cur.execute("INSERT INTO cuentas (user_id, saldo) VALUES (1, 5000000) ON CONFLICT DO NOTHING")
        conn.commit()

def enviar_log(mensaje, severidad="INFO"):
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

def validar_jwt(token):
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return data["user_id"]
    except:
        return None

@app.route("/retiro", methods=["POST"])
def retirar():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user_id = validar_jwt(token)
    
    if not user_id:
        enviar_log("Intento de retiro con token invalido o expirado", "WARN")
        return jsonify({"error": "No autorizado"}), 401

    monto = request.get_json().get("monto", 0)

    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT saldo FROM cuentas WHERE user_id = %s FOR UPDATE", (user_id,))
            resultado = cur.fetchone()
            
            if not resultado or resultado[0] < monto:
                enviar_log(f"Fallo de retiro para user {user_id}. Fondos insuficientes", "ERROR")
                return jsonify({"error": "Fondos insuficientes"}), 400
                
            nuevo_saldo = resultado[0] - monto
            cur.execute("UPDATE cuentas SET saldo = %s WHERE user_id = %s", (nuevo_saldo, user_id))
            conn.commit()

    enviar_log(f"Retiro exitoso de {monto} para user {user_id}. Nuevo saldo: {nuevo_saldo}")
    return jsonify({"mensaje": "Retiro exitoso", "nuevo_saldo": float(nuevo_saldo)}), 200

if __name__ == "__main__":
    inicializar_db()
    app.run(host="0.0.0.0", port=5002)