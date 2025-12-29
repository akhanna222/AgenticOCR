# 🧠 Agentic OCR System - Complete Guide

## Overview

This is a **robust, production-ready OCR system** with autonomous field assessment and intelligent flagging capabilities. Unlike traditional OCR that simply extracts text, this agentic system:

- **Auto-assesses** every extracted field
- **Flags** unfilled, low-confidence, or invalid fields
- **Retries** problematic fields with targeted prompts
- **Validates** data against domain-specific rules
- **Scores** extraction quality comprehensively

---

## 🎯 Key Features

### 1. **Field-Level Confidence Scoring**
Every extracted field receives a confidence score (0-1) indicating certainty:
- `1.0` = Crystal clear, no ambiguity
- `0.8-0.9` = High confidence
- `0.6-0.7` = Readable but some uncertainty
- `0.4-0.5` = Partially visible or inferred
- `0.2-0.3` = Barely visible
- `0.0-0.1` = Not visible or guessed

### 2. **Automatic Field Assessment**
Each field is automatically classified:
- ✅ **FILLED** - Valid data with good confidence
- ⚠️ **UNFILLED** - Empty or missing
- ⚠️ **LOW_CONFIDENCE** - Has data but below confidence threshold
- ❌ **INVALID** - Fails validation rules
- 🔍 **NEEDS_REVIEW** - Flagged for manual review

### 3. **Smart Validation Rules**
Built-in validators for common field types:
- **DATE** - Multiple formats (YYYY-MM-DD, DD/MM/YYYY, etc.)
- **CURRENCY** - Amounts with symbols (€1,234.56)
- **NUMBER** - Numeric values
- **EMAIL** - Email address format
- **PHONE** - Phone number formats
- **IBAN** - Bank account format
- **ADDRESS** - Address blocks

### 4. **Multi-Pass Extraction with Retry**
1. **Pass 1**: Extract all fields from all pages
2. **Pass 2**: Assess field quality
3. **Pass 3**: Retry flagged fields with focused prompts
4. **Pass 4** (Optional): Evaluator agent reviews results

### 5. **Comprehensive Quality Reporting**
- **Completion Rate**: % of fields successfully filled
- **Quality Score**: Overall score (0-100) combining fill rate, confidence, and validation
- **Field Details**: Per-field status, confidence, validation errors
- **Flagged Fields**: List of fields needing attention

---

## 📁 Architecture

### Core Components

```
ocr_agent.py              # Main agentic OCR engine
├── FieldStatus           # Enum: FILLED, UNFILLED, LOW_CONFIDENCE, etc.
├── FieldType             # Enum: TEXT, DATE, CURRENCY, etc.
├── FieldMetadata         # Field validation rules and requirements
├── FieldResult           # Individual field extraction result
├── ExtractionReport      # Comprehensive assessment report
├── FieldValidator        # Validation rules engine
├── FieldAssessor         # Assesses and flags fields
├── OCRExtractor          # Abstract interface for providers
└── AgenticOCR            # Main orchestrator

openai_extractor.py       # OpenAI Vision implementation
├── OpenAIVisionExtractor # Implements OCRExtractor interface
└── OpenAIEvaluatorAgent  # Separate evaluator for quality check

mortgage_core.py          # Integration layer
└── run_agentic_pipeline() # Main entry point

app.py                    # Flask API
└── /api/run-agentic-ocr  # HTTP endpoint
```

---

## 🚀 Usage

### Python API

```python
from mortgage_core import run_agentic_pipeline

# Run agentic OCR with auto-assessment
result = run_agentic_pipeline(
    path="document.pdf",
    override_doc_type_id="current_acct_statements",  # Optional
    use_evaluator=True,                               # Optional
    required_fields=["account_number", "iban"],      # Optional
)

# Access results
print(f"Quality Score: {result['quality_metrics']['quality_score']}/100")
print(f"Completion Rate: {result['quality_metrics']['completion_rate']}%")

# Check flagged fields
for field in result['flagged_fields']:
    detail = result['assessment_report']['field_details'][field]
    print(f"⚠️ {field}: {detail['status']} (confidence: {detail['confidence']:.2f})")

# Get extracted data
extracted = result['extracted_data']
confidences = result['confidence_scores']
```

### HTTP API

