# 🎨 Gradio Interface Guide

Beautiful web UI for the Agentic OCR System - perfect for demos and Google Colab!

---

## 🚀 Quick Start

### **Option 1: Google Colab** (Easiest!)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/akhanna222/AgenticOCR/blob/claude/ocr-field-detection-agent-8eTcB/agentic_ocr_colab.ipynb)

**Steps:**
1. Click the "Open in Colab" badge above
2. Run all cells (`Runtime` → `Run all`)
3. Wait for public URL to appear (~1 minute)
4. Click the URL and start processing documents!

---

### **Option 2: Local Machine**

```bash
# Install dependencies
pip install gradio pandas

# Run Gradio interface
python gradio_app.py

# Open browser to http://localhost:7860
```

---

### **Option 3: Command Line**

```bash
# In Python
python -c "from gradio_app import launch_gradio; launch_gradio()"

# Or interactive
python
>>> from gradio_app import launch_gradio
>>> launch_gradio(share=True)  # Creates public URL
```

---

## 🎯 Features

### **Beautiful UI**
- 📤 Drag-and-drop file upload
- 🎨 Color-coded quality metrics
- 📊 Interactive field tables
- 🔍 Detailed field status with emojis

### **Intelligent Processing**
- ✅ Auto document classification
- ✅ Field-level confidence scoring
- ✅ Automatic flagging of problematic fields
- ✅ Quality metrics and completion rates
- ✅ Optional evaluator agent

### **Easy Configuration**
- 🔑 API key input in interface
- 📋 Document type selection
- ⚙️ Required fields specification
- 🔧 Evaluator toggle

---

## 📖 How to Use

### 1. **Upload Document**
- Click "Upload Document" button
- Select PDF or image (PNG, JPG)
- Supports multi-page PDFs

### 2. **Enter API Key**
- Paste your OpenAI API key
- Get one at: https://platform.openai.com/api-keys
- Key is only used for this session (not stored)

### 3. **Configure (Optional)**
```
Document Type: Auto-detect (or select specific type)
Required Fields: account_number, iban, account_holder_name
Use Evaluator: ✅ (for thorough quality check)
```

### 4. **Process**
- Click "🚀 Process Document"
- Wait 10-30 seconds
- View results!

---

## 📊 Understanding Results

### **Summary Section**
Shows:
- Document type and classification confidence
- Total pages processed
- Total fields in template

### **Quality Metrics**
Three key scores:
- **Quality Score** (0-100): Overall extraction quality
- **Completion Rate** (%): Percentage of filled fields
- **Avg Confidence** (0-1): Mean confidence across fields

Plus breakdown:
- ✅ Filled fields
- ⚠️ Unfilled fields
- ⚠️ Low confidence fields
- ❌ Invalid fields

### **Flagged Fields**
Lists fields that need attention:
- Shows field name
- Status (unfilled, low confidence, invalid)
- Confidence score
- Notes explaining why flagged

### **All Fields Tab**
Complete table with:
- Field names
- Extracted values
- Confidence scores
- Status indicators

### **Raw JSON Tab**
Full extraction result in JSON format for:
- API integration
- Further processing
- Debugging

---

## 🎨 Screenshots

### Main Interface
```
┌─────────────────────────────────────────────┐
│  📤 Upload Document                         │
│  ┌───────────────────────────────────────┐ │
│  │  Drag and drop or click to upload    │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  🔑 OpenAI API Key                          │
│  [sk-................................................] │
│                                             │
│  📋 Document Type                           │
│  [Auto-detect ▼]                            │
│                                             │
│  🚀 Process Document                        │
└─────────────────────────────────────────────┘
```

### Results Display
```
┌─────────────────────────────────────────────┐
│  📄 Document Analysis Complete              │
│  ┌─────────────┬─────────────┬───────────┐ │
│  │  Quality    │ Completion  │    Avg    │ │
│  │   Score     │    Rate     │Confidence │ │
│  │   81.2      │    84%      │   0.81    │ │
│  └─────────────┴─────────────┴───────────┘ │
│                                             │
│  ⚠️ Flagged Fields (4)                      │
│  • opening_balance: unfilled (0.00)         │
│  • bank_address: low_confidence (0.54)      │
└─────────────────────────────────────────────┘
```

---

## ⚙️ Configuration Options

### **Document Types**
Select from 30+ pre-configured types:
- Bank statements
- Payslips
- Tax forms
- ID documents
- Property documents
- Or "Auto-detect"

### **Required Fields**
Specify critical fields as comma-separated list:
```
account_number, iban, account_holder_name
```

These will be flagged if unfilled or low confidence.

### **Evaluator Agent**
- ✅ **Enabled**: More thorough, slower (~30s)
- ❌ **Disabled**: Faster results (~15s)

