"""
Phase 2 API Endpoints
Team Management, Billing, Webhooks, and Branding
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

# Import from existing modules
from auth import get_current_user, require_admin
from database import get_db_session
from models import (
    Invoice,
    Subscription,
    TeamInvite,
    TeamMember,
    TenantBranding,
    UsageQuota,
    User,
    WebhookDelivery,
    WebhookEndpoint,
)
from schemas import (
    InvoiceResponse,
    SubscriptionCreate,
    SubscriptionResponse,
    TeamInviteCreate,
    TeamInviteResponse,
    TeamMemberResponse,
    TeamMemberUpdate,
    TenantBrandingResponse,
    TenantBrandingUpdate,
    UsageQuotaResponse,
    WebhookCreate,
    WebhookDeliveryResponse,
    WebhookResponse,
    WebhookUpdate,
    success_response,
)

# Create router
router = APIRouter(prefix="/api/v1", tags=["phase2"])


# ==========================================
# TEAM MANAGEMENT ENDPOINTS
# ==========================================

@router.post("/team/invite", response_model=TeamInviteResponse)
async def invite_team_member(
    invite_data: TeamInviteCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db_session)
):
    """
    Invite a user to join the team (Admin only)

    Creates an invitation that can be sent via email
    """
    # Check if user already invited or exists
    existing_invite = db.query(TeamInvite).filter(
        TeamInvite.tenant_id == current_user.tenant_id,
        TeamInvite.email == invite_data.email,
        TeamInvite.status == "pending"
    ).first()

    if existing_invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already invited"
        )

    # Check quota
    quota = db.query(UsageQuota).filter(
        UsageQuota.tenant_id == current_user.tenant_id
    ).first()

    if quota:
        current_members = db.query(func.count(TeamMember.id)).filter(
            TeamMember.tenant_id == current_user.tenant_id,
            TeamMember.is_active == True
        ).scalar()

        if current_members >= quota.team_members_limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Team member limit reached ({quota.team_members_limit}). Upgrade plan to add more members."
            )

    # Generate invitation token
    token = secrets.token_urlsafe(32)

    # Create invitation
    invite = TeamInvite(
        tenant_id=current_user.tenant_id,
        email=invite_data.email,
        role=invite_data.role,
        permissions=invite_data.permissions or {},
        invited_by=current_user.id,
        token=token,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(days=7)
    )

    db.add(invite)
    db.commit()
    db.refresh(invite)

    # TODO: Send invitation email with token

    return invite


@router.get("/team/invites", response_model=List[TeamInviteResponse])
async def list_team_invites(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db_session)
):
    """List all pending team invitations (Admin only)"""
    invites = db.query(TeamInvite).filter(
        TeamInvite.tenant_id == current_user.tenant_id,
        TeamInvite.status == "pending"
    ).all()

    return invites


@router.delete("/team/invites/{invite_id}")
async def revoke_team_invite(
    invite_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db_session)
):
    """Revoke a team invitation (Admin only)"""
    invite = db.query(TeamInvite).filter(
        TeamInvite.id == invite_id,
        TeamInvite.tenant_id == current_user.tenant_id
    ).first()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )

    invite.status = "revoked"
    db.commit()

    return success_response(
        data={"invite_id": invite_id},
        message="Invitation revoked successfully"
    )


@router.post("/team/accept/{token}")
async def accept_team_invite(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Accept team invitation"""
    invite = db.query(TeamInvite).filter(
        TeamInvite.token == token,
        TeamInvite.status == "pending"
    ).first()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found or expired"
        )

    if invite.expires_at < datetime.utcnow():
        invite.status = "expired"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired"
        )

    # Check if user email matches
    if current_user.email != invite.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invitation is for a different email address"
        )

    # Create team member
    member = TeamMember(
        tenant_id=invite.tenant_id,
        user_id=current_user.id,
        role=invite.role,
        permissions=invite.permissions,
        invited_by=invite.invited_by,
        joined_at=datetime.utcnow()
    )

    db.add(member)

    # Update invitation
    invite.status = "accepted"
    invite.accepted_at = datetime.utcnow()

    db.commit()

    return success_response(
        data={"tenant_id": invite.tenant_id},
        message="Successfully joined team"
    )


