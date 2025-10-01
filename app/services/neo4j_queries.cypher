// =====================================
// Neo4j Cypher Queries - AML Detection
// =====================================

// 1. Criar Schema e Constraints
// =====================================
CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.customer_id IS UNIQUE;
CREATE CONSTRAINT account_id IF NOT EXISTS FOR (a:Account) REQUIRE a.account_id IS UNIQUE;
CREATE CONSTRAINT transaction_id IF NOT EXISTS FOR (t:Transaction) REQUIRE t.transaction_id IS UNIQUE;

// Criar índices para performance
CREATE INDEX customer_risk IF NOT EXISTS FOR (c:Customer) ON (c.risk_rating);
CREATE INDEX account_balance IF NOT EXISTS FOR (a:Account) ON (a.balance);
CREATE INDEX transaction_suspicious IF NOT EXISTS FOR (t:Transaction) ON (t.is_suspicious);
CREATE INDEX transaction_timestamp IF NOT EXISTS FOR (t:Transaction) ON (t.timestamp);


// 2. Carregar Dados (Customers)
// =====================================
LOAD CSV WITH HEADERS FROM 'file:///customers.csv' AS row
CREATE (c:Customer {
    customer_id: row.customer_id,
    name: row.name,
    customer_type: row.customer_type,
    risk_rating: row.risk_rating,
    country: row.country,
    registration_date: datetime(row.registration_date)
});


// 3. Carregar Dados (Accounts)
// =====================================
LOAD CSV WITH HEADERS FROM 'file:///accounts.csv' AS row
CREATE (a:Account {
    account_id: row.account_id,
    account_type: row.account_type,
    balance: toFloat(row.balance),
    opening_date: datetime(row.opening_date),
    status: row.status,
    risk_score: 0.0
});


// 4. Criar Relacionamento Customer -> Account
// =====================================
LOAD CSV WITH HEADERS FROM 'file:///accounts.csv' AS row
MATCH (c:Customer {customer_id: row.customer_id})
MATCH (a:Account {account_id: row.account_id})
CREATE (c)-[:OWNS]->(a);


// 5. Carregar Transações e Criar Relacionamentos
// =====================================
LOAD CSV WITH HEADERS FROM 'file:///transactions.csv' AS row
MATCH (source:Account {account_id: row.source_account})
MATCH (target:Account {account_id: row.target_account})
CREATE (source)-[t:TRANSACTED {
    transaction_id: row.transaction_id,
    amount: toFloat(row.amount),
    timestamp: datetime(row.timestamp),
    transaction_type: row.transaction_type,
    is_suspicious: CASE row.is_suspicious WHEN 'True' THEN true ELSE false END,
    typology: row.typology
}]->(target);


// 6. Query: Buscar Rede de um Cliente (com profundidade)
// =====================================
// Parâmetros: $customer_id, $depth
MATCH path = (c:Customer {customer_id: $customer_id})-[:OWNS]->(a:Account)
              -[:TRANSACTED*1..$depth]-(other:Account)
RETURN path;


// 7. Query: Detectar Padrão Fan-Out
// =====================================
// Encontra contas que enviaram dinheiro para muitas contas em curto período
MATCH (source:Account)-[t:TRANSACTED]->(target:Account)
WHERE t.timestamp > datetime() - duration('P30D')
WITH source, COUNT(DISTINCT target) as num_targets, 
     SUM(t.amount) as total_amount,
     COLLECT(DISTINCT target.account_id) as targets
WHERE num_targets >= 5
RETURN source.account_id, num_targets, total_amount, targets
ORDER BY num_targets DESC;


// 8. Query: Detectar Padrão Fan-In
// =====================================
// Encontra contas que receberam dinheiro de muitas contas
MATCH (source:Account)-[t:TRANSACTED]->(target:Account)
WHERE t.timestamp > datetime() - duration('P30D')
WITH target, COUNT(DISTINCT source) as num_sources,
     SUM(t.amount) as total_amount,
     COLLECT(DISTINCT source.account_id) as sources
