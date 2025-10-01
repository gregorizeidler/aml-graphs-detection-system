"""
Gerenciamento de conexões com bancos de dados.
"""

from neo4j import GraphDatabase
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


# Neo4j
class Neo4jConnection:
    """Gerenciador de conexão com Neo4j."""
    
    def __init__(self):
        self._driver = None
    
    def connect(self):
        """Conecta ao Neo4j."""
        self._driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
    
    def close(self):
        """Fecha a conexão."""
        if self._driver:
            self._driver.close()
    
    def get_session(self):
        """Retorna uma sessão do Neo4j."""
        return self._driver.session()
    
    @property
    def driver(self):
        """Retorna o driver do Neo4j."""
        return self._driver


neo4j_conn = Neo4jConnection()


# PostgreSQL
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency para obter sessão do PostgreSQL."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_neo4j():
    """Dependency para obter sessão do Neo4j."""
    session = neo4j_conn.get_session()
    try:
        yield session
    finally:
        session.close()


def get_neo4j_driver():
    """Retorna o driver do Neo4j para serviços que precisam dele diretamente."""
    return neo4j_conn.driver