```bash
# 1. Upload document
curl -X POST http://localhost:5005/api/upload \
  -F "file=@bank_statement.pdf"

# Response: {"doc_id": "abc-123", "classification": {...}}

# 2. Run agentic OCR
curl -X POST http://localhost:5005/api/run-agentic-ocr \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "abc-123",
    "doc_type_id": "current_acct_statements",
    "use_evaluator": true,
    "required_fields": ["account_number", "iban"]
  }'
```

### Response Structure

```json
{
  "classification": {
    "doc_type_id": "current_acct_statements",
    "confidence": 0.95,
    "rationale": "Bank statement with account details"
  },
  "extracted_data": {
    "account_number": "12345678",
    "iban": "IE12BOFI90000112345678",
    "account_holder_name": "John Doe",
    ...
  },
  "confidence_scores": {
    "account_number": 0.95,
    "iban": 0.92,
    "account_holder_name": 0.88,
    ...
  },
  "assessment_report": {
    "total_fields": 25,
    "filled_fields": 18,
    "unfilled_fields": 5,
    "low_confidence_fields": 2,
    "invalid_fields": 0,
    "average_confidence": 0.78,
    "completion_rate": 72.0,
    "quality_score": 76.5,
    "flagged_field_names": ["opening_balance", "closing_balance"],
    "field_details": {
      "account_number": {
        "name": "account_number",
        "value": "12345678",
        "confidence": 0.95,
        "status": "filled",
        "validation_errors": [],
        "notes": ""
      },
      "opening_balance": {
        "name": "opening_balance",
        "value": "",
        "confidence": 0.0,
        "status": "unfilled",
        "validation_errors": [],
        "notes": "Required field is unfilled"
      }
    }
  },
  "flagged_fields": ["opening_balance", "closing_balance", ...],
  "quality_metrics": {
    "completion_rate": 72.0,
    "quality_score": 76.5,
    "average_confidence": 0.78
  },
  "evaluation": {
    "overall_quality": "fair",
    "critical_issues": ["Missing balance information"],
    "suggestions": ["Check if balances are on page 2"],
    "corrected_fields": {...}
  }
}
```

---

## 🔧 Configuration

### Field Metadata

Define field requirements and validation rules:

```python
from ocr_agent import FieldMetadata, FieldType

metadata_map = {
    "account_number": FieldMetadata(
        name="account_number",
        field_type=FieldType.TEXT,
        required=True,
        min_confidence=0.8,
        description="Bank account number"
    ),
    "iban": FieldMetadata(
        name="iban",
        field_type=FieldType.IBAN,
        required=True,
        min_confidence=0.7,
    ),
    "opening_balance": FieldMetadata(
        name="opening_balance",
        field_type=FieldType.CURRENCY,
        required=True,
        min_confidence=0.6,
    ),
}
```

### Custom Validators

Add custom validation logic:

```python
from ocr_agent import FieldValidator

# Extend FieldValidator class
class CustomValidator(FieldValidator):
    @staticmethod
    def validate_custom_field(value: str) -> Tuple[bool, Optional[str]]:
        if not value.startswith("IE"):
            return False, "Must start with IE"
        return True, None
```

### Confidence Thresholds

Adjust confidence requirements:

```python
from ocr_agent import FieldAssessor

# Default threshold: 0.6
assessor = FieldAssessor(min_confidence_threshold=0.7)

# Or per-field via metadata
metadata = FieldMetadata(
    name="sensitive_field",
    min_confidence=0.9  # Higher threshold for critical fields
)
```

---

## 🎨 Advanced Features

### 1. Provider-Agnostic Design

The system uses an abstract `OCRExtractor` interface. You can implement extractors for any provider:

```python
from ocr_agent import OCRExtractor
from PIL import Image
from typing import Dict, Any, Tuple

class CustomExtractor(OCRExtractor):
    def extract_fields_from_image(
        self,
        image: Image.Image,
        schema: Dict[str, Any],
        system_prompt: str,
        user_instructions: str,
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        # Your custom extraction logic
        # Return (values_dict, confidence_dict)
        pass
```

### 2. Custom Schema Support

Create custom document schemas:

```bash
# Create schema file
cat > schemas/invoice.json << EOF
{
  "doc_type_id": "invoice",
  "invoice_number": "",
  "invoice_date": "",
  "due_date": "",
  "vendor_name": "",
  "total_amount": "",
  "tax_amount": "",
  "line_items": []
}
EOF
```

### 3. Retry Strategies

Customize retry behavior:

```python
agent = AgenticOCR(
    extractor=extractor,
    assessor=assessor,
    max_retry_attempts=5  # Default: 3
)
```

---

