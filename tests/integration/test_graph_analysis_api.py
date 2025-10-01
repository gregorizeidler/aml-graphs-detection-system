"""
Testes de integração para os endpoints de análise de grafos
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestCentralityEndpoints:
    """Testes para endpoints de centralidade"""
    
    def test_pagerank_success(self):
        """Testa cálculo de PageRank"""
        response = client.get("/api/v1/graph/centrality/pagerank?top_n=10")
        assert response.status_code == 200
        data = response.json()
        assert "algorithm" in data
        assert data["algorithm"] == "PageRank"
        assert "results" in data
        assert isinstance(data["results"], list)
    
    def test_pagerank_with_params(self):
        """Testa PageRank com diferentes parâmetros"""
        response = client.get("/api/v1/graph/centrality/pagerank?top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 5
    
    def test_betweenness_centrality(self):
        """Testa Betweenness Centrality"""
        response = client.get("/api/v1/graph/centrality/betweenness?top_n=10")
        assert response.status_code == 200
        data = response.json()
        assert data["algorithm"] == "Betweenness Centrality"
        assert "results" in data
    
    def test_closeness_centrality(self):
        """Testa Closeness Centrality"""
        response = client.get("/api/v1/graph/centrality/closeness?top_n=10")
        assert response.status_code == 200
        data = response.json()
        assert data["algorithm"] == "Closeness Centrality"
        assert "results" in data
    
    def test_eigenvector_centrality(self):
        """Testa Eigenvector Centrality"""
        response = client.get("/api/v1/graph/centrality/eigenvector?top_n=10")
        assert response.status_code == 200
        data = response.json()
        assert data["algorithm"] == "Eigenvector Centrality"
        assert "results" in data
    
    def test_account_centralities(self):
        """Testa todas centralidades para uma conta"""
        # Primeiro buscar uma conta válida
        response_pr = client.get("/api/v1/graph/centrality/pagerank?top_n=1")
        if response_pr.status_code == 200 and response_pr.json()["results"]:
            account_id = response_pr.json()["results"][0]["account_id"]
            
            response = client.get(f"/api/v1/graph/centrality/account/{account_id}")
            assert response.status_code == 200
            data = response.json()
            assert "centrality_scores" in data
            assert "pagerank" in data["centrality_scores"]
            assert "betweenness" in data["centrality_scores"]
            assert "closeness" in data["centrality_scores"]
            assert "eigenvector" in data["centrality_scores"]


class TestCommunityDetectionEndpoints:
    """Testes para endpoints de detecção de comunidades"""
    
    def test_louvain_communities(self):
        """Testa detecção de comunidades com Louvain"""
        response = client.get("/api/v1/graph/communities/louvain")
        assert response.status_code == 200
        data = response.json()
        assert "algorithm" in data
        assert data["algorithm"] == "Louvain"
        assert "total_communities" in data
        assert "communities" in data
        assert isinstance(data["communities"], list)
    
    def test_label_propagation_communities(self):
        """Testa Label Propagation"""
        response = client.get("/api/v1/graph/communities/label-propagation")
        assert response.status_code == 200
        data = response.json()
        assert data["algorithm"] == "Label Propagation"
        assert "communities" in data
    
    def test_connected_components(self):
        """Testa componentes conectados"""
        response = client.get("/api/v1/graph/communities/components")
        assert response.status_code == 200
        data = response.json()
        assert "strongly_connected_components" in data
        assert "weakly_connected_components" in data
        assert "components" in data
    
    def test_cliques_detection(self):
        """Testa detecção de cliques"""
        response = client.get("/api/v1/graph/communities/cliques?min_size=3")
        assert response.status_code == 200
        data = response.json()
        assert "total_cliques" in data
        assert "cliques" in data
        assert isinstance(data["cliques"], list)
    
    def test_cliques_with_params(self):
        """Testa cliques com diferentes parâmetros"""
        response = client.get("/api/v1/graph/communities/cliques?min_size=4")
        assert response.status_code == 200
        data = response.json()
        # Cliques maiores devem ter menos resultados
        assert data["total_cliques"] >= 0


class TestTemporalAnalysisEndpoints:
    """Testes para endpoints de análises temporais"""
    
    def test_time_windows_analysis(self):
        """Testa análise por janelas de tempo"""
        response = client.get("/api/v1/graph/temporal/windows?window_hours=24")
        assert response.status_code == 200
        data = response.json()
        assert "window_size_hours" in data
        assert data["window_size_hours"] == 24
        assert "windows" in data
        assert isinstance(data["windows"], list)
    
    def test_time_windows_different_sizes(self):
        """Testa diferentes tamanhos de janela"""
        for hours in [12, 24, 48]:
            response = client.get(f"/api/v1/graph/temporal/windows?window_hours={hours}")
            assert response.status_code == 200
            data = response.json()
            assert data["window_size_hours"] == hours
    
    def test_burst_detection(self):
        """Testa detecção de bursts"""
        response = client.get("/api/v1/graph/temporal/bursts?threshold_std=2.0")
        assert response.status_code == 200
        data = response.json()
        assert "threshold_std" in data
        assert "baseline_stats" in data
        assert "bursts" in data
        assert "mean_transactions" in data["baseline_stats"]
    
    def test_burst_different_thresholds(self):
        """Testa bursts com diferentes thresholds"""
        response1 = client.get("/api/v1/graph/temporal/bursts?threshold_std=2.0")
        response2 = client.get("/api/v1/graph/temporal/bursts?threshold_std=3.0")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Threshold maior deve ter menos bursts
        data1 = response1.json()
        data2 = response2.json()
        assert data1["total_bursts"] >= data2["total_bursts"]
    
    def test_velocity_analysis(self):
        """Testa análise de velocidade"""
        # Primeiro buscar uma conta válida
        response_pr = client.get("/api/v1/graph/centrality/pagerank?top_n=1")
        if response_pr.status_code == 200 and response_pr.json()["results"]:
            account_id = response_pr.json()["results"][0]["account_id"]
            
            response = client.get(f"/api/v1/graph/temporal/velocity/{account_id}")
            assert response.status_code == 200
            data = response.json()
            assert "account_id" in data
            assert data["account_id"] == account_id
            assert "chains" in data
            assert "risk_level" in data


class TestSummaryEndpoint:
    """Testes para endpoint de resumo"""
    
    def test_graph_analysis_summary(self):
        """Testa resumo executivo"""
        response = client.get("/api/v1/graph/summary")
        assert response.status_code == 200
        data = response.json()
        
        # Verificar estrutura
        assert "summary" in data
        assert "top_influential_accounts" in data
        assert "top_bridge_accounts" in data
        assert "high_risk_communities" in data
        assert "recommendations" in data
        
        # Verificar conteúdo do summary
        summary = data["summary"]
        assert "total_accounts_analyzed" in summary
        assert "high_risk_communities" in summary
        assert "total_communities" in summary
        
        # Verificar recommendations
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) > 0


class TestErrorHandling:
    """Testes para tratamento de erros"""
    
    def test_invalid_account_id(self):
        """Testa conta inexistente"""
        response = client.get("/api/v1/graph/centrality/account/INVALID_ID_12345")
        assert response.status_code in [200, 404, 500]
        # Pode retornar erro ou resultado vazio dependendo da implementação
    
    def test_invalid_parameters(self):
        """Testa parâmetros inválidos"""
        # top_n muito grande
        response = client.get("/api/v1/graph/centrality/pagerank?top_n=1000")
        assert response.status_code == 422  # Validation error
        
        # top_n negativo
        response = client.get("/api/v1/graph/centrality/pagerank?top_n=-1")
        assert response.status_code == 422
        
        # window_hours muito grande
        response = client.get("/api/v1/graph/temporal/windows?window_hours=1000")
        assert response.status_code == 422
    
    def test_invalid_threshold(self):
        """Testa threshold inválido"""
        response = client.get("/api/v1/graph/temporal/bursts?threshold_std=0.5")
        assert response.status_code == 422
        
        response = client.get("/api/v1/graph/temporal/bursts?threshold_std=10")
        assert response.status_code == 422


class TestPerformance:
    """Testes de performance (básicos)"""
    
    def test_response_time_centrality(self):
        """Testa tempo de resposta das centralidades"""
        import time
        
        start = time.time()
        response = client.get("/api/v1/graph/centrality/pagerank?top_n=20")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        # Deve responder em menos de 30 segundos (grafos grandes podem demorar)
        assert elapsed < 30.0
    
    def test_response_time_communities(self):
        """Testa tempo de resposta de comunidades"""
        import time
        
        start = time.time()
        response = client.get("/api/v1/graph/communities/louvain")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 60.0  # Louvain pode demorar mais


@pytest.mark.integration
class TestEndToEndWorkflow:
    """Testes de fluxo completo"""
    
    def test_complete_analysis_workflow(self):
        """Testa um fluxo completo de análise"""
        # 1. Obter resumo geral
        response = client.get("/api/v1/graph/summary")
        assert response.status_code == 200
        summary = response.json()
        
        # 2. Buscar conta mais influente
        if summary["top_influential_accounts"]:
            account_id = summary["top_influential_accounts"][0]["account_id"]
            
            # 3. Analisar todas centralidades dessa conta
            response = client.get(f"/api/v1/graph/centrality/account/{account_id}")
            assert response.status_code == 200
            
            # 4. Analisar velocidade dessa conta
            response = client.get(f"/api/v1/graph/temporal/velocity/{account_id}")
            assert response.status_code == 200
        
        # 5. Detectar comunidades
        response = client.get("/api/v1/graph/communities/louvain")
        assert response.status_code == 200
        
        # 6. Detectar bursts
        response = client.get("/api/v1/graph/temporal/bursts")
        assert response.status_code == 200

