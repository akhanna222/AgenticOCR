"""
FastAPI Application - Phase 1 MVP
Production-ready document parsing SaaS with multi-tenant architecture
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

# Import our modules
from auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    decode_token,
    generate_api_key,
    get_current_user,
    get_current_user_or_api_key,
    require_admin,
)
from database import (
    get_db,
    get_db_session,
    init_db,
    set_tenant_context,
)
from models import (
    APIKey,
    AuditLog,
    Document,
    Template,
    Tenant,
    UsageLog,
    User,
)
from schemas import (
    APIKeyCreate,
    APIKeyInfo,
    APIKeyResponse,
    AnalyticsOverview,
    DocumentListResponse,
    DocumentProcess,
    DocumentResponse,
    DocumentUpload,
    ErrorResponse,
    PaginationParams,
    ProcessingResult,
    TemplateCreate,
    TemplateResponse,
    TemplateUpdate,
    TenantCreate,
    TenantResponse,
    TenantUpdate,
    TokenResponse,
    UsageStats,
    UserLogin,
    UserRegister,
    UserResponse,
    error_response,
    success_response,
)

# Import OCR system
from mortgage_core import run_agentic_pipeline, classify_document
from pdf2image import convert_from_path

# Import Phase 2 router
from api_phase2 import router as phase2_router

# Import Web routes
from web_routes import router as web_router

# Initialize FastAPI app
app = FastAPI(
    title="AgenticOCR API",
    description="Production-ready document parsing SaaS with intelligent OCR",
    version="2.0.0",  # Phase 2
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include Phase 2 API routes
app.include_router(phase2_router)

# Include Web UI routes
app.include_router(web_router)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# MIDDLEWARE - Usage Tracking
# ==========================================

@app.middleware("http")
async def track_usage(request, call_next):
    """Track API usage for billing and analytics"""
    start_time = datetime.utcnow()

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    # Log usage if authenticated
    if hasattr(request.state, "user") and hasattr(request.state, "tenant_id"):
        try:
            db = next(get_db_session())

            usage_log = UsageLog(
                tenant_id=request.state.tenant_id,
                user_id=request.state.user.id if request.state.user else None,
                api_key_id=request.state.api_key.id if hasattr(request.state, "api_key") else None,
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
                request_size_bytes=int(request.headers.get("content-length", 0)),
                response_size_bytes=int(response.headers.get("content-length", 0)),
            )

            db.add(usage_log)
            db.commit()
        except Exception as e:
            print(f"Error logging usage: {e}")

    return response


# ==========================================
# STARTUP/SHUTDOWN
# ==========================================

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("✅ Database initialized")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ==========================================
# AUTH ENDPOINTS
# ==========================================

@app.post("/api/v1/auth/register", response_model=Dict[str, Any])
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db_session)
):
    """
    Register new user and optionally create new tenant

    If tenant_name is provided, creates new tenant and makes user admin.
    Otherwise, user must be invited to existing tenant.
    """
    try:
        # Create tenant if specified
        if user_data.tenant_name:
            # Generate slug from name
            slug = user_data.tenant_name.lower().replace(" ", "-")

            # Check if tenant exists
            existing_tenant = db.query(Tenant).filter(Tenant.slug == slug).first()
            if existing_tenant:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tenant with this name already exists"
                )

            # Create tenant
            tenant = Tenant(
                name=user_data.tenant_name,
                slug=slug,
                plan="free",
                settings={},
                is_active=True,
            )
            db.add(tenant)
            db.flush()  # Get tenant.id

            tenant_id = tenant.id
            role = "admin"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tenant_name is required for new registrations"
            )

        # Create user
        user = create_user(
            email=user_data.email,
            password=user_data.password,
            tenant_id=tenant_id,
            full_name=user_data.full_name,
            role=role,
            db=db,
        )

        # Create tokens
        access_token = create_access_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            role=user.role,
        )

        refresh_token = create_refresh_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
        )

        # Log audit event
        audit = AuditLog(
            tenant_id=tenant_id,
            user_id=user.id,
            action="user.register",
            resource_type="user",
            resource_id=user.id,
            details={"email": user.email, "role": role},
        )
        db.add(audit)
        db.commit()

        return success_response(
            data={
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                    "tenant_id": user.tenant_id,
                },
                "tokens": {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer",
                    "expires_in": 3600,
                }
            },
            message="User registered successfully"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db_session)
):
    """Login with email and password"""
    user = authenticate_user(credentials.email, credentials.password, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Create tokens
    access_token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
    )

    refresh_token = create_refresh_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
    )

    # Log audit event
    audit = AuditLog(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="user.login",
        resource_type="user",
        resource_id=user.id,
        details={"email": user.email},
    )
    db.add(audit)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=3600,
    )


@app.post("/api/v1/auth/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db_session)
):
    """Refresh access token using refresh token"""
    payload = decode_token(refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Create new tokens
    new_access_token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
    )

    new_refresh_token = create_refresh_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=3600,
    )


@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        tenant_id=current_user.tenant_id,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


# ==========================================
# API KEY ENDPOINTS
# ==========================================

@app.post("/api/v1/auth/api-keys", response_model=APIKeyResponse)
async def create_api_key_endpoint(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create new API key"""
    # Generate key
    full_key, key_prefix, key_hash = generate_api_key()

    # Calculate expiration
    expires_at = None
    if key_data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)

    # Create API key record
    api_key = APIKey(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        name=key_data.name or f"API Key {datetime.utcnow().strftime('%Y-%m-%d')}",
        key_prefix=key_prefix,
        key_hash=key_hash,
        permissions={},
        expires_at=expires_at,
        is_active=True,
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    # Log audit event
    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="api_key.create",
        resource_type="api_key",
        resource_id=api_key.id,
        details={"name": api_key.name},
    )
    db.add(audit)
    db.commit()

    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=full_key,  # Only shown once!
        key_prefix=api_key.key_prefix,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
    )


