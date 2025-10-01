"""
Testes de integração para API.
"""

import pytest
from fastapi.testclient import TestClient


class TestAPIEndpoints:
    """Testes de integração para endpoints da API."""
    
    def test_root_endpoint(self, client):
        """Testa endpoint raiz."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["message"] == "AML Detection System API"
    
    def test_health_check(self, client):
        """Testa health check."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "environment" in data
    
    def test_api_docs_available(self, client):
        """Testa que documentação da API está disponível."""
        response = client.get("/docs")
        
        assert response.status_code == 200
    
    def test_openapi_schema_available(self, client):
        """Testa que schema OpenAPI está disponível."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "AML Detection System"


class TestCustomerEndpoints:
    """Testes para endpoints de clientes."""
    
    @pytest.mark.skip(reason="Requer Neo4j rodando e dados carregados")
    def test_get_customer_not_found(self, client):
        """Testa busca de cliente inexistente."""
        response = client.get("/api/v1/customers/NONEXISTENT")
        
        assert response.status_code == 404
    
    @pytest.mark.skip(reason="Requer Neo4j rodando e dados carregados")
    def test_get_customer_network_invalid_depth(self, client, sample_customer_id):
        """Testa busca de rede com profundidade inválida."""
        response = client.get(
            f"/api/v1/customers/{sample_customer_id}/network",
            params={"depth": 10}
        )
        
        assert response.status_code == 400


class TestAnalysisEndpoints:
    """Testes para endpoints de análise."""
    
    @pytest.mark.skip(reason="Requer Neo4j rodando e dados carregados")
    def test_analyze_risk_customer_not_found(self, client):
        """Testa análise de risco para cliente inexistente."""
        response = client.post(
            "/api/v1/analysis/risk",
            json={"customer_id": "NONEXISTENT", "depth": 2}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.skip(reason="Requer Neo4j rodando e dados carregados")
    def test_get_statistics(self, client):
        """Testa obtenção de estatísticas."""
        response = client.get("/api/v1/analysis/statistics")
        
        # Pode retornar 200 com dados ou 404 se não houver dados
        assert response.status_code in [200, 404]

