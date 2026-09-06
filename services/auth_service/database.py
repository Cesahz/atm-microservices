import os
import psycopg2

#verificar en la variable de entorno
DB_URL = os.environ.get("DATABASE_URL", "postgresql://admin:password@db_auth:5432/auth_db")


#se inicia la base de datos con usuarios predefinidos
def inicializar_db():
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute('CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, pin TEXT NOT NULL)')
            usuarios = [
                ('Cesar Espinola', '2701'),
                ('Jose Toledo', '1111'),
                ('Penguin Academy', '0000')
            ]
            cur.executemany("INSERT INTO usuarios (username, pin) VALUES (%s, %s) ON CONFLICT DO NOTHING", usuarios)
        conn.commit()

#funcion que devuelve un usuario y  si el user y pin son correctos, sino none
def verificar_credenciales(username, pin):
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM usuarios WHERE username = %s AND pin = %s", (username, pin))
            return cur.fetchone()
