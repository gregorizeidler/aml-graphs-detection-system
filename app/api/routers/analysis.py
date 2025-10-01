"""
Router para endpoints de análise de risco e detecção de padrões.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from neo4j import Session
from app.core.database import get_neo4j
from app.models.schemas import RiskAnalysisRequest, RiskAnalysisResponse, StatisticsResponse
from app.services.neo4j_service import Neo4jService

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/risk", response_model=RiskAnalysisResponse)
async def analyze_risk(
    request: RiskAnalysisRequest,
    neo4j_session: Session = Depends(get_neo4j)
):
    """
    Analisa o risco de um cliente baseado em sua rede de transações.
    
    Args:
        request: Requisição com customer_id e parâmetros
        neo4j_session: Sessão do Neo4j
        
    Returns:
        RiskAnalysisResponse: Análise completa de risco
    """
    try:
        # Buscar contas do cliente
        query = """
        MATCH (c:Customer {customer_id: $customer_id})-[:OWNS]->(a:Account)
        RETURN a.account_id as account_id
        """
        result = neo4j_session.run(query, customer_id=request.customer_id)
        accounts = [record["account_id"] for record in result]
        
        if not accounts:
            raise HTTPException(
                status_code=404,
                detail="Cliente não encontrado ou sem contas"
            )
        
        # Calcular risco para cada conta
        risk_scores = []
        risk_factors = []
        suspicious_patterns = []
        
        for account_id in accounts:
            risk_data = Neo4jService.calculate_account_risk(
                neo4j_session, 
                account_id
            )
            
            if risk_data:
                risk_scores.append(risk_data.get("suspicion_ratio", 0.0))
                
                # Identificar fatores de risco
                if risk_data.get("suspicious_out", 0) > 0:
                    risk_factors.append({
                        "account": account_id,
                        "factor": "suspicious_outgoing_transactions",
                        "count": risk_data["suspicious_out"]
                    })
                
                if risk_data.get("suspicious_in", 0) > 0:
                    risk_factors.append({
                        "account": account_id,
                        "factor": "suspicious_incoming_transactions",
                        "count": risk_data["suspicious_in"]
                    })
        
        # Detectar padrões suspeitos
        fan_out = Neo4jService.detect_fan_out_patterns(neo4j_session)
        fan_in = Neo4jService.detect_fan_in_patterns(neo4j_session)
        
        for pattern in fan_out:
            if pattern["account_id"] in accounts:
                suspicious_patterns.append({
                    "type": "fan_out",
                    "account": pattern["account_id"],
                    "details": f"Distribuiu fundos para {pattern['num_targets']} contas"
                })
        
        for pattern in fan_in:
            if pattern["account_id"] in accounts:
                suspicious_patterns.append({
                    "type": "fan_in",
                    "account": pattern["account_id"],
                    "details": f"Recebeu fundos de {pattern['num_sources']} contas"
                })
        
        # Calcular score geral
        overall_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0
        
        # Gerar recomendações
        recommendations = []
        if overall_risk > 0.7:
            recommendations.append("🚨 ALTO RISCO: Realizar investigação detalhada imediatamente")
            recommendations.append("Revisar todas as transações dos últimos 90 dias")
        elif overall_risk > 0.4:
            recommendations.append("⚠️ RISCO MÉDIO: Monitoramento reforçado recomendado")
            recommendations.append("Verificar padrões de transação recentes")
        else:
            recommendations.append("✅ RISCO BAIXO: Manter monitoramento padrão")
        
        if len(suspicious_patterns) > 0:
            recommendations.append(
                f"Investigar {len(suspicious_patterns)} padrões suspeitos detectados"
            )
        
        # Métricas de rede
        network_metrics = {
            "total_accounts": len(accounts),
            "accounts_with_risk": len([s for s in risk_scores if s > 0]),
            "suspicious_patterns_found": len(suspicious_patterns)
        }
        
        return RiskAnalysisResponse(
            customer_id=request.customer_id,
            overall_risk_score=round(overall_risk, 4),
            risk_factors=risk_factors,
            suspicious_patterns=suspicious_patterns,
            network_metrics=network_metrics,
            recommendations=recommendations
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro na análise de risco: {str(e)}"
        )


@router.get("/patterns/fan-out", response_model=List[Dict[str, Any]])
async def get_fan_out_patterns(
    days: int = 30,
    min_targets: int = 5,
    neo4j_session: Session = Depends(get_neo4j)
):
    """
    Detecta padrões fan-out no sistema.
    
    Args:
        days: Período de análise em dias
        min_targets: Número mínimo de contas destino
        neo4j_session: Sessão do Neo4j
        
    Returns:
        Lista de padrões detectados
    """
    try:
        patterns = Neo4jService.detect_fan_out_patterns(
            neo4j_session, 
            days, 
            min_targets
        )
        return patterns
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao detectar padrões: {str(e)}"
        )


@router.get("/patterns/fan-in", response_model=List[Dict[str, Any]])
async def get_fan_in_patterns(
    days: int = 30,
    min_sources: int = 5,
    neo4j_session: Session = Depends(get_neo4j)
):
    """
    Detecta padrões fan-in no sistema.
    
    Args:
        days: Período de análise em dias
        min_sources: Número mínimo de contas origem
        neo4j_session: Sessão do Neo4j
        
    Returns:
        Lista de padrões detectados
    """
    try:
        patterns = Neo4jService.detect_fan_in_patterns(
            neo4j_session, 
            days, 
            min_sources
        )
        return patterns
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao detectar padrões: {str(e)}"
        )


@router.get("/patterns/cycles", response_model=List[Dict[str, Any]])
async def get_cycle_patterns(
    min_length: int = 3,
    max_length: int = 6,
    neo4j_session: Session = Depends(get_neo4j)
):
    """
    Detecta ciclos de transferências.
    
    Args:
        min_length: Comprimento mínimo do ciclo
        max_length: Comprimento máximo do ciclo
        neo4j_session: Sessão do Neo4j
        
    Returns:
        Lista de ciclos detectados
    """
    try:
        cycles = Neo4jService.detect_cycles(
            neo4j_session, 
            min_length, 
            max_length
        )
        return cycles
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao detectar ciclos: {str(e)}"
        )


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    neo4j_session: Session = Depends(get_neo4j)
):
    """
    Obtém estatísticas gerais do sistema.
    
    Args:
        neo4j_session: Sessão do Neo4j
        
    Returns:
        StatisticsResponse: Estatísticas do sistema
    """
    try:
        stats = Neo4jService.get_statistics(neo4j_session)
        
        if not stats:
            raise HTTPException(
                status_code=404,
                detail="Nenhuma estatística disponível"
            )
        
        return StatisticsResponse(
            total_customers=stats.get("total_customers", 0),
            total_accounts=stats.get("total_accounts", 0),
            total_transactions=stats.get("total_transactions", 0),
            suspicious_transactions=stats.get("suspicious_transactions", 0),
            suspicious_percentage=round(stats.get("suspicious_percentage", 0.0), 2),
            typologies=stats.get("typologies", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter estatísticas: {str(e)}"
        )


@router.post("/update-risk-scores")
async def update_risk_scores(
    neo4j_session: Session = Depends(get_neo4j)
):
    """
    Atualiza os risk scores de todas as contas.
    
    Args:
        neo4j_session: Sessão do Neo4j
        
    Returns:
        Número de contas atualizadas
    """
    try:
        updated_count = Neo4jService.update_risk_scores(neo4j_session)
        return {
            "message": "Risk scores atualizados com sucesso",
            "updated_accounts": updated_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar risk scores: {str(e)}"
        )
