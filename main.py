import requests

AUTH_URL = "http://127.0.0.1:5001/login"
ACCOUNT_URL = "http://127.0.0.1:5002"

def main():
    print("=" * 30)
    print("Cajero Automatico - The Huddle 7")
    print("=" * 30)
    
    usuario = input("Ingrese Usuario: ")
    pin = input("Ingrese PIN: ")

    #intertar autenticarse con el servicio de auth
    res_auth = requests.post(AUTH_URL, json={"username": usuario, "pin": pin})
    
    #si el servicio responde con error, mostrar mensaje y salir
    if res_auth.status_code != 200:
        print("\nAcceso Denegado: Credenciales invalidas.")
        return

    #si el loggin es exitoso, extraer el token JWT de la respuesta
    token = res_auth.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"\nConexion segura establecida. Bienvenido {usuario}.")

    #bucle principal del cajero
    while True:
        #imprimir consola
        print("\n" + "-" * 35)
        print("1. Retirar Efectivo")
        print("2. Transferir a otra cuenta")
        print("3. Retirar Tarjeta (Salir)")
        
        #solicitar opcion al user
        opcion = input("Seleccione una operacion (1-3): ")

        if opcion == "1":
            monto = input("Monto a retirar (Gs): ")
            res = requests.post(f"{ACCOUNT_URL}/retiro", json={"monto": float(monto)}, headers=headers)
            print("-> RESPUESTA DEL OPERADOR:", res.json())

        elif opcion == "2":
            print("\nDirectorio: [1] Cesar | [2] Jose Toledo | [3] Penguin Academy")
            receptor = input("ID de la cuenta destino: ")
            monto = input("Monto a transferir (Gs): ")
            res = requests.post(f"{ACCOUNT_URL}/transferir", json={"receptor_id": int(receptor), "monto": float(monto)}, headers=headers)
            print("RESPUESTA DEL OPERADOR:", res.json())

        elif opcion == "3":
            print("\nDesconectando sistema de forma segura... Adios.")
            break
        else:
            print("Operacion no reconocida.")

if __name__ == "__main__":
    main()