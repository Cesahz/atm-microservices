import os
import psycopg2

DB_URL = os.environ.get("DB_ACCOUNT_URL", "postgresql://admin:password@db_operador:5432/operador_db") 

#craar tabla de cuentas precargada
def inicializar_db():
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute('CREATE TABLE IF NOT EXISTS cuentas (user_id INTEGER PRIMARY KEY, saldo NUMERIC NOT NULL)')
            saldos = [(1, 5000000), (2, 7000000), (3, 999999999)] 
            cur.executemany("INSERT INTO cuentas (user_id, saldo) VALUES (%s, %s) ON CONFLICT DO NOTHING", saldos)
        conn.commit()



#funcion para realizar la transferencia entre cuentas
def ejecutar_transferencia(emisor_id, receptor_id, monto):
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            #for update bloquea la fila del emisor para evitar dos transferencias simultaneas
            cur.execute("SELECT saldo FROM cuentas WHERE user_id = %s FOR UPDATE", (emisor_id,))
            saldo_emisor = float(cur.fetchone()[0])
            if saldo_emisor < monto: return False, "Fondos insuficientes"
            
            #sumar y restar el monto a las cuentas correspondientes
            cur.execute("UPDATE cuentas SET saldo = saldo - %s WHERE user_id = %s", (monto, emisor_id))
            cur.execute("UPDATE cuentas SET saldo = saldo + %s WHERE user_id = %s", (monto, receptor_id))
            conn.commit()
            return True, "Transferencia exitosa"

def procesar_retiro(user_id, monto):
    """
    Intenta descontar el saldo. Retorna (exito_booleano, nuevo_saldo_o_mensaje)
    """
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT saldo FROM cuentas WHERE user_id = %s FOR UPDATE", (user_id,))
            resultado = cur.fetchone()
            
            if not resultado:
                return False, "Cuenta no encontrada"
                
            saldo_actual = float(resultado[0])
            if saldo_actual < monto:
                return False, "Fondos insuficientes"
                
            nuevo_saldo = saldo_actual - monto
            cur.execute("UPDATE cuentas SET saldo = %s WHERE user_id = %s", (nuevo_saldo, user_id))
            conn.commit()
            
            return True, nuevo_saldo