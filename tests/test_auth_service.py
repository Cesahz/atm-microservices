import sqlite3
import pytest
from flask.testing import FlaskClient

from services.auth_service.security import hash_pin, verify_pin, decode_access_token
from tests.conftest import TEST_JWT_SECRET

def test_health_check(auth_client: FlaskClient) -> None:
    """Verifica que el endpoint de salud responda 200 OK con metadatos."""
    res = auth_client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "atm-auth-service"

def test_login_success_default_users(auth_client: FlaskClient) -> None:
    """Verifica la autenticación exitosa de los usuarios precargados."""
    credenciales = [
        ("Cesar Espinola", "2701", 1),
        ("Jose Toledo", "1111", 2),
        ("Penguin Academy", "0000", 3),
    ]
    for username, pin, expected_id in credenciales:
        res = auth_client.post("/login", json={"username": username, "pin": pin})
        assert res.status_code == 200, f"Fallo login para {username}: {res.get_json()}"
        data = res.get_json()
        assert "token" in data
        payload = decode_access_token(data["token"], TEST_JWT_SECRET)
        assert payload is not None
        assert payload["user_id"] == expected_id

def test_login_invalid_pin(auth_client: FlaskClient) -> None:
    """Verifica el rechazo de credenciales con PIN erróneo (401 Unauthorized)."""
    res = auth_client.post("/login", json={"username": "Cesar Espinola", "pin": "9999"})
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"] == "Credenciales invalidas"

def test_login_nonexistent_user(auth_client: FlaskClient) -> None:
    """Verifica el rechazo de un usuario que no existe en el sistema."""
    res = auth_client.post("/login", json={"username": "Usuario Fantasma", "pin": "1234"})
    assert res.status_code == 401

def test_login_missing_fields(auth_client: FlaskClient) -> None:
    """Verifica el rechazo de solicitudes malformadas o campos vacíos (400 Bad Request)."""
    res1 = auth_client.post("/login", json={"username": "Cesar Espinola"})
    assert res1.status_code == 400

    res2 = auth_client.post("/login", json={"pin": "2701"})
    assert res2.status_code == 400

    res3 = auth_client.post("/login", json={"username": "", "pin": "2701"})
    assert res3.status_code == 400

    res4 = auth_client.post("/login", data="not json", content_type="text/plain")
    assert res4.status_code == 400

def test_pin_hashing_security(auth_db_path: str) -> None:
    """Verifica que los PINs no se almacenen en texto plano en la base de datos."""
    db_file = auth_db_path.replace("sqlite:///", "")
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT username, pin FROM usuarios")
    rows = cur.fetchall()
    conn.close()

    assert len(rows) >= 3
    for username, stored_pin in rows:
        assert not stored_pin.isdigit(), f"El PIN para {username} está almacenado en texto plano!"
        assert stored_pin.startswith("pbkdf2:sha256:"), f"Algoritmo inseguro para {username}"

def test_pin_hashing_and_verification_logic() -> None:
    """Prueba unitaria directa del módulo de seguridad PBKDF2."""
    raw_pin = "54321"
    hashed = hash_pin(raw_pin)
    assert hashed != raw_pin
    assert verify_pin(raw_pin, hashed) is True
    assert verify_pin("wrong_pin", hashed) is False
    assert verify_pin("", hashed) is False
    assert verify_pin(raw_pin, "") is False
