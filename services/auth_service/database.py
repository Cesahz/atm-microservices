import os
import sqlite3
import time
from typing import Any, List, Optional, Tuple, Union
import psycopg2
from config import config
from security import hash_pin, verify_pin

DEFAULT_USERS: List[Tuple[str, str]] = [
    ("Cesar Espinola", "2701"),
    ("Jose Toledo", "1111"),
    ("Penguin Academy", "0000"),
]

def get_connection(db_url: Optional[str] = None) -> Union[psycopg2.extensions.connection, sqlite3.Connection]:
    """Obtiene una conexión a la base de datos configurada (PostgreSQL o SQLite)."""
    target_url = db_url or config.database_url

    if target_url.startswith("sqlite"):
        # Extraer ruta o memoria
        path = target_url.replace("sqlite:///", "").replace("sqlite://", "")
        conn = sqlite3.connect(path or ":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    return psycopg2.connect(target_url)

def connect_with_retry(max_retries: int = 5, delay: float = 1.5, db_url: Optional[str] = None) -> Any:
    """Intenta conectar con la base de datos aplicando reintentos exponenciales."""
    last_err: Optional[Exception] = None
    current_delay = delay
    for attempt in range(1, max_retries + 1):
        try:
            conn = get_connection(db_url)
            return conn
        except Exception as exc:
            last_err = exc
            time.sleep(current_delay)
            current_delay *= 1.5
    raise ConnectionError(f"No fue posible conectar a la base de datos tras {max_retries} intentos: {last_err}")

def inicializar_db(db_url: Optional[str] = None) -> None:
    """Inicializa el esquema de usuarios y realiza el sembrado de datos con contraseñas seguras."""
    target_url = db_url or config.database_url
    is_sqlite = target_url.startswith("sqlite")

    conn = connect_with_retry(db_url=target_url)
    try:
        with conn:
            cur = conn.cursor()
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
                for username, raw_pin in DEFAULT_USERS:
                    hashed = hash_pin(raw_pin)
                    cur.execute(
                        "INSERT OR IGNORE INTO usuarios (username, pin) VALUES (?, ?)",
                        (username, hashed),
                    )
            else:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS usuarios (
                        id SERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        pin TEXT NOT NULL
                    )
                    """
                )
                for username, raw_pin in DEFAULT_USERS:
                    hashed = hash_pin(raw_pin)
                    cur.execute(
                        "INSERT INTO usuarios (username, pin) VALUES (%s, %s) ON CONFLICT (username) DO NOTHING",
                        (username, hashed),
                    )
    finally:
        conn.close()

def verificar_credenciales(username: str, pin: str, db_url: Optional[str] = None) -> Optional[Tuple[int, str]]:
    """
    Busca al usuario por nombre y valida el PIN provisto contra su hash criptográfico.
    Retorna una tupla (id, username) si las credenciales son válidas, o None si no coinciden.
    """
    if not username or not pin:
        return None

    target_url = db_url or config.database_url
    is_sqlite = target_url.startswith("sqlite")
    conn = get_connection(target_url)
    try:
        cur = conn.cursor()
        if is_sqlite:
            cur.execute("SELECT id, pin, username FROM usuarios WHERE username = ?", (username,))
            row = cur.fetchone()
        else:
            cur.execute("SELECT id, pin, username FROM usuarios WHERE username = %s", (username,))
            row = cur.fetchone()

        if not row:
            return None

        user_id = row[0]
        stored_hash = row[1]
        user_name = row[2]

        if verify_pin(pin, stored_hash):
            return (int(user_id), str(user_name))
        return None
    finally:
        conn.close()
