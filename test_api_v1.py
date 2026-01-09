#!/usr/bin/env python3
"""
Test script for API v1
Run after installing dependencies: pip install -r requirements.txt
"""

import os
import sys

# Set test environment
os.environ.setdefault('DATABASE_URL', 'sqlite:///./test_agenticocr.db')
os.environ.setdefault('OPENAI_API_KEY', 'test-key-for-init')
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

print("=" * 60)
print("🧪 AgenticOCR API v1 - Test Suite")
print("=" * 60)
print()


def test_imports():
    """Test that all modules can be imported"""
    print("1️⃣ Testing imports...")

    try:
        import database
        import models
        import auth
        import schemas
        import api_v1
        print("   ✅ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        print("\n   💡 Run: pip install -r requirements.txt")
        return False


def test_database():
    """Test database initialization"""
    print("\n2️⃣ Testing database initialization...")

    try:
        from database import init_db, engine
        from sqlalchemy import inspect

        # Initialize database
        init_db()

        # Verify tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        expected = ['tenants', 'users', 'api_keys', 'templates', 'documents', 'usage_logs', 'audit_logs']
        missing = [t for t in expected if t not in tables]

        if missing:
            print(f"   ❌ Missing tables: {missing}")
            return False

        print(f"   ✅ All {len(tables)} tables created successfully")
        return True

    except Exception as e:
        print(f"   ❌ Database test failed: {e}")
        return False


def test_models():
    """Test creating model instances"""
    print("\n3️⃣ Testing models...")

    try:
        from database import engine
        from models import Tenant, User, Template
        from auth import hash_password
        from sqlalchemy.orm import Session

        with Session(engine) as db:
            # Create tenant
            tenant = Tenant(
                name='Test Company',
                slug='test',
                plan='free',
                settings={},
                is_active=True,
            )
            db.add(tenant)
            db.flush()

            # Create user
            user = User(
                tenant_id=tenant.id,
                email='test@test.com',
                password_hash=hash_password('password123'),
                full_name='Test User',
                role='admin',
                is_active=True,
            )
            db.add(user)
            db.flush()

            # Create template
            template = Template(
                tenant_id=tenant.id,
                created_by=user.id,
                name='Test Template',
                slug='test_template',
                schema={'fields': [{'name': 'test_field', 'type': 'text'}]},
                version='1.0',
                is_active=True,
            )
            db.add(template)
            db.commit()

            print(f"   ✅ Created tenant: {tenant.name} ({tenant.id})")
            print(f"   ✅ Created user: {user.email} ({user.id})")
            print(f"   ✅ Created template: {template.name} ({template.id})")

        return True

    except Exception as e:
        print(f"   ❌ Models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auth():
    """Test authentication functions"""
    print("\n4️⃣ Testing authentication...")

    try:
        from auth import hash_password, verify_password, create_access_token, decode_token

        # Test password hashing
        password = "test123"
        hashed = hash_password(password)
        if not verify_password(password, hashed):
            print("   ❌ Password verification failed")
            return False

        print("   ✅ Password hashing works")

        # Test JWT tokens
        token = create_access_token(
            user_id="test-user",
            tenant_id="test-tenant",
            role="admin"
        )
        payload = decode_token(token)

        if payload['sub'] != 'test-user' or payload['tenant_id'] != 'test-tenant':
            print("   ❌ Token payload incorrect")
            return False

        print("   ✅ JWT token creation/decoding works")

        return True

    except Exception as e:
        print(f"   ❌ Auth test failed: {e}")
        return False


def test_schemas():
    """Test Pydantic schemas"""
    print("\n5️⃣ Testing schemas...")

    try:
        from schemas import UserRegister, TemplateCreate, DocumentProcess

        # Test UserRegister
        user = UserRegister(
            email="test@example.com",
            password="password123",
            full_name="Test User",
            tenant_name="Test Company"
        )
        print("   ✅ UserRegister schema works")

        # Test TemplateCreate
        template = TemplateCreate(
            name="Test Template",
            slug="test_template",
            schema={"fields": [{"name": "test", "type": "text"}]}
        )
        print("   ✅ TemplateCreate schema works")

        # Test DocumentProcess
        doc = DocumentProcess(
            doc_id="test-doc",
            template_id="test-template",
            use_evaluator=True,
            required_fields=["field1", "field2"]
        )
        print("   ✅ DocumentProcess schema works")

        return True

    except Exception as e:
        print(f"   ❌ Schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_app():
    """Test FastAPI app creation"""
    print("\n6️⃣ Testing FastAPI app...")

    try:
        from api_v1 import app

        # Check app attributes
        if not hasattr(app, 'routes'):
            print("   ❌ App doesn't have routes")
            return False

        route_paths = [route.path for route in app.routes]

        # Check critical endpoints exist
        critical_endpoints = [
            '/api/v1/auth/register',
            '/api/v1/auth/login',
            '/api/v1/templates',
            '/api/v1/documents/upload',
        ]

        missing = [ep for ep in critical_endpoints if ep not in route_paths]
        if missing:
            print(f"   ❌ Missing endpoints: {missing}")
            return False

        print(f"   ✅ FastAPI app created with {len(route_paths)} routes")
        print(f"   ✅ All critical endpoints registered")

        return True

    except Exception as e:
        print(f"   ❌ API app test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup():
    """Clean up test database"""
    print("\n🧹 Cleaning up...")
    try:
        if os.path.exists('test_agenticocr.db'):
            os.remove('test_agenticocr.db')
            print("   ✅ Test database removed")
    except Exception as e:
        print(f"   ⚠️  Cleanup warning: {e}")


def main():
    """Run all tests"""
    results = []

    # Run tests
    results.append(("Imports", test_imports()))

    if results[0][1]:  # Only continue if imports worked
        results.append(("Database", test_database()))
        results.append(("Models", test_models()))
        results.append(("Auth", test_auth()))
        results.append(("Schemas", test_schemas()))
        results.append(("API App", test_api_app()))

    # Cleanup
    cleanup()

    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {test_name}")

    print("=" * 60)
    print(f"Result: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("\n🎉 All tests passed! API v1 is ready to use.")
        print("\n📝 Next steps:")
        print("   1. Run: python init_db.py")
        print("   2. Run: python api_v1.py")
        print("   3. Visit: http://localhost:8000/api/docs")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests cancelled by user")
        cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        cleanup()
        sys.exit(1)
