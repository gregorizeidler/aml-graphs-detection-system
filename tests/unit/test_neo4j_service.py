"""
Testes unitários para o serviço Neo4j.
"""

import pytest
from unittest.mock import Mock, MagicMock
from app.services.neo4j_service import Neo4jService


class TestNeo4jService:
    """Testes para Neo4jService."""
    
    def test_get_statistics_empty(self):
        """Testa obtenção de estatísticas quando não há dados."""
        mock_session = Mock()
        mock_session.run.return_value.single.return_value = None
        
        result = Neo4jService.get_statistics(mock_session)
        
        assert result == {}
    
    def test_calculate_account_risk_not_found(self):
        """Testa cálculo de risco quando conta não existe."""
        mock_session = Mock()
        mock_session.run.return_value.single.return_value = None
        
        result = Neo4jService.calculate_account_risk(
            mock_session, 
            "NONEXISTENT"
        )
        
        assert result == {}
    
    def test_detect_fan_out_patterns_returns_list(self):
        """Testa que detecção de fan-out retorna uma lista."""
        mock_session = Mock()
        mock_records = [
            {"account_id": "ACC_001", "num_targets": 10, "total_amount": 50000},
            {"account_id": "ACC_002", "num_targets": 8, "total_amount": 40000}
        ]
        mock_session.run.return_value = mock_records
        
        result = Neo4jService.detect_fan_out_patterns(mock_session)
        
        assert isinstance(result, list)
        assert len(result) == 2
    
    def test_detect_fan_in_patterns_returns_list(self):
        """Testa que detecção de fan-in retorna uma lista."""
        mock_session = Mock()
        mock_records = [
            {"account_id": "ACC_003", "num_sources": 12, "total_amount": 60000}
        ]
        mock_session.run.return_value = mock_records
        
        result = Neo4jService.detect_fan_in_patterns(mock_session)
        
        assert isinstance(result, list)
        assert len(result) == 1
    
    def test_detect_cycles_with_parameters(self):
        """Testa detecção de ciclos com parâmetros customizados."""
        mock_session = Mock()
        mock_session.run.return_value = []
        
        result = Neo4jService.detect_cycles(
            mock_session, 
            min_length=4, 
            max_length=8
        )
        
        assert isinstance(result, list)
        mock_session.run.assert_called_once()
    
    def test_update_risk_scores_returns_count(self):
        """Testa que atualização de risk scores retorna contagem."""
        mock_session = Mock()
        mock_result = Mock()
        mock_result.single.return_value = {"updated_count": 100}
        mock_session.run.return_value = mock_result
        
        result = Neo4jService.update_risk_scores(mock_session)
        
        assert result == 100

