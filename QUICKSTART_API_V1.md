# 🚀 Quick Start - API v1

Get started with AgenticOCR API in 5 minutes!

## Step 1: Install & Setup (2 min)

```bash
# Clone repository (if not already done)
git clone https://github.com/akhanna222/AgenticOCR.git
cd AgenticOCR

# Install dependencies
pip install -r requirements.txt

# Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# Optional: Set secret key (auto-generated if not set)
export SECRET_KEY="your-secret-key-here"
```

## Step 2: Initialize Database (1 min)

```bash
python init_db.py
```

When prompted:
- **Create demo tenant?** → Type `y`
- **Admin email** → Press Enter (uses: `admin@demo.com`)
- **Admin password** → Press Enter (uses: `admin123`)

You'll see:
```
✨ Setup Complete!

📝 Demo Credentials:
   Email:    admin@demo.com
   Password: admin123
   Tenant:   demo

🚀 Start the server:
   python api_v1.py
```

## Step 3: Start Server (30 sec)

```bash
python api_v1.py
```

Server starts at: **http://localhost:8000**

## Step 4: Test API (1.5 min)

### Option A: Using Browser (Swagger UI)

1. Open: http://localhost:8000/api/docs
2. Click **"Authorize"** button (top right)
3. Login to get token:
   - Go to **POST /api/v1/auth/login**
   - Click "Try it out"
   - Enter credentials:
     ```json
     {
       "email": "admin@demo.com",
       "password": "admin123"
     }
     ```
   - Click "Execute"
   - Copy the `access_token` from response
4. Paste token in Authorization dialog
5. Now try any endpoint!

### Option B: Using curl

```bash
# 1. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@demo.com",
    "password": "admin123"
  }'

# Copy access_token from response
export TOKEN="eyJ..."

# 2. List templates
curl http://localhost:8000/api/v1/templates \
  -H "Authorization: Bearer $TOKEN"

# 3. Process an invoice
curl -X POST http://localhost:8000/api/v1/process/invoice \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@your_invoice.pdf"
```

## Example: Process Your First Document

### Using Invoice Template

```bash
# Set your access token
export TOKEN="your-access-token-here"

# Process invoice
curl -X POST http://localhost:8000/api/v1/process/invoice \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@invoice.pdf" | jq '.'
```

**Response:**
```json
{
  "success": true,
  "document_id": "uuid",
  "status": "completed",
  "extracted_data": {
    "invoice_number": "INV-2024-001",
    "invoice_date": "2024-01-15",
    "vendor_name": "Acme Corp",
    "total_amount": "1234.56"
  },
  "confidence_scores": {
    "invoice_number": 0.95,
    "invoice_date": 0.92,
    "vendor_name": 0.88,
    "total_amount": 0.91
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

### Using Bank Statement Template

```bash
curl -X POST http://localhost:8000/api/v1/process/bank_statement \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@statement.pdf" | jq '.'
```

## Creating Your Own Template

```bash
# Create custom template
curl -X POST http://localhost:8000/api/v1/templates \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Purchase Order",
    "slug": "purchase_order",
    "description": "Purchase order parser",
    "schema": {
      "fields": [
        {
          "name": "po_number",
          "type": "text",
          "required": true,
          "description": "Purchase order number"
        },
        {
          "name": "po_date",
          "type": "date",
          "required": true,
          "description": "PO date"
        },
        {
          "name": "supplier",
          "type": "text",
          "required": true,
          "description": "Supplier name"
        },
        {
          "name": "total",
          "type": "currency",
          "required": true,
          "description": "Total amount"
        }
      ]
    }
  }' | jq '.'

# Now use it!
curl -X POST http://localhost:8000/api/v1/process/purchase_order \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@po.pdf" | jq '.'
```

## Creating API Keys for Production

```bash
# Create API key
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Key",
    "expires_in_days": 365
  }' | jq '.'

# Copy the key from response (only shown once!)
export API_KEY="sk_live_..."

