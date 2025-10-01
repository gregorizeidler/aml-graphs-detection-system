"""
Configuração de fixtures para testes.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Fixture para cliente de teste da API."""
    return TestClient(app)


@pytest.fixture
def sample_customer_id():
    """Fixture com ID de cliente de exemplo."""
    return "CUST_00001"


@pytest.fixture
def sample_account_id():
    """Fixture com ID de conta de exemplo."""
    return "ACC_00001"

