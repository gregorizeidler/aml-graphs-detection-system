.PHONY: help install dev test lint format clean docker-up docker-down docker-rebuild data

help:
	@echo "🔧 AML Detection System - Available Commands:"
	@echo ""
	@echo "  make install        - Instalar dependências"
	@echo "  make dev           - Rodar servidor de desenvolvimento"
	@echo "  make test          - Executar todos os testes"
	@echo "  make lint          - Executar linters"
	@echo "  make format        - Formatar código"
	@echo "  make clean         - Limpar arquivos temporários"
	@echo "  make docker-up     - Subir containers Docker"
	@echo "  make docker-down   - Parar containers Docker"
	@echo "  make docker-rebuild - Reconstruir containers"
	@echo "  make data          - Gerar dados sintéticos"
	@echo "  make load-neo4j    - Carregar dados no Neo4j"
	@echo ""

install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v --cov=app --cov-report=term-missing

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

lint:
	@echo "Running Ruff..."
	ruff check app/ tests/
	@echo "Running Black check..."
	black --check app/ tests/
	@echo "Running MyPy..."
	mypy app/ --ignore-missing-imports

format:
	@echo "Formatting with Black..."
	black app/ tests/
	@echo "Sorting imports..."
	ruff check --fix app/ tests/

clean:
	@echo "Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml
	@echo "✅ Clean complete"

docker-up:
	docker-compose up -d
	@echo "✅ Services started"
	@echo "📊 Neo4j Browser: http://localhost:7474"
	@echo "🚀 API: http://localhost:8000"
	@echo "📖 API Docs: http://localhost:8000/docs"

docker-down:
	docker-compose down
	@echo "✅ Services stopped"

docker-rebuild:
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d
	@echo "✅ Services rebuilt and started"

docker-logs:
	docker-compose logs -f

data:
	@echo "📊 Generating synthetic AML data..."
	python scripts/generate_aml_data.py
	@echo "✅ Data generated in data/raw/"

load-neo4j:
	@echo "📤 Loading data into Neo4j..."
	@echo "Copy data files to Neo4j import directory..."
	docker cp data/raw/customers.csv aml-neo4j:/var/lib/neo4j/import/
	docker cp data/raw/accounts.csv aml-neo4j:/var/lib/neo4j/import/
	docker cp data/raw/transactions.csv aml-neo4j:/var/lib/neo4j/import/
	@echo "✅ Data files copied. Run Cypher queries from app/services/neo4j_queries.cypher"

setup: install data
	@echo "✅ Setup complete! Run 'make docker-up' to start services"

