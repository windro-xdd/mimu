"""Database models for the backend domain."""

from __future__ import annotations

import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class TimestampMixin:
    """Reusable timestamp columns for created/updated tracking."""

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CREATOR = "creator"
    VIEWER = "viewer"


class ContentStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ContentType(str, enum.Enum):
    ARTICLE = "article"
    VIDEO = "video"
    AUDIO = "audio"


class User(TimestampMixin, Base):
    """Application user with role and aggregate score."""

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_username", "username", unique=True),
        Index("ix_users_email", "email", unique=True),
    )

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False)
    email = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(
        SAEnum(UserRole, name="userrole"),
        nullable=False,
        server_default=UserRole.VIEWER.value,
    )
    total_score = Column(Integer, nullable=False, server_default="0")

    contents = relationship(
        "Content", back_populates="author", cascade="all, delete-orphan"
    )
    votes = relationship(
        "Vote", back_populates="user", cascade="all, delete-orphan"
    )
    user_achievements = relationship(
        "UserAchievement",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Content(TimestampMixin, Base):
    """User-generated content that can receive votes."""

    __tablename__ = "content"
    __table_args__ = (Index("ix_content_status", "status"),)

    id = Column(Integer, primary_key=True)
    author_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(
        SAEnum(ContentStatus, name="contentstatus"),
        nullable=False,
        server_default=ContentStatus.DRAFT.value,
    )
    content_type = Column(
        SAEnum(ContentType, name="contenttype"), nullable=False
    )
    score = Column(Integer, nullable=False, server_default="0")
    upvotes = Column(Integer, nullable=False, server_default="0")
    downvotes = Column(Integer, nullable=False, server_default="0")

    author = relationship("User", back_populates="contents")
    votes = relationship(
        "Vote", back_populates="content", cascade="all, delete-orphan"
    )


class Vote(TimestampMixin, Base):
    """Single vote per user per content item."""

    __tablename__ = "votes"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    content_id = Column(
        Integer,
        ForeignKey("content.id", ondelete="CASCADE"),
        primary_key=True,
    )
    value = Column(Integer, nullable=False, server_default="1")

    user = relationship("User", back_populates="votes")
    content = relationship("Content", back_populates="votes")


class Achievement(TimestampMixin, Base):
    """Static catalog of achievements users can earn."""

    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True)
    code = Column(String(64), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    points = Column(Integer, nullable=False, server_default="0")

    user_achievements = relationship(
        "UserAchievement",
        back_populates="achievement",
        cascade="all, delete-orphan",
    )


class UserAchievement(TimestampMixin, Base):
    """Association table tracking user progress toward achievements."""

    __tablename__ = "user_achievements"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    achievement_id = Column(
        Integer,
        ForeignKey("achievements.id", ondelete="CASCADE"),
        primary_key=True,
    )
    progress = Column(Integer, nullable=False, server_default="0")
    awarded_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="user_achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")


__all__ = [
    "Achievement",
    "Content",
    "ContentStatus",
    "ContentType",
    "User",
    "UserAchievement",
    "UserRole",
    "Vote",
]
