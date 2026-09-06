from decimal import Decimal
import pytest
from flask.testing import FlaskClient

from services.account_service.database import obtener_saldo
from tests.conftest import TEST_JWT_SECRET

def test_health_check(account_client: FlaskClient) -> None:
    """Verifica que el endpoint de salud de account responda 200 OK."""
    res = account_client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "healthy"

def test_consultar_saldo_autorizado(account_client: FlaskClient, make_auth_token) -> None:
    """Verifica la consulta de saldo para un usuario autenticado."""
    token = make_auth_token(user_id=1)
    res = account_client.get("/saldo", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["user_id"] == 1
    assert data["saldo"] == 5000000.0

def test_retiro_exitoso(account_client: FlaskClient, account_db_path: str, make_auth_token) -> None:
    """Verifica un retiro válido y la actualización correcta del saldo."""
    token = make_auth_token(user_id=1)
    res = account_client.post(
        "/retiro",
        json={"monto": 500000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["mensaje"] == "Retiro exitoso"
    assert data["monto_retirado"] == 500000.0
    assert data["nuevo_saldo"] == 4500000.0

    saldo_en_db = obtener_saldo(1, account_db_path)
    assert saldo_en_db == Decimal("4500000")

def test_retiro_fondos_insuficientes(account_client: FlaskClient, make_auth_token) -> None:
    """Verifica el rechazo de retiro si el monto supera el saldo disponible."""
    token = make_auth_token(user_id=1)
    res = account_client.post(
        "/retiro",
        json={"monto": 999999999},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    data = res.get_json()
    assert "insuficientes" in data["error"].lower()

def test_retiro_monto_negativo_o_cero(account_client: FlaskClient, make_auth_token) -> None:
    """Verifica la prevención de exploits mediante montos no positivos en retiros."""
    token = make_auth_token(user_id=1)

    res_neg = account_client.post(
        "/retiro",
        json={"monto": -100000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_neg.status_code == 400

    res_cero = account_client.post(
        "/retiro",
        json={"monto": 0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_cero.status_code == 400

    res_str = account_client.post(
        "/retiro",
        json={"monto": "invalido"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_str.status_code == 400

def test_retiro_sin_autorizacion(account_client: FlaskClient) -> None:
    """Verifica que /retiro requiera token JWT válido (401)."""
    res1 = account_client.post("/retiro", json={"monto": 50000})
    assert res1.status_code == 401

    res2 = account_client.post("/retiro", json={"monto": 50000}, headers={"Authorization": "Bearer token_falso"})
    assert res2.status_code == 401

def test_transferencia_exitosa(account_client: FlaskClient, account_db_path: str, make_auth_token) -> None:
    """Verifica una transferencia válida entre dos cuentas."""
    token_emisor = make_auth_token(user_id=1)
    res = account_client.post(
        "/transferir",
        json={"receptor_id": 2, "monto": 1000000},
        headers={"Authorization": f"Bearer {token_emisor}"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["mensaje"] == "Transferencia exitosa"
    assert data["monto"] == 1000000.0

    assert obtener_saldo(1, account_db_path) == Decimal("4000000")
    assert obtener_saldo(2, account_db_path) == Decimal("8000000")

def test_transferencia_a_misma_cuenta(account_client: FlaskClient, make_auth_token) -> None:
    """Verifica que no sea posible transferir fondos hacia la propia cuenta."""
    token = make_auth_token(user_id=1)
    res = account_client.post(
        "/transferir",
        json={"receptor_id": 1, "monto": 50000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert "misma cuenta" in res.get_json()["error"].lower()

def test_transferencia_cuenta_destino_inexistente(account_client: FlaskClient, account_db_path: str, make_auth_token) -> None:
    """Verifica que transferir a un destino inexistente falle sin descontar dinero al emisor."""
    token = make_auth_token(user_id=1)
    saldo_inicial = obtener_saldo(1, account_db_path)

    res = account_client.post(
        "/transferir",
        json={"receptor_id": 9999, "monto": 100000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert "no encontrada" in res.get_json()["error"].lower()

    # Invariante: El saldo no debe haber disminuido
    assert obtener_saldo(1, account_db_path) == saldo_inicial

def test_transferencia_monto_invalido(account_client: FlaskClient, make_auth_token) -> None:
    """Verifica el rechazo de transferencias con montos `<= 0` o no numéricos."""
    token = make_auth_token(user_id=1)
    for monto in [-5000, 0, "cien mil"]:
        res = account_client.post(
            "/transferir",
            json={"receptor_id": 2, "monto": monto},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 400
