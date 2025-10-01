"""
Schemas Pydantic para validação de dados da API.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class CustomerType(str, Enum):
    """Tipos de cliente."""
    INDIVIDUAL = "individual"
    BUSINESS = "business"


class RiskRating(str, Enum):
    """Níveis de risco."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AccountType(str, Enum):
    """Tipos de conta."""
    CHECKING = "checking"
    SAVINGS = "savings"
    BUSINESS = "business"


class TransactionType(str, Enum):
    """Tipos de transação."""
    TRANSFER = "transfer"
    PAYMENT = "payment"
    WITHDRAWAL = "withdrawal"
    DEPOSIT = "deposit"


# Customer Schemas
class CustomerBase(BaseModel):
    """Schema base de cliente."""
    customer_id: str
    name: str
    customer_type: CustomerType
    risk_rating: RiskRating
    country: str


class CustomerResponse(CustomerBase):
    """Schema de resposta de cliente."""
    registration_date: datetime
    
    class Config:
        from_attributes = True


# Account Schemas
class AccountBase(BaseModel):
    """Schema base de conta."""
    account_id: str
    customer_id: str
    account_type: AccountType
    balance: float


class AccountResponse(AccountBase):
    """Schema de resposta de conta."""
    opening_date: datetime
    status: str
    risk_score: Optional[float] = None
    
    class Config:
        from_attributes = True


# Transaction Schemas
class TransactionBase(BaseModel):
    """Schema base de transação."""
    transaction_id: str
    source_account: str
    target_account: str
    amount: float = Field(gt=0, description="Valor deve ser positivo")
    transaction_type: TransactionType


class TransactionResponse(TransactionBase):
    """Schema de resposta de transação."""
    timestamp: datetime
    is_suspicious: bool
    typology: Optional[str] = None
    
    class Config:
        from_attributes = True


# Network Schemas
class NetworkNode(BaseModel):
    """Nó da rede."""
    id: str
    label: str
    type: str  # 'account', 'customer'
    risk_score: Optional[float] = None
    properties: dict = {}


class NetworkEdge(BaseModel):
    """Aresta da rede."""
    source: str
    target: str
    amount: float
    timestamp: datetime
    is_suspicious: bool


class NetworkResponse(BaseModel):
    """Schema de resposta de rede."""
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]
    metadata: dict = {}


# Analysis Schemas
class RiskAnalysisRequest(BaseModel):
    """Schema de requisição de análise de risco."""
    customer_id: str
    depth: int = Field(default=2, ge=1, le=5, description="Profundidade da análise de rede")
    include_suspicious_only: bool = False


class RiskAnalysisResponse(BaseModel):
    """Schema de resposta de análise de risco."""
    customer_id: str
    overall_risk_score: float
    risk_factors: List[dict]
    suspicious_patterns: List[dict]
    network_metrics: dict
    recommendations: List[str]


# Statistics Schemas
class StatisticsResponse(BaseModel):
    """Schema de resposta de estatísticas."""
    total_customers: int
    total_accounts: int
    total_transactions: int
    suspicious_transactions: int
    suspicious_percentage: float
    typologies: dict

