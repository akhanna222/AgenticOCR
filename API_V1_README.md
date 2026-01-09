# AgenticOCR API v1 - Production SaaS Platform

Complete document parsing SaaS with multi-tenant architecture, authentication, and intelligent OCR.

## 🎯 Features

### Phase 1: MVP ✅ (Implemented)

- ✅ **Multi-Tenant Architecture** - Complete tenant isolation
- ✅ **Authentication System** - JWT tokens + API keys
- ✅ **Template Management** - Create custom document parsers
- ✅ **Default Templates** - Invoice & Bank Statement
- ✅ **Direct Template API** - Every template = API endpoint
- ✅ **Agentic OCR** - Field-level confidence & assessment
- ✅ **Usage Tracking** - Analytics & billing data
- ✅ **Audit Logging** - Compliance trail

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export OPENAI_API_KEY="sk-..."
export DATABASE_URL="sqlite:///./agenticocr.db"  # Or PostgreSQL URL
export SECRET_KEY="your-secret-key-here"
```

### 3. Initialize Database

```bash
python init_db.py
```

This creates:
- All database tables
- Demo tenant (optional)
- Admin user (optional)
- Default templates (invoice, bank_statement)

### 4. Start the Server

```bash
python api_v1.py
```

Server runs on: http://localhost:8000

### 5. Access API Documentation

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## 📖 API Overview

### Authentication Endpoints

#### Register New User & Tenant
```bash
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@company.com",
  "password": "securepassword",
  "full_name": "John Doe",
  "tenant_name": "My Company"
}

Response:
{
  "success": true,
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@company.com",
      "role": "admin",
      "tenant_id": "uuid"
    },
    "tokens": {
      "access_token": "eyJ...",
      "refresh_token": "eyJ...",
      "token_type": "bearer",
      "expires_in": 3600
    }
  }
}
```

#### Login
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@company.com",
  "password": "securepassword"
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### Create API Key
```bash
POST /api/v1/auth/api-keys
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "Production API Key",
  "expires_in_days": 365
}

Response:
{
  "id": "uuid",
  "name": "Production API Key",
  "key": "sk_live_...",  # Only shown once!
  "key_prefix": "sk_live_",
  "created_at": "2024-01-01T00:00:00Z",
  "expires_at": "2025-01-01T00:00:00Z"
}
```

### Template Endpoints

#### Create Custom Template
```bash
POST /api/v1/templates
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "W-2 Tax Form",
  "slug": "w2_tax_form",
  "description": "W-2 wage and tax statement",
  "schema": {
    "fields": [
      {
        "name": "employer_name",
        "type": "text",
        "required": true,
        "description": "Employer name"
      },
      {
        "name": "employee_ssn",
        "type": "text",
        "required": true,
        "description": "Employee SSN"
      },
      {
        "name": "wages",
        "type": "currency",
        "required": true,
        "description": "Total wages"
      },
      {
        "name": "federal_tax_withheld",
        "type": "currency",
        "required": true,
        "description": "Federal income tax withheld"
      }
    ]
  },
  "is_public": false
}

