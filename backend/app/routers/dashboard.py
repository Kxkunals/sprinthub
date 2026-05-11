from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.core import WorkItem, Workspace, WorkspaceMember, AuditEvent
from app.schemas.schemas import DashboardSummary, AuditEventOut

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    now = datetime.utcnow()

    if current_user.role == "admin":
        all_items = db.query(WorkItem).all()
        total_workspaces = db.query(Workspace).filter(Workspace.is_active == True).count()
    else:
        ws_ids = db.query(WorkspaceMember.workspace_id).filter(
            WorkspaceMember.account_id == current_user.id
        ).subquery()
        all_items = db.query(WorkItem).filter(WorkItem.workspace_id.in_(ws_ids)).all()
        total_workspaces = db.query(Workspace).filter(
            Workspace.is_active == True, Workspace.id.in_(ws_ids)
        ).count()

    def _past_deadline(item):
        if not item.deadline or item.status == "closed":
            return False
        dl = item.deadline.replace(tzinfo=None) if item.deadline.tzinfo else item.deadline
        return dl < now

    return DashboardSummary(
        total_items=len(all_items),
        backlog=sum(1 for i in all_items if i.status == "backlog"),
        active=sum(1 for i in all_items if i.status == "active"),
        review=sum(1 for i in all_items if i.status == "review"),
        closed=sum(1 for i in all_items if i.status == "closed"),
        overdue=sum(1 for i in all_items if _past_deadline(i)),
        total_workspaces=total_workspaces,
        my_items=sum(1 for i in all_items if i.assignee_id == current_user.id),
    )


@router.get("/feed", response_model=list[AuditEventOut])
def activity_feed(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(20).all()


@router.get("/assigned")
def my_assigned_items(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    now = datetime.utcnow()
    items = db.query(WorkItem).filter(
        WorkItem.assignee_id == current_user.id
    ).order_by(WorkItem.deadline.asc()).all()

    result = []
    for item in items:
        overdue = False
        if item.deadline and item.status != "closed":
            dl = item.deadline.replace(tzinfo=None) if item.deadline.tzinfo else item.deadline
            overdue = dl < now
        result.append({
            "id": item.id,
            "title": item.title,
            "status": item.status,
            "priority": item.priority,
            "deadline": item.deadline,
            "workspace_id": item.workspace_id,
            "is_overdue": overdue,
        })
    return result
