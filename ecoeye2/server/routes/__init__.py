from fastapi import APIRouter, Depends

from ecoeye2.server.routes import analytics, econ_routes, health, pipeline, reporting, tables, uploads, ai_routes
from ecoeye2.server.security import require_api_key

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])

_secured = APIRouter(dependencies=[Depends(require_api_key)])
_secured.include_router(uploads.router, tags=["uploads"])
_secured.include_router(pipeline.router, tags=["pipeline"])
_secured.include_router(tables.router, tags=["tables"])
_secured.include_router(econ_routes.router, tags=["econ"])
_secured.include_router(analytics.router, tags=["analytics"])
_secured.include_router(reporting.router, tags=["reporting"])
_secured.include_router(ai_routes.router, tags=["ai"])
api_router.include_router(_secured)
