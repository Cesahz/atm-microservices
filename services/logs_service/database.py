import os
import psycopg2

#leer variables de entorno inyectada por docker
DB_URL = os.environ.get("DB_LOGS_URL", "postgresql://admin:password@db_logs:5432/logs_db") 

def inicializar_db():
    """Crea la tabla si no existe al arrancar el contenedor"""
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
            conn.commit()

#insertar varios logs a la vez
def insertar_logs(logs_a_insertar):
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.executemany('''
                INSERT INTO logs (service, severity, message, timestamp, received_at)
                VALUES (%s, %s, %s, %s, %s)
            ''', logs_a_insertar)
            conn.commit()
