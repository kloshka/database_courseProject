from sqlalchemy import (
    Column, String, Date, Text, Numeric, Boolean, ForeignKey, Table,
    DateTime, func, UniqueConstraint, BigInteger, Integer, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()
metadata = Base.metadata

# Связующие таблицы
title_genres = Table(
    "title_genres", metadata,
    Column("title_id", BigInteger, ForeignKey("titles.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", BigInteger, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)

title_studios = Table(
    "title_studios", metadata,
    Column("title_id", BigInteger, ForeignKey("titles.id", ondelete="CASCADE"), primary_key=True),
    Column("studio_id", BigInteger, ForeignKey("studios.id", ondelete="CASCADE"), primary_key=True),
    Column("role", String(100), nullable=True),
)

title_authors = Table(
    "title_authors", metadata,
    Column("title_id", BigInteger, ForeignKey("titles.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", BigInteger, ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
    Column("role", String(100), nullable=True),
)

class Genre(Base):
    __tablename__ = "genres"
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    titles = relationship("Title", secondary=title_genres, back_populates="genres")

class Title(Base):
    __tablename__ = "titles"
    __table_args__ = (
        CheckConstraint("type IN ('anime', 'manga')", name="ck_title_type"),
        CheckConstraint("status IN ('announced', 'ongoing', 'released', 'discontinued')", name="ck_title_status"),
        CheckConstraint("episodes_count >= 0 OR episodes_count IS NULL", name="ck_episodes_non_negative"),
        CheckConstraint("volumes_count >= 0 OR volumes_count IS NULL", name="ck_volumes_non_negative"),
        CheckConstraint("chapters_count >= 0 OR chapters_count IS NULL", name="ck_chapters_non_negative"),
        CheckConstraint("total_score >= 0", name="ck_total_score_non_negative"),
        CheckConstraint("vote_count >= 0", name="ck_vote_count_non_negative"),
        CheckConstraint("average_rating BETWEEN 0 AND 10 OR average_rating IS NULL", name="ck_rating_range"),
    )
    
    id = Column(BigInteger, primary_key=True, index=True)
    type = Column(String(10), nullable=False)
    canonical_title = Column(String(255), nullable=False)
    russian_title = Column(String(255), nullable=True)
    synopsis = Column(Text, nullable=True)
    poster_url = Column(String(255), nullable=True)
    
    status = Column(String(20), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    
    episodes_count = Column(Integer, nullable=True)
    volumes_count = Column(Integer, nullable=True)
    chapters_count = Column(Integer, nullable=True)
    
    total_score = Column(BigInteger, nullable=False, default=0, server_default="0")
    vote_count = Column(Integer, nullable=False, default=0, server_default="0")
    average_rating = Column(Numeric(4, 2), nullable=True)
    
    # Отношения
    genres = relationship("Genre", secondary=title_genres, back_populates="titles")
    studios = relationship("Studio", secondary=title_studios, back_populates="titles")
    authors = relationship("Author", secondary=title_authors, back_populates="titles")
    reviews = relationship("Review", back_populates="title", cascade="all, delete-orphan")
    library_entries = relationship("UserLibrary", back_populates="title", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("is_active IN (TRUE, FALSE)", name="ck_user_active"),
    )
    
    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    avatar_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")
    library = relationship("UserLibrary", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    reports_filed = relationship("Report", foreign_keys="Report.reporter_user_id", back_populates="reporter")
    reports_received = relationship("Report", foreign_keys="Report.reported_user_id", back_populates="reported")
    reports_resolved = relationship("Report", foreign_keys="Report.resolved_by", back_populates="resolver")

class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint("birth_date <= CURRENT_DATE", name="ck_birth_date_not_future"),
    )
    
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    birth_date = Column(Date, nullable=True)
    about_text = Column(Text, nullable=True)
    user = relationship("User", back_populates="profile")

class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "title_id", name="uq_review_user_title"),
    )
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title_id = Column(BigInteger, ForeignKey("titles.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    user = relationship("User", back_populates="reviews")
    title = relationship("Title", back_populates="reviews")

class UserLibrary(Base):
    __tablename__ = "user_library"
    __table_args__ = (
        UniqueConstraint("user_id", "title_id", name="uq_user_title"),
        CheckConstraint("status IN ('planned', 'watching', 'completed', 'dropped', 'on_hold')", name="ck_library_status"),
        CheckConstraint("progress >= 0", name="ck_progress_non_negative"),
        CheckConstraint("user_score BETWEEN 1 AND 10 OR user_score IS NULL", name="ck_user_score_range"),
    )
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title_id = Column(BigInteger, ForeignKey("titles.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False)
    progress = Column(Integer, nullable=False, default=0, server_default="0")
    user_score = Column(Integer, nullable=True)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="library")
    title = relationship("Title", back_populates="library_entries")

class Studio(Base):
    __tablename__ = "studios"
    __table_args__ = (
        CheckConstraint("type IN ('studio', 'publisher')", name="ck_studio_type"),
    )
    
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    type = Column(String(20), nullable=False)
    country = Column(String(50), nullable=True)
    founded_date = Column(Date, nullable=True)
    
    titles = relationship("Title", secondary=title_studios, back_populates="studios")

class Author(Base):
    __tablename__ = "authors"
    id = Column(BigInteger, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=True)
    
    titles = relationship("Title", secondary=title_authors, back_populates="authors")

class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint("user_role IN ('admin', 'moderator', 'user', 'system')", name="ck_audit_user_role"),
        CheckConstraint("action_type IN ('catalog_create', 'catalog_update', 'catalog_delete', "
                       "'review_create', 'review_update', 'review_delete', 'library_add', "
                       "'library_update', 'library_delete', 'user_create', 'user_update', "
                       "'user_delete', 'user_block', 'user_unblock', 'system_event', "
                       "'report_created', 'report_resolved')", name="ck_audit_action_type"),
        CheckConstraint("entity_type IN ('title', 'review', 'user', 'studio', 'genre', "
                       "'author', 'user_library', 'report')", name="ck_audit_entity_type"),
    )
    
    id = Column(BigInteger, primary_key=True, index=True)
    event_timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_role = Column(String(20), nullable=False)
    action_type = Column(String(50), nullable=False)
    entity_type = Column(String(20), nullable=False)
    entity_id = Column(BigInteger, nullable=False)
    description = Column(String(500), nullable=False)
    changes = Column(JSONB, nullable=True)
    
    user = relationship("User", back_populates="audit_logs")

class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("entity_type IN ('review', 'user_avatar')", name="ck_report_entity_type"),
        CheckConstraint("reason IN ('spam', 'offensive_language', 'hate_speech', "
                       "'inappropriate_content', 'spoiler', 'copyright_violation', 'other')", name="ck_report_reason"),
        CheckConstraint("status IN ('pending', 'investigating', 'resolved', 'rejected')", name="ck_report_status"),
        CheckConstraint("resolution IN ('content_removed', 'user_warned', 'user_banned', "
                       "'no_violation', 'duplicate') OR resolution IS NULL", name="ck_report_resolution"),
    )
    
    id = Column(BigInteger, primary_key=True, index=True)
    reporter_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String(20), nullable=False)
    entity_id = Column(BigInteger, nullable=False)
    reported_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason = Column(String(30), nullable=False)
    description = Column(Text, nullable=True)
    evidence_url = Column(String(255), nullable=True)
    
    status = Column(String(20), nullable=False, default="pending", server_default="'pending'")
    resolution = Column(String(20), nullable=True)
    moderator_comment = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Отношения
    reporter = relationship("User", foreign_keys=[reporter_user_id], back_populates="reports_filed")
    reported = relationship("User", foreign_keys=[reported_user_id], back_populates="reports_received")
    resolver = relationship("User", foreign_keys=[resolved_by], back_populates="reports_resolved")