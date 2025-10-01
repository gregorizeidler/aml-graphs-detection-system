"""
Script para gerar dados sintéticos de transações bancárias
simulando tipologias de lavagem de dinheiro (AML).

Tipologias implementadas:
- Fan-out: Uma conta distribui fundos para múltiplas contas
- Fan-in: Múltiplas contas enviam fundos para uma conta central
- Ciclos: Transferências circulares para obscurecer origem
- Smurfing: Múltiplas transações pequenas para evitar detecção
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path

# Configurações
np.random.seed(42)
NUM_ACCOUNTS = 1000
NUM_CUSTOMERS = 800
NUM_TRANSACTIONS = 10000
SUSPICIOUS_RATIO = 0.15  # 15% de transações suspeitas

# Diretórios
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Criar diretórios
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def generate_customers():
    """Gera dados de clientes."""
    customers = []
    
    for i in range(NUM_CUSTOMERS):
        customer = {
            "customer_id": f"CUST_{i:05d}",
            "name": f"Customer {i}",
            "customer_type": np.random.choice(
                ["individual", "business"], 
                p=[0.7, 0.3]
            ),
            "risk_rating": np.random.choice(
                ["low", "medium", "high"], 
                p=[0.7, 0.25, 0.05]
            ),
            "country": np.random.choice(
                ["USA", "UK", "Brazil", "China", "Russia", "Germany"],
                p=[0.3, 0.2, 0.15, 0.15, 0.1, 0.1]
            ),
            "registration_date": (
                datetime.now() - timedelta(days=np.random.randint(30, 3650))
            ).strftime("%Y-%m-%d"),
        }
        customers.append(customer)
    
    return pd.DataFrame(customers)


def generate_accounts(customers_df):
    """Gera contas bancárias."""
    accounts = []
    
    for i in range(NUM_ACCOUNTS):
        # Alguns clientes têm múltiplas contas
        customer_id = customers_df.iloc[
            np.random.randint(0, len(customers_df))
        ]["customer_id"]
        
        account = {
            "account_id": f"ACC_{i:05d}",
            "customer_id": customer_id,
            "account_type": np.random.choice(
                ["checking", "savings", "business"], 
                p=[0.5, 0.3, 0.2]
            ),
            "balance": np.random.lognormal(10, 2),
            "opening_date": (
                datetime.now() - timedelta(days=np.random.randint(1, 3650))
            ).strftime("%Y-%m-%d"),
            "status": np.random.choice(
                ["active", "dormant", "closed"], 
                p=[0.85, 0.10, 0.05]
            ),
        }
        accounts.append(account)
    
    return pd.DataFrame(accounts)


def generate_fan_out_pattern(accounts_df, start_date):
    """
    Tipologia Fan-out: Uma conta (fonte) distribui fundos para múltiplas contas.
    Padrão comum em lavagem de dinheiro para distribuir fundos ilícitos.
    """
    transactions = []
    source_account = accounts_df.sample(1).iloc[0]["account_id"]
    target_accounts = accounts_df.sample(np.random.randint(5, 15))
    
    base_time = start_date
    
    for idx, row in target_accounts.iterrows():
        amount = np.random.uniform(1000, 9000)  # Abaixo do limite de reporte
        transaction = {
            "transaction_id": f"TXN_{len(transactions):08d}",
            "source_account": source_account,
            "target_account": row["account_id"],
            "amount": round(amount, 2),
            "timestamp": (base_time + timedelta(minutes=np.random.randint(1, 120))).isoformat(),
            "transaction_type": "transfer",
            "is_suspicious": True,
            "typology": "fan_out",
        }
        transactions.append(transaction)
    
    return transactions


def generate_fan_in_pattern(accounts_df, start_date):
    """
    Tipologia Fan-in: Múltiplas contas enviam fundos para uma conta central.
    Usado para consolidar fundos de várias fontes em uma conta.
    """
    transactions = []
    target_account = accounts_df.sample(1).iloc[0]["account_id"]
    source_accounts = accounts_df.sample(np.random.randint(5, 15))
    
    base_time = start_date
    
    for idx, row in source_accounts.iterrows():
        amount = np.random.uniform(1000, 9000)
        transaction = {
            "transaction_id": f"TXN_{len(transactions):08d}",
            "source_account": row["account_id"],
            "target_account": target_account,
            "amount": round(amount, 2),
            "timestamp": (base_time + timedelta(minutes=np.random.randint(1, 120))).isoformat(),
            "transaction_type": "transfer",
            "is_suspicious": True,
            "typology": "fan_in",
        }
        transactions.append(transaction)
    
    return transactions


def generate_cycle_pattern(accounts_df, start_date):
    """
    Tipologia Ciclo: Transferências circulares entre contas.
    Usado para obscurecer a origem dos fundos.
    """
    transactions = []
    cycle_length = np.random.randint(3, 7)
    cycle_accounts = accounts_df.sample(cycle_length)["account_id"].tolist()
    
    base_time = start_date
    initial_amount = np.random.uniform(10000, 50000)
    
    for i in range(cycle_length):
        source = cycle_accounts[i]
        target = cycle_accounts[(i + 1) % cycle_length]
        amount = initial_amount * np.random.uniform(0.9, 0.95)  # Pequena perda a cada hop
        
        transaction = {
            "transaction_id": f"TXN_{len(transactions):08d}",
            "source_account": source,
            "target_account": target,
            "amount": round(amount, 2),
            "timestamp": (base_time + timedelta(hours=i * 2)).isoformat(),
            "transaction_type": "transfer",
            "is_suspicious": True,
            "typology": "cycle",
        }
        transactions.append(transaction)
    
    return transactions


def generate_normal_transactions(accounts_df, num_transactions):
    """Gera transações normais (legítimas)."""
    transactions = []
    
    for i in range(num_transactions):
        source = accounts_df.sample(1).iloc[0]
        target = accounts_df.sample(1).iloc[0]
        
        # Evitar auto-transferência
        while source["account_id"] == target["account_id"]:
            target = accounts_df.sample(1).iloc[0]
        
        # Transações normais têm distribuição mais natural
        amount = np.random.choice([
            np.random.uniform(10, 100),      # Pequenas: 40%
            np.random.uniform(100, 1000),    # Médias: 40%
            np.random.uniform(1000, 10000),  # Grandes: 20%
        ], p=[0.4, 0.4, 0.2])
        
        transaction = {
            "transaction_id": f"TXN_{i:08d}",
            "source_account": source["account_id"],
            "target_account": target["account_id"],
            "amount": round(amount, 2),
            "timestamp": (
                datetime.now() - timedelta(days=np.random.randint(0, 365))
            ).isoformat(),
            "transaction_type": np.random.choice(
                ["transfer", "payment", "withdrawal", "deposit"],
                p=[0.5, 0.3, 0.1, 0.1]
            ),
            "is_suspicious": False,
            "typology": "normal",
        }
        transactions.append(transaction)
    
    return transactions


def generate_transactions(accounts_df):
    """Gera todas as transações (normais e suspeitas)."""
    all_transactions = []
    
    # Calcular número de transações suspeitas
    num_suspicious = int(NUM_TRANSACTIONS * SUSPICIOUS_RATIO)
    num_normal = NUM_TRANSACTIONS - num_suspicious
    
    # Gerar transações suspeitas
    patterns_per_type = num_suspicious // 3
    
    for _ in range(patterns_per_type):
        start_date = datetime.now() - timedelta(days=np.random.randint(0, 365))
        all_transactions.extend(generate_fan_out_pattern(accounts_df, start_date))
    
    for _ in range(patterns_per_type):
        start_date = datetime.now() - timedelta(days=np.random.randint(0, 365))
        all_transactions.extend(generate_fan_in_pattern(accounts_df, start_date))
    
    for _ in range(patterns_per_type):
        start_date = datetime.now() - timedelta(days=np.random.randint(0, 365))
        all_transactions.extend(generate_cycle_pattern(accounts_df, start_date))
    
    # Gerar transações normais
    all_transactions.extend(generate_normal_transactions(accounts_df, num_normal))
    
    # Converter para DataFrame e reorganizar IDs
    df = pd.DataFrame(all_transactions)
    df = df.sample(frac=1).reset_index(drop=True)  # Shuffle
    df["transaction_id"] = [f"TXN_{i:08d}" for i in range(len(df))]
    
    return df


def main():
    """Função principal."""
    print("🚀 Iniciando geração de dados AML...")
    
    # Gerar dados
    print("📊 Gerando clientes...")
    customers_df = generate_customers()
    
    print("🏦 Gerando contas...")
    accounts_df = generate_accounts(customers_df)
    
    print("💸 Gerando transações...")
    transactions_df = generate_transactions(accounts_df)
    
    # Salvar dados brutos
    print("💾 Salvando dados...")
    customers_df.to_csv(RAW_DIR / "customers.csv", index=False)
    accounts_df.to_csv(RAW_DIR / "accounts.csv", index=False)
    transactions_df.to_csv(RAW_DIR / "transactions.csv", index=False)
    
    # Estatísticas
    print("\n📈 Estatísticas dos Dados Gerados:")
    print(f"  • Clientes: {len(customers_df)}")
    print(f"  • Contas: {len(accounts_df)}")
    print(f"  • Transações: {len(transactions_df)}")
    print(f"  • Transações Suspeitas: {len(transactions_df[transactions_df['is_suspicious']])} ({len(transactions_df[transactions_df['is_suspicious']])/len(transactions_df)*100:.1f}%)")
    print(f"\nTipologias:")
    print(transactions_df['typology'].value_counts())
    
    print(f"\n✅ Dados salvos em: {RAW_DIR}")


if __name__ == "__main__":
    main()

