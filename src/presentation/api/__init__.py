"""API presentation layer."""

from fastapi import FastAPI

def create_api_routes(app: FastAPI) -> None:
    """Create API routes."""
    
    @app.get("/")
    async def root():
        return {
            "message": "Selfology Bot API v2.0",
            "architecture": "Clean Architecture",
            "status": "running"
        }
    
    @app.get("/health")
    async def health_check():
        try:
            health_service = app.state.health_service
            health = await health_service.get_health_status()
            return health
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    @app.get("/ready")
    async def readiness_check():
        try:
            health_service = app.state.health_service
            readiness = await health_service.get_readiness_status()
            return readiness
        except Exception as e:
            return {"ready": False, "error": str(e)}