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
# PHASE 2: TEAM MANAGEMENT MODELS
# ==========================================

class TeamMember(Base):
    """
    Team members with roles and permissions
    Allows multiple users per tenant with different access levels
    """
    __tablename__ = "team_members"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False, default="member")  # owner, admin, member, viewer
    permissions = Column(JSON, default=dict)  # Custom permissions
    department = Column(String(100))
    title = Column(String(100))
    is_active = Column(Boolean, default=True)
    invited_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    joined_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TeamMember {self.user_id} - {self.role}>"


class TeamInvite(Base):
    """
    Pending team invitations
    Users can be invited to join a tenant
    """
    __tablename__ = "team_invites"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False, default="member")
    permissions = Column(JSON, default=dict)
    invited_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    token = Column(String(255), unique=True, nullable=False)  # Invitation token
    status = Column(String(50), default="pending")  # pending, accepted, expired, revoked
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TeamInvite {self.email} - {self.status}>"


class Permission(Base):
    """
    Custom permissions for advanced RBAC
    Defines granular access control
    """
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=False)  # templates, documents, users, etc.
    action = Column(String(50), nullable=False)  # create, read, update, delete, execute
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Permission {self.resource}:{self.action}>"


# ==========================================
# PHASE 2: BILLING & QUOTA MODELS
# ==========================================

class UsageQuota(Base):
    """
    Usage quotas per tenant/plan
    Enforces limits on document processing, API calls, etc.
    """
    __tablename__ = "usage_quotas"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True)
    plan = Column(String(50), nullable=False, default="free")  # free, starter, professional, enterprise

    # Document quotas
    documents_per_month = Column(Integer, default=100)
    documents_used_this_month = Column(Integer, default=0)

    # API quotas
    api_calls_per_month = Column(Integer, default=1000)
    api_calls_used_this_month = Column(Integer, default=0)

    # Storage quotas (in MB)
    storage_limit_mb = Column(Integer, default=1000)
    storage_used_mb = Column(Integer, default=0)

    # Feature flags
    custom_templates_allowed = Column(Boolean, default=True)
    team_members_limit = Column(Integer, default=5)
    webhooks_allowed = Column(Boolean, default=False)
    api_keys_limit = Column(Integer, default=2)

    # Billing
    overage_allowed = Column(Boolean, default=False)
    billing_cycle_start = Column(DateTime, default=datetime.utcnow)
    last_reset = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UsageQuota {self.plan} - {self.documents_used_this_month}/{self.documents_per_month} docs>"


class Subscription(Base):
    """
    Subscription management
    Tracks subscription status, payments, and renewals
    """
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True)
    plan = Column(String(50), nullable=False)  # free, starter, professional, enterprise
    status = Column(String(50), default="active")  # active, past_due, canceled, trialing

    # Pricing
    amount = Column(Integer, default=0)  # Amount in cents
    currency = Column(String(3), default="USD")
    billing_interval = Column(String(20), default="monthly")  # monthly, yearly

    # Dates
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    trial_start = Column(DateTime)
    trial_end = Column(DateTime)
    canceled_at = Column(DateTime)
    ended_at = Column(DateTime)

    # External integration
    stripe_subscription_id = Column(String(255), unique=True)
    stripe_customer_id = Column(String(255))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Subscription {self.plan} - {self.status}>"


class Invoice(Base):
    """
    Billing invoices
    Tracks charges and payments
    """
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id", ondelete="SET NULL"))

    # Invoice details
    invoice_number = Column(String(100), unique=True, nullable=False)
    status = Column(String(50), default="draft")  # draft, open, paid, void, uncollectible
    amount_due = Column(Integer, nullable=False)  # Amount in cents
    amount_paid = Column(Integer, default=0)
    currency = Column(String(3), default="USD")

    # Dates
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    due_date = Column(DateTime)
    paid_at = Column(DateTime)

    # Line items
    line_items = Column(JSON, default=list)  # List of charges

    # External integration
    stripe_invoice_id = Column(String(255), unique=True)
    hosted_invoice_url = Column(String(500))
    invoice_pdf_url = Column(String(500))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Invoice {self.invoice_number} - {self.status}>"


# ==========================================
# PHASE 2: WEBHOOK DELIVERY LOGS
# ==========================================

class WebhookDelivery(Base):
    """
    Webhook delivery attempts log
    Tracks webhook delivery status for debugging
    """
    __tablename__ = "webhook_deliveries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    webhook_id = Column(String(36), ForeignKey("webhook_endpoints.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Delivery details
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON)
    status_code = Column(Integer)
    response_body = Column(Text)
    error_message = Column(Text)

    # Attempt tracking
    attempt_number = Column(Integer, default=1)
    max_attempts = Column(Integer, default=3)
    next_retry_at = Column(DateTime)

    # Status
    status = Column(String(50), default="pending")  # pending, success, failed, retrying
    delivered_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<WebhookDelivery {self.event_type} - {self.status}>"


# ==========================================
# PHASE 2: TENANT BRANDING
# ==========================================

class TenantBranding(Base):
    """
    Custom branding per tenant
    Allows white-labeling and customization
    """
    __tablename__ = "tenant_branding"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Branding
    company_name = Column(String(255))
    logo_url = Column(String(500))
    favicon_url = Column(String(500))
    primary_color = Column(String(7))  # Hex color
    secondary_color = Column(String(7))
    accent_color = Column(String(7))

    # Contact
    support_email = Column(String(255))
    support_url = Column(String(500))
    website_url = Column(String(500))

    # Custom domain
    custom_domain = Column(String(255))
    domain_verified = Column(Boolean, default=False)

    # Email templates
    email_from_name = Column(String(255))
    email_from_address = Column(String(255))
    email_footer_text = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TenantBranding {self.company_name}>"


# ==========================================
# INDEXES FOR PERFORMANCE
# ==========================================

# Additional indexes created above using Index()
# For optimal query performance in multi-tenant setup
