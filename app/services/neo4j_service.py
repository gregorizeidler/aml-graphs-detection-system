"""
Serviço para interação com Neo4j.
Implementa queries otimizadas e análise de grafos.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from neo4j import Session
from app.models.schemas import NetworkNode, NetworkEdge, NetworkResponse


class Neo4jService:
    """Serviço para operações com Neo4j."""
    
    @staticmethod
    def get_customer_network(
        session: Session, 
        customer_id: str, 
        depth: int = 2
    ) -> NetworkResponse:
        """
        Obtém a rede de transações de um cliente.
        
        Args:
            session: Sessão do Neo4j
            customer_id: ID do cliente
            depth: Profundidade da busca na rede
            
        Returns:
            NetworkResponse com nós e arestas
        """
        query = """
        MATCH path = (c:Customer {customer_id: $customer_id})-[:OWNS]->(a:Account)
                      -[:TRANSACTED*1..$depth]-(other:Account)
        RETURN path
        """
        
        result = session.run(query, customer_id=customer_id, depth=depth)
        
        nodes_dict = {}
        edges = []
        
        for record in result:
            path = record["path"]
            
            # Processar nós
            for node in path.nodes:
                node_id = node.element_id
                if node_id not in nodes_dict:
                    labels = list(node.labels)
                    node_type = labels[0] if labels else "Unknown"
                    
                    if node_type == "Customer":
                        nodes_dict[node_id] = NetworkNode(
                            id=node["customer_id"],
                            label=node.get("name", "Unknown"),
                            type="customer",
                            properties=dict(node)
                        )
                    elif node_type == "Account":
                        nodes_dict[node_id] = NetworkNode(
                            id=node["account_id"],
                            label=node["account_id"],
                            type="account",
                            risk_score=node.get("risk_score", 0.0),
                            properties=dict(node)
                        )
            
            # Processar arestas
            for rel in path.relationships:
                if rel.type == "TRANSACTED":
                    edges.append(NetworkEdge(
                        source=rel.start_node["account_id"],
                        target=rel.end_node["account_id"],
                        amount=rel["amount"],
                        timestamp=rel["timestamp"],
                        is_suspicious=rel.get("is_suspicious", False)
                    ))
        
        return NetworkResponse(
            nodes=list(nodes_dict.values()),
            edges=edges,
            metadata={
                "customer_id": customer_id,
                "depth": depth,
                "node_count": len(nodes_dict),
                "edge_count": len(edges)
            }
        )
    
    @staticmethod
    def detect_fan_out_patterns(
        session: Session, 
        days: int = 30, 
        min_targets: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Detecta padrões fan-out (uma conta -> múltiplas contas).
        
        Args:
            session: Sessão do Neo4j
            days: Período de análise em dias
            min_targets: Número mínimo de contas destino
            
        Returns:
            Lista de padrões detectados
        """
        query = """
        MATCH (source:Account)-[t:TRANSACTED]->(target:Account)
        WHERE t.timestamp > datetime() - duration({days: $days})
        WITH source, COUNT(DISTINCT target) as num_targets, 
             SUM(t.amount) as total_amount,
             COLLECT(DISTINCT target.account_id) as targets
        WHERE num_targets >= $min_targets
        RETURN source.account_id as account_id, 
               num_targets, 
               total_amount, 
               targets
        ORDER BY num_targets DESC
        """
        
        result = session.run(
            query, 
            days=days, 
            min_targets=min_targets
        )
        
        return [dict(record) for record in result]
    
    @staticmethod
    def detect_fan_in_patterns(
        session: Session, 
        days: int = 30, 
        min_sources: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Detecta padrões fan-in (múltiplas contas -> uma conta).
        
        Args:
            session: Sessão do Neo4j
            days: Período de análise em dias
            min_sources: Número mínimo de contas origem
            
        Returns:
            Lista de padrões detectados
        """
        query = """
        MATCH (source:Account)-[t:TRANSACTED]->(target:Account)
        WHERE t.timestamp > datetime() - duration({days: $days})
        WITH target, COUNT(DISTINCT source) as num_sources,
             SUM(t.amount) as total_amount,
             COLLECT(DISTINCT source.account_id) as sources
        WHERE num_sources >= $min_sources
        RETURN target.account_id as account_id, 
               num_sources, 
               total_amount, 
               sources
        ORDER BY num_sources DESC
        """
        
        result = session.run(
            query, 
            days=days, 
            min_sources=min_sources
        )
        
        return [dict(record) for record in result]
    
    @staticmethod
    def detect_cycles(
        session: Session, 
        min_length: int = 3, 
        max_length: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Detecta ciclos de transferências.
        
        Args:
            session: Sessão do Neo4j
            min_length: Comprimento mínimo do ciclo
            max_length: Comprimento máximo do ciclo
            
        Returns:
            Lista de ciclos detectados
        """
        query = f"""
        MATCH path = (a:Account)-[:TRANSACTED*{min_length}..{max_length}]->(a)
        WHERE ALL(r IN relationships(path) WHERE r.is_suspicious = true)
        RETURN [n IN nodes(path) | n.account_id] as cycle_accounts,
               LENGTH(path) as cycle_length,
               REDUCE(total = 0, r IN relationships(path) | total + r.amount) as total_amount
        LIMIT 100
        """
        
        result = session.run(query)
        return [dict(record) for record in result]
    
    @staticmethod
    def calculate_account_risk(
        session: Session, 
        account_id: str
    ) -> Dict[str, Any]:
        """
        Calcula o score de risco de uma conta.
        
        Args:
            session: Sessão do Neo4j
            account_id: ID da conta
            
        Returns:
            Dicionário com métricas de risco
        """
        query = """
        MATCH (a:Account {account_id: $account_id})
        OPTIONAL MATCH (a)-[out:TRANSACTED]->(target)
        OPTIONAL MATCH (source)-[in:TRANSACTED]->(a)
        WITH a,
             COUNT(DISTINCT out) as outgoing_count,
             COUNT(DISTINCT in) as incoming_count,
             SUM(CASE WHEN out.is_suspicious THEN 1 ELSE 0 END) as suspicious_out,
             SUM(CASE WHEN in.is_suspicious THEN 1 ELSE 0 END) as suspicious_in,
             AVG(out.amount) as avg_outgoing,
             AVG(in.amount) as avg_incoming
        RETURN a.account_id as account_id,
               outgoing_count,
               incoming_count,
               suspicious_out,
               suspicious_in,
               avg_outgoing,
               avg_incoming,
               CASE 
                   WHEN (outgoing_count + incoming_count) = 0 THEN 0.0
                   ELSE (suspicious_out + suspicious_in) * 1.0 / (outgoing_count + incoming_count)
               END as suspicion_ratio
        """
        
        result = session.run(query, account_id=account_id)
        record = result.single()
        
        if record:
            return dict(record)
        return {}
    
    @staticmethod
    def update_risk_scores(session: Session) -> int:
        """
        Atualiza os risk scores de todas as contas.
        
        Args:
            session: Sessão do Neo4j
            
        Returns:
            Número de contas atualizadas
        """
        query = """
        MATCH (a:Account)
        OPTIONAL MATCH (a)-[t:TRANSACTED]-()
        WITH a, COUNT(t) as total_transactions,
             SUM(CASE WHEN t.is_suspicious THEN 1 ELSE 0 END) as suspicious_count
        SET a.risk_score = CASE 
            WHEN total_transactions = 0 THEN 0.0
            ELSE (suspicious_count * 1.0 / total_transactions)
        END
        RETURN COUNT(a) as updated_count
        """
        
        result = session.run(query)
        record = result.single()
        return record["updated_count"] if record else 0
    
    @staticmethod
    def get_statistics(session: Session) -> Dict[str, Any]:
        """
        Obtém estatísticas gerais do sistema.
        
        Args:
            session: Sessão do Neo4j
            
        Returns:
            Dicionário com estatísticas
        """
        query = """
        MATCH (c:Customer)
        WITH COUNT(c) as total_customers
        MATCH (a:Account)
        WITH total_customers, COUNT(a) as total_accounts
        MATCH ()-[t:TRANSACTED]->()
        WITH total_customers, total_accounts, 
             COUNT(t) as total_transactions,
             SUM(CASE WHEN t.is_suspicious THEN 1 ELSE 0 END) as suspicious_transactions
        RETURN total_customers, 
               total_accounts, 
               total_transactions, 
               suspicious_transactions,
               (suspicious_transactions * 100.0 / total_transactions) as suspicious_percentage
        """
        
        result = session.run(query)
        record = result.single()
        
        if record:
            stats = dict(record)
            
            # Obter tipologias
            typology_query = """
            MATCH ()-[t:TRANSACTED]->()
            WHERE t.is_suspicious = true
            RETURN t.typology as typology, COUNT(t) as count
            """
            typology_result = session.run(typology_query)
            stats["typologies"] = {
                record["typology"]: record["count"] 
                for record in typology_result
            }
            
            return stats
        
        return {}

