"""
Router para endpoints relacionados a clientes.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from neo4j import Session
from app.core.database import get_neo4j
from app.models.schemas import CustomerResponse, NetworkResponse

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    neo4j_session: Session = Depends(get_neo4j)
):
    """
    Obtém informações de um cliente específico.
    
    Args:
        customer_id: ID do cliente
        neo4j_session: Sessão do Neo4j
        
    Returns:
        CustomerResponse: Dados do cliente
    """
    query = """
    MATCH (c:Customer {customer_id: $customer_id})
    RETURN c
    """
    
    result = neo4j_session.run(query, customer_id=customer_id)
    record = result.single()
    
    if not record:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    customer_node = record["c"]
    return CustomerResponse(
        customer_id=customer_node["customer_id"],
        name=customer_node["name"],
        customer_type=customer_node["customer_type"],
        risk_rating=customer_node["risk_rating"],
        country=customer_node["country"],
        registration_date=customer_node["registration_date"]
    )


@router.get("/{customer_id}/network", response_model=NetworkResponse)
async def get_customer_network(
    customer_id: str,
    depth: int = 2,
    neo4j_session: Session = Depends(get_neo4j)
):
    """
    Obtém a rede de transações de um cliente.
    
    Args:
        customer_id: ID do cliente
        depth: Profundidade da busca (1-5)
        neo4j_session: Sessão do Neo4j
        
    Returns:
        NetworkResponse: Rede com nós e arestas
    """
    from app.services.neo4j_service import Neo4jService
    
    if depth < 1 or depth > 5:
        raise HTTPException(
            status_code=400, 
            detail="Depth deve estar entre 1 e 5"
        )
    
    try:
        network = Neo4jService.get_customer_network(
            neo4j_session, 
            customer_id, 
            depth
        )
        return network
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao obter rede: {str(e)}"
        )


@router.get("/{customer_id}/accounts", response_model=List[dict])
async def get_customer_accounts(
    customer_id: str,
    neo4j_session: Session = Depends(get_neo4j)
):
    """
    Obtém todas as contas de um cliente.
    
    Args:
        customer_id: ID do cliente
        neo4j_session: Sessão do Neo4j
        
    Returns:
        Lista de contas
    """
    query = """
    MATCH (c:Customer {customer_id: $customer_id})-[:OWNS]->(a:Account)
    RETURN a
    """
    
    result = neo4j_session.run(query, customer_id=customer_id)
    accounts = [dict(record["a"]) for record in result]
    
    if not accounts:
        raise HTTPException(
            status_code=404, 
            detail="Nenhuma conta encontrada para este cliente"
        )
    
    return accounts

