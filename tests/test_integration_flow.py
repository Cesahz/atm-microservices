from decimal import Decimal
import pytest
from flask.testing import FlaskClient

from services.account_service.database import obtener_saldo

def test_flujo_completo_atm(
    auth_client: FlaskClient,
    account_client: FlaskClient,
    logs_client: FlaskClient,
    account_db_path: str,
) -> None:
    """
    Simulación completa del ciclo de vida del ATM:
    1. Login de Usuario 1 -> Obtención de JWT
    2. Consulta de Saldo Inicial
    3. Retiro de Efectivo
    4. Transferencia de fondos a Usuario 2
    5. Login de Usuario 2 -> Verificación de recepción de saldo
    6. Verificación de persistencia de logs en el servicio de auditoría
    """
    # 1. Autenticación de Usuario 1
    res_login_1 = auth_client.post(
        "/login",
        json={"username": "Cesar Espinola", "pin": "2701"},
    )
    assert res_login_1.status_code == 200
    token_1 = res_login_1.get_json()["token"]
    headers_1 = {"Authorization": f"Bearer {token_1}"}

    # 2. Consulta de saldo inicial de Usuario 1 (5.000.000 Gs)
    res_saldo_1 = account_client.get("/saldo", headers=headers_1)
    assert res_saldo_1.status_code == 200
    assert res_saldo_1.get_json()["saldo"] == 5000000.0

    # 3. Retiro de 500.000 Gs
    res_retiro = account_client.post(
        "/retiro",
        json={"monto": 500000},
        headers=headers_1,
    )
    assert res_retiro.status_code == 200
    assert res_retiro.get_json()["nuevo_saldo"] == 4500000.0

    # 4. Transferencia de 1.000.000 Gs a Usuario 2 (Jose Toledo)
    res_transfer = account_client.post(
        "/transferir",
        json={"receptor_id": 2, "monto": 1000000},
        headers=headers_1,
    )
    assert res_transfer.status_code == 200
    assert res_transfer.get_json()["mensaje"] == "Transferencia exitosa"

    # Saldo final esperado de Usuario 1: 5.000.000 - 500.000 - 1.000.000 = 3.500.000 Gs
    saldo_actual_1 = obtener_saldo(1, account_db_path)
    assert saldo_actual_1 == Decimal("3500000")

    # 5. Autenticación de Usuario 2 y verificación de saldo
    res_login_2 = auth_client.post(
        "/login",
        json={"username": "Jose Toledo", "pin": "1111"},
    )
    assert res_login_2.status_code == 200
    token_2 = res_login_2.get_json()["token"]
    headers_2 = {"Authorization": f"Bearer {token_2}"}

    # Saldo inicial era 7.000.000 + 1.000.000 transferido = 8.000.000 Gs
    res_saldo_2 = account_client.get("/saldo", headers=headers_2)
    assert res_saldo_2.status_code == 200
    assert res_saldo_2.get_json()["saldo"] == 8000000.0

    # 6. Registrar manualmente logs simulados y verificar consulta
    headers_admin = {"Authorization": "Token TOKEN-ADMIN-005"}
    logs_client.post(
        "/logs",
        json={
            "service": "atm-auth-service",
            "severity": "INFO",
            "message": "Login exitoso para Cesar Espinola",
        },
        headers=headers_admin,
    )
    logs_client.post(
        "/logs",
        json={
            "service": "atm-account-service",
            "severity": "INFO",
            "message": "Retiro exitoso de 500000 para user_id 1",
        },
        headers=headers_admin,
    )

    res_logs = logs_client.get("/logs", headers=headers_admin)
    assert res_logs.status_code == 200
    assert res_logs.get_json()["total"] == 2
