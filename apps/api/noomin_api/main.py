from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from noomin_api.api.analyses import router as analyses_router
from noomin_api.api.auth import router as auth_router
from noomin_api.api.datasets import router as datasets_router
from noomin_api.api.health import router as health_router
from noomin_api.api.members import router as members_router
from noomin_api.api.pipelines import router as pipelines_router
from noomin_api.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.2.0", description="API NOOMIN — comptes, accès multi-tenant et jeux de données.")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type", "X-Organization-ID"])
app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(datasets_router, prefix=settings.api_v1_prefix)
app.include_router(pipelines_router, prefix=settings.api_v1_prefix)
app.include_router(analyses_router, prefix=settings.api_v1_prefix)
app.include_router(members_router, prefix=settings.api_v1_prefix)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs", "health": f"{settings.api_v1_prefix}/health"}
