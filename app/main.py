"""
Aplicação principal FastAPI.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import neo4j_conn
from app.api.routers import customers, analysis, graph_analysis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciamento do ciclo de vida da aplicação."""
    # Startup
    print("🚀 Iniciando aplicação...")
    neo4j_conn.connect()
    print("✅ Conectado ao Neo4j")
    
    yield
    
    # Shutdown
    print("🛑 Encerrando aplicação...")
    neo4j_conn.close()
    print("✅ Conexões fechadas")


# Criar aplicação
app = FastAPI(
    title=settings.APP_NAME,
    description="Sistema de detecção de lavagem de dinheiro usando análise de grafos",
    version=settings.MODEL_VERSION,
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(customers.router, prefix=settings.API_V1_PREFIX)
app.include_router(analysis.router, prefix=settings.API_V1_PREFIX)
app.include_router(graph_analysis.router)  # Já tem prefix="/api/v1/graph"


@app.get("/")
async def root():
    """Endpoint raiz."""
    return {
        "message": "AML Detection System API",
        "version": settings.MODEL_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.ENV
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )

