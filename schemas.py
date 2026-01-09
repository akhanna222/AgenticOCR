"""
Pydantic schemas for request/response validation
Type-safe API contracts
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, validator


# ==========================================
# AUTH SCHEMAS
# ==========================================

class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    tenant_name: Optional[str] = None  # For creating new tenant

    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class UserResponse(BaseModel):
    """User response"""
    id: str
    email: str
    full_name: Optional[str]
    role: str
    tenant_id: str
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True


# ==========================================
# API KEY SCHEMAS
# ==========================================

class APIKeyCreate(BaseModel):
    """Create API key request"""
    name: Optional[str] = None
    expires_in_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    """API key response (only shown once)"""
    id: str
    name: Optional[str]
    key: str  # Full key (only returned on creation)
    key_prefix: str
    created_at: datetime
    expires_at: Optional[datetime]


class APIKeyInfo(BaseModel):
    """API key info (without secret)"""
    id: str
    name: Optional[str]
    key_prefix: str
    last_used: Optional[datetime]
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool

    class Config:
        orm_mode = True


# ==========================================
# TENANT SCHEMAS
# ==========================================

class TenantCreate(BaseModel):
    """Create tenant request"""
    name: str
    slug: str = Field(..., regex="^[a-z0-9-]+$")
    plan: str = "free"


class TenantUpdate(BaseModel):
    """Update tenant request"""
    name: Optional[str]
    plan: Optional[str]
    settings: Optional[Dict[str, Any]]


class TenantResponse(BaseModel):
    """Tenant response"""
    id: str
    name: str
    slug: str
    plan: str
    settings: Dict[str, Any]
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True


# ==========================================
# TEMPLATE SCHEMAS
# ==========================================

class TemplateField(BaseModel):
    """Template field definition"""
    name: str
    type: str = "text"  # text, number, date, currency, email, phone, etc.
    required: bool = False
    validation: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class TemplateCreate(BaseModel):
    """Create template request"""
    name: str
    slug: str = Field(..., regex="^[a-z0-9_-]+$")
    description: Optional[str] = None
    schema: Dict[str, Any]
    is_public: bool = False


class TemplateUpdate(BaseModel):
    """Update template request"""
    name: Optional[str]
    description: Optional[str]
    schema: Optional[Dict[str, Any]]
    is_active: Optional[bool]


class TemplateResponse(BaseModel):
    """Template response"""
    id: str
    name: str
    slug: str
    description: Optional[str]
    schema: Dict[str, Any]
    version: str
    is_public: bool
    is_active: bool
    usage_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# ==========================================
# DOCUMENT SCHEMAS
# ==========================================

class DocumentUpload(BaseModel):
    """Document upload metadata"""
    template_id: Optional[str] = None
    filename: Optional[str] = None


class DocumentProcess(BaseModel):
    """Document processing request"""
    doc_id: str
    template_id: Optional[str] = None
    use_evaluator: bool = True
    required_fields: Optional[List[str]] = None


class DocumentResponse(BaseModel):
    """Document response"""
    id: str
    filename: str
    status: str
    template_id: Optional[str]
    extracted_data: Optional[Dict[str, Any]]
    confidence_scores: Optional[Dict[str, float]]
    quality_metrics: Optional[Dict[str, Any]]
    flagged_fields: Optional[List[str]]
    processing_time_ms: Optional[int]
    created_at: datetime
    processed_at: Optional[datetime]

    class Config:
        orm_mode = True


class DocumentListResponse(BaseModel):
    """Paginated document list"""
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# ==========================================
# PROCESSING RESULT SCHEMAS
# ==========================================

class ProcessingResult(BaseModel):
    """Complete processing result"""
    success: bool
    document_id: str
    status: str
    extracted_data: Dict[str, Any]
    confidence_scores: Dict[str, float]
    assessment_report: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    flagged_fields: List[str]
    processing_time_ms: int
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error: Dict[str, Any]


# ==========================================
# ANALYTICS SCHEMAS
# ==========================================

class UsageStats(BaseModel):
    """Usage statistics"""
    total_documents: int
    documents_today: int
    documents_this_month: int
    average_quality_score: float
    success_rate: float
    total_api_calls: int


class AnalyticsOverview(BaseModel):
    """Analytics overview"""
    usage: UsageStats
    top_templates: List[Dict[str, Any]]
    recent_documents: List[DocumentResponse]
    processing_trends: List[Dict[str, Any]]


# ==========================================
# WEBHOOK SCHEMAS
# ==========================================

class WebhookCreate(BaseModel):
    """Create webhook request"""
    url: str = Field(..., regex="^https?://")
    events: List[str] = ["document.completed", "document.failed"]
    secret: Optional[str] = None


class WebhookResponse(BaseModel):
    """Webhook response"""
    id: str
    url: str
    events: List[str]
    is_active: bool
    failure_count: int
    last_success: Optional[datetime]
    created_at: datetime

    class Config:
        orm_mode = True


# ==========================================
# PAGINATION SCHEMAS
# ==========================================

class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class SortParams(BaseModel):
    """Sorting parameters"""
    sort_by: str = "created_at"
    sort_order: str = "desc"  # asc or desc


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def success_response(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """Create success response"""
    response = {
        "success": True,
        "data": data,
    }
    if message:
        response["message"] = message
    return response


def error_response(
    code: str,
    message: str,
    details: Optional[str] = None,
    status_code: int = 400
) -> Dict[str, Any]:
    """Create error response"""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }
