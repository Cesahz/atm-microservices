import os
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Tuple
import requests
from dotenv import load_dotenv

load_dotenv()

AUTH_URL: str = os.getenv("AUTH_URL", "http://127.0.0.1:5001/login")
ACCOUNT_URL: str = os.getenv("ACCOUNT_URL", "http://127.0.0.1:5002")
REQUEST_TIMEOUT: float = 5.0

def formatear_guaranies(monto: Any) -> str:
    """Formatea una cantidad monetaria con separadores de miles estándar."""
    try:
        val = int(Decimal(str(monto)))
        return f"{val:,}".replace(",", ".") + " Gs."
    except (InvalidOperation, ValueError, TypeError):
        return f"{monto} Gs."

def solicitar_monto(mensaje: str) -> Optional[Decimal]:
    """Solicita y valida un monto numérico positivo ingresado por el usuario."""
    entrada = input(mensaje).strip().replace(".", "").replace(",", ".")
    if not entrada:
        print("Error: No se ingreso ningun valor.")
        return None
    try:
        monto = Decimal(entrada)
        if monto <= Decimal(0):
            print("Error: El monto debe ser estrictamente mayor a 0.")
            return None
        return monto
    except (InvalidOperation, ValueError):
        print("Error: Ingrese un valor numerico valido.")
        return None

def solicitar_entero_positivo(mensaje: str) -> Optional[int]:
    """Solicita y valida un número entero positivo (identificador de cuenta)."""
    entrada = input(mensaje).strip()
    if not entrada:
        print("Error: No se ingreso ningun identificador.")
        return None
    try:
        valor = int(entrada)
        if valor <= 0:
            print("Error: El identificador debe ser un numero positivo.")
            return None
        return valor
    except ValueError:
        print("Error: El identificador debe ser un numero entero.")
        return None

def consultar_saldo(headers: Dict[str, str]) -> None:
    """Consulta y presenta en pantalla el saldo actual de la cuenta autenticada."""
    try:
        res = requests.get(f"{ACCOUNT_URL}/saldo", headers=headers, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            datos = res.json()
            print(f"\nSaldo disponible: {formatear_guaranies(datos.get('saldo', 0))}")
        elif res.status_code == 401:
            print("\nSesion expirada o invalida. Por favor, vuelva a iniciar sesion.")
        else:
            print(f"\nNo fue posible obtener el saldo: {res.text}")
    except requests.exceptions.RequestException as err:
        print(f"\nError de conexion con el servicio financiero: {err}")

def ejecutar_retiro(headers: Dict[str, str]) -> None:
    """Gestiona el flujo de retiro de efectivo interactivo."""
    monto = solicitar_monto("Monto a retirar (Gs.): ")
    if monto is None:
        return

    try:
        res = requests.post(
            f"{ACCOUNT_URL}/retiro",
            json={"monto": float(monto)},
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        if res.headers.get("content-type", "").startswith("application/json"):
            respuesta = res.json()
            if res.status_code == 200:
                nuevo_saldo = formatear_guaranies(respuesta.get("nuevo_saldo", 0))
                print("\n[OK] Retiro exitoso:")
                print(f"     Monto retirado: {formatear_guaranies(monto)}")
                print(f"     Nuevo saldo:    {nuevo_saldo}")
            else:
                print(f"\n[ERROR] {respuesta.get('error', 'Operacion no permitida')}")
        else:
            print(f"\n[ERROR] Respuesta no reconocida del servidor (HTTP {res.status_code})")
    except requests.exceptions.RequestException as err:
        print(f"\n[ERROR] No fue posible comunicarse con account_service: {err}")

def ejecutar_transferencia(headers: Dict[str, str]) -> None:
    """Gestiona el flujo de transferencia de fondos interactiva."""
    print("\nDirectorio de Referencia: [1] Cesar Espinola | [2] Jose Toledo | [3] Penguin Academy")
    receptor_id = solicitar_entero_positivo("ID de la cuenta destino: ")
    if receptor_id is None:
        return

    monto = solicitar_monto("Monto a transferir (Gs.): ")
    if monto is None:
        return

    try:
        res = requests.post(
            f"{ACCOUNT_URL}/transferir",
            json={"receptor_id": receptor_id, "monto": float(monto)},
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        if res.headers.get("content-type", "").startswith("application/json"):
            respuesta = res.json()
            if res.status_code == 200:
                print("\n[OK] Transferencia exitosa:")
                print(f"     Cuenta destino: {receptor_id}")
                print(f"     Monto enviado:  {formatear_guaranies(monto)}")
            else:
                print(f"\n[ERROR] {respuesta.get('error', 'Operacion no permitida')}")
        else:
            print(f"\n[ERROR] Respuesta no reconocida del servidor (HTTP {res.status_code})")
    except requests.exceptions.RequestException as err:
        print(f"\n[ERROR] No fue posible comunicarse con account_service: {err}")

def iniciar_sesion() -> Optional[Tuple[str, str]]:
    """Solicita credenciales e interactúa con auth_service para obtener un JWT."""
    print("=" * 45)
    print("      ATM System — The Huddle 7")
    print("=" * 45)

    usuario = input("Ingrese Usuario: ").strip()
    pin = input("Ingrese PIN: ").strip()

    if not usuario or not pin:
        print("\nError: Debe proporcionar tanto el usuario como el PIN.")
        return None

    try:
        res = requests.post(
            AUTH_URL,
            json={"username": usuario, "pin": pin},
            timeout=REQUEST_TIMEOUT,
        )
        if res.status_code == 200:
            token = res.json().get("token")
            if token:
                print(f"\nConexion segura establecida. Bienvenido/a, {usuario}.")
                return token, usuario
        elif res.status_code == 401:
            print("\nAcceso Denegado: Credenciales invalidas.")
            return None
        else:
            print(f"\nError de autenticacion (HTTP {res.status_code}): {res.text}")
            return None
    except requests.exceptions.RequestException as err:
        print(f"\nError critico: No fue posible conectar con el servicio de autenticacion en {AUTH_URL}.")
        print(f"Detalle tecnico: {err}")
        return None

    return None

def main() -> None:
    """Bucle principal de ejecucion del cliente CLI."""
    sesion = iniciar_sesion()
    if not sesion:
        return

    token, usuario = sesion
    headers = {"Authorization": f"Bearer {token}"}

    while True:
        print("\n" + "-" * 40)
        print("  MENU DE OPERACIONES")
        print("-" * 40)
        print("1. Consultar Saldo")
        print("2. Retirar Efectivo")
        print("3. Transferir a otra cuenta")
        print("4. Retirar Tarjeta (Salir)")

        opcion = input("Seleccione una operacion (1-4): ").strip()

        if opcion == "1":
            consultar_saldo(headers)
        elif opcion == "2":
            ejecutar_retiro(headers)
        elif opcion == "3":
            ejecutar_transferencia(headers)
        elif opcion == "4":
            print(f"\nCerrando sesion de forma segura para {usuario}. Adios.")
            break
        else:
            print("Opcion no reconocida. Por favor, seleccione un numero del 1 al 4.")

if __name__ == "__main__":
    main()