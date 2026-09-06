#importar utilidades de precision decimal y base de datos
from decimal import Decimal
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import psycopg2

#importar configuracion interna del operador
try:
    from .config import config
except ImportError:
    from config import config

#definir balances iniciales para cuentas de prueba
DEFAULT_BALANCES: List[Tuple[int, Decimal]] = [
    (1, Decimal("5000000")),
    (2, Decimal("7000000")),
    (3, Decimal("999999999")),
]

#obtener conexion activa segun motor postgresql o sqlite
def get_connection(db_url: Optional[str] = None) -> Union[psycopg2.extensions.connection, sqlite3.Connection]:
    target_url = db_url or config.database_url
    if target_url.startswith("sqlite"):
        path = target_url.replace("sqlite:///", "").replace("sqlite://", "")
        conn = sqlite3.connect(path or ":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    return psycopg2.connect(target_url)

#reintentar conexion a base de datos con retroceso exponencial
def connect_with_retry(max_retries: int = 5, delay: float = 1.5, db_url: Optional[str] = None) -> Any:
    last_err: Optional[Exception] = None
    current_delay = delay
    for _ in range(1, max_retries + 1):
        try:
            return get_connection(db_url)
        except Exception as exc:
            last_err = exc
            time.sleep(current_delay)
            current_delay *= 1.5
    raise ConnectionError(f"No fue posible conectar a db_operador tras {max_retries} intentos: {last_err}")

#crear tabla de cuentas y sembrar saldos iniciales si no existen
def inicializar_db(db_url: Optional[str] = None) -> None:
    target_url = db_url or config.database_url
    is_sqlite = target_url.startswith("sqlite")

    conn = connect_with_retry(db_url=target_url)
    try:
        with conn:
            cur = conn.cursor()
            if is_sqlite:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cuentas (
                        user_id INTEGER PRIMARY KEY,
                        saldo NUMERIC NOT NULL
                    )
                    """
                )
                for user_id, saldo in DEFAULT_BALANCES:
                    cur.execute(
                        "INSERT OR IGNORE INTO cuentas (user_id, saldo) VALUES (?, ?)",
                        (user_id, str(saldo)),
                    )
            else:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cuentas (
                        user_id INTEGER PRIMARY KEY,
                        saldo NUMERIC NOT NULL
                    )
                    """
                )
                for user_id, saldo in DEFAULT_BALANCES:
                    cur.execute(
                        "INSERT INTO cuentas (user_id, saldo) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING",
                        (user_id, saldo),
                    )
    finally:
        conn.close()

#consultar saldo actual de la cuenta especificada
def obtener_saldo(user_id: int, db_url: Optional[str] = None) -> Optional[Decimal]:
    target_url = db_url or config.database_url
    is_sqlite = target_url.startswith("sqlite")
    conn = get_connection(target_url)
    try:
        cur = conn.cursor()
        if is_sqlite:
            cur.execute("SELECT saldo FROM cuentas WHERE user_id = ?", (user_id,))
        else:
            cur.execute("SELECT saldo FROM cuentas WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        return Decimal(str(row[0]))
    finally:
        conn.close()

#procesar retiro de efectivo aplicando bloqueo pesimista
def procesar_retiro(
    user_id: int,
    monto: Decimal,
    db_url: Optional[str] = None
) -> Tuple[bool, Union[Decimal, str]]:
    if monto <= Decimal(0):
        return False, "El monto a retirar debe ser estrictamente positivo"

    target_url = db_url or config.database_url
    is_sqlite = target_url.startswith("sqlite")
    conn = get_connection(target_url)

    try:
        with conn:
            cur = conn.cursor()
            if is_sqlite:
                cur.execute("SELECT saldo FROM cuentas WHERE user_id = ?", (user_id,))
            else:
                cur.execute("SELECT saldo FROM cuentas WHERE user_id = %s FOR UPDATE", (user_id,))

            row = cur.fetchone()
            if not row:
                return False, "Cuenta no encontrada"

            saldo_actual = Decimal(str(row[0]))
            if saldo_actual < monto:
                return False, "Fondos insuficientes"

            nuevo_saldo = saldo_actual - monto

            if is_sqlite:
                cur.execute("UPDATE cuentas SET saldo = ? WHERE user_id = ?", (str(nuevo_saldo), user_id))
            else:
                cur.execute("UPDATE cuentas SET saldo = %s WHERE user_id = %s", (nuevo_saldo, user_id))

            return True, nuevo_saldo
    except Exception as exc:
        conn.rollback()
        return False, f"Error transaccional al procesar retiro: {str(exc)}"
    finally:
        conn.close()

#ejecutar transferencia atomica con orden canonico de bloqueo
def ejecutar_transferencia(
    emisor_id: int,
    receptor_id: int,
    monto: Decimal,
    db_url: Optional[str] = None
) -> Tuple[bool, str]:
    if monto <= Decimal(0):
        return False, "El monto a transferir debe ser estrictamente positivo"

    if emisor_id == receptor_id:
        return False, "No es posible realizar una transferencia hacia la misma cuenta"

    target_url = db_url or config.database_url
    is_sqlite = target_url.startswith("sqlite")
    conn = get_connection(target_url)

    #orden canonico determinista para evitar interbloqueos entre transferencias concurrentes cruzadas
    primer_id, segundo_id = (
        (emisor_id, receptor_id) if emisor_id < receptor_id else (receptor_id, emisor_id)
    )

    try:
        with conn:
            cur = conn.cursor()
            if is_sqlite:
                #en sqlite se leen y validan ambas cuentas secuencialmente
                cur.execute("SELECT user_id, saldo FROM cuentas WHERE user_id IN (?, ?)", (primer_id, segundo_id))
                rows = cur.fetchall()
            else:
                #en postgresql se bloquean ambas filas en orden ascendente por clave primaria
                cur.execute(
                    """
                    SELECT user_id, saldo FROM cuentas
                    WHERE user_id IN (%s, %s)
                    ORDER BY user_id FOR UPDATE
                    """,
                    (primer_id, segundo_id)
                )
                rows = cur.fetchall()

            cuentas_map: Dict[int, Decimal] = {row[0]: Decimal(str(row[1])) for row in rows}

            if emisor_id not in cuentas_map:
                return False, "Cuenta de origen no encontrada"

            if receptor_id not in cuentas_map:
                return False, "Cuenta destino no encontrada"

            saldo_emisor = cuentas_map[emisor_id]
            if saldo_emisor < monto:
                return False, "Fondos insuficientes"

            #ejecutar debito y credito atomicos
            if is_sqlite:
                cur.execute("UPDATE cuentas SET saldo = saldo - ? WHERE user_id = ?", (str(monto), emisor_id))
                cur.execute("UPDATE cuentas SET saldo = saldo + ? WHERE user_id = ?", (str(monto), receptor_id))
            else:
                cur.execute("UPDATE cuentas SET saldo = saldo - %s WHERE user_id = %s", (monto, emisor_id))
                cur.execute("UPDATE cuentas SET saldo = saldo + %s WHERE user_id = %s", (monto, receptor_id))

            return True, "Transferencia exitosa"
    except Exception as exc:
        conn.rollback()
        return False, f"Error transaccional al ejecutar transferencia: {str(exc)}"
    finally:
        conn.close()