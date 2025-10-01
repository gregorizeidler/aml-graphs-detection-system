"""
Script para carregar dados no Neo4j.
"""

import os
from pathlib import Path
from neo4j import GraphDatabase
import pandas as pd
from tqdm import tqdm

# Configurações
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "aml_password_123")

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"


def clear_database(driver):
    """Limpa o banco de dados."""
    print("🗑️  Limpando banco de dados...")
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("✅ Banco de dados limpo")


def create_constraints(driver):
    """Cria constraints e índices."""
    print("🔧 Criando constraints e índices...")
    
    constraints = [
        "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.customer_id IS UNIQUE",
        "CREATE CONSTRAINT account_id IF NOT EXISTS FOR (a:Account) REQUIRE a.account_id IS UNIQUE",
    ]
    
    indexes = [
        "CREATE INDEX customer_risk IF NOT EXISTS FOR (c:Customer) ON (c.risk_rating)",
        "CREATE INDEX account_balance IF NOT EXISTS FOR (a:Account) ON (a.balance)",
    ]
    
    with driver.session() as session:
        for constraint in constraints:
            try:
                session.run(constraint)
            except Exception as e:
                print(f"  ⚠️  {e}")
        
        for index in indexes:
            try:
                session.run(index)
            except Exception as e:
                print(f"  ⚠️  {e}")
    
    print("✅ Constraints e índices criados")


def load_customers(driver, df):
    """Carrega clientes no Neo4j."""
    print(f"👥 Carregando {len(df)} clientes...")
    
    query = """
    UNWIND $customers AS customer
    CREATE (c:Customer {
        customer_id: customer.customer_id,
        name: customer.name,
        customer_type: customer.customer_type,
        risk_rating: customer.risk_rating,
        country: customer.country,
        registration_date: datetime(customer.registration_date)
    })
    """
    
    customers = df.to_dict('records')
    batch_size = 500
    
    with driver.session() as session:
        for i in tqdm(range(0, len(customers), batch_size)):
            batch = customers[i:i+batch_size]
            session.run(query, customers=batch)
    
    print("✅ Clientes carregados")


def load_accounts(driver, df):
    """Carrega contas no Neo4j."""
    print(f"🏦 Carregando {len(df)} contas...")
    
    query = """
    UNWIND $accounts AS account
    CREATE (a:Account {
        account_id: account.account_id,
        account_type: account.account_type,
        balance: toFloat(account.balance),
        opening_date: datetime(account.opening_date),
        status: account.status,
        risk_score: 0.0
    })
    """
    
    accounts = df.to_dict('records')
    batch_size = 500
    
    with driver.session() as session:
        for i in tqdm(range(0, len(accounts), batch_size)):
            batch = accounts[i:i+batch_size]
            session.run(query, accounts=batch)
    
    print("✅ Contas carregadas")


def create_ownership_relationships(driver, df):
    """Cria relacionamentos Customer -> Account."""
    print(f"🔗 Criando relacionamentos de propriedade...")
    
    query = """
    UNWIND $accounts AS account
    MATCH (c:Customer {customer_id: account.customer_id})
    MATCH (a:Account {account_id: account.account_id})
    CREATE (c)-[:OWNS]->(a)
    """
    
    accounts = df[['customer_id', 'account_id']].to_dict('records')
    batch_size = 500
    
    with driver.session() as session:
        for i in tqdm(range(0, len(accounts), batch_size)):
            batch = accounts[i:i+batch_size]
            session.run(query, accounts=batch)
    
    print("✅ Relacionamentos criados")


def load_transactions(driver, df):
    """Carrega transações no Neo4j."""
    print(f"💸 Carregando {len(df)} transações...")
    
    query = """
    UNWIND $transactions AS txn
    MATCH (source:Account {account_id: txn.source_account})
    MATCH (target:Account {account_id: txn.target_account})
    CREATE (source)-[t:TRANSACTED {
        transaction_id: txn.transaction_id,
        amount: toFloat(txn.amount),
        timestamp: datetime(txn.timestamp),
        transaction_type: txn.transaction_type,
        is_suspicious: txn.is_suspicious,
        typology: txn.typology
    }]->(target)
    """
    
    # Converter boolean para Neo4j
    df['is_suspicious'] = df['is_suspicious'].astype(bool)
    
    transactions = df.to_dict('records')
    batch_size = 200
    
    with driver.session() as session:
        for i in tqdm(range(0, len(transactions), batch_size)):
            batch = transactions[i:i+batch_size]
            try:
                session.run(query, transactions=batch)
            except Exception as e:
                print(f"  ⚠️  Erro no batch {i}: {e}")
    
    print("✅ Transações carregadas")


def update_risk_scores(driver):
    """Atualiza risk scores das contas."""
    print("📊 Calculando risk scores...")
    
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
    
    with driver.session() as session:
        result = session.run(query)
        record = result.single()
        count = record["updated_count"] if record else 0
        print(f"✅ Risk scores atualizados para {count} contas")


def main():
    """Função principal."""
    print("🚀 Iniciando carregamento de dados no Neo4j...")
    print(f"📍 URI: {NEO4J_URI}")
    
    # Conectar ao Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        # Verificar conexão
        driver.verify_connectivity()
        print("✅ Conectado ao Neo4j")
        
        # Limpar banco
        clear_database(driver)
        
        # Criar constraints
        create_constraints(driver)
        
        # Carregar dados
        print("\n📂 Carregando arquivos CSV...")
        customers_df = pd.read_csv(DATA_DIR / "customers.csv")
        accounts_df = pd.read_csv(DATA_DIR / "accounts.csv")
        transactions_df = pd.read_csv(DATA_DIR / "transactions.csv")
        
        # Carregar no Neo4j
        load_customers(driver, customers_df)
        load_accounts(driver, accounts_df)
        create_ownership_relationships(driver, accounts_df)
        load_transactions(driver, transactions_df)
        
        # Atualizar risk scores
        update_risk_scores(driver)
        
        print("\n✅ Todos os dados carregados com sucesso!")
        print(f"   • Clientes: {len(customers_df)}")
        print(f"   • Contas: {len(accounts_df)}")
        print(f"   • Transações: {len(transactions_df)}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        raise
    finally:
        driver.close()


if __name__ == "__main__":
    main()

