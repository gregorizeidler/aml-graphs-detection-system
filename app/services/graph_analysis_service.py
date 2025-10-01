"""
Graph Analysis Service - Algoritmos avançados de análise de grafos para detecção de AML
"""
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import networkx as nx
import community as community_louvain
from neo4j import Session
from loguru import logger
import pandas as pd
import numpy as np


class GraphAnalysisService:
    """Serviço para análises avançadas de grafos"""
    
    def __init__(self, session: Session):
        self.session = session
        
    def _build_networkx_graph(self, include_amounts: bool = False, 
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None) -> nx.DiGraph:
        """
        Constrói um grafo NetworkX a partir dos dados do Neo4j
        
        Args:
            include_amounts: Se True, adiciona peso das transações
            start_date: Data inicial para filtro temporal
            end_date: Data final para filtro temporal
        """
        query = """
        MATCH (a:Account)-[t:TRANSACTED]->(b:Account)
        """
        
        where_clauses = []
        params = {}
        
        if start_date:
            where_clauses.append("t.timestamp >= datetime($start_date)")
            params['start_date'] = start_date.isoformat()
            
        if end_date:
            where_clauses.append("t.timestamp <= datetime($end_date)")
            params['end_date'] = end_date.isoformat()
            
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        query += """
        RETURN 
            a.account_id as source, 
            b.account_id as target,
            t.amount as amount,
            t.timestamp as timestamp
        """
        
        result = self.session.run(query, params)
        
        G = nx.DiGraph()
        
        for record in result:
            source = record['source']
            target = record['target']
            amount = record['amount']
            
            if include_amounts:
                if G.has_edge(source, target):
                    # Soma os valores se já existe a aresta
                    G[source][target]['weight'] += amount
                    G[source][target]['count'] += 1
                else:
                    G.add_edge(source, target, weight=amount, count=1)
            else:
                if not G.has_edge(source, target):
                    G.add_edge(source, target)
                    
        logger.info(f"Grafo construído: {G.number_of_nodes()} nós, {G.number_of_edges()} arestas")
        return G
    
    # ============================================================================
    # ALGORITMOS DE CENTRALIDADE
    # ============================================================================
    
    def calculate_pagerank(self, top_n: int = 20) -> List[Dict[str, Any]]:
        """
        Calcula PageRank - identifica contas mais "influentes" na rede
        """
        logger.info("Calculando PageRank...")
        G = self._build_networkx_graph(include_amounts=True)
        
        if G.number_of_nodes() == 0:
            return []
        
        pagerank = nx.pagerank(G, weight='weight')
        
        # Buscar detalhes das contas do Neo4j
        top_accounts = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        results = []
        for account_id, score in top_accounts:
            account_info = self._get_account_info(account_id)
            results.append({
                "account_id": account_id,
                "pagerank_score": round(score, 6),
                "rank": len(results) + 1,
                **account_info
            })
            
        logger.info(f"PageRank calculado para {len(results)} contas")
        return results
    
    def calculate_betweenness_centrality(self, top_n: int = 20) -> List[Dict[str, Any]]:
        """
        Calcula Betweenness Centrality - identifica contas que servem de "ponte"
        """
        logger.info("Calculando Betweenness Centrality...")
        G = self._build_networkx_graph()
        
        if G.number_of_nodes() == 0:
            return []
        
        betweenness = nx.betweenness_centrality(G)
        
        top_accounts = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        results = []
        for account_id, score in top_accounts:
            account_info = self._get_account_info(account_id)
            results.append({
                "account_id": account_id,
                "betweenness_score": round(score, 6),
                "rank": len(results) + 1,
                **account_info
            })
            
        logger.info(f"Betweenness calculado para {len(results)} contas")
        return results
    
    def calculate_closeness_centrality(self, top_n: int = 20) -> List[Dict[str, Any]]:
        """
        Calcula Closeness Centrality - mede proximidade na rede
        """
        logger.info("Calculando Closeness Centrality...")
        G = self._build_networkx_graph()
        
        if G.number_of_nodes() == 0:
            return []
        
        # Usar apenas o componente fortemente conectado maior
        if nx.is_strongly_connected(G):
            closeness = nx.closeness_centrality(G)
        else:
            # Pegar o maior componente fortemente conectado
            largest_cc = max(nx.strongly_connected_components(G), key=len)
            G_largest = G.subgraph(largest_cc).copy()
            closeness = nx.closeness_centrality(G_largest)
        
        top_accounts = sorted(closeness.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        results = []
        for account_id, score in top_accounts:
            account_info = self._get_account_info(account_id)
            results.append({
                "account_id": account_id,
                "closeness_score": round(score, 6),
                "rank": len(results) + 1,
                **account_info
            })
            
        logger.info(f"Closeness calculado para {len(results)} contas")
        return results
    
    def calculate_eigenvector_centrality(self, top_n: int = 20) -> List[Dict[str, Any]]:
        """
        Calcula Eigenvector Centrality - importância baseada em conexões importantes
        """
        logger.info("Calculando Eigenvector Centrality...")
        G = self._build_networkx_graph(include_amounts=True)
        
        if G.number_of_nodes() == 0:
            return []
        
        try:
            eigenvector = nx.eigenvector_centrality(G, weight='weight', max_iter=1000)
        except nx.PowerIterationFailedConvergence:
            logger.warning("Eigenvector não convergiu, usando valores parciais")
            eigenvector = nx.eigenvector_centrality(G, weight='weight', max_iter=100, tol=1e-3)
        
        top_accounts = sorted(eigenvector.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        results = []
        for account_id, score in top_accounts:
            account_info = self._get_account_info(account_id)
            results.append({
                "account_id": account_id,
                "eigenvector_score": round(score, 6),
                "rank": len(results) + 1,
                **account_info
            })
            
        logger.info(f"Eigenvector calculado para {len(results)} contas")
        return results
    
    def get_all_centralities(self, account_id: str) -> Dict[str, Any]:
        """Calcula todas as centralidades para uma conta específica"""
        logger.info(f"Calculando todas centralidades para conta {account_id}")
        G = self._build_networkx_graph(include_amounts=True)
        
        if account_id not in G:
            return {"error": "Conta não encontrada no grafo"}
        
        pagerank = nx.pagerank(G, weight='weight')
        betweenness = nx.betweenness_centrality(G)
        
        # Closeness apenas se conectado
        try:
            closeness = nx.closeness_centrality(G)
            closeness_score = closeness.get(account_id, 0)
        except:
            closeness_score = 0
            
        try:
            eigenvector = nx.eigenvector_centrality(G, weight='weight', max_iter=1000)
            eigenvector_score = eigenvector.get(account_id, 0)
        except:
            eigenvector_score = 0
        
        account_info = self._get_account_info(account_id)
        
        return {
            "account_id": account_id,
            "centrality_scores": {
                "pagerank": round(pagerank.get(account_id, 0), 6),
                "betweenness": round(betweenness.get(account_id, 0), 6),
                "closeness": round(closeness_score, 6),
                "eigenvector": round(eigenvector_score, 6)
            },
            "network_position": {
                "in_degree": G.in_degree(account_id),
                "out_degree": G.out_degree(account_id),
                "total_degree": G.in_degree(account_id) + G.out_degree(account_id)
            },
            **account_info
        }
    
    # ============================================================================
    # DETECÇÃO DE COMUNIDADES
    # ============================================================================
    
    def detect_communities_louvain(self) -> Dict[str, Any]:
        """
        Detecta comunidades usando o algoritmo Louvain
        Identifica grupos de contas fortemente relacionadas
        """
        logger.info("Detectando comunidades com Louvain...")
        G = self._build_networkx_graph(include_amounts=True)
        
        if G.number_of_nodes() == 0:
            return {"communities": [], "total_communities": 0}
        
        # Converter para não-direcionado para Louvain
        G_undirected = G.to_undirected()
        
        # Detectar comunidades
        partition = community_louvain.best_partition(G_undirected, weight='weight')
        
        # Organizar resultados
        communities = {}
        for account_id, community_id in partition.items():
            if community_id not in communities:
                communities[community_id] = []
            communities[community_id].append(account_id)
        
        # Calcular estatísticas de cada comunidade
        community_stats = []
        for comm_id, members in communities.items():
            subgraph = G.subgraph(members)
            
            # Calcular volume total de transações na comunidade
            total_volume = sum(data.get('weight', 0) 
                             for _, _, data in subgraph.edges(data=True))
            
            # Verificar se tem contas suspeitas
            suspicious_count = self._count_suspicious_accounts(members)
            
            community_stats.append({
                "community_id": comm_id,
                "size": len(members),
                "members": members[:10],  # Primeiros 10
                "total_members": len(members),
                "internal_edges": subgraph.number_of_edges(),
                "total_volume": round(total_volume, 2),
                "suspicious_accounts": suspicious_count,
                "risk_level": "HIGH" if suspicious_count > len(members) * 0.3 else "MEDIUM" if suspicious_count > 0 else "LOW"
            })
        
        # Ordenar por tamanho
        community_stats.sort(key=lambda x: x['size'], reverse=True)
        
        logger.info(f"Detectadas {len(community_stats)} comunidades")
        
        return {
            "algorithm": "Louvain",
            "total_communities": len(community_stats),
            "modularity": round(community_louvain.modularity(partition, G_undirected, weight='weight'), 4),
            "communities": community_stats
        }
    
    def detect_communities_label_propagation(self) -> Dict[str, Any]:
        """
        Detecta comunidades usando Label Propagation
        Mais rápido que Louvain, bom para grafos grandes
        """
        logger.info("Detectando comunidades com Label Propagation...")
        G = self._build_networkx_graph()
        
        if G.number_of_nodes() == 0:
            return {"communities": [], "total_communities": 0}
        
        # Converter para não-direcionado
        G_undirected = G.to_undirected()
        
        # Detectar comunidades
        communities_generator = nx.algorithms.community.label_propagation_communities(G_undirected)
        communities = list(communities_generator)
        
        # Organizar resultados
        community_stats = []
        for idx, members in enumerate(communities):
            members_list = list(members)
            subgraph = G.subgraph(members_list)
            
            suspicious_count = self._count_suspicious_accounts(members_list)
            
            community_stats.append({
                "community_id": idx,
                "size": len(members_list),
                "members": members_list[:10],
                "total_members": len(members_list),
                "internal_edges": subgraph.number_of_edges(),
                "suspicious_accounts": suspicious_count,
                "risk_level": "HIGH" if suspicious_count > len(members_list) * 0.3 else "MEDIUM" if suspicious_count > 0 else "LOW"
            })
        
        community_stats.sort(key=lambda x: x['size'], reverse=True)
        
        logger.info(f"Detectadas {len(community_stats)} comunidades")
        
        return {
            "algorithm": "Label Propagation",
            "total_communities": len(community_stats),
            "communities": community_stats
        }
    
    def find_connected_components(self) -> Dict[str, Any]:
        """
        Encontra componentes conectados - sub-redes isoladas
        Útil para identificar grupos independentes
        """
        logger.info("Encontrando componentes conectados...")
        G = self._build_networkx_graph(include_amounts=True)
        
        if G.number_of_nodes() == 0:
            return {"components": [], "total_components": 0}
        
        # Componentes fortemente conectados
        strongly_connected = list(nx.strongly_connected_components(G))
        
        # Componentes fracamente conectados
        weakly_connected = list(nx.weakly_connected_components(G))
        
        # Analisar componentes fracos (mais interessante para AML)
        component_stats = []
        for idx, component in enumerate(weakly_connected):
            members = list(component)
            subgraph = G.subgraph(members)
            
            total_volume = sum(data.get('weight', 0) 
                             for _, _, data in subgraph.edges(data=True))
            
            suspicious_count = self._count_suspicious_accounts(members)
            
            component_stats.append({
                "component_id": idx,
                "size": len(members),
                "members": members[:10],
                "total_members": len(members),
                "edges": subgraph.number_of_edges(),
                "total_volume": round(total_volume, 2),
                "density": round(nx.density(subgraph), 4),
                "suspicious_accounts": suspicious_count,
                "is_isolated": len(members) < 5,
                "risk_level": "HIGH" if suspicious_count > len(members) * 0.3 else "MEDIUM" if suspicious_count > 0 else "LOW"
            })
        
        component_stats.sort(key=lambda x: x['size'], reverse=True)
        
        logger.info(f"Encontrados {len(component_stats)} componentes")
        
        return {
            "strongly_connected_components": len(strongly_connected),
            "weakly_connected_components": len(weakly_connected),
            "largest_component_size": max(len(c) for c in weakly_connected) if weakly_connected else 0,
            "components": component_stats
        }
    
    def find_cliques(self, min_size: int = 3) -> Dict[str, Any]:
        """
        Detecta cliques - grupos totalmente conectados
        Pode indicar conluio ou redes criminosas organizadas
        """
        logger.info(f"Detectando cliques (tamanho mínimo: {min_size})...")
        G = self._build_networkx_graph()
        
        if G.number_of_nodes() == 0:
            return {"cliques": [], "total_cliques": 0}
        
        # Converter para não-direcionado
        G_undirected = G.to_undirected()
        
        # Encontrar cliques
        cliques = list(nx.find_cliques(G_undirected))
        
        # Filtrar por tamanho mínimo
        filtered_cliques = [c for c in cliques if len(c) >= min_size]
        
        # Analisar cliques
        clique_stats = []
        for idx, clique in enumerate(filtered_cliques):
            subgraph = G.subgraph(clique)
            
            total_volume = sum(data.get('weight', 0) 
                             for _, _, data in subgraph.edges(data=True))
            
            suspicious_count = self._count_suspicious_accounts(clique)
            
            clique_stats.append({
                "clique_id": idx,
                "size": len(clique),
                "members": list(clique),
                "total_volume": round(total_volume, 2),
                "suspicious_accounts": suspicious_count,
                "risk_level": "CRITICAL" if suspicious_count > len(clique) * 0.5 else "HIGH" if suspicious_count > 0 else "MEDIUM"
            })
        
        # Ordenar por tamanho
        clique_stats.sort(key=lambda x: x['size'], reverse=True)
        
        logger.info(f"Detectados {len(clique_stats)} cliques")
        
        return {
            "total_cliques": len(clique_stats),
            "largest_clique_size": max((c['size'] for c in clique_stats), default=0),
            "cliques": clique_stats[:50]  # Limitar a 50
        }
    
    # ============================================================================
    # ANÁLISES TEMPORAIS
    # ============================================================================
    
    def analyze_time_windows(self, window_hours: int = 24) -> Dict[str, Any]:
        """
        Analisa a rede em janelas temporais
        Mostra evolução da rede ao longo do tempo
        """
        logger.info(f"Analisando janelas temporais ({window_hours}h)...")
        
        try:
            # Buscar todas transações com timestamp
            query = """
            MATCH (a:Account)-[t:TRANSACTED]->(b:Account)
            WHERE t.timestamp IS NOT NULL
            RETURN 
                t.timestamp as timestamp,
                count(*) as transaction_count,
                sum(t.amount) as total_volume
            ORDER BY t.timestamp
            """
            
            result = self.session.run(query)
            records = []
            for record in result:
                rec_dict = dict(record)
                # Converter neo4j.time.DateTime para string ISO
                if 'timestamp' in rec_dict and rec_dict['timestamp']:
                    rec_dict['timestamp'] = rec_dict['timestamp'].iso_format()
                records.append(rec_dict)
            
            if not records:
                return {"windows": [], "total_windows": 0}
            
            df = pd.DataFrame(records)
            
            # Converter timestamp para datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Criar janelas de tempo
            df['window'] = df['timestamp'].dt.floor(f'{window_hours}H')
            
            # Agrupar por janela
            windows_stats = df.groupby('window').agg({
                'transaction_count': 'sum',
                'total_volume': 'sum'
            }).reset_index()
            
            # Calcular métricas para cada janela (limitar para evitar timeout)
            window_results = []
            max_windows = 10  # Limitar a 10 janelas para performance
            
            for idx, (_, row) in enumerate(windows_stats.iterrows()):
                if idx >= max_windows:
                    break
                    
                start_time = row['window']
                end_time = start_time + timedelta(hours=window_hours)
                
                try:
                    # Construir grafo para essa janela
                    G = self._build_networkx_graph(
                        include_amounts=True,
                        start_date=start_time,
                        end_date=end_time
                    )
                    
                    window_results.append({
                        "window_start": start_time.strftime('%Y-%m-%d %H:%M:%S'),
                        "window_end": end_time.strftime('%Y-%m-%d %H:%M:%S'),
                        "transaction_count": int(row['transaction_count']),
                        "total_volume": round(float(row['total_volume']), 2),
                        "unique_accounts": G.number_of_nodes(),
                        "network_edges": G.number_of_edges(),
                        "network_density": round(nx.density(G), 6) if G.number_of_nodes() > 0 else 0
                    })
                except Exception as e:
                    logger.error(f"Erro ao processar janela {start_time}: {e}")
                    continue
            
            logger.info(f"Analisadas {len(window_results)} janelas temporais")
            
            return {
                "window_size_hours": window_hours,
                "total_windows": len(window_results),
                "windows": window_results
            }
        except Exception as e:
            logger.error(f"Erro em analyze_time_windows: {e}")
            raise
    
    def detect_bursts(self, threshold_std: float = 2.0) -> Dict[str, Any]:
        """
        Detecta picos súbitos de atividade (bursts)
        Identifica momentos de atividade anormal
        """
        logger.info(f"Detectando bursts (threshold: {threshold_std} std)...")
        
        # Buscar transações agrupadas por hora
        query = """
        MATCH (a:Account)-[t:TRANSACTED]->(b:Account)
        WHERE t.timestamp IS NOT NULL
        WITH 
            datetime(t.timestamp).year as year,
            datetime(t.timestamp).month as month,
            datetime(t.timestamp).day as day,
            datetime(t.timestamp).hour as hour,
            count(*) as tx_count,
            sum(t.amount) as volume
        RETURN 
            year, month, day, hour,
            tx_count, volume
        ORDER BY year, month, day, hour
        """
        
        result = self.session.run(query)
        data = [dict(record) for record in result]
        
        if not data:
            return {"bursts": [], "total_bursts": 0}
        
        df = pd.DataFrame(data)
        
        # Calcular estatísticas
        mean_tx = df['tx_count'].mean()
        std_tx = df['tx_count'].std()
        mean_vol = df['volume'].mean()
        std_vol = df['volume'].std()
        
        # Detectar bursts
        df['is_burst_tx'] = df['tx_count'] > (mean_tx + threshold_std * std_tx)
        df['is_burst_vol'] = df['volume'] > (mean_vol + threshold_std * std_vol)
        df['is_burst'] = df['is_burst_tx'] | df['is_burst_vol']
        
        bursts = df[df['is_burst']].to_dict('records')
        
        # Formatar resultados
        burst_results = []
        for burst in bursts:
            burst_results.append({
                "timestamp": f"{burst['year']}-{burst['month']:02d}-{burst['day']:02d} {burst['hour']:02d}:00",
                "transaction_count": int(burst['tx_count']),
                "total_volume": round(float(burst['volume']), 2),
                "deviation_tx": round((burst['tx_count'] - mean_tx) / std_tx, 2),
                "deviation_volume": round((burst['volume'] - mean_vol) / std_vol, 2),
                "severity": "CRITICAL" if burst['tx_count'] > mean_tx + 3*std_tx else "HIGH"
            })
        
        logger.info(f"Detectados {len(burst_results)} bursts")
        
        return {
            "threshold_std": threshold_std,
            "baseline_stats": {
                "mean_transactions": round(mean_tx, 2),
                "std_transactions": round(std_tx, 2),
                "mean_volume": round(mean_vol, 2),
                "std_volume": round(std_vol, 2)
            },
            "total_bursts": len(burst_results),
            "bursts": burst_results
        }
    
    def calculate_velocity_analysis(self, account_id: str) -> Dict[str, Any]:
        """
        Analisa velocidade de movimentação de fundos para uma conta
        Detecta transferências rápidas em cadeia (layering)
        """
        logger.info(f"Calculando velocity analysis para {account_id}...")
        
        # Buscar cadeias de transações
        query = """
        MATCH path = (start:Account {account_id: $account_id})-[t:TRANSACTED*1..5]->(end:Account)
        WHERE ALL(rel in t WHERE rel.timestamp IS NOT NULL)
        WITH path, relationships(path) as rels
        WITH path, rels,
            [rel in rels | datetime(rel.timestamp)] as timestamps,
            [rel in rels | rel.amount] as amounts
        RETURN 
            [node in nodes(path) | node.account_id] as account_chain,
            timestamps,
            amounts,
            size(timestamps) as chain_length
        ORDER BY chain_length DESC
        LIMIT 100
        """
        
        result = self.session.run(query, account_id=account_id)
        chains = [dict(record) for record in result]
        
        if not chains:
            return {
                "account_id": account_id,
                "chains": [],
                "max_velocity": 0,
                "risk_level": "LOW"
            }
        
        # Analisar velocidade de cada cadeia
        chain_analysis = []
        max_velocity = 0
        
        for chain in chains:
            timestamps = chain['timestamps']
            amounts = chain['amounts']
            account_chain = chain['account_chain']
            
            if len(timestamps) < 2:
                continue
            
            # Calcular tempo total e velocidade
            time_diffs = []
            for i in range(1, len(timestamps)):
                # Neo4j retorna datetime objects
                diff = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600  # horas
                time_diffs.append(diff)
            
            total_time = sum(time_diffs)
            total_amount = sum(amounts)
            
            if total_time > 0:
                velocity = total_amount / total_time  # $/hora
                max_velocity = max(max_velocity, velocity)
                
                chain_analysis.append({
                    "chain": account_chain,
                    "chain_length": len(account_chain),
                    "total_amount": round(total_amount, 2),
                    "total_time_hours": round(total_time, 2),
                    "velocity_per_hour": round(velocity, 2),
                    "avg_time_between_hops": round(sum(time_diffs) / len(time_diffs), 2) if time_diffs else 0,
                    "risk_level": "CRITICAL" if velocity > 10000 and total_time < 24 else "HIGH" if velocity > 5000 else "MEDIUM"
                })
        
        # Ordenar por velocidade
        chain_analysis.sort(key=lambda x: x['velocity_per_hour'], reverse=True)
        
        # Determinar risk level geral
        if max_velocity > 10000:
            risk_level = "CRITICAL"
        elif max_velocity > 5000:
            risk_level = "HIGH"
        elif max_velocity > 1000:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        logger.info(f"Velocity analysis: {len(chain_analysis)} cadeias, max velocity: {max_velocity:.2f}")
        
        return {
            "account_id": account_id,
            "total_chains": len(chain_analysis),
            "max_velocity_per_hour": round(max_velocity, 2),
            "chains": chain_analysis[:20],  # Top 20
            "risk_level": risk_level,
            "explanation": "Velocity > 10k/h é crítico, > 5k/h é alto"
        }
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    def _get_account_info(self, account_id: str) -> Dict[str, Any]:
        """Busca informações básicas de uma conta"""
        query = """
        MATCH (a:Account {account_id: $account_id})
        OPTIONAL MATCH (c:Customer)-[:OWNS]->(a)
        OPTIONAL MATCH (a)-[t:TRANSACTED]->()
        RETURN 
            a.account_id as account_id,
            a.is_sar as is_suspicious,
            c.customer_id as customer_id,
            count(t) as transaction_count
        """
        
        result = self.session.run(query, account_id=account_id)
        record = result.single()
        
        if not record:
            return {
                "is_suspicious": False,
                "customer_id": None,
                "transaction_count": 0
            }
        
        return {
            "is_suspicious": record.get('is_suspicious', False),
            "customer_id": record.get('customer_id'),
            "transaction_count": record.get('transaction_count', 0)
        }
    
    def _count_suspicious_accounts(self, account_ids: List[str]) -> int:
        """Conta quantas contas suspeitas existem em uma lista"""
        if not account_ids:
            return 0
        
        query = """
        MATCH (a:Account)
        WHERE a.account_id IN $account_ids AND a.is_sar = true
        RETURN count(a) as count
        """
        
        result = self.session.run(query, account_ids=account_ids)
        record = result.single()
        
        return record['count'] if record else 0