Response:
{
  "id": "uuid",
  "name": "W-2 Tax Form",
  "slug": "w2_tax_form",
  "schema": {...},
  "version": "1.0",
  "is_active": true,
  "usage_count": 0,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### List Templates
```bash
GET /api/v1/templates?include_public=true
Authorization: Bearer {access_token}

Response:
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "name": "Invoice",
      "slug": "invoice",
      "is_public": true,
      "usage_count": 1234
    },
    {
      "id": "uuid",
      "name": "Bank Statement",
      "slug": "bank_statement",
      "is_public": true,
      "usage_count": 567
    }
  ]
}
```

### Document Processing

#### Method 1: Upload Then Process
```bash
# Step 1: Upload document
POST /api/v1/documents/upload
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

file: @document.pdf
template_id: uuid (optional)

Response:
{
  "success": true,
  "data": {
    "doc_id": "uuid",
    "filename": "document.pdf",
    "status": "uploaded"
  }
}

# Step 2: Process document
POST /api/v1/documents/{doc_id}/process
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "template_id": "uuid",
  "use_evaluator": true,
  "required_fields": ["account_number", "total_amount"]
}

Response:
{
  "success": true,
  "document_id": "uuid",
  "status": "completed",
  "extracted_data": {
    "account_number": "123456789",
    "total_amount": "1234.56",
    ...
  },
  "confidence_scores": {
    "account_number": 0.95,
    "total_amount": 0.88,
    ...
  },
  "quality_metrics": {
    "quality_score": 85.5,
    "completion_rate": 92.0,
    "average_confidence": 0.87
  },
  "flagged_fields": ["opening_balance"],
  "processing_time_ms": 3456
}
```

#### Method 2: Direct Template API (Recommended)
```bash
# Every template becomes a direct API endpoint!
POST /api/v1/process/{template_slug}
Authorization: Bearer {api_key}
Content-Type: multipart/form-data

file: @invoice.pdf
use_evaluator: true
required_fields: invoice_number,total_amount

Response:
{
  "success": true,
  "document_id": "uuid",
  "status": "completed",
  "extracted_data": {
    "invoice_number": "INV-2024-001",
    "invoice_date": "2024-01-15",
    "vendor_name": "Acme Corp",
    "customer_name": "Widget Inc",
    "subtotal": "1000.00",
    "tax_amount": "80.00",
    "total_amount": "1080.00",
    "currency": "USD"
  },
  "confidence_scores": {
    "invoice_number": 0.98,
    "invoice_date": 0.95,
    "vendor_name": 0.92,
    ...
  },
  "quality_metrics": {
    "quality_score": 88.5,
    "completion_rate": 100.0,
    "average_confidence": 0.91
  },
  "flagged_fields": [],
  "processing_time_ms": 2345
}
```

#### Get Document
```bash
GET /api/v1/documents/{doc_id}
Authorization: Bearer {access_token}

Response:
{
  "id": "uuid",
  "filename": "invoice.pdf",
  "status": "completed",
  "template_id": "uuid",
  "extracted_data": {...},
  "confidence_scores": {...},
  "quality_metrics": {...},
  "flagged_fields": [],
  "processing_time_ms": 2345,
  "created_at": "2024-01-01T00:00:00Z",
  "processed_at": "2024-01-01T00:00:03Z"
}
```

#### List Documents
```bash
GET /api/v1/documents?page=1&page_size=20&status=completed&template_id=uuid
Authorization: Bearer {access_token}

Response:
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "has_more": true
}
```

### Analytics

#### Usage Statistics
```bash
GET /api/v1/analytics/usage
Authorization: Bearer {access_token}

Response:
{
  "total_documents": 1234,
  "documents_today": 45,
  "documents_this_month": 678,
  "average_quality_score": 87.5,
  "success_rate": 98.5,
  "total_api_calls": 5678
}
```

## 🔐 Authentication

### JWT Tokens

```bash
# Use in Authorization header
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### API Keys

```bash
# Use in Authorization header (same as JWT)
Authorization: Bearer sk_live_abc123...
```

## 🏗️ Architecture

### Multi-Tenant Isolation

- Every table has `tenant_id` column
- Row-level security enforced
- Tenant context set from JWT/API key
- Complete data isolation

### Database Models

```
Tenant
  ├── Users
  ├── APIKeys
  ├── Templates
  ├── Documents
  ├── UsageLogs
  └── AuditLogs
```

### Template Schema Format

```json
{
  "fields": [
    {
      "name": "field_name",
      "type": "text|number|date|currency|email|phone|iban|address",
      "required": true|false,
      "description": "Field description",
      "validation": {
        "min": 0,
        "max": 100,
        "pattern": "regex"
      }
    }
  ]
}
```

### Field Types & Validation

| Type | Validation | Example |
|------|------------|---------|
| `text` | Basic string | "Acme Corp" |
| `number` | Numeric value | 1234.56 |
| `date` | ISO date format | "2024-01-15" |
| `currency` | Decimal with 2 places | "1234.56" |
| `email` | Email format | "user@example.com" |
| `phone` | Phone number | "+1-555-0100" |
| `iban` | IBAN validation | "GB82 WEST..." |
| `address` | Multi-line address | "123 Main St..." |

## 📊 Agentic OCR Features

### Field Assessment

Every field is automatically assessed:

- **FILLED** - Extracted with good confidence (>0.7)
- **UNFILLED** - No value found
- **LOW_CONFIDENCE** - Extracted but low confidence (<0.7)
- **INVALID** - Failed validation
- **NEEDS_REVIEW** - Manual review required

### Quality Metrics

```json
{
  "quality_score": 85.5,      // 0-100
  "completion_rate": 92.0,    // % filled
  "average_confidence": 0.87, // 0-1
  "total_fields": 25,
  "filled_fields": 23,
  "flagged_fields": 2
}
```

### Multi-Pass Extraction

1. **Pass 1**: Initial extraction of all fields
2. **Pass 2**: Field assessment & validation
3. **Pass 3**: Targeted retry of flagged fields
4. **Pass 4** (optional): Evaluator agent suggestions

## 🎯 Use Cases

### Invoice Processing
```bash
POST /api/v1/process/invoice
```

### Bank Statement Analysis
```bash
POST /api/v1/process/bank_statement
```

### Custom Document Types
```bash
# 1. Create template
POST /api/v1/templates

# 2. Use template
POST /api/v1/process/{your_custom_slug}
```

## 🔧 Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...          # OpenAI API key
DATABASE_URL=postgresql://...  # Database connection
SECRET_KEY=your-secret-key     # JWT secret

# Optional
OPENAI_VISION_MODEL=gpt-4o     # Default: gpt-4o
ACCESS_TOKEN_EXPIRE_MINUTES=60 # Default: 60
REFRESH_TOKEN_EXPIRE_DAYS=30   # Default: 30
```

### Database

Supports both SQLite (dev) and PostgreSQL (production):

```bash
# SQLite (default)
export DATABASE_URL="sqlite:///./agenticocr.db"

# PostgreSQL
export DATABASE_URL="postgresql://user:pass@localhost/dbname"
```

## 📈 Scaling

### Async Processing

For production, use Celery for async document processing:

```python
# In api_v1.py
from celery import Celery

celery = Celery('agenticocr')

@celery.task
def process_document_async(doc_id, template_id):
    result = run_agentic_pipeline(...)
    # Update database
    return result
```

### Rate Limiting

Add rate limiting middleware:

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/process/{template_slug}")
@limiter.limit("100/hour")
async def process_with_template(...):
    ...
```

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Test specific endpoint
pytest tests/test_auth.py::test_register

# With coverage
pytest --cov=. tests/
```

## 🚀 Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "api_v1:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db/agenticocr
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=agenticocr
      - POSTGRES_PASSWORD=password
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

## 🔒 Security

### Best Practices

1. **Use HTTPS** in production
2. **Rotate API keys** regularly
3. **Set strong SECRET_KEY**
4. **Enable CORS** properly
5. **Rate limit** API endpoints
6. **Monitor audit logs**
7. **Backup database** regularly

### CORS Configuration

```python
# In api_v1.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

## 📝 Example Integration

### Python Client

```python
import requests

class AgenticOCRClient:
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def process_invoice(self, file_path: str):
        with open(file_path, 'rb') as f:
            response = requests.post(
                f"{self.base_url}/api/v1/process/invoice",
                headers=self.headers,
                files={"file": f}
            )
        return response.json()

    def get_document(self, doc_id: str):
        response = requests.get(
            f"{self.base_url}/api/v1/documents/{doc_id}",
            headers=self.headers
        )
        return response.json()

# Usage
client = AgenticOCRClient(api_key="sk_live_...")
result = client.process_invoice("invoice.pdf")
print(f"Quality: {result['quality_metrics']['quality_score']}/100")
```

### JavaScript Client

```javascript
class AgenticOCRClient {
  constructor(apiKey, baseUrl = 'http://localhost:8000') {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
  }

  async processInvoice(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/api/v1/process/invoice`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`
      },
      body: formData
    });

    return await response.json();
  }

  async getDocument(docId) {
    const response = await fetch(`${this.baseUrl}/api/v1/documents/${docId}`, {
      headers: {
        'Authorization': `Bearer ${this.apiKey}`
      }
    });

    return await response.json();
  }
}