@app.get("/api/v1/auth/api-keys", response_model=List[APIKeyInfo])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """List all API keys for current user"""
    api_keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.tenant_id == current_user.tenant_id,
    ).all()

    return [
        APIKeyInfo(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            last_used=key.last_used,
            created_at=key.created_at,
            expires_at=key.expires_at,
            is_active=key.is_active,
        )
        for key in api_keys
    ]


@app.delete("/api/v1/auth/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Revoke API key"""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id,
        APIKey.tenant_id == current_user.tenant_id,
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    api_key.is_active = False
    db.commit()

    # Log audit event
    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="api_key.revoke",
        resource_type="api_key",
        resource_id=api_key.id,
        details={"name": api_key.name},
    )
    db.add(audit)
    db.commit()

    return success_response(
        data={"key_id": key_id},
        message="API key revoked successfully"
    )


# ==========================================
# TEMPLATE ENDPOINTS
# ==========================================

@app.post("/api/v1/templates", response_model=TemplateResponse)
async def create_template(
    template_data: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create new document template"""
    # Check if template exists
    existing = db.query(Template).filter(
        Template.tenant_id == current_user.tenant_id,
        Template.slug == template_data.slug,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template with this slug already exists"
        )

    # Create template
    template = Template(
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        name=template_data.name,
        slug=template_data.slug,
        description=template_data.description,
        schema=template_data.schema,
        version="1.0",
        is_public=template_data.is_public,
        is_active=True,
        usage_count=0,
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    # Log audit event
    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="template.create",
        resource_type="template",
        resource_id=template.id,
        details={"name": template.name, "slug": template.slug},
    )
    db.add(audit)
    db.commit()

    return TemplateResponse(
        id=template.id,
        name=template.name,
        slug=template.slug,
        description=template.description,
        schema=template.schema,
        version=template.version,
        is_public=template.is_public,
        is_active=template.is_active,
        usage_count=template.usage_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@app.get("/api/v1/templates", response_model=List[TemplateResponse])
async def list_templates(
    include_public: bool = Query(True, description="Include public templates"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """List all available templates"""
    query = db.query(Template).filter(Template.is_active == True)

    if include_public:
        # Show tenant templates + public templates
        query = query.filter(
            (Template.tenant_id == current_user.tenant_id) |
            (Template.is_public == True)
        )
    else:
        # Show only tenant templates
        query = query.filter(Template.tenant_id == current_user.tenant_id)

    templates = query.order_by(Template.created_at.desc()).all()

    return [
        TemplateResponse(
            id=t.id,
            name=t.name,
            slug=t.slug,
            description=t.description,
            schema=t.schema,
            version=t.version,
            is_public=t.is_public,
            is_active=t.is_active,
            usage_count=t.usage_count,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in templates
    ]


@app.get("/api/v1/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get template by ID"""
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.is_active == True,
        (
            (Template.tenant_id == current_user.tenant_id) |
            (Template.is_public == True)
        )
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    return TemplateResponse(
        id=template.id,
        name=template.name,
        slug=template.slug,
        description=template.description,
        schema=template.schema,
        version=template.version,
        is_public=template.is_public,
        is_active=template.is_active,
        usage_count=template.usage_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@app.put("/api/v1/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    template_data: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update template"""
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.tenant_id == current_user.tenant_id,
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Update fields
    if template_data.name:
        template.name = template_data.name
    if template_data.description is not None:
        template.description = template_data.description
    if template_data.schema:
        template.schema = template_data.schema
        # Increment version
        major, minor = template.version.split(".")
        template.version = f"{major}.{int(minor) + 1}"
    if template_data.is_active is not None:
        template.is_active = template_data.is_active

    template.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(template)

    # Log audit event
    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="template.update",
        resource_type="template",
        resource_id=template.id,
        details={"name": template.name},
    )
    db.add(audit)
    db.commit()

    return TemplateResponse(
        id=template.id,
        name=template.name,
        slug=template.slug,
        description=template.description,
        schema=template.schema,
        version=template.version,
        is_public=template.is_public,
        is_active=template.is_active,
        usage_count=template.usage_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@app.delete("/api/v1/templates/{template_id}")
async def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Delete template (soft delete)"""
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.tenant_id == current_user.tenant_id,
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Soft delete
    template.is_active = False
    template.updated_at = datetime.utcnow()

    db.commit()

    # Log audit event
    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="template.delete",
        resource_type="template",
        resource_id=template.id,
        details={"name": template.name},
    )
    db.add(audit)
    db.commit()

    return success_response(
        data={"template_id": template_id},
        message="Template deleted successfully"
    )


# ==========================================
# DOCUMENT ENDPOINTS
# ==========================================

@app.post("/api/v1/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    template_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Upload document for processing"""
    try:
        # Generate document ID
        doc_id = str(uuid.uuid4())

        # Create upload directory
        upload_dir = os.path.join("uploads", current_user.tenant_id)
        os.makedirs(upload_dir, exist_ok=True)

        # Save file
        file_path = os.path.join(upload_dir, f"{doc_id}_{file.filename}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Create document record
        document = Document(
            id=doc_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            template_id=template_id,
            filename=file.filename,
            file_path=file_path,
            file_size=len(content),
            mime_type=file.content_type,
            status="uploaded",
            extracted_data={},
            confidence_scores={},
            quality_metrics={},
            flagged_fields=[],
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        return success_response(
            data={
                "doc_id": doc_id,
                "filename": file.filename,
                "status": "uploaded",
            },
            message="Document uploaded successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@app.post("/api/v1/documents/{doc_id}/process", response_model=ProcessingResult)
async def process_document(
    doc_id: str,
    process_data: Optional[DocumentProcess] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Process document with agentic OCR"""
    # Get document
    document = db.query(Document).filter(
        Document.id == doc_id,
        Document.tenant_id == current_user.tenant_id,
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Get template ID
    template_id = process_data.template_id if process_data else document.template_id

    if not template_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template ID is required"
        )

    # Get template
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.is_active == True,
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    try:
        # Update status
        document.status = "processing"
        db.commit()

        # Run agentic OCR
        start_time = datetime.utcnow()

        result = run_agentic_pipeline(
            path=document.file_path,
            override_doc_type_id=template.slug,
            use_evaluator=process_data.use_evaluator if process_data else True,
            required_fields=process_data.required_fields if process_data else None,
        )

        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Update document
        document.status = "completed" if result["success"] else "failed"
        document.template_id = template_id
        document.extracted_data = result.get("extracted_data", {})
        document.confidence_scores = result.get("confidence_scores", {})
        document.quality_metrics = result.get("quality_metrics", {})
        document.flagged_fields = result.get("flagged_fields", [])
        document.processing_time_ms = processing_time_ms
        document.processed_at = datetime.utcnow()

        db.commit()

        # Update template usage count
        template.usage_count += 1
        db.commit()

        # Log audit event
        audit = AuditLog(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            action="document.process",
            resource_type="document",
            resource_id=document.id,
            details={
                "template": template.name,
                "status": document.status,
                "quality_score": result.get("quality_metrics", {}).get("quality_score", 0),
            },
        )
        db.add(audit)
        db.commit()

        return ProcessingResult(
            success=result["success"],
            document_id=doc_id,
            status=document.status,
            extracted_data=result.get("extracted_data", {}),
            confidence_scores=result.get("confidence_scores", {}),
            assessment_report=result.get("assessment_report", {}),
            quality_metrics=result.get("quality_metrics", {}),
            flagged_fields=result.get("flagged_fields", []),
            processing_time_ms=processing_time_ms,
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        document.status = "failed"
        document.error_message = str(e)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}"
        )


@app.get("/api/v1/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get document by ID"""
    document = db.query(Document).filter(
        Document.id == doc_id,
        Document.tenant_id == current_user.tenant_id,
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        status=document.status,
        template_id=document.template_id,
        extracted_data=document.extracted_data,
        confidence_scores=document.confidence_scores,
        quality_metrics=document.quality_metrics,
        flagged_fields=document.flagged_fields,
        processing_time_ms=document.processing_time_ms,
        created_at=document.created_at,
        processed_at=document.processed_at,
    )


@app.get("/api/v1/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    template_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """List documents with pagination"""
    query = db.query(Document).filter(
        Document.tenant_id == current_user.tenant_id
    )

    # Apply filters
    if status:
        query = query.filter(Document.status == status)
    if template_id:
        query = query.filter(Document.template_id == template_id)

    # Get total count
    total = query.count()

    # Paginate
    documents = query.order_by(
        Document.created_at.desc()
    ).offset((page - 1) * page_size).limit(page_size).all()

    return DocumentListResponse(
        items=[
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                status=doc.status,
                template_id=doc.template_id,
                extracted_data=doc.extracted_data,
                confidence_scores=doc.confidence_scores,
                quality_metrics=doc.quality_metrics,
                flagged_fields=doc.flagged_fields,
                processing_time_ms=doc.processing_time_ms,
                created_at=doc.created_at,
                processed_at=doc.processed_at,
            )
            for doc in documents
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


# ==========================================
# DIRECT TEMPLATE API ENDPOINTS
# ==========================================

@app.post("/api/v1/process/{template_slug}", response_model=ProcessingResult)
async def process_with_template(
    template_slug: str,
    file: UploadFile = File(...),
    use_evaluator: bool = Query(True),
    required_fields: Optional[str] = Query(None),
    user_api_key: tuple = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db_session)
):
    """
    Direct template API endpoint - upload and process in one call

    Every template becomes a direct API endpoint: /api/v1/process/{template_slug}
    """
    current_user, api_key = user_api_key
    tenant_id = current_user.tenant_id if current_user else api_key.tenant_id

    # Get template
    template = db.query(Template).filter(
        Template.slug == template_slug,
        Template.is_active == True,
        (
            (Template.tenant_id == tenant_id) |
            (Template.is_public == True)
        )
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_slug}' not found"
        )

    try:
        # Generate document ID
        doc_id = str(uuid.uuid4())

        # Create upload directory
        upload_dir = os.path.join("uploads", tenant_id)
        os.makedirs(upload_dir, exist_ok=True)

        # Save file
        file_path = os.path.join(upload_dir, f"{doc_id}_{file.filename}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Create document record
        document = Document(
            id=doc_id,
            tenant_id=tenant_id,
            user_id=current_user.id if current_user else None,
            template_id=template.id,
            filename=file.filename,
            file_path=file_path,
            file_size=len(content),
            mime_type=file.content_type,
            status="processing",
            extracted_data={},
            confidence_scores={},
            quality_metrics={},
            flagged_fields=[],
        )

        db.add(document)
        db.commit()

        # Process with agentic OCR
        start_time = datetime.utcnow()

        result = run_agentic_pipeline(
            path=file_path,
            override_doc_type_id=template_slug,
            use_evaluator=use_evaluator,
            required_fields=required_fields.split(",") if required_fields else None,
        )

        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Update document
        document.status = "completed" if result["success"] else "failed"
        document.extracted_data = result.get("extracted_data", {})
        document.confidence_scores = result.get("confidence_scores", {})
        document.quality_metrics = result.get("quality_metrics", {})
        document.flagged_fields = result.get("flagged_fields", [])
        document.processing_time_ms = processing_time_ms
        document.processed_at = datetime.utcnow()

        db.commit()

        # Update template usage count
        template.usage_count += 1
        db.commit()

        return ProcessingResult(
            success=result["success"],
            document_id=doc_id,
            status=document.status,
            extracted_data=result.get("extracted_data", {}),
            confidence_scores=result.get("confidence_scores", {}),
            assessment_report=result.get("assessment_report", {}),
            quality_metrics=result.get("quality_metrics", {}),
            flagged_fields=result.get("flagged_fields", []),
            processing_time_ms=processing_time_ms,
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        if document:
            document.status = "failed"
            document.error_message = str(e)
            db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}"
        )


# ==========================================
# ANALYTICS ENDPOINTS
# ==========================================

@app.get("/api/v1/analytics/usage", response_model=UsageStats)
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get usage statistics for current tenant"""
    tenant_id = current_user.tenant_id

    # Total documents
    total_documents = db.query(func.count(Document.id)).filter(
        Document.tenant_id == tenant_id
    ).scalar()

    # Documents today
    today = datetime.utcnow().date()
    documents_today = db.query(func.count(Document.id)).filter(
        Document.tenant_id == tenant_id,
        func.date(Document.created_at) == today,
    ).scalar()

    # Documents this month
    first_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
    documents_this_month = db.query(func.count(Document.id)).filter(
        Document.tenant_id == tenant_id,
        Document.created_at >= first_of_month,
    ).scalar()

    # Average quality score
    quality_scores = db.query(Document.quality_metrics).filter(
        Document.tenant_id == tenant_id,
        Document.status == "completed",
    ).all()

    avg_quality = 0.0
    if quality_scores:
        scores = [
            q[0].get("quality_score", 0)
            for q in quality_scores
            if q[0] and "quality_score" in q[0]
        ]
        avg_quality = sum(scores) / len(scores) if scores else 0.0

    # Success rate
    completed = db.query(func.count(Document.id)).filter(
        Document.tenant_id == tenant_id,
        Document.status == "completed",
    ).scalar()

    success_rate = (completed / total_documents * 100) if total_documents > 0 else 0.0

    # Total API calls
    total_api_calls = db.query(func.count(UsageLog.id)).filter(
        UsageLog.tenant_id == tenant_id
    ).scalar()

    return UsageStats(
        total_documents=total_documents or 0,
        documents_today=documents_today or 0,
        documents_this_month=documents_this_month or 0,
        average_quality_score=round(avg_quality, 2),
        success_rate=round(success_rate, 2),
        total_api_calls=total_api_calls or 0,
    )


# ==========================================
# DOCUMENT CLASSIFICATION ENDPOINT
# ==========================================

@app.post("/api/v1/documents/classify")
async def classify_document_endpoint(
    file: UploadFile = File(...),
    user_api_key: tuple = Depends(get_current_user_or_api_key),
    db: Session = Depends(get_db_session)
):
    """
    Classify document type without full OCR processing

    Returns document type, confidence, and suggested template
    """
    current_user, api_key = user_api_key
    tenant_id = current_user.tenant_id if current_user else api_key.tenant_id

    try:
        # Generate temporary ID
        doc_id = str(uuid.uuid4())

        # Create temporary upload directory
        upload_dir = os.path.join("uploads", tenant_id, "temp")
        os.makedirs(upload_dir, exist_ok=True)

        # Save file temporarily
        file_path = os.path.join(upload_dir, f"{doc_id}_{file.filename}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Convert first page to image
        pages = convert_from_path(file_path, first_page=1, last_page=1)

        if not pages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract pages from document"
            )

        # Classify document
        classification = classify_document(pages)

        # Find matching template
        doc_type_id = classification.get("doc_type_id", "unknown")

        # Search for template by slug
        template = db.query(Template).filter(
            Template.slug == doc_type_id,
            Template.is_active == True,
            (
                (Template.tenant_id == tenant_id) |
                (Template.is_public == True)
            )
        ).first()

        # Clean up temporary file
        try:
            os.remove(file_path)
        except:
            pass

        # Log audit event
        if current_user:
            audit = AuditLog(
                tenant_id=tenant_id,
                user_id=current_user.id,
                action="document.classify",
                resource_type="document",
                resource_id=doc_id,
                details={
                    "filename": file.filename,
                    "classification": classification,
                },
            )
            db.add(audit)
            db.commit()

        return success_response(
            data={
                "classification": classification,
                "suggested_template": {
                    "id": template.id if template else None,
                    "name": template.name if template else None,
                    "slug": template.slug if template else None,
                } if template else None,
                "filename": file.filename,
            },
            message="Document classified successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Classification failed: {str(e)}"
        )


# ==========================================
# TENANT MANAGEMENT (ADMIN ONLY)
# ==========================================

@app.get("/api/v1/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db_session)
):
    """Get tenant information (admin only)"""
    if admin.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other tenant information"
        )

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        settings=tenant.settings,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
    )


@app.put("/api/v1/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    tenant_data: TenantUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db_session)
):
    """Update tenant (admin only)"""
    if admin.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update other tenant"
        )

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    # Update fields
    if tenant_data.name:
        tenant.name = tenant_data.name
    if tenant_data.plan:
        tenant.plan = tenant_data.plan
    if tenant_data.settings:
        tenant.settings.update(tenant_data.settings)

    tenant.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(tenant)

    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        settings=tenant.settings,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
    )


# ==========================================
# ERROR HANDLERS
# ==========================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            code=f"HTTP_{exc.status_code}",
            message=exc.detail,
            status_code=exc.status_code,
        )
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            code="INTERNAL_ERROR",
            message="An internal error occurred",
            details=str(exc),
            status_code=500,
        )
    )


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":
    import uvicorn

    # Run server
    uvicorn.run(
        "api_v1:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
