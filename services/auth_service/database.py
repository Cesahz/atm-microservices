#importar modulos de base de datos y control de flujo
import os
import sqlite3
import time
from typing import Any, List, Optional, Tuple, Union
import psycopg2

#importar configuracion local y metodos criptograficos
try:
    from .config import config
    from .security import hash_pin, verify_pin
except ImportError:
    from config import config
    from security import hash_pin, verify_pin

#definir usuarios semilla para el entorno de pruebas y arranque
DEFAULT_USERS: List[Tuple[str, str]] = [
    ("Cesar Espinola", "2701"),
    ("Jose Toledo", "1111"),
    ("Penguin Academy", "0000"),
]

#obtener conexion activa segun motor postgresql o sqlite
def get_connection(db_url: Optional[str] = None) -> Union[psycopg2.extensions.connection, sqlite3.Connection]:
    target_url = db_url or config.database_url

    #verificar si se utiliza base embebida sqlite para testing
    if target_url.startswith("sqlite"):
        #extraer ruta de archivo o memoria volatil
        path = target_url.replace("sqlite:///", "").replace("sqlite://", "")
        conn = sqlite3.connect(path or ":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    #conectar con motor relacional postgresql
    return psycopg2.connect(target_url)

#reintentar conexion con retroceso exponencial durante el arranque
def connect_with_retry(max_retries: int = 5, delay: float = 1.5, db_url: Optional[str] = None) -> Any:
    last_err: Optional[Exception] = None
    current_delay = delay
    #ejecutar bucle de reintentos
    for attempt in range(1, max_retries + 1):
        try:
            conn = get_connection(db_url)
            return conn
        except Exception as exc:
            last_err = exc
            time.sleep(current_delay)
            current_delay *= 1.5
    #lanzar excepcion si expiran los intentos
    raise ConnectionError(f"No fue posible conectar a la base de datos tras {max_retries} intentos: {last_err}")

#inicializar esquema de usuarios y sembrar datos con hash seguro
def inicializar_db(db_url: Optional[str] = None) -> None:
    target_url = db_url or config.database_url
    is_sqlite = target_url.startswith("sqlite")

    #abrir conexion con reintentos
    conn = connect_with_retry(db_url=target_url)
    try:
        with conn:
            cur = conn.cursor()
            #crear tabla en sqlite si aplica
            if is_sqlite:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        pin TEXT NOT NULL
                    )
                    """
                )
                #insertar usuarios semilla con hash pbkdf2
                for username, raw_pin in DEFAULT_USERS:
                    hashed = hash_pin(raw_pin)
                    cur.execute(
                        "INSERT OR IGNORE INTO usuarios (username, pin) VALUES (?, ?)",
                        (username, hashed),
                    )
            else:
                #crear tabla en postgresql
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS usuarios (
                        id SERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        pin TEXT NOT NULL
                    )
                    """
                )
                #insertar usuarios semilla en postgresql
                for username, raw_pin in DEFAULT_USERS:
                    hashed = hash_pin(raw_pin)
                    cur.execute(
                        "INSERT INTO usuarios (username, pin) VALUES (%s, %s) ON CONFLICT (username) DO NOTHING",
                        (username, hashed),
                    )
    finally:
        #asegurar cierre de conexion
        conn.close()

#verificar credenciales consultando base de datos y validando hash
def verificar_credenciales(username: str, pin: str, db_url: Optional[str] = None) -> Optional[Tuple[int, str]]:
    #descartar credenciales incompletas
    if not username or not pin:
        return None

    target_url = db_url or config.database_url
    is_sqlite = target_url.startswith("sqlite")
    conn = get_connection(target_url)
    try:
        cur = conn.cursor()
        #ejecutar consulta parametrizada segura
        if is_sqlite:
            cur.execute("SELECT id, pin, username FROM usuarios WHERE username = ?", (username,))
            row = cur.fetchone()
        else:
            cur.execute("SELECT id, pin, username FROM usuarios WHERE username = %s", (username,))
            row = cur.fetchone()

        #retornar vacio si el usuario no existe
        if not row:
            return None

        user_id = row[0]
        stored_hash = row[1]
        user_name = row[2]

        #validar pin en tiempo constante
        if verify_pin(pin, stored_hash):
            return (int(user_id), str(user_name))
        return None
    finally:
        #cerrar conexion
        conn.close()
