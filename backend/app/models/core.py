from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class MemberRole(str, enum.Enum):
    admin = "admin"
    member = "member"


class ItemStatus(str, enum.Enum):
    backlog = "backlog"
    active = "active"
    review = "review"
    closed = "closed"


class ItemPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(MemberRole), default=MemberRole.member, nullable=False)
    badge_color = Column(String(7), default="#7c3aed")
    is_active = Column(Boolean, default=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owned_workspaces = relationship("Workspace", back_populates="owner", foreign_keys="Workspace.owner_id")
    memberships = relationship("WorkspaceMember", back_populates="account")
    assigned_items = relationship("WorkItem", back_populates="assignee", foreign_keys="WorkItem.assignee_id")
    created_items = relationship("WorkItem", back_populates="author", foreign_keys="WorkItem.author_id")
    remarks = relationship("Remark", back_populates="poster")
    audit_events = relationship("AuditEvent", back_populates="account")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    summary = Column(Text, nullable=True)
    theme_color = Column(String(7), default="#7c3aed")
    owner_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("Account", back_populates="owned_workspaces", foreign_keys=[owner_id])
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    items = relationship("WorkItem", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    workspace = relationship("Workspace", back_populates="members")
    account = relationship("Account", back_populates="memberships")


class WorkItem(Base):
    __tablename__ = "work_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=True)
    status = Column(Enum(ItemStatus), default=ItemStatus.backlog, nullable=False)
    priority = Column(Enum(ItemPriority), default=ItemPriority.medium, nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    author_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    workspace = relationship("Workspace", back_populates="items")
    assignee = relationship("Account", back_populates="assigned_items", foreign_keys=[assignee_id])
    author = relationship("Account", back_populates="created_items", foreign_keys=[author_id])
    remarks = relationship("Remark", back_populates="item", cascade="all, delete-orphan")


class Remark(Base):
    __tablename__ = "remarks"

    id = Column(Integer, primary_key=True, index=True)
    body = Column(Text, nullable=False)
    item_id = Column(Integer, ForeignKey("work_items.id", ondelete="CASCADE"), nullable=False)
    poster_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    item = relationship("WorkItem", back_populates="remarks")
    poster = relationship("Account", back_populates="remarks")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    verb = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(Integer, nullable=False)
    resource_label = Column(String(300), nullable=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())

    account = relationship("Account", back_populates="audit_events")