@router.get("/team/members", response_model=List[TeamMemberResponse])
async def list_team_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """List all team members"""
    members = db.query(TeamMember).filter(
        TeamMember.tenant_id == current_user.tenant_id,
        TeamMember.is_active == True
    ).all()

    return members


@router.put("/team/members/{member_id}", response_model=TeamMemberResponse)
async def update_team_member(
    member_id: str,
    member_data: TeamMemberUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db_session)
):
    """Update team member role/permissions (Admin only)"""
    member = db.query(TeamMember).filter(
        TeamMember.id == member_id,
        TeamMember.tenant_id == current_user.tenant_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )

    # Update fields
    if member_data.role:
        member.role = member_data.role
    if member_data.permissions is not None:
        member.permissions = member_data.permissions
    if member_data.department:
        member.department = member_data.department
    if member_data.title:
        member.title = member_data.title

    db.commit()
    db.refresh(member)

    return member


@router.delete("/team/members/{member_id}")
async def remove_team_member(
    member_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db_session)
):
    """Remove team member (Admin only)"""
    member = db.query(TeamMember).filter(
        TeamMember.id == member_id,
        TeamMember.tenant_id == current_user.tenant_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )

    member.is_active = False
    db.commit()

    return success_response(
        data={"member_id": member_id},
        message="Team member removed successfully"
    )


# ==========================================
# USAGE QUOTA & BILLING ENDPOINTS
# ==========================================

