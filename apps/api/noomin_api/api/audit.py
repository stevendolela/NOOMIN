from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from noomin_api.api.dependencies import get_current_organization, get_current_user
from noomin_api.api.permissions import Permission, require_permission
from noomin_api.db.session import get_db
from noomin_api.models import AuditLog, Membership, Organization, User
from noomin_api.schemas.audit import AuditEventResponse, AuditLogResponse

router = APIRouter(prefix="/audit", tags=["audit"])


def record_audit(
    db: Session,
    organization_id: UUID,
    actor_user_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID | str | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(AuditLog(organization_id=organization_id, actor_user_id=actor_user_id, action=action, entity_type=entity_type, entity_id=str(entity_id) if entity_id is not None else None, metadata_json=metadata or {}))


@router.get("", response_model=AuditLogResponse)
def list_audit_events(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    organization: Organization = Depends(get_current_organization),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuditLogResponse:
    membership = db.scalar(select(Membership).where(Membership.organization_id == organization.id, Membership.user_id == user.id))
    if membership is None:
        raise HTTPException(status_code=403, detail="Vous n’avez pas accès à cette organisation.")
    require_permission(membership.role, Permission.VIEW_AUDIT_LOG, "Votre rôle ne permet pas de consulter le journal d’audit.")
    base = select(AuditLog, User).outerjoin(User, User.id == AuditLog.actor_user_id).where(AuditLog.organization_id == organization.id)
    total = db.scalar(select(func.count()).select_from(select(AuditLog.id).where(AuditLog.organization_id == organization.id).subquery())) or 0
    rows = db.execute(base.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).offset(offset).limit(limit)).all()
    items = [AuditEventResponse(id=event.id, actor_name=actor.full_name if actor else "Utilisateur supprimé", actor_email=actor.email if actor else None, action=event.action, entity_type=event.entity_type, entity_id=event.entity_id, metadata=event.metadata_json, created_at=event.created_at) for event, actor in rows]
    return AuditLogResponse(items=items, total=total)
