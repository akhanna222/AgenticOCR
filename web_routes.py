"""
Web UI Routes
HTML pages for the dashboard interface
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db_session
from models import User

# Setup templates
templates = Jinja2Templates(directory="templates")

# Create router
router = APIRouter()


# ==========================================
# AUTHENTICATION CHECK
# ==========================================

async def check_web_auth(request: Request):
    """Check if user is authenticated via cookie or redirect to login"""
    # For web UI, we'll use the Authorization header or redirect
    # This is a simplified version - in production, use session cookies
    pass  # We'll handle auth in JavaScript


# ==========================================
# WEB ROUTES
# ==========================================

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page - redirect to dashboard or login"""
    return RedirectResponse(url="/dashboard")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login/Register page"""
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": None  # Will be loaded via API
    })


@router.get("/documents", response_class=HTMLResponse)
async def documents_page(request: Request):
    """Documents list page"""
    return templates.TemplateResponse("documents.html", {
        "request": request,
        "user": None
    })


@router.get("/templates", response_class=HTMLResponse)
async def templates_page(request: Request):
    """Templates management page"""
    return templates.TemplateResponse("templates.html", {
        "request": request,
        "user": None
    })


@router.get("/api-keys", response_class=HTMLResponse)
async def api_keys_page(request: Request):
    """API keys management page"""
    return templates.TemplateResponse("api-keys.html", {
        "request": request,
        "user": None
    })


@router.get("/team", response_class=HTMLResponse)
async def team_page(request: Request):
    """Team management page"""
    return templates.TemplateResponse("team.html", {
        "request": request,
        "user": None
    })


@router.get("/billing", response_class=HTMLResponse)
async def billing_page(request: Request):
    """Billing and subscription page"""
    return templates.TemplateResponse("billing.html", {
        "request": request,
        "user": None
    })


@router.get("/webhooks", response_class=HTMLResponse)
async def webhooks_page(request: Request):
    """Webhooks management page"""
    return templates.TemplateResponse("webhooks.html", {
        "request": request,
        "user": None
    })


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings and branding page"""
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user": None
    })