@router.get("/billing/quota", response_model=UsageQuotaResponse)
async def get_usage_quota(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get current usage quota and limits"""
    quota = db.query(UsageQuota).filter(
        UsageQuota.tenant_id == current_user.tenant_id
    ).first()

    if not quota:
        # Create default quota
        quota = UsageQuota(
            tenant_id=current_user.tenant_id,
            plan="free"
        )
        db.add(quota)
        db.commit()
        db.refresh(quota)

    return quota


@router.get("/billing/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db_session)
):
    """Get current subscription (Admin only)"""
    subscription = db.query(Subscription).filter(
        Subscription.tenant_id == current_user.tenant_id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )

    return subscription


@router.post("/billing/subscription", response_model=SubscriptionResponse)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db_session)
):
    """Create or update subscription (Admin only)"""
    # Check if subscription exists
    existing = db.query(Subscription).filter(
        Subscription.tenant_id == current_user.tenant_id
    ).first()

    if existing:
        # Update existing subscription
        existing.plan = subscription_data.plan
        existing.billing_interval = subscription_data.billing_interval
        existing.updated_at = datetime.utcnow()

        # Update quota
        quota = db.query(UsageQuota).filter(
            UsageQuota.tenant_id == current_user.tenant_id
        ).first()

        if quota:
            quota.plan = subscription_data.plan
            # Update limits based on plan
            if subscription_data.plan == "starter":
                quota.documents_per_month = 1000
                quota.api_calls_per_month = 10000
                quota.team_members_limit = 10
                quota.webhooks_allowed = True
            elif subscription_data.plan == "professional":
                quota.documents_per_month = 5000
                quota.api_calls_per_month = 50000
                quota.team_members_limit = 50
                quota.webhooks_allowed = True
            elif subscription_data.plan == "enterprise":
                quota.documents_per_month = -1  # Unlimited
                quota.api_calls_per_month = -1
                quota.team_members_limit = -1
                quota.webhooks_allowed = True

        db.commit()
        db.refresh(existing)
        return existing

    # Create new subscription
    subscription = Subscription(
        tenant_id=current_user.tenant_id,
        plan=subscription_data.plan,
        status="active",
        billing_interval=subscription_data.billing_interval,
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=30 if subscription_data.billing_interval == "monthly" else 365)
    )

    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return subscription


@router.get("/billing/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db_session)
):
    """List all invoices (Admin only)"""
    invoices = db.query(Invoice).filter(
        Invoice.tenant_id == current_user.tenant_id
    ).order_by(Invoice.created_at.desc()).all()

    return invoices


@router.get("/billing/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db_session)
):
    """Get specific invoice (Admin only)"""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.tenant_id == current_user.tenant_id
    ).first()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    return invoice


# ==========================================
# ENHANCED WEBHOOK ENDPOINTS
# ==========================================

@router.post("/webhooks", response_model=WebhookResponse)
async def create_webhook(
    webhook_data: WebhookCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db_session)
):
    """Create webhook endpoint (Admin only)"""
    # Check quota
    quota = db.query(UsageQuota).filter(
        UsageQuota.tenant_id == current_user.tenant_id
    ).first()

    if quota and not quota.webhooks_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhooks not allowed on current plan. Upgrade to enable webhooks."
        )

    # Create webhook
    webhook = WebhookEndpoint(
        tenant_id=current_user.tenant_id,
        url=webhook_data.url,
        secret=webhook_data.secret or secrets.token_urlsafe(32),
        events=webhook_data.events,
        is_active=True
    )

    db.add(webhook)
    db.commit()
    db.refresh(webhook)

    return webhook


@router.get("/webhooks", response_model=List[WebhookResponse])
async def list_webhooks(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db_session)
):
    """List all webhooks (Admin only)"""
    webhooks = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.tenant_id == current_user.tenant_id
    ).all()

    return webhooks


@router.put("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    webhook_data: WebhookUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db_session)
):
    """Update webhook (Admin only)"""
    webhook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.tenant_id == current_user.tenant_id
    ).first()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    # Update fields
    if webhook_data.url:
        webhook.url = webhook_data.url
    if webhook_data.events is not None:
        webhook.events = webhook_data.events
    if webhook_data.is_active is not None:
        webhook.is_active = webhook_data.is_active

    db.commit()
    db.refresh(webhook)

    return webhook


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db_session)
):
    """Delete webhook (Admin only)"""
    webhook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.tenant_id == current_user.tenant_id
    ).first()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    db.delete(webhook)
    db.commit()

    return success_response(
        data={"webhook_id": webhook_id},
        message="Webhook deleted successfully"
    )


@router.get("/webhooks/{webhook_id}/deliveries", response_model=List[WebhookDeliveryResponse])
async def list_webhook_deliveries(
    webhook_id: str,
    limit: int = Query(50, le=100),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db_session)
):
    """List webhook delivery attempts (Admin only)"""
    # Verify webhook belongs to tenant
    webhook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.tenant_id == current_user.tenant_id
    ).first()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    # Get deliveries
    deliveries = db.query(WebhookDelivery).filter(
        WebhookDelivery.webhook_id == webhook_id
    ).order_by(WebhookDelivery.created_at.desc()).limit(limit).all()

    return deliveries


# ==========================================
# TENANT BRANDING ENDPOINTS
# ==========================================

@router.get("/branding", response_model=TenantBrandingResponse)
async def get_branding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get tenant branding"""
    branding = db.query(TenantBranding).filter(
        TenantBranding.tenant_id == current_user.tenant_id
    ).first()

    if not branding:
        # Create default branding
        branding = TenantBranding(
            tenant_id=current_user.tenant_id
        )
        db.add(branding)
        db.commit()
        db.refresh(branding)

    return branding


@router.put("/branding", response_model=TenantBrandingResponse)
async def update_branding(
    branding_data: TenantBrandingUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db_session)
):
    """Update tenant branding (Admin only)"""
    branding = db.query(TenantBranding).filter(
        TenantBranding.tenant_id == current_user.tenant_id
    ).first()

    if not branding:
        # Create new branding
        branding = TenantBranding(tenant_id=current_user.tenant_id)
        db.add(branding)

    # Update fields
    for field, value in branding_data.dict(exclude_unset=True).items():
        setattr(branding, field, value)

    branding.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(branding)

    return branding
