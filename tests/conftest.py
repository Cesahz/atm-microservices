import os
import tempfile
from decimal import Decimal
from typing import Generator
import pytest
from flask.testing import FlaskClient

from services.auth_service.auth import create_app as create_auth_app
from services.auth_service.database import inicializar_db as init_auth_db
from services.auth_service.security import create_access_token
from services.account_service.account import create_app as create_account_app
from services.account_service.database import inicializar_db as init_account_db
from services.logs_service.app import create_app as create_logs_app
from services.logs_service.database import inicializar_db as init_logs_db

TEST_JWT_SECRET = "secreto_del_pinguino_aislado_clave_maestra_segura_32b"

@pytest.fixture
def auth_db_path() -> Generator[str, None, None]:
    """Crea una base de datos SQLite aislada para el servicio de autenticación."""
    fd, path = tempfile.mkstemp(suffix="_auth.db")
    os.close(fd)
    db_url = f"sqlite:///{path}"
    init_auth_db(db_url)
    yield db_url
    if os.path.exists(path):
        os.remove(path)

@pytest.fixture
def account_db_path() -> Generator[str, None, None]:
    """Crea una base de datos SQLite aislada para el servicio de cuentas."""
    fd, path = tempfile.mkstemp(suffix="_acc.db")
    os.close(fd)
    db_url = f"sqlite:///{path}"
    init_account_db(db_url)
    yield db_url
    if os.path.exists(path):
        os.remove(path)

@pytest.fixture
def logs_db_path() -> Generator[str, None, None]:
    """Crea una base de datos SQLite aislada para el servicio de logs."""
    fd, path = tempfile.mkstemp(suffix="_logs.db")
    os.close(fd)
    db_url = f"sqlite:///{path}"
    init_logs_db(db_url)
    yield db_url
    if os.path.exists(path):
        os.remove(path)

@pytest.fixture
def auth_client(auth_db_path: str) -> FlaskClient:
    """Cliente de pruebas para auth_service."""
    app = create_auth_app({
        "DATABASE_URL": auth_db_path,
        "JWT_SECRET": TEST_JWT_SECRET,
        "TESTING": True,
    })
    return app.test_client()

@pytest.fixture
def account_client(account_db_path: str) -> FlaskClient:
    """Cliente de pruebas para account_service."""
    app = create_account_app({
        "DATABASE_URL": account_db_path,
        "JWT_SECRET": TEST_JWT_SECRET,
        "TESTING": True,
    })
    return app.test_client()

@pytest.fixture
def logs_client(logs_db_path: str) -> FlaskClient:
    """Cliente de pruebas para logs_service."""
    app = create_logs_app({
        "DATABASE_URL": logs_db_path,
        "TESTING": True,
    })
    return app.test_client()

@pytest.fixture
def make_auth_token():
    """Generador de tokens JWT para pruebas con parámetros personalizables."""
    def _generator(user_id: int = 1, expiry_minutes: int = 15, secret: str = TEST_JWT_SECRET) -> str:
        return create_access_token(user_id=user_id, secret_key=secret, expiry_minutes=expiry_minutes)
    return _generator
