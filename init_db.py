#!/usr/bin/env python3
"""
Database Initialization Script
Creates all tables and sets up default data
"""

import os
import sys
from datetime import datetime

from database import engine, init_db
from models import Base, Tenant, Template, User
from auth import hash_password


def create_default_templates(db, tenant_id: str):
    """Create default templates for invoice and bank statement"""

    # Invoice template
    invoice_template = Template(
        tenant_id=tenant_id,
        name="Invoice",
        slug="invoice",
        description="Standard invoice document parser",
        schema={
            "fields": [
                {
                    "name": "invoice_number",
                    "type": "text",
                    "required": True,
                    "description": "Invoice number or reference"
                },
                {
                    "name": "invoice_date",
                    "type": "date",
                    "required": True,
                    "description": "Invoice date"
                },
                {
                    "name": "due_date",
                    "type": "date",
                    "required": False,
                    "description": "Payment due date"
                },
                {
                    "name": "vendor_name",
                    "type": "text",
                    "required": True,
                    "description": "Vendor or supplier name"
                },
                {
                    "name": "vendor_address",
                    "type": "address",
                    "required": False,
                    "description": "Vendor address"
                },
                {
                    "name": "customer_name",
                    "type": "text",
                    "required": True,
                    "description": "Customer or bill-to name"
                },
                {
                    "name": "customer_address",
                    "type": "address",
                    "required": False,
                    "description": "Customer address"
                },
                {
                    "name": "subtotal",
                    "type": "currency",
                    "required": True,
                    "description": "Subtotal amount before tax"
                },
                {
                    "name": "tax_amount",
                    "type": "currency",
                    "required": False,
                    "description": "Tax amount"
                },
                {
                    "name": "total_amount",
                    "type": "currency",
                    "required": True,
                    "description": "Total amount due"
                },
                {
                    "name": "currency",
                    "type": "text",
                    "required": False,
                    "description": "Currency code (USD, EUR, etc.)"
                },
                {
                    "name": "payment_terms",
                    "type": "text",
                    "required": False,
                    "description": "Payment terms"
                },
                {
                    "name": "line_items",
                    "type": "array",
                    "required": False,
                    "description": "Line items list"
                }
            ]
        },
        version="1.0",
        is_public=True,
        is_active=True,
        usage_count=0,
    )

    # Bank statement template
    bank_statement_template = Template(
        tenant_id=tenant_id,
        name="Bank Statement",
        slug="bank_statement",
        description="Bank account statement parser",
        schema={
            "fields": [
                {
                    "name": "account_holder",
                    "type": "text",
                    "required": True,
                    "description": "Account holder name"
                },
                {
                    "name": "account_number",
                    "type": "text",
                    "required": True,
                    "description": "Bank account number"
                },
                {
                    "name": "bank_name",
                    "type": "text",
                    "required": True,
                    "description": "Bank name"
                },
                {
                    "name": "statement_period_start",
                    "type": "date",
                    "required": True,
                    "description": "Statement period start date"
                },
                {
                    "name": "statement_period_end",
                    "type": "date",
                    "required": True,
                    "description": "Statement period end date"
                },
                {
                    "name": "opening_balance",
                    "type": "currency",
                    "required": True,
                    "description": "Opening balance"
                },
                {
                    "name": "closing_balance",
                    "type": "currency",
                    "required": True,
                    "description": "Closing balance"
                },
                {
                    "name": "total_deposits",
                    "type": "currency",
                    "required": False,
                    "description": "Total deposits"
                },
                {
                    "name": "total_withdrawals",
                    "type": "currency",
                    "required": False,
                    "description": "Total withdrawals"
                },
                {
                    "name": "currency",
                    "type": "text",
                    "required": False,
                    "description": "Currency code"
                },
                {
                    "name": "transactions",
                    "type": "array",
                    "required": False,
                    "description": "List of transactions"
                }
            ]
        },
        version="1.0",
        is_public=True,
        is_active=True,
        usage_count=0,
    )

    db.add(invoice_template)
    db.add(bank_statement_template)
    db.commit()

    return invoice_template, bank_statement_template


def setup_database():
    """Initialize database and create default data"""
    print("=" * 60)
    print("🚀 AgenticOCR Database Initialization")
    print("=" * 60)
    print()

    # Create all tables
    print("📊 Creating database tables...")
    init_db()
    print("   ✅ Tables created successfully")
    print()

    # Check if we should create demo data
    create_demo = input("Create demo tenant and admin user? (y/n): ").lower() == 'y'

    if create_demo:
        from sqlalchemy.orm import Session

        with Session(engine) as db:
            # Check if demo tenant exists
            existing = db.query(Tenant).filter(Tenant.slug == "demo").first()
            if existing:
                print("   ⚠️  Demo tenant already exists, skipping...")
                return

            print("👤 Creating demo tenant...")

            # Create demo tenant
            demo_tenant = Tenant(
                name="Demo Company",
                slug="demo",
                plan="free",
                settings={},
                is_active=True,
            )
            db.add(demo_tenant)
            db.flush()

            print(f"   ✅ Tenant created: {demo_tenant.name} (ID: {demo_tenant.id})")
            print()

            # Create admin user
            print("🔐 Creating admin user...")
            admin_email = input("   Admin email (default: admin@demo.com): ").strip()
            if not admin_email:
                admin_email = "admin@demo.com"

            admin_password = input("   Admin password (default: admin123): ").strip()
            if not admin_password:
                admin_password = "admin123"

            admin_user = User(
                tenant_id=demo_tenant.id,
                email=admin_email,
                password_hash=hash_password(admin_password),
                full_name="Demo Admin",
                role="admin",
                is_active=True,
                is_verified=True,
            )
            db.add(admin_user)
            db.commit()

            print(f"   ✅ Admin user created: {admin_email}")
            print()

            # Create default templates
            print("📋 Creating default templates...")
            invoice_tmpl, bank_tmpl = create_default_templates(db, demo_tenant.id)
            print(f"   ✅ Invoice template created (slug: {invoice_tmpl.slug})")
            print(f"   ✅ Bank statement template created (slug: {bank_tmpl.slug})")
            print()

            print("=" * 60)
            print("✨ Setup Complete!")
            print("=" * 60)
            print()
            print("📝 Demo Credentials:")
            print(f"   Email:    {admin_email}")
            print(f"   Password: {admin_password}")
            print(f"   Tenant:   {demo_tenant.slug}")
            print()
            print("🚀 Start the server:")
            print("   python api_v1.py")
            print()
            print("📖 API Documentation:")
            print("   http://localhost:8000/api/docs")
            print()
            print("🔑 Next Steps:")
            print("   1. Visit http://localhost:8000/api/docs")
            print("   2. Click 'Authorize' and login")
            print("   3. Try the /api/v1/auth/login endpoint")
            print("   4. Use the access token for other endpoints")
            print()
    else:
        print("=" * 60)
        print("✨ Database tables created successfully!")
        print("=" * 60)
        print()
        print("To create your first tenant and user, use the API:")
        print("   POST /api/v1/auth/register")
        print()
        print("Start the server:")
        print("   python api_v1.py")
        print()


if __name__ == "__main__":
    try:
        setup_database()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error during setup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
