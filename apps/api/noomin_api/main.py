from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import hmac

from noomin_api.api.analyses import router as analyses_router
from noomin_api.api.api_keys import customer_router as customer_api_router, management_router as api_key_router
from noomin_api.api.audit import router as audit_router
from noomin_api.api.auth import router as auth_router
from noomin_api.api.datasets import router as datasets_router
from noomin_api.api.health import router as health_router
from noomin_api.api.members import invitations_router, router as members_router
from noomin_api.api.pipelines import router as pipelines_router
from noomin_api.core.config import get_settings
from noomin_api.core.security import create_csrf_token

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.2.0", description="API NOOMIN — comptes, accès multi-tenant et jeux de données.")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type", "X-Organization-ID", "X-CSRF-Token"])


@app.middleware("http")
async def csrf_guard(request, call_next):
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return await call_next(request)
    origin = request.headers.get("origin")
    if request.headers.get("sec-fetch-site") == "cross-site":
        return JSONResponse(status_code=403, content={"detail": "Requête intersite refusée."})
    if origin and origin not in settings.allowed_origins:
        return JSONResponse(status_code=403, content={"detail": "Origine non autorisée."})
    session_token = request.cookies.get("session")
    if origin and session_token:
        cookie_token = request.cookies.get("csrf_token", "")
        header_token = request.headers.get("x-csrf-token", "")
        if (cookie_token or header_token) and (not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token) or not hmac.compare_digest(cookie_token, create_csrf_token(session_token))):
            return JSONResponse(status_code=403, content={"detail": "Jeton CSRF invalide ou manquant."})
    return await call_next(request)
app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(datasets_router, prefix=settings.api_v1_prefix)
app.include_router(pipelines_router, prefix=settings.api_v1_prefix)
app.include_router(analyses_router, prefix=settings.api_v1_prefix)
app.include_router(members_router, prefix=settings.api_v1_prefix)
app.include_router(invitations_router, prefix=settings.api_v1_prefix)
app.include_router(audit_router, prefix=settings.api_v1_prefix)
app.include_router(api_key_router, prefix=settings.api_v1_prefix)
app.include_router(customer_api_router, prefix=settings.api_v1_prefix)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs", "health": f"{settings.api_v1_prefix}/health"}
