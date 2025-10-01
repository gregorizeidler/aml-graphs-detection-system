"""
Graph Analysis Router - Endpoints para análises avançadas de grafos
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.services.graph_analysis_service import GraphAnalysisService
from app.core.database import get_neo4j_driver
from neo4j import Session

router = APIRouter(prefix="/api/v1/graph", tags=["Graph Analysis"])


def get_graph_service() -> GraphAnalysisService:
    """Dependency para obter o serviço de análise de grafos"""
    driver = get_neo4j_driver()
    session = driver.session()
    try:
        yield GraphAnalysisService(session)
    finally:
        session.close()


# ============================================================================
# ALGORITMOS DE CENTRALIDADE
# ============================================================================

@router.get("/centrality/pagerank", 
            summary="Calcular PageRank",
            description="Identifica as contas mais 'influentes' na rede de transações")
async def get_pagerank(
    top_n: int = Query(20, ge=1, le=100, description="Número de contas a retornar"),
    service: GraphAnalysisService = Depends(get_graph_service)
) -> Dict[str, Any]:
    """
    **PageRank** - Algoritmo usado pelo Google para ranquear páginas web.
    
    No contexto AML:
    - Contas com alto PageRank recebem muitas transações de outras contas importantes
    - Pode indicar contas centralizadoras (money mules, contas de integração)
    - Útil para identificar "hubs" na rede de lavagem
    """
    try:
        results = service.calculate_pagerank(top_n=top_n)
        return {
            "algorithm": "PageRank",
            "description": "Identifica contas mais influentes baseado em conexões",
            "total_results": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/centrality/betweenness",
            summary="Calcular Betweenness Centrality", 
            description="Identifica contas que servem de 'ponte' entre outras")
async def get_betweenness_centrality(
    top_n: int = Query(20, ge=1, le=100, description="Número de contas a retornar"),
    service: GraphAnalysisService = Depends(get_graph_service)
) -> Dict[str, Any]:
    """
    **Betweenness Centrality** - Mede quantos caminhos passam por uma conta.
    
    No contexto AML:
    - Contas com alta betweenness são "pontes" críticas na rede
    - Remoção dessas contas fragmentaria a rede
    - Típico de contas intermediárias em esquemas de layering
    """
    try:
        results = service.calculate_betweenness_centrality(top_n=top_n)
        return {
            "algorithm": "Betweenness Centrality",
            "description": "Identifica contas que servem de ponte na rede",
            "total_results": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/centrality/closeness",
            summary="Calcular Closeness Centrality",
            description="Mede a proximidade de uma conta em relação a todas as outras")
async def get_closeness_centrality(
    top_n: int = Query(20, ge=1, le=100, description="Número de contas a retornar"),
    service: GraphAnalysisService = Depends(get_graph_service)
) -> Dict[str, Any]:
    """
    **Closeness Centrality** - Mede o quão "próxima" uma conta está de todas as outras.
    
    No contexto AML:
    - Contas com alta closeness podem alcançar muitas outras rapidamente
    - Útil para detectar contas que coordenam operações
    - Indica posição estratégica na rede
    """
    try:
        results = service.calculate_closeness_centrality(top_n=top_n)
        return {
            "algorithm": "Closeness Centrality",
            "description": "Mede proximidade na rede",
            "total_results": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/centrality/eigenvector",
            summary="Calcular Eigenvector Centrality",
            description="Importância baseada em conexões com outras contas importantes")
async def get_eigenvector_centrality(
    top_n: int = Query(20, ge=1, le=100, description="Número de contas a retornar"),
    service: GraphAnalysisService = Depends(get_graph_service)
) -> Dict[str, Any]:
    """
    **Eigenvector Centrality** - Uma conta é importante se está conectada a outras contas importantes.
    
    No contexto AML:
    - Similar ao PageRank mas considera mutualidade
    - Identifica "elite" da rede criminosa
    - Útil para mapear hierarquia organizacional
    """
    try:
        results = service.calculate_eigenvector_centrality(top_n=top_n)
        return {
            "algorithm": "Eigenvector Centrality",
            "description": "Importância baseada em conexões importantes",
            "total_results": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/centrality/account/{account_id}",
            summary="Todas centralidades de uma conta",
            description="Retorna todas as métricas de centralidade para uma conta específica")
async def get_account_centralities(
    account_id: str,
    service: GraphAnalysisService = Depends(get_graph_service)
) -> Dict[str, Any]:
    """
    Retorna **todas as métricas de centralidade** para uma conta específica:
    - PageRank
    - Betweenness
    - Closeness
    - Eigenvector
    - Grau de entrada/saída
    """
    try:
        results = service.get_all_centralities(account_id)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DETECÇÃO DE COMUNIDADES
# ============================================================================

@router.get("/communities/louvain",
            summary="Detectar comunidades (Louvain)",
            description="Identifica grupos de contas fortemente relacionadas usando o algoritmo Louvain")
async def detect_communities_louvain(
    service: GraphAnalysisService = Depends(get_graph_service)
) -> Dict[str, Any]:
    """
    **Louvain Algorithm** - Detecta comunidades maximizando modularidade.
    
    No contexto AML:
    - Identifica grupos de contas que transacionam principalmente entre si
    - Pode revelar redes organizadas de lavagem de dinheiro
    - Útil para mapear "células" de operação
    - Comunidades grandes com muitas contas suspeitas são de alto risco
    """
    try:
        results = service.detect_communities_louvain()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/communities/label-propagation",
            summary="Detectar comunidades (Label Propagation)",
            description="Detecta comunidades usando propagação de rótulos - rápido para grafos grandes")
async def detect_communities_label_propagation(
    service: GraphAnalysisService = Depends(get_graph_service)
) -> Dict[str, Any]:
    """
    **Label Propagation** - Algoritmo mais rápido que Louvain.
    
    No contexto AML:
    - Cada nó "adota" o rótulo da maioria de seus vizinhos
    - Mais rápido que Louvain para grafos grandes
    - Bom para análises exploratórias iniciais
    """
    try:
        results = service.detect_communities_label_propagation()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/communities/components",
            summary="Componentes conectados",
            description="Identifica sub-redes isoladas e componentes fortemente conectados")
async def find_connected_components(
    service: GraphAnalysisService = Depends(get_graph_service)
) -> Dict[str, Any]:
    """
    **Connected Components** - Encontra sub-redes isoladas.
    
    No contexto AML:
    - Componentes isolados podem ser operações independentes
    - Componentes pequenos e isolados são suspeitos
    - Útil para identificar "células" operacionais
    - Densidade alta em componente pequeno = alto risco
    """
    try:
        results = service.find_connected_components()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/communities/cliques",
            summary="Detectar cliques",
            description="Encontra grupos totalmente conectados - possível conluio")
async def find_cliques(
    min_size: int = Query(3, ge=2, le=10, description="Tamanho mínimo do clique"),
    service: GraphAnalysisService = Depends(get_graph_service)
) -> Dict[str, Any]:
    """
    **Clique Detection** - Grupos onde TODAS as contas transacionam entre si.
    
    No contexto AML:
    - Cliques grandes são raros em redes normais
    - Indicam conluio ou coordenação deliberada
    - Muito suspeito se várias contas do clique já são SAR
    - Típico de esquemas de "round-tripping" ou "smurfing"
    """
    try:
        results = service.find_cliques(min_size=min_size)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ANÁLISES TEMPORAIS
# ============================================================================

@router.get("/temporal/windows",
            summary="Análise por janelas de tempo",
            description="Analisa evolução da rede ao longo do tempo")
async def analyze_time_windows(
    window_hours: int = Query(24, ge=1, le=168, description="Tamanho da janela em horas (max 7 dias)"),
    service: GraphAnalysisService = Depends(get_graph_service)
) -> Dict[str, Any]:
    """
    **Time Windows** - Analisa a rede em períodos específicos.
    
    No contexto AML:
    - Mostra evolução da atividade ao longo do tempo
    - Identifica padrões temporais (fins de semana, horário comercial)
    - Detecta crescimento súbito da rede
    - Útil para correlacionar com eventos externos
    """
    try:
        results = service.analyze_time_windows(window_hours=window_hours)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/temporal/bursts",
            summary="Detectar picos de atividade",
            description="Identifica momentos de atividade anormalmente alta")
async def detect_bursts(
    threshold_std: float = Query(2.0, ge=1.0, le=5.0, description="Limiar em desvios padrão"),
    service: GraphAnalysisService = Depends(get_graph_service)
) -> Dict[str, Any]:
    """
    **Burst Detection** - Detecta picos súbitos de atividade.
    
    No contexto AML:
    - Picos de transações podem indicar "placement" acelerado
    - Bursts noturnos ou em horários incomuns são suspeitos
    - Correlação com eventos (feriados, fechamento de mercados)
    - Threshold de 2-3 std é considerado anormal
    """
    try:
        results = service.detect_bursts(threshold_std=threshold_std)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/temporal/velocity/{account_id}",
            summary="Análise de velocidade de fundos",
            description="Mede velocidade de movimentação de dinheiro através de contas")
async def calculate_velocity(
    account_id: str,
    service: GraphAnalysisService = Depends(get_graph_service)
) -> Dict[str, Any]:
    """
    **Velocity Analysis** - Analisa velocidade de movimentação de fundos.
    
    No contexto AML:
    - Transferências rápidas em cadeia indicam "layering"
    - Velocidade > 10k/hora é crítico
    - Múltiplos saltos em < 24h é suspeito
    - Detecta "pass-through accounts" (contas de passagem)
    """
    try:
        results = service.calculate_velocity_analysis(account_id)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINT DE RESUMO
# ============================================================================

@router.get("/summary",
            summary="Resumo de todas análises",
            description="Retorna um resumo executivo de todas as análises de grafos")
async def get_graph_analysis_summary(
    service: GraphAnalysisService = Depends(get_graph_service)
) -> Dict[str, Any]:
    """
    **Resumo Executivo** - Visão geral de todas as análises.
    
    Retorna:
    - Top 5 contas por cada métrica de centralidade
    - Número de comunidades detectadas
    - Componentes conectados
    - Bursts detectados
    - Recomendações de investigação
    """
    try:
        # Executar análises principais
        pagerank = service.calculate_pagerank(top_n=5)
        betweenness = service.calculate_betweenness_centrality(top_n=5)
        communities = service.detect_communities_louvain()
        components = service.find_connected_components()
        bursts = service.detect_bursts()
        
        # Contas que aparecem em múltiplas análises (mais suspeitas)
        top_accounts = set()
        for result in pagerank:
            top_accounts.add(result['account_id'])
        for result in betweenness:
            top_accounts.add(result['account_id'])
        
        # Contar comunidades de alto risco
        high_risk_communities = sum(
            1 for c in communities.get('communities', [])
            if c.get('risk_level') in ['HIGH', 'CRITICAL']
        )
        
        return {
            "summary": {
                "total_accounts_analyzed": len(top_accounts),
                "high_risk_communities": high_risk_communities,
                "total_communities": communities.get('total_communities', 0),
                "isolated_components": components.get('weakly_connected_components', 0),
                "bursts_detected": bursts.get('total_bursts', 0)
            },
            "top_influential_accounts": pagerank[:5],
            "top_bridge_accounts": betweenness[:5],
            "high_risk_communities": [
                c for c in communities.get('communities', [])
                if c.get('risk_level') in ['HIGH', 'CRITICAL']
            ][:5],
            "recommendations": [
                "Investigar contas que aparecem em múltiplas análises de centralidade",
                "Revisar comunidades com alta proporção de contas suspeitas",
                "Analisar componentes isolados com alta densidade",
                "Investigar contas envolvidas em bursts de atividade",
                "Aplicar velocity analysis nas contas de maior centralidade"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