Evaluator provides:
- Critical issue detection
- Suggestions for improvement
- Confidence adjustments

---

## 🌐 Google Colab Integration

### **Why Use Colab?**
- ✅ No local setup required
- ✅ Free GPU/CPU resources
- ✅ Share public URL with team
- ✅ Pre-installed dependencies
- ✅ Easy collaboration

### **Colab-Specific Features**
```python
# The notebook includes:
1. Automatic dependency installation
2. Repository cloning
3. API key setup
4. One-click launch
5. Public URL generation
```

### **Custom Colab Usage**
```python
# In a Colab cell:
from gradio_app import create_gradio_interface

demo = create_gradio_interface()
demo.launch(share=True, debug=True)
```

---

## 💡 Tips & Tricks

### **Better Extraction Quality**
1. Use high-resolution scans (200+ DPI)
2. Ensure documents are upright (not rotated)
3. Good lighting and contrast
4. Complete pages (no cut-off edges)

### **Faster Processing**
1. Disable evaluator agent
2. Use smaller documents
3. Select specific document type (skip auto-detect)

### **Batch Processing**
For multiple documents, use Python API:
```python
from mortgage_core import run_agentic_pipeline

documents = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
results = []

for doc in documents:
    result = run_agentic_pipeline(doc)
    results.append(result)
```

### **Custom Validation**
Add required fields for critical validation:
```
# For bank statements
account_number, iban, opening_balance, closing_balance

# For payslips
employee_name, pay_date, gross_pay, net_pay

# For ID documents
holder_full_name, date_of_birth, document_number
```

---

## 🔧 Customization

### **Change Theme**
```python
# In gradio_app.py, line ~300
demo = gr.Blocks(
    theme=gr.themes.Base(),  # or Monochrome, Soft, Glass
    ...
)
```

### **Add Custom CSS**
```python
css = """
.gradio-container {
    max-width: 1400px !important;
    font-family: 'Arial', sans-serif;
}
"""
demo = gr.Blocks(css=css, ...)
```

### **Modify Layout**
Edit `create_gradio_interface()` function in `gradio_app.py`

---

## 🐛 Troubleshooting

### **"Module not found" errors**
```bash
pip install -r requirements.txt
```

### **"API key invalid" error**
- Check your OpenAI API key
- Ensure it starts with `sk-`
- Verify you have API credits

### **Gradio won't launch in Colab**
```python
# Try explicit port:
demo.launch(server_port=7860, share=True)
```

### **Slow processing**
- Disable evaluator agent
- Use gpt-4o-mini model (default)
- Check internet connection

### **Results look wrong**
- Verify document type is correct
- Check image quality
- Try with different document

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| **Average Processing** | 15-30 seconds |
| **With Evaluator** | 25-40 seconds |
| **File Upload** | < 1 second |
| **UI Load Time** | 2-3 seconds |
| **Memory Usage** | ~500MB |

---

## 🔒 Security & Privacy

### **API Key Handling**
- ✅ Keys entered in UI are session-only
- ✅ Not stored on server
- ✅ Not logged
- ✅ Cleared after session

### **Document Handling**
- ✅ Processed in memory when possible
- ✅ Temporary files cleaned up
- ✅ No permanent storage
- ⚠️ Consider data privacy when using public URLs

### **Best Practices**
1. Don't share public URLs with sensitive documents
2. Use environment variables for API keys in production
3. Consider running locally for confidential data
4. Review OpenAI's data usage policies

---

## 📚 Additional Resources

- **Main Docs**: [README.md](README.md)
- **Quick Start**: [QUICK_START.md](QUICK_START.md)
- **Technical Details**: [AGENTIC_OCR_README.md](AGENTIC_OCR_README.md)
- **API Reference**: [mortgage_core.py](mortgage_core.py)

---

## 🎓 Examples

### **Example 1: Bank Statement**
```
Upload: bank_statement.pdf
Type: current_acct_statements
Required: account_number, iban
Result: Quality Score 85/100, 2 flagged fields
```

### **Example 2: Payslip**
```
Upload: payslip_march_2024.pdf
Type: payslips
Required: employee_name, net_pay, gross_pay
Result: Quality Score 92/100, 0 flagged fields
```

### **Example 3: ID Document**
```
Upload: passport_scan.jpg
Type: photo_id
Required: holder_full_name, document_number
Result: Quality Score 78/100, 1 flagged field
```

---

## 🚀 Next Steps

1. **Try the Demo**: Open in Colab and process a document
2. **Read the Docs**: Check out [README.md](README.md)
3. **Customize**: Modify the UI for your needs
4. **Deploy**: Run on your own server
5. **Integrate**: Use the Python API in your app

---

**Enjoy the beautiful Gradio interface! 🎨**
