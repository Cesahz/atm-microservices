import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import psycopg2
from psycopg2.extras import RealDictCursor
from config import config

def get_connection(db_url: Optional[str] = None) -> Union[psycopg2.extensions.connection, sqlite3.Connection]:
    """Obtiene una conexión a la base de datos (PostgreSQL o SQLite para pruebas)."""
    target_url = db_url or config.database_url
    if target_url.startswith("sqlite"):
        path = target_url.replace("sqlite:///", "").replace("sqlite://", "")
        conn = sqlite3.connect(path or ":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    return psycopg2.connect(target_url)

def connect_with_retry(max_retries: int = 5, delay: float = 1.5, db_url: Optional[str] = None) -> Any:
    """Intenta conectar con la base de datos aplicando reintentos exponenciales."""
    last_err: Optional[Exception] = None
    current_delay = delay
    for _ in range(1, max_retries + 1):
        try:
            return get_connection(db_url)
        except Exception as exc:
            last_err = exc
            time.sleep(current_delay)
            current_delay *= 1.5
    raise ConnectionError(f"No fue posible conectar a db_logs tras {max_retries} intentos: {last_err}")

def inicializar_db(db_url: Optional[str] = None) -> None:
    """Crea la tabla de logs y sus índices de búsqueda."""
    target_url = db_url or config.database_url
    is_sqlite = target_url.startswith("sqlite")

    conn = connect_with_retry(db_url=target_url)
    try:
        with conn:
            cur = conn.cursor()
            if is_sqlite:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        received_at TEXT NOT NULL
                    )
                    """
                )
            else:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS logs (
                        id SERIAL PRIMARY KEY,
                        service TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        received_at TEXT NOT NULL
                    )
                    """
                )
            # Índices para optimización de consultas y filtros
            cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_service ON logs(service)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_severity ON logs(severity)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_received ON logs(received_at DESC)")
    finally:
        conn.close()

def insertar_logs(
    logs_a_insertar: List[Tuple[str, str, str, str, str]],
    db_url: Optional[str] = None,
) -> int:
    """Inserta una lista de registros de log de forma atómica."""
    if not logs_a_insertar:
        return 0

    target_url = db_url or config.database_url
    is_sqlite = target_url.startswith("sqlite")
    conn = get_connection(target_url)

    try:
        with conn:
            cur = conn.cursor()
            placeholder = "(?, ?, ?, ?, ?)" if is_sqlite else "(%s, %s, %s, %s, %s)"
            query = f"""
                INSERT INTO logs (service, severity, message, timestamp, received_at)
                VALUES {placeholder}
            """
            cur.executemany(query, logs_a_insertar)
            return len(logs_a_insertar)
    finally:
        conn.close()

def consultar_logs(
    filtros: Dict[str, Any],
    db_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Consulta registros de log aplicando filtros parametrizados seguros contra inyección SQL."""
    target_url = db_url or config.database_url
    is_sqlite = target_url.startswith("sqlite")
    conn = get_connection(target_url)

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor) if not is_sqlite else conn.cursor()

        query_parts = ["SELECT id, service, severity, message, timestamp, received_at FROM logs WHERE 1=1"]
        params: List[Any] = []
        p = "?" if is_sqlite else "%s"

        if filtros.get("service"):
            query_parts.append(f"AND service = {p}")
            params.append(filtros["service"])

        if filtros.get("severity"):
            query_parts.append(f"AND severity = {p}")
            params.append(filtros["severity"])

        if filtros.get("timestamp_start"):
            query_parts.append(f"AND timestamp >= {p}")
            params.append(filtros["timestamp_start"])

        if filtros.get("timestamp_end"):
            query_parts.append(f"AND timestamp <= {p}")
            params.append(filtros["timestamp_end"])

        query_parts.append(f"ORDER BY received_at DESC LIMIT {p} OFFSET {p}")
        limit = min(max(int(filtros.get("limit", 100)), 1), 1000)
        offset = max(int(filtros.get("offset", 0)), 0)
        params.extend([limit, offset])

        query = " ".join(query_parts)
        cur.execute(query, tuple(params))

        if is_sqlite:
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        return list(cur.fetchall())
    finally:
        conn.close()

def obtener_estadisticas(db_url: Optional[str] = None) -> Dict[str, Dict[str, int]]:
    """Genera conteos agregados por servicio emisor y nivel de severidad."""
    target_url = db_url or config.database_url
    is_sqlite = target_url.startswith("sqlite")
    conn = get_connection(target_url)

    try:
        cur = conn.cursor()
        cur.execute("SELECT service, COUNT(*) FROM logs GROUP BY service")
        por_servicio: Dict[str, int] = {str(row[0]): int(row[1]) for row in cur.fetchall()}

        cur.execute("SELECT severity, COUNT(*) FROM logs GROUP BY severity")
        por_severidad: Dict[str, int] = {str(row[0]): int(row[1]) for row in cur.fetchall()}

        return {
            "Por_servicio": por_servicio,
            "Por_severidad": por_severidad,
        }
    finally:
        conn.close()
