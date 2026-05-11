from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MemberRole(str, Enum):
    admin = "admin"
    member = "member"


class ItemStatus(str, Enum):
    backlog = "backlog"
    active = "active"
    review = "review"
    closed = "closed"


class ItemPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


# ── Auth ─────────────────────────────────────────────────────────────────────

class SignUpRequest(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    role: MemberRole = MemberRole.member


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    refresh_token: str


# ── Account ──────────────────────────────────────────────────────────────────

class AccountOut(BaseModel):
    id: int
    display_name: str
    email: str
    role: str
    badge_color: str
    is_active: bool
    registered_at: datetime

    class Config:
        from_attributes = True


class AccountPublic(BaseModel):
    id: int
    display_name: str
    email: str
    role: str
    badge_color: str

    class Config:
        from_attributes = True


class AccountPatch(BaseModel):
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    badge_color: Optional[str] = None


# ── Workspace ─────────────────────────────────────────────────────────────────

class WorkspaceCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    summary: Optional[str] = Field(None, max_length=1000)
    theme_color: Optional[str] = "#7c3aed"


class WorkspacePatch(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    summary: Optional[str] = None
    theme_color: Optional[str] = None


class WorkspaceMemberInfo(BaseModel):
    id: int
    display_name: str
    email: str
    role: str
    badge_color: str

    class Config:
        from_attributes = True


class WorkspaceOut(BaseModel):
    id: int
    title: str
    summary: Optional[str]
    theme_color: str
    owner_id: int
    owner: AccountPublic
    is_active: bool
    created_at: datetime
    item_count: Optional[int] = 0
    member_count: Optional[int] = 0

    class Config:
        from_attributes = True


class WorkspaceDetail(WorkspaceOut):
    members: List[WorkspaceMemberInfo] = []


# ── Work Items ────────────────────────────────────────────────────────────────

class WorkItemCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=300)
    body: Optional[str] = Field(None, max_length=2000)
    status: ItemStatus = ItemStatus.backlog
    priority: ItemPriority = ItemPriority.medium
    assignee_id: Optional[int] = None
    deadline: Optional[datetime] = None


class WorkItemPatch(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=300)
    body: Optional[str] = None
    status: Optional[ItemStatus] = None
    priority: Optional[ItemPriority] = None
    assignee_id: Optional[int] = None
    deadline: Optional[datetime] = None


class WorkItemOut(BaseModel):
    id: int
    title: str
    body: Optional[str]
    status: str
    priority: str
    workspace_id: int
    assignee_id: Optional[int]
    assignee: Optional[AccountPublic]
    author_id: int
    author: AccountPublic
    deadline: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    is_overdue: Optional[bool] = False

    class Config:
        from_attributes = True


# ── Remarks ───────────────────────────────────────────────────────────────────

class RemarkCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


class RemarkOut(BaseModel):
    id: int
    body: str
    item_id: int
    poster_id: int
    poster: AccountPublic
    created_at: datetime

    class Config:
        from_attributes = True


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardSummary(BaseModel):
    total_items: int
    backlog: int
    active: int
    review: int
    closed: int
    overdue: int
    total_workspaces: int
    my_items: int


class AuditEventOut(BaseModel):
    id: int
    verb: str
    resource_type: str
    resource_id: int
    resource_label: Optional[str]
    account_id: Optional[int]
    account: Optional[AccountPublic]
    occurred_at: datetime

    class Config:
        from_attributes = True


# ── Generic ───────────────────────────────────────────────────────────────────

class OkResponse(BaseModel):
    message: str


class AddMemberRequest(BaseModel):
    account_id: int