// Usage
const client = new AgenticOCRClient('sk_live_...');
const result = await client.processInvoice(fileInput.files[0]);
console.log(`Quality: ${result.quality_metrics.quality_score}/100`);
```

## 🆘 Troubleshooting

### Common Issues

**Issue**: Database connection error
```bash
# Solution: Check DATABASE_URL
export DATABASE_URL="postgresql://user:pass@localhost/dbname"
```

**Issue**: OpenAI API key not set
```bash
# Solution: Set environment variable
export OPENAI_API_KEY="sk-..."
```

**Issue**: Import errors
```bash
# Solution: Install all dependencies
pip install -r requirements.txt
```

**Issue**: Token expired
```bash
# Solution: Use refresh token to get new access token
POST /api/v1/auth/refresh
```

## 📚 Additional Resources

- **Main README**: [README.md](README.md)
- **Agentic OCR Guide**: [AGENTIC_OCR_README.md](AGENTIC_OCR_README.md)
- **Quick Start**: [QUICK_START.md](QUICK_START.md)
- **API Docs**: http://localhost:8000/api/docs

## 🎯 Roadmap

### Phase 2: Multi-Tenant Enhancements (Planned)
- Team management
- Role-based permissions
- Usage quotas & billing
- Webhook notifications
- Custom branding

### Phase 3: Advanced Features (Planned)
- Batch processing
- Document classification
- Custom validators
- Template versioning
- A/B testing

### Phase 4: Enterprise (Planned)
- SSO/SAML
- Advanced analytics
- Custom deployments
- SLA guarantees
- Priority support

## 📞 Support

For issues or questions:
1. Check the documentation
2. Review API docs at `/api/docs`
3. Check example code
4. Open an issue on GitHub

---

**Built with ❤️ using FastAPI, SQLAlchemy, and OpenAI GPT-4o**
