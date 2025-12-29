# 🚀 Quick Start: Agentic OCR

## What's New?

The new **Agentic OCR system** automatically:
- ✅ Scores confidence for each field (0-1)
- ✅ Flags unfilled fields
- ✅ Flags low-confidence fields
- ✅ Validates field data (dates, currencies, IBANs, etc.)
- ✅ Retries problematic fields automatically
- ✅ Provides quality scores and completion rates

## Installation

No new dependencies! Uses the same requirements:

```bash
pip install -r requirements.txt
```

## Usage Methods

### Method 1: Python Script (Recommended for Testing)

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# Run the example script
python example_agentic_ocr.py your_document.pdf
```

**Output**:
```
============================================================
🧠 AGENTIC OCR EXAMPLE
============================================================

Document: bank_statement.pdf

============================================================
📊 QUALITY METRICS
============================================================
  Quality Score:     76.5/100
  Completion Rate:   72.0%
  Avg Confidence:    0.78

  Total Fields:      25
  ✅ Filled:         18
  ⚠️  Unfilled:       5
  ⚠️  Low Confidence: 2
  ❌ Invalid:        0

============================================================
⚠️  FLAGGED FIELDS (7)
============================================================
  ⚠️ opening_balance              unfilled        (conf: 0.00)
  ⚠️ closing_balance              unfilled        (conf: 0.00)
  ⚠️ bank_address                 low_confidence  (conf: 0.54)
  ...
```

### Method 2: Python API (Recommended for Integration)

```python
from mortgage_core import run_agentic_pipeline

# Run OCR with auto-assessment
result = run_agentic_pipeline(
    path="document.pdf",
    override_doc_type_id="current_acct_statements",  # Optional
    use_evaluator=True,
    required_fields=["account_number", "iban"]
)

# Check quality
quality_score = result['quality_metrics']['quality_score']
print(f"Quality: {quality_score}/100")

# Get flagged fields
for field in result['flagged_fields']:
    detail = result['assessment_report']['field_details'][field]
    print(f"⚠️ {field}: {detail['status']}")

# Access extracted data
data = result['extracted_data']
confidences = result['confidence_scores']
```

### Method 3: HTTP API (Recommended for Web Apps)

```bash
# 1. Start the server
export OPENAI_API_KEY="sk-..."
python app.py

# 2. Upload document
curl -X POST http://localhost:5005/api/upload \
  -F "file=@document.pdf" \
  > upload_response.json

# Extract doc_id from response
DOC_ID=$(cat upload_response.json | jq -r '.doc_id')

# 3. Run agentic OCR
curl -X POST http://localhost:5005/api/run-agentic-ocr \
  -H "Content-Type: application/json" \
  -d "{
    \"doc_id\": \"$DOC_ID\",
    \"doc_type_id\": \"current_acct_statements\",
    \"use_evaluator\": true,
    \"required_fields\": [\"account_number\", \"iban\"]
  }" | jq '.'
```

## Understanding the Output

### Field Status Categories

| Status | Meaning | Action |
|--------|---------|--------|
| ✅ **FILLED** | Valid data, good confidence | No action needed |
| ⚠️ **UNFILLED** | Field is empty | Check if field exists in document |
| ⚠️ **LOW_CONFIDENCE** | Has data but low confidence | Review extracted value |
| ❌ **INVALID** | Fails validation rules | Check data format |
| 🔍 **NEEDS_REVIEW** | Flagged for manual review | Human verification needed |

### Quality Metrics

**Quality Score** (0-100): Overall extraction quality
- 80-100: Excellent
- 60-79: Good
- 40-59: Fair (review flagged fields)
- 0-39: Poor (manual review recommended)

**Completion Rate** (%): Percentage of fields successfully filled

**Average Confidence** (0-1): Mean confidence across all fields

## Common Workflows

### Workflow 1: Process Document & Review Flags

```python
# 1. Extract
result = run_agentic_pipeline("document.pdf")

# 2. Check quality
if result['quality_metrics']['quality_score'] < 60:
    print("⚠️ Low quality - manual review needed")