WHERE num_sources >= 5
RETURN target.account_id, num_sources, total_amount, sources
ORDER BY num_sources DESC;


// 9. Query: Detectar Ciclos (Circular Transfers)
// =====================================
// Encontra ciclos de transferências entre contas
MATCH path = (a:Account)-[:TRANSACTED*3..6]->(a)
WHERE ALL(r IN relationships(path) WHERE r.is_suspicious = true)
RETURN path, LENGTH(path) as cycle_length,
       REDUCE(total = 0, r IN relationships(path) | total + r.amount) as total_amount;


// 10. Query: Calcular Métricas de Centralidade
// =====================================
// PageRank para encontrar contas mais influentes
CALL gds.pageRank.stream({
    nodeProjection: 'Account',
    relationshipProjection: {
        TRANSACTED: {
            type: 'TRANSACTED',
            orientation: 'NATURAL'
        }
    }
})
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).account_id AS account_id, score
ORDER BY score DESC
LIMIT 20;


// 11. Query: Detectar Comunidades (Louvain)
// =====================================
CALL gds.louvain.stream({
    nodeProjection: 'Account',
    relationshipProjection: 'TRANSACTED'
})
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).account_id AS account_id, communityId
ORDER BY communityId;


// 12. Query: Análise de Risco de uma Conta
// =====================================
// Parâmetro: $account_id
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
RETURN a.account_id,
       outgoing_count,
       incoming_count,
       suspicious_out,
       suspicious_in,
       avg_outgoing,
       avg_incoming,
       (suspicious_out + suspicious_in) * 1.0 / (outgoing_count + incoming_count) as suspicion_ratio;


// 13. Query: Transações Suspeitas por Período
// =====================================
// Parâmetros: $start_date, $end_date
MATCH (source:Account)-[t:TRANSACTED]->(target:Account)
WHERE t.is_suspicious = true
  AND t.timestamp >= datetime($start_date)
  AND t.timestamp <= datetime($end_date)
RETURN source.account_id, target.account_id, 
       t.amount, t.timestamp, t.typology
ORDER BY t.timestamp DESC;


// 14. Query: Atualizar Risk Score das Contas
// =====================================
MATCH (a:Account)
OPTIONAL MATCH (a)-[t:TRANSACTED]-()
WITH a, COUNT(t) as total_transactions,
     SUM(CASE WHEN t.is_suspicious THEN 1 ELSE 0 END) as suspicious_count
SET a.risk_score = CASE 
    WHEN total_transactions = 0 THEN 0.0
    ELSE (suspicious_count * 1.0 / total_transactions)
END
RETURN a.account_id, a.risk_score;


// 15. Query: Shortest Path entre Contas Suspeitas
// =====================================
// Parâmetros: $account1, $account2
MATCH path = shortestPath(
    (a1:Account {account_id: $account1})-[:TRANSACTED*]-(a2:Account {account_id: $account2})
)
RETURN path, LENGTH(path) as path_length,
       [r IN relationships(path) | r.amount] as amounts,
       [r IN relationships(path) | r.is_suspicious] as suspicious_flags;


// 16. Query: Estatísticas Gerais
// =====================================
MATCH (c:Customer)
WITH COUNT(c) as total_customers
MATCH (a:Account)
WITH total_customers, COUNT(a) as total_accounts
MATCH ()-[t:TRANSACTED]->()
WITH total_customers, total_accounts, 
     COUNT(t) as total_transactions,
     SUM(CASE WHEN t.is_suspicious THEN 1 ELSE 0 END) as suspicious_transactions
RETURN total_customers, total_accounts, total_transactions, 
       suspicious_transactions,
       (suspicious_transactions * 100.0 / total_transactions) as suspicious_percentage;

