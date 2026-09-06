#importar modulos de persistencia relacional
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import psycopg2
from psycopg2.extras import RealDictCursor

#importar configuracion interna de logs
try:
    from .config import config
except ImportError:
    from config import config

#obtener conexion segun motor postgresql o sqlite
def get_connection(db_url: Optional[str] = None) -> Union[psycopg2.extensions.connection, sqlite3.Connection]:
    target_url = db_url or config.database_url
    #identificar si se utiliza base de datos sqlite en memoria o archivo
    if target_url.startswith("sqlite"):
        path = target_url.replace("sqlite:///", "").replace("sqlite://", "")
        conn = sqlite3.connect(path or ":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    #conectar a instancia postgresql
    return psycopg2.connect(target_url)

#reintentar conexion con retroceso exponencial durante arranque
def connect_with_retry(max_retries: int = 5, delay: float = 1.5, db_url: Optional[str] = None) -> Any:
    last_err: Optional[Exception] = None
    current_delay = delay
    #ejecutar intentos sucesivos
    for _ in range(1, max_retries + 1):
        try:
            return get_connection(db_url)
        except Exception as exc:
            last_err = exc
            time.sleep(current_delay)
            current_delay *= 1.5
    #notificar fallo definitivo tras agotar reintentos
    raise ConnectionError(f"No fue posible conectar a db_logs tras {max_retries} intentos: {last_err}")

#crear tabla de logs e indices requeridos
def inicializar_db(db_url: Optional[str] = None) -> None:
    target_url = db_url or config.database_url
    is_sqlite = target_url.startswith("sqlite")

    #abrir conexion con reintento
    conn = connect_with_retry(db_url=target_url)
    try:
        with conn:
            cur = conn.cursor()
            #crear tabla para sqlite si aplica
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
                #crear tabla para postgresql
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
            #crear indices para optimizacion de filtros
            cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_service ON logs(service)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_severity ON logs(severity)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_received ON logs(received_at DESC)")
    finally:
        #cerrar conexion
        conn.close()

#insertar registros de log en bloque
def insertar_logs(
    logs_a_insertar: List[Tuple[str, str, str, str, str]],
    db_url: Optional[str] = None,
) -> int:
    #validar que la lista no este vacia
    if not logs_a_insertar:
        return 0

    target_url = db_url or config.database_url
    is_sqlite = target_url.startswith("sqlite")
    conn = get_connection(target_url)

    #ejecutar insercion multiple
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

#consultar logs con filtros dinamicos y paginacion
def consultar_logs(
    filtros: Dict[str, Any],
    db_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    target_url = db_url or config.database_url
    is_sqlite = target_url.startswith("sqlite")
    conn = get_connection(target_url)

    #construir consulta sql parametrizada
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor) if not is_sqlite else conn.cursor()

        query_parts = ["SELECT id, service, severity, message, timestamp, received_at FROM logs WHERE 1=1"]
        params: List[Any] = []
        p = "?" if is_sqlite else "%s"

        #filtrar por servicio emisor
        if filtros.get("service"):
            query_parts.append(f"AND service = {p}")
            params.append(filtros["service"])

        #filtrar por nivel de severidad
        if filtros.get("severity"):
            query_parts.append(f"AND severity = {p}")
            params.append(filtros["severity"])

        #filtrar por limite inferior de tiempo
        if filtros.get("timestamp_start"):
            query_parts.append(f"AND timestamp >= {p}")
            params.append(filtros["timestamp_start"])

        #filtrar por limite superior de tiempo
        if filtros.get("timestamp_end"):
            query_parts.append(f"AND timestamp <= {p}")
            params.append(filtros["timestamp_end"])

        #aplicar ordenamiento y limites
        query_parts.append(f"ORDER BY received_at DESC LIMIT {p} OFFSET {p}")
        limit = min(max(int(filtros.get("limit", 100)), 1), 1000)
        offset = max(int(filtros.get("offset", 0)), 0)
        params.extend([limit, offset])

        query = " ".join(query_parts)
        cur.execute(query, tuple(params))

        #formatear filas obtenidas
        if is_sqlite:
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        return list(cur.fetchall())
    finally:
        conn.close()

#calcular metricas cuantitativas de logs por servicio y severidad
def obtener_estadisticas(db_url: Optional[str] = None) -> Dict[str, Dict[str, int]]:
    target_url = db_url or config.database_url
    is_sqlite = target_url.startswith("sqlite")
    conn = get_connection(target_url)

    #agrupar conteos por dimensiones clave
    try:
        cur = conn.cursor()
        #conteo agrupado por servicio
        cur.execute("SELECT service, COUNT(*) FROM logs GROUP BY service")
        por_servicio: Dict[str, int] = {str(row[0]): int(row[1]) for row in cur.fetchall()}

        #conteo agrupado por severidad
        cur.execute("SELECT severity, COUNT(*) FROM logs GROUP BY severity")
        por_severidad: Dict[str, int] = {str(row[0]): int(row[1]) for row in cur.fetchall()}

        return {
            "Por_servicio": por_servicio,
            "Por_severidad": por_severidad,
        }
    finally:
        conn.close()