# 3. Review flagged fields
for field in result['flagged_fields']:
    detail = result['assessment_report']['field_details'][field]
    if detail['status'] == 'unfilled':
        print(f"Missing: {field}")
    elif detail['status'] == 'low_confidence':
        print(f"Uncertain: {field} = {detail['value']} (conf: {detail['confidence']})")
```

### Workflow 2: Validate Critical Fields

```python
# Define critical fields
critical_fields = ["account_number", "iban", "account_holder_name"]

# Run with required fields
result = run_agentic_pipeline(
    "document.pdf",
    required_fields=critical_fields
)

# Check if critical fields are filled
assessment = result['assessment_report']
for field in critical_fields:
    detail = assessment['field_details'][field]
    if detail['status'] != 'filled':
        print(f"❌ Critical field issue: {field} - {detail['status']}")
        # Trigger manual review workflow
```

### Workflow 3: Batch Processing

```python
import glob

documents = glob.glob("documents/*.pdf")
results = []

for doc_path in documents:
    print(f"Processing {doc_path}...")
    result = run_agentic_pipeline(doc_path)

    results.append({
        'path': doc_path,
        'quality': result['quality_metrics']['quality_score'],
        'flagged_count': len(result['flagged_fields']),
        'completion': result['quality_metrics']['completion_rate']
    })

# Sort by quality (lowest first - needs most attention)
results.sort(key=lambda x: x['quality'])

for r in results:
    print(f"{r['path']}: Quality={r['quality']:.1f}, Flags={r['flagged_count']}")
```

## Configuration Tips

### Adjust Confidence Threshold

```python
from ocr_agent import FieldAssessor, AgenticOCR
from openai_extractor import OpenAIVisionExtractor

# Higher threshold = more strict flagging
assessor = FieldAssessor(min_confidence_threshold=0.75)  # Default: 0.6

extractor = OpenAIVisionExtractor(api_key=api_key)
agent = AgenticOCR(extractor, assessor, max_retry_attempts=3)
```

### Use Higher Quality Model

```python
extractor = OpenAIVisionExtractor(
    api_key=api_key,
    model="gpt-4o"  # More accurate than gpt-4o-mini
)
```

### Define Custom Required Fields

```python
# For bank statements
required = ["account_number", "iban", "account_holder_name",
            "opening_balance", "closing_balance"]

# For payslips
required = ["employee_name", "pay_date", "gross_pay", "net_pay"]

result = run_agentic_pipeline(
    "document.pdf",
    required_fields=required
)
```

## Comparison: Old vs New

| Feature | Old System | New Agentic System |
|---------|-----------|-------------------|
| Field confidence | ❌ No | ✅ Yes (per field) |
| Auto-assessment | ❌ No | ✅ Yes |
| Field flagging | ❌ No | ✅ Yes (5 categories) |
| Validation | ❌ No | ✅ Yes (7+ types) |
| Targeted retry | ❌ No | ✅ Yes |
| Quality scoring | ❌ No | ✅ Yes |
| Completion rate | ❌ No | ✅ Yes |
| Detailed reporting | ⚠️ Basic | ✅ Comprehensive |

## Next Steps

1. ✅ Try the example script: `python example_agentic_ocr.py your_doc.pdf`
2. 📖 Read full documentation: `AGENTIC_OCR_README.md`
3. 🔧 Customize for your use case
4. 🚀 Integrate into your application

## Troubleshooting

**Problem**: Most fields flagged as low confidence
- **Solution**: Use higher DPI (200+) when scanning/converting images
- **Solution**: Try `gpt-4o` instead of `gpt-4o-mini`

**Problem**: Many unfilled fields
- **Solution**: Verify document type matches schema
- **Solution**: Check if data spans multiple pages
- **Solution**: Increase `max_retry_attempts`

**Problem**: Validation errors
- **Solution**: Review validation rules in `ocr_agent.py`
- **Solution**: Adjust rules for your data format

## Support

For detailed information, see:
- `AGENTIC_OCR_README.md` - Complete documentation
- `ocr_agent.py` - Core agent implementation
- `openai_extractor.py` - OpenAI integration
- `example_agentic_ocr.py` - Usage examples

---

**Ready to build robust OCR systems! 🚀**