## 📊 Quality Metrics Explained

### Completion Rate
```
Completion Rate = (Filled Fields / Total Fields) × 100
```

### Quality Score
Weighted combination of:
- **50%** Completion rate
- **30%** Average confidence
- **20%** Validation success rate

```
Quality Score = (0.5 × completion) + (0.3 × avg_confidence × 100) + (0.2 × validation_rate)
```

### Field Status Priority
When multiple issues exist, status is assigned by priority:
1. INVALID (fails validation)
2. LOW_CONFIDENCE (below threshold)
3. UNFILLED (empty)
4. FILLED (valid)

---

## 🐛 Troubleshooting

### Low Confidence Scores

**Problem**: Most fields have confidence < 0.6

**Solutions**:
- Use higher resolution images (DPI ≥ 200)
- Ensure document is not skewed or rotated
- Check image quality (no blur, good contrast)
- Try a more powerful model (gpt-4o instead of gpt-4o-mini)

### High Unfilled Rate

**Problem**: Many fields showing as UNFILLED

**Solutions**:
- Verify schema matches document type
- Check if information spans multiple pages
- Increase `max_retry_attempts`
- Review flagged fields in detail

### Validation Failures

**Problem**: Fields marked as INVALID

**Solutions**:
- Check validation rules match your data format
- Review specific validation errors in field_details
- Consider relaxing validation for non-critical fields
- Implement custom validators for edge cases

---

## 🔐 Security Considerations

1. **API Key Management**: Never hardcode API keys
   ```bash
   export OPENAI_API_KEY="your-key-here"
   ```

2. **Data Privacy**: Ensure compliance with data protection regulations when processing sensitive documents

3. **Input Validation**: API endpoints validate all inputs

4. **Error Handling**: All exceptions are caught and logged safely

---

## 🧪 Testing

```bash
# Set API key
export OPENAI_API_KEY="your-key"

# Test with sample document
python -c "
from mortgage_core import run_agentic_pipeline
result = run_agentic_pipeline('test_document.pdf')
print(f'Quality Score: {result[\"quality_metrics\"][\"quality_score\"]}/100')
"
```

---

## 📈 Performance Tips

1. **Batch Processing**: Process multiple pages in parallel
2. **Model Selection**:
   - Use `gpt-4o-mini` for speed and cost
   - Use `gpt-4o` for maximum accuracy
3. **Caching**: Cache schemas and validation rules
4. **Error Recovery**: Handle API rate limits gracefully

---

## 🤝 Extending the System

### Add New Field Type

```python
# 1. Add to FieldType enum
class FieldType(Enum):
    CUSTOM_TYPE = "custom_type"

# 2. Add validator
@staticmethod
def validate_custom_type(value: str) -> Tuple[bool, Optional[str]]:
    # Your validation logic
    return True, None

# 3. Register in validate_by_type
validators = {
    FieldType.CUSTOM_TYPE: FieldValidator.validate_custom_type,
}
```

### Add New Provider

```python
# Implement OCRExtractor interface
class ClaudeExtractor(OCRExtractor):
    def extract_fields_from_image(self, ...):
        # Use Claude API
        pass

# Use in pipeline
extractor = ClaudeExtractor(api_key=...)
agent = AgenticOCR(extractor=extractor, ...)
```

---

## 📚 API Reference

### `run_agentic_pipeline()`

Main entry point for agentic OCR.

**Parameters**:
- `path` (str): Path to PDF or image file
- `override_doc_type_id` (Optional[str]): Force specific doc type
- `use_evaluator` (bool): Run evaluator agent (default: True)
- `required_fields` (Optional[List[str]]): Required field names

**Returns**: `Dict[str, Any]` with keys:
- `classification`: Document classification
- `extracted_data`: Field values
- `confidence_scores`: Per-field confidence
- `assessment_report`: Quality assessment
- `flagged_fields`: Fields needing attention
- `quality_metrics`: Overall metrics
- `evaluation`: Evaluator feedback (if enabled)

---

## 📄 License

See main project LICENSE file.

---

## 🙏 Credits

Built with:
- OpenAI GPT-4o Vision API
- Pillow for image processing
- pdf2image for PDF conversion
- Flask for API server

---

## 📞 Support

For issues or questions:
1. Check troubleshooting section
2. Review flagged field details
3. Examine evaluation suggestions
4. Adjust confidence thresholds
5. Try with different document quality

---

**Built for production use with mortgage underwriting documents, adaptable to any document type.**