# Use API key instead of JWT token
curl -X POST http://localhost:8000/api/v1/process/invoice \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@invoice.pdf" | jq '.'
```

## Checking Usage Statistics

```bash
curl http://localhost:8000/api/v1/analytics/usage \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

**Response:**
```json
{
  "total_documents": 150,
  "documents_today": 12,
  "documents_this_month": 89,
  "average_quality_score": 87.5,
  "success_rate": 98.2,
  "total_api_calls": 456
}
```

## Python Integration Example

```python
import requests

class AgenticOCRClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://localhost:8000"
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def process_document(self, template_slug: str, file_path: str):
        with open(file_path, 'rb') as f:
            response = requests.post(
                f"{self.base_url}/api/v1/process/{template_slug}",
                headers=self.headers,
                files={"file": f}
            )
        return response.json()

# Usage
client = AgenticOCRClient("sk_live_...")
result = client.process_document("invoice", "invoice.pdf")

print(f"✅ Extracted: {result['extracted_data']}")
print(f"📊 Quality: {result['quality_metrics']['quality_score']}/100")
print(f"⚠️ Flagged: {result['flagged_fields']}")
```

## JavaScript/Node.js Example

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

async function processDocument(apiKey, templateSlug, filePath) {
  const form = new FormData();
  form.append('file', fs.createReadStream(filePath));

  const response = await axios.post(
    `http://localhost:8000/api/v1/process/${templateSlug}`,
    form,
    {
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        ...form.getHeaders()
      }
    }
  );

  return response.data;
}

// Usage
processDocument('sk_live_...', 'invoice', 'invoice.pdf')
  .then(result => {
    console.log('✅ Extracted:', result.extracted_data);
    console.log('📊 Quality:', result.quality_metrics.quality_score);
  });
```

## Common Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Register new user & tenant |
| `/api/v1/auth/login` | POST | Login and get tokens |
| `/api/v1/auth/api-keys` | POST | Create API key |
| `/api/v1/templates` | GET | List templates |
| `/api/v1/templates` | POST | Create template |
| `/api/v1/process/{slug}` | POST | Process with template |
| `/api/v1/documents/{id}` | GET | Get document result |
| `/api/v1/documents` | GET | List all documents |
| `/api/v1/analytics/usage` | GET | Get usage stats |

## Next Steps

1. **Read Full Documentation**: [API_V1_README.md](API_V1_README.md)
2. **Explore API Docs**: http://localhost:8000/api/docs
3. **Create Custom Templates**: For your document types
4. **Integrate**: Use Python/JS examples above
5. **Deploy**: See deployment guide in API_V1_README.md

## Troubleshooting

### "OpenAI API key not set"
```bash
export OPENAI_API_KEY="sk-..."
```

### "Database file not found"
```bash
python init_db.py
```

### "Token has expired"
```bash
# Login again to get new token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@demo.com", "password": "admin123"}'
```

### "Template not found"
```bash
# List available templates
curl http://localhost:8000/api/v1/templates \
  -H "Authorization: Bearer $TOKEN"
```

## Production Deployment

### Environment Variables
```bash
export OPENAI_API_KEY="sk-..."
export DATABASE_URL="postgresql://user:pass@host/db"
export SECRET_KEY="$(openssl rand -base64 32)"
export ACCESS_TOKEN_EXPIRE_MINUTES="60"
```

### Run with Gunicorn
```bash
pip install gunicorn
gunicorn api_v1:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Docker
```bash
docker build -t agenticocr .
docker run -p 8000:8000 \
  -e OPENAI_API_KEY="sk-..." \
  -e DATABASE_URL="postgresql://..." \
  agenticocr
```

## Support & Resources

- **Full API Docs**: [API_V1_README.md](API_V1_README.md)
- **Interactive Docs**: http://localhost:8000/api/docs
- **Agentic OCR Guide**: [AGENTIC_OCR_README.md](AGENTIC_OCR_README.md)
- **Main README**: [README.md](README.md)

---

**🎉 You're all set! Start processing documents with intelligent OCR!**
