from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.core import WorkItem, Workspace, WorkspaceMember, AuditEvent, Account, Remark
from app.schemas.schemas import (
    WorkItemCreate, WorkItemPatch, WorkItemOut,
    RemarkCreate, RemarkOut, OkResponse,
)

router = APIRouter(prefix="/workspaces/{ws_id}/items", tags=["Work Items"])


def _record_event(db, verb, resource_type, resource_id, resource_label, account_id):
    db.add(AuditEvent(
        verb=verb, resource_type=resource_type,
        resource_id=resource_id, resource_label=resource_label,
        account_id=account_id,
    ))


def _resolve_workspace(ws_id: int, user, db: Session) -> Workspace:
    ws = db.query(Workspace).filter(Workspace.id == ws_id, Workspace.is_active == True).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if user.role == "admin" or ws.owner_id == user.id:
        return ws
    is_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == ws_id,
        WorkspaceMember.account_id == user.id,
    ).first()
    if not is_member:
        raise HTTPException(status_code=403, detail="You do not have access to this workspace")
    return ws


def _mark_overdue(item: WorkItem) -> WorkItem:
    now = datetime.utcnow()
    if item.deadline and item.status != "closed":
        dl = item.deadline.replace(tzinfo=None) if item.deadline.tzinfo else item.deadline
        item.is_overdue = dl < now
    else:
        item.is_overdue = False
    return item


@router.post("", response_model=WorkItemOut, status_code=status.HTTP_201_CREATED)
def create_item(
    ws_id: int,
    payload: WorkItemCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _resolve_workspace(ws_id, current_user, db)
    if payload.assignee_id:
        if not db.query(Account).filter(Account.id == payload.assignee_id, Account.is_active == True).first():
            raise HTTPException(status_code=404, detail="Assignee not found")

    item = WorkItem(
        title=payload.title,
        body=payload.body,
        status=payload.status,
        priority=payload.priority,
        workspace_id=ws_id,
        assignee_id=payload.assignee_id,
        author_id=current_user.id,
        deadline=payload.deadline,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    _record_event(db, "created", "item", item.id, item.title, current_user.id)
    db.commit()
    return _mark_overdue(item)


@router.get("", response_model=List[WorkItemOut])
def list_items(
    ws_id: int,
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assignee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _resolve_workspace(ws_id, current_user, db)
    q = db.query(WorkItem).filter(WorkItem.workspace_id == ws_id)
    if status:
        q = q.filter(WorkItem.status == status)
    if priority:
        q = q.filter(WorkItem.priority == priority)
    if assignee_id:
        q = q.filter(WorkItem.assignee_id == assignee_id)
    return [_mark_overdue(i) for i in q.order_by(WorkItem.created_at.desc()).all()]


@router.get("/{item_id}", response_model=WorkItemOut)
def get_item(
    ws_id: int, item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _resolve_workspace(ws_id, current_user, db)
    item = db.query(WorkItem).filter(WorkItem.id == item_id, WorkItem.workspace_id == ws_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Work item not found")
    return _mark_overdue(item)


@router.patch("/{item_id}", response_model=WorkItemOut)
def update_item(
    ws_id: int, item_id: int,
    payload: WorkItemPatch,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _resolve_workspace(ws_id, current_user, db)
    item = db.query(WorkItem).filter(WorkItem.id == item_id, WorkItem.workspace_id == ws_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Work item not found")

    if payload.title is not None:
        item.title = payload.title
    if payload.body is not None:
        item.body = payload.body
    if payload.status is not None:
        item.status = payload.status
    if payload.priority is not None:
        item.priority = payload.priority
    if payload.assignee_id is not None:
        item.assignee_id = payload.assignee_id
    if payload.deadline is not None:
        item.deadline = payload.deadline

    db.commit()
    db.refresh(item)
    _record_event(db, "updated", "item", item.id, item.title, current_user.id)
    db.commit()
    return _mark_overdue(item)


@router.delete("/{item_id}", response_model=OkResponse)
def delete_item(
    ws_id: int, item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ws = _resolve_workspace(ws_id, current_user, db)
    item = db.query(WorkItem).filter(WorkItem.id == item_id, WorkItem.workspace_id == ws_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Work item not found")

    if current_user.role != "admin" and ws.owner_id != current_user.id and item.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not permitted to delete this item")

    _record_event(db, "deleted", "item", item.id, item.title, current_user.id)
    db.delete(item)
    db.commit()
    return {"message": "Work item deleted"}


# ── Remarks ───────────────────────────────────────────────────────────────────

@router.post("/{item_id}/remarks", response_model=RemarkOut, status_code=201)
def post_remark(
    ws_id: int, item_id: int,
    payload: RemarkCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _resolve_workspace(ws_id, current_user, db)
    item = db.query(WorkItem).filter(WorkItem.id == item_id, WorkItem.workspace_id == ws_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Work item not found")
    remark = Remark(body=payload.body, item_id=item_id, poster_id=current_user.id)
    db.add(remark)
    db.commit()
    db.refresh(remark)
    return remark


@router.get("/{item_id}/remarks", response_model=List[RemarkOut])
def get_remarks(
    ws_id: int, item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _resolve_workspace(ws_id, current_user, db)
    return db.query(Remark).filter(Remark.item_id == item_id).order_by(Remark.created_at.asc()).all()
