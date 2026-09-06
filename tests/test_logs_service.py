import pytest
from flask.testing import FlaskClient

def test_health_check(logs_client: FlaskClient) -> None:
    """Verifica que el endpoint de salud de logs responda 200 OK."""
    res = logs_client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "healthy"

def test_recibir_log_individual(logs_client: FlaskClient) -> None:
    """Verifica la persistencia de un registro individual con token autorizado."""
    headers = {"Authorization": "Token TOKEN-AUTH-002"}
    payload = {
        "service": "atm-auth-service",
        "severity": "INFO",
        "message": "Usuario Cesar Espinola autenticado",
    }
    res = logs_client.post("/logs", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.get_json()["insertados"] == 1

def test_recibir_logs_en_lote(logs_client: FlaskClient) -> None:
    """Verifica la inserción masiva de múltiples logs en una sola transacción."""
    headers = {"Authorization": "Token TOKEN-PAYMENTS-003"}
    payload = [
        {"service": "atm-account-service", "severity": "INFO", "message": "Retiro procesado"},
        {"service": "atm-account-service", "severity": "WARN", "message": "Intento con saldo bajo"},
    ]
    res = logs_client.post("/logs", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.get_json()["insertados"] == 2

def test_logs_no_autorizado(logs_client: FlaskClient) -> None:
    """Verifica que requests sin token o con token inválido sean rechazados (401)."""
    res1 = logs_client.post("/logs", json={"service": "x", "message": "y"})
    assert res1.status_code == 401

    res2 = logs_client.post(
        "/logs",
        json={"service": "x", "message": "y"},
        headers={"Authorization": "Token TOKEN-INVALIDO"},
    )
    assert res2.status_code == 401

def test_logs_validacion_esquema(logs_client: FlaskClient) -> None:
    """Verifica la validación de severidad y campos obligatorios."""
    headers = {"Authorization": "Token TOKEN-ADMIN-005"}

    # Falta mensaje
    res1 = logs_client.post("/logs", json={"service": "auth"}, headers=headers)
    assert res1.status_code == 400

    # Severidad inválida
    res2 = logs_client.post(
        "/logs",
        json={"service": "auth", "severity": "CRITICO_INVENTADO", "message": "hola"},
        headers=headers,
    )
    assert res2.status_code == 400

def test_consultar_logs_con_filtros(logs_client: FlaskClient) -> None:
    """Verifica el endpoint GET /logs con filtrado por servicio y severidad."""
    headers = {"Authorization": "Token TOKEN-ADMIN-005"}

    # Insertar logs de prueba
    logs_client.post(
        "/logs",
        json=[
            {"service": "auth", "severity": "INFO", "message": "msg 1"},
            {"service": "auth", "severity": "ERROR", "message": "msg 2"},
            {"service": "account", "severity": "INFO", "message": "msg 3"},
        ],
        headers=headers,
    )

    # Filtrar por servicio
    res_auth = logs_client.get("/logs?service=auth", headers=headers)
    assert res_auth.status_code == 200
    assert res_auth.get_json()["total"] == 2

    # Filtrar por severidad
    res_error = logs_client.get("/logs?severity=ERROR", headers=headers)
    assert res_error.status_code == 200
    assert res_error.get_json()["total"] == 1
    assert res_error.get_json()["logs"][0]["message"] == "msg 2"

def test_obtener_estadisticas(logs_client: FlaskClient) -> None:
    """Verifica el cálculo agregado en /stats."""
    headers = {"Authorization": "Token TOKEN-ADMIN-005"}

    logs_client.post(
        "/logs",
        json=[
            {"service": "atm-auth-service", "severity": "INFO", "message": "Login 1"},
            {"service": "atm-auth-service", "severity": "WARN", "message": "Login fallido"},
            {"service": "atm-account-service", "severity": "INFO", "message": "Retiro 1"},
        ],
        headers=headers,
    )

    res = logs_client.get("/stats", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["Por_servicio"]["atm-auth-service"] == 2
    assert data["Por_servicio"]["atm-account-service"] == 1
    assert data["Por_severidad"]["INFO"] == 2
    assert data["Por_severidad"]["WARN"] == 1
