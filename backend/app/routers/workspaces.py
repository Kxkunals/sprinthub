from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.core import Workspace, WorkspaceMember, WorkItem, AuditEvent, Account
from app.schemas.schemas import (
    WorkspaceCreate, WorkspacePatch, WorkspaceOut,
    WorkspaceDetail, OkResponse, AddMemberRequest, WorkspaceMemberInfo,
)

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


def _record_event(db, verb, resource_type, resource_id, resource_label, account_id):
    db.add(AuditEvent(
        verb=verb,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_label=resource_label,
        account_id=account_id,
    ))


def _fetch_workspace(ws_id: int, db: Session) -> Workspace:
    ws = db.query(Workspace).filter(Workspace.id == ws_id, Workspace.is_active == True).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


def _is_member(ws_id: int, account_id: int, db: Session) -> bool:
    return db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == ws_id,
        WorkspaceMember.account_id == account_id,
    ).first() is not None


def _can_access(ws: Workspace, user, db: Session) -> bool:
    if user.role == "admin":
        return True
    if ws.owner_id == user.id:
        return True
    return _is_member(ws.id, user.id, db)


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ws = Workspace(
        title=payload.title,
        summary=payload.summary,
        theme_color=payload.theme_color or "#7c3aed",
        owner_id=current_user.id,
    )
    db.add(ws)
    db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, account_id=current_user.id))
    db.commit()
    db.refresh(ws)
    _record_event(db, "created", "workspace", ws.id, ws.title, current_user.id)
    db.commit()
    ws.item_count = 0
    ws.member_count = 1
    return ws


@router.get("", response_model=List[WorkspaceOut])
def list_workspaces(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.role == "admin":
        workspaces = db.query(Workspace).filter(Workspace.is_active == True).all()
    else:
        ids = db.query(WorkspaceMember.workspace_id).filter(
            WorkspaceMember.account_id == current_user.id
        ).subquery()
        workspaces = db.query(Workspace).filter(
            Workspace.is_active == True, Workspace.id.in_(ids)
        ).all()

    for ws in workspaces:
        ws.item_count = db.query(WorkItem).filter(WorkItem.workspace_id == ws.id).count()
        ws.member_count = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws.id).count()
    return workspaces


@router.get("/{ws_id}", response_model=WorkspaceDetail)
def get_workspace(ws_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ws = _fetch_workspace(ws_id, db)
    if not _can_access(ws, current_user, db):
        raise HTTPException(status_code=403, detail="Access denied")

    ws.item_count = db.query(WorkItem).filter(WorkItem.workspace_id == ws.id).count()
    raw_members = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws_id).all()
    ws.member_count = len(raw_members)
    ws.members = [
        WorkspaceMemberInfo(
            id=m.account.id,
            display_name=m.account.display_name,
            email=m.account.email,
            role=m.account.role,
            badge_color=m.account.badge_color,
        )
        for m in raw_members if m.account
    ]
    return ws


@router.patch("/{ws_id}", response_model=WorkspaceOut)
def update_workspace(
    ws_id: int,
    payload: WorkspacePatch,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ws = _fetch_workspace(ws_id, db)
    if current_user.role != "admin" and ws.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner or an admin can edit this workspace")

    if payload.title:
        ws.title = payload.title
    if payload.summary is not None:
        ws.summary = payload.summary
    if payload.theme_color:
        ws.theme_color = payload.theme_color

    db.commit()
    db.refresh(ws)
    _record_event(db, "updated", "workspace", ws.id, ws.title, current_user.id)
    db.commit()
    ws.item_count = db.query(WorkItem).filter(WorkItem.workspace_id == ws.id).count()
    ws.member_count = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ws.id).count()
    return ws


@router.delete("/{ws_id}", response_model=OkResponse)
def delete_workspace(ws_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ws = _fetch_workspace(ws_id, db)
    if current_user.role != "admin" and ws.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner or an admin can delete this workspace")
    ws.is_active = False
    _record_event(db, "deleted", "workspace", ws.id, ws.title, current_user.id)
    db.commit()
    return {"message": "Workspace removed successfully"}


@router.post("/{ws_id}/members", response_model=OkResponse)
def add_member(
    ws_id: int,
    payload: AddMemberRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ws = _fetch_workspace(ws_id, db)
    if current_user.role != "admin" and ws.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner or an admin can add members")

    account = db.query(Account).filter(Account.id == payload.account_id, Account.is_active == True).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if _is_member(ws_id, payload.account_id, db):
        raise HTTPException(status_code=400, detail="Account is already a member")

    db.add(WorkspaceMember(workspace_id=ws_id, account_id=payload.account_id))
    _record_event(db, "added_member", "workspace", ws.id, f"{account.display_name} → {ws.title}", current_user.id)
    db.commit()
    return {"message": f"{account.display_name} added to workspace"}


@router.delete("/{ws_id}/members/{account_id}", response_model=OkResponse)
def remove_member(
    ws_id: int,
    account_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ws = _fetch_workspace(ws_id, db)
    if current_user.role != "admin" and ws.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner or an admin can remove members")
    if account_id == ws.owner_id:
        raise HTTPException(status_code=400, detail="The workspace owner cannot be removed")

    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == ws_id,
        WorkspaceMember.account_id == account_id,
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="This account is not a member")

    db.delete(membership)
    db.commit()
    return {"message": "Member removed from workspace"}
