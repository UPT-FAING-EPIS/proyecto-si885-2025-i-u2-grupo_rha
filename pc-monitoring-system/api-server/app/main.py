from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .routers import auth, agent, admin, dashboard, machines, threats, powerbi, scans, invitations

app = FastAPI(
    title="PC Monitoring System API",
    description="API RESTful para sistema de monitoreo de PCs",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(agent.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(machines.router, prefix="/api/v1")
app.include_router(threats.router, prefix="/api/v1")
app.include_router(powerbi.router, prefix="/api/v1")
app.include_router(scans.router, prefix="/api/v1")
app.include_router(invitations.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "PC Monitoring System API",
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=True
    )