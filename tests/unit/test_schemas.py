"""
Testes unitários para schemas Pydantic.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from app.models.schemas import (
    CustomerType, 
    RiskRating, 
    AccountType,
    TransactionBase,
    RiskAnalysisRequest,
    NetworkNode,
    NetworkEdge
)


class TestSchemas:
    """Testes para validação de schemas."""
    
    def test_transaction_base_valid(self):
        """Testa criação de transação válida."""
        transaction = TransactionBase(
            transaction_id="TXN_001",
            source_account="ACC_001",
            target_account="ACC_002",
            amount=1000.50,
            transaction_type="transfer"
        )
        
        assert transaction.amount == 1000.50
        assert transaction.transaction_type == "transfer"
    
    def test_transaction_negative_amount_fails(self):
        """Testa que valor negativo falha na validação."""
        with pytest.raises(ValidationError):
            TransactionBase(
                transaction_id="TXN_001",
                source_account="ACC_001",
                target_account="ACC_002",
                amount=-100,  # Negativo deve falhar
                transaction_type="transfer"
            )
    
    def test_risk_analysis_request_default_depth(self):
        """Testa valores default de RiskAnalysisRequest."""
        request = RiskAnalysisRequest(customer_id="CUST_001")
        
        assert request.depth == 2
        assert request.include_suspicious_only is False
    
    def test_risk_analysis_request_depth_validation(self):
        """Testa validação de profundidade."""
        # Depth muito alto deve passar (validação no endpoint)
        request = RiskAnalysisRequest(
            customer_id="CUST_001",
            depth=10
        )
        assert request.depth == 10
    
    def test_network_node_creation(self):
        """Testa criação de nó de rede."""
        node = NetworkNode(
            id="ACC_001",
            label="Account 001",
            type="account",
            risk_score=0.75,
            properties={"balance": 10000}
        )
        
        assert node.id == "ACC_001"
        assert node.risk_score == 0.75
        assert node.properties["balance"] == 10000
    
    def test_network_edge_creation(self):
        """Testa criação de aresta de rede."""
        edge = NetworkEdge(
            source="ACC_001",
            target="ACC_002",
            amount=5000.0,
            timestamp=datetime.now(),
            is_suspicious=True
        )
        
        assert edge.source == "ACC_001"
        assert edge.is_suspicious is True
    
    def test_customer_type_enum(self):
        """Testa enum de tipos de cliente."""
        assert CustomerType.INDIVIDUAL == "individual"
        assert CustomerType.BUSINESS == "business"
    
    def test_risk_rating_enum(self):
        """Testa enum de níveis de risco."""
        assert RiskRating.LOW == "low"
        assert RiskRating.MEDIUM == "medium"
        assert RiskRating.HIGH == "high"
    
    def test_account_type_enum(self):
        """Testa enum de tipos de conta."""
        assert AccountType.CHECKING == "checking"
        assert AccountType.SAVINGS == "savings"
        assert AccountType.BUSINESS == "business"

