"""
Database models for multi-tenant document parsing SaaS
Complete implementation with tenant isolation
"""

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    BigInteger,
    Index,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def generate_uuid() -> str:
    """Generate UUID as string"""
    return str(uuid.uuid4())


def generate_api_key() -> tuple[str, str]:
    """
    Generate API key with prefix and secret
    Returns: (full_key, hashed_key)
    """
    prefix = "sk_live_"
    secret = secrets.token_urlsafe(32)
    full_key = f"{prefix}{secret}"

    # In production, use bcrypt/argon2 for hashing
    import hashlib
    hashed = hashlib.sha256(full_key.encode()).hexdigest()

    return full_key, hashed


# ==========================================
# MODELS
# ==========================================

class Tenant(Base):
    """
    Tenant model for multi-tenancy
    Each tenant is a separate organization/company
    """
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    plan = Column(String(50), nullable=False, default="free")  # free, starter, pro, enterprise
    settings = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    templates = relationship("Template", back_populates="tenant", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="tenant", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant {self.name}>"


class User(Base):
    """
    User model with authentication
    Users belong to a tenant
    """
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), nullable=False, default="user")  # admin, user, api
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user")
    created_templates = relationship("Template", foreign_keys="Template.created_by")

    def __repr__(self):
        return f"<User {self.email}>"


class APIKey(Base):
    """
    API Key model for programmatic access
    Each user can have multiple API keys
    """
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100))
    key_prefix = Column(String(20), nullable=False, index=True)
    key_hash = Column(String(255), nullable=False)
    permissions = Column(JSON, default=dict)
    last_used = Column(DateTime)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="api_keys")
    tenant = relationship("Tenant", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey {self.key_prefix}...>"


class Template(Base):
    """
    Template model for document types
    Defines structure and validation rules
    """
    __tablename__ = "templates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    schema = Column(JSON, nullable=False)
    version = Column(String(20), default="1.0")
    is_public = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(36), ForeignKey("users.id"))
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="templates")
    creator = relationship("User", foreign_keys=[created_by])
    documents = relationship("Document", back_populates="template")

    # Composite unique constraint
    __table_args__ = (
        Index("ix_template_tenant_slug", "tenant_id", "slug", unique=True),
    )

    def __repr__(self):
        return f"<Template {self.name}>"


class Document(Base):
    """
    Document model for processed files
    Stores extracted data and quality metrics
    """
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    template_id = Column(String(36), ForeignKey("templates.id", ondelete="SET NULL"))

    # File information
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger)
    mime_type = Column(String(100))
    page_count = Column(Integer, default=1)

    # Processing status
    status = Column(String(50), nullable=False, default="uploaded", index=True)
    # Status: uploaded, processing, completed, failed, review, approved

    # Extraction results
    extracted_data = Column(JSON)
    confidence_scores = Column(JSON)
    quality_metrics = Column(JSON)
    flagged_fields = Column(JSON)
    error_message = Column(Text)

    # Performance metrics
    processing_time_ms = Column(Integer)
    processing_started_at = Column(DateTime)
    processed_at = Column(DateTime)

    # Review
    reviewed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)

    # Metadata
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="documents")
    user = relationship("User", foreign_keys=[user_id], back_populates="documents")
    template = relationship("Template", back_populates="documents")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self):
        return f"<Document {self.filename}>"


class UsageLog(Base):
    """
    Usage tracking for billing and analytics
    Tracks all API calls and document processing
    """
    __tablename__ = "usage_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(100), nullable=False, index=True)  # document_processed, api_call, etc.
    resource_type = Column(String(100))
    resource_id = Column(String(36))
    credits_used = Column(Integer, default=1)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<UsageLog {self.action}>"


class AuditLog(Base):
    """
    Audit logging for compliance
    Tracks all user actions for security
    """
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100))
    resource_id = Column(String(36))
    changes = Column(JSON)
    ip_address = Column(String(45))  # INET for PostgreSQL, String for SQLite
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<AuditLog {self.action}>"


class WebhookEndpoint(Base):
    """
    Webhook endpoints for event notifications
    Allows users to receive real-time updates
    """
    __tablename__ = "webhook_endpoints"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    url = Column(String(500), nullable=False)
    secret = Column(String(255))  # For signature verification
    events = Column(JSON, default=list)  # List of events to listen for
    is_active = Column(Boolean, default=True)
    failure_count = Column(Integer, default=0)
    last_success = Column(DateTime)
    last_failure = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<WebhookEndpoint {self.url}>"


# ==========================================
# INDEXES FOR PERFORMANCE
# ==========================================

# Additional indexes created above using Index()
# For optimal query performance in multi-tenant setup
