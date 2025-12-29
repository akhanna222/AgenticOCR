import base64
import json
import os
from io import BytesIO
from typing import Any, Dict, List, Optional

from openai import OpenAI
from pdf2image import convert_from_path
from PIL import Image, ImageFile

# Import new agentic OCR system
try:
    from ocr_agent import AgenticOCR, FieldAssessor, create_metadata_from_schema_hints
    from openai_extractor import OpenAIEvaluatorAgent, OpenAIVisionExtractor

    AGENTIC_OCR_AVAILABLE = True
except ImportError:
    AGENTIC_OCR_AVAILABLE = False
    print("[mortgage_core] Warning: Agentic OCR modules not available")

# Allow slightly truncated images without crashing
ImageFile.LOAD_TRUNCATED_IMAGES = True

# ==========================================
# 0. API KEY SETUP
# ==========================================
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
OPENAI_VISION_MODEL = "gpt-4o-mini"


# ==========================================
# 1. DOCUMENT TYPES & BUILT-IN SCHEMAS
# ==========================================
MORTGAGE_DOC_TYPES = {
    "app_form": "Mortgage Application Form",
    "current_acct_statements": "Bank / Current Account Statement (simple)",
    "savings_investment_statements": "Savings / Investment Statements (external)",
    "borrowings_statements": "Loan/Credit/Mortgage Statements (external)",
    "equity_input_proof": "Evidence of Deposit / Equity & Source of Funds",
    "rent_evidence": "Lease/Rental Agreement or Landlord Letter",
    "photo_id": "Photo ID",
    "proof_of_address": "Proof of Address",
    "ppsn_trn_verification": "PPSN/TRN Proof",
    "valuation_report": "Valuation Report",
    "salary_certificate": "Employer Salary Certificate",
    "payslips": "Most Recent Payslips",
    "eds_summary_standard": "Employment Detail Summary (latest year)",
    "eds_summary_3yr": "Employment Detail Summary (3 years)",
    "tax_affairs_confirmation_non_paye": "Tax Affairs Confirmation (non-PAYE)",
    "revenue_forms11_extra_income": "Revenue Form 11 – Non-PAYE / Extra Income",
    "audited_or_trading_accounts": "Audited/Trading Accounts",
    "revenue_forms11_self_emp": "Revenue Form 11 – Self-Employed",
    "tax_position_confirmation": "Tax Position Confirmation",
    "business_account_statements": "Business Current Account Statements",
    "business_borrowings_statements": "Business Borrowings Statements",
    "rental_income_tax_forms": "Tax Returns Showing Rental Income",
    "rental_income_bank_stmts": "Bank Statements evidencing rental income",
    "rental_tax_clearance": "Tax Confirmation for Rental Income",
    "borrow_past_68_letter": "Employer Letter confirming retirement date",
    "on_leave_return_letter": "Employer Letter confirming return from leave",
    "work_permit_irp": "Irish Residence Permit / Work Permit",
    "foreign_credit_check": "Foreign Credit Check (English)",
    "separation_agreement": "Separation/Divorce Agreement",
    "self_build_section_g": "Self-Build Application Form Section G",
    "self_build_certified_costings": "Self-Build Certified Costings & Evidence",
}
DOC_TYPE_CHOICES_TEXT = "\n".join(
    f"- {k}: {v}" for k, v in MORTGAGE_DOC_TYPES.items()
)

# ---------- GENERIC FALLBACK SCHEMA ----------
GENERIC_DOC_TEMPLATE: Dict[str, Any] = {
    "doc_type_id": "unknown",
    "title": "",
    "issuing_institution": "",
    "holder_name": "",
    "reference_number": "",
    "issue_date": "",
    "effective_date": "",
    "address_block": "",
    "summary": "",
    "notes": "",
}

# ---------- BUILT-IN SCHEMAS BY DOC TYPE ----------
SCHEMAS: Dict[str, Dict[str, Any]] = {}

# Bank / Current Account Statements (simple)
SCHEMAS["current_acct_statements"] = {
    "doc_type_id": "current_acct_statements",
    "issueDate": "",
    "periodStartDate": "",
    "periodEndDate": "",
    "initialBalance": "",
    "finalBalance": "",
    "bankName": "",
    "bankBranchCode": "",
    "bankBIC": "",
    "accountName": "",
    "accountNumber": "",
    "accountType": "",
    "address": "",
    "transactions": [],
}

# Savings / Investment Statements
SCHEMAS["savings_investment_statements"] = {
    "doc_type_id": "savings_investment_statements",
    "institution_name": "",
    "institution_address": "",
    "account_holder_name": "",
    "account_holder_address": "",
    "account_number": "",
    "iban": "",
    "account_type": "",
    "currency": "",
    "statement_start_date": "",
    "statement_end_date": "",
    "document_issue_date": "",
    "opening_balance": "",
    "closing_balance": "",
    "total_deposits": "",
    "total_withdrawals": "",
    "interest_earned": "",
    "header_address_block": "",
    "document_summary": "",
    "anomalies_or_notes": "",
}

# Borrowings Statements (loans, credit cards, mortgages)
SCHEMAS["borrowings_statements"] = {
    "doc_type_id": "borrowings_statements",
    "lender_name": "",
    "lender_address": "",
    "borrower_name": "",
    "borrower_address": "",
    "account_or_loan_number": "",
    "product_type": "",
    "currency": "",
    "statement_start_date": "",
    "statement_end_date": "",
    "document_issue_date": "",
    "opening_balance": "",
    "closing_balance": "",
    "credit_limit": "",
    "interest_rate": "",
    "arrears_amount": "",
    "minimum_payment_due": "",
    "payment_due_date": "",
    "total_interest_charged": "",
    "total_fees_charged": "",
    "document_summary": "",
    "anomalies_or_notes": "",
}

# Payslips
SCHEMAS["payslips"] = {
    "doc_type_id": "payslips",
    "employee_name": "",
    "employee_address": "",
    "employee_number": "",
    "employer_name": "",
    "employer_address": "",
    "pay_period_start": "",
    "pay_period_end": "",
    "pay_date": "",
    "gross_pay": "",
    "net_pay": "",
    "basic_pay": "",
    "overtime_pay": "",
    "bonus_or_commission": "",
    "tax_deducted": "",
    "prsi_or_social_insurance": "",
    "pension_contribution_employee": "",
    "pension_contribution_employer": "",
    "other_deductions": "",
    "year_to_date_gross": "",
    "year_to_date_tax": "",
    "year_to_date_net": "",
    "pay_frequency": "",
    "pps_number": "",
    "iban": "",
    "document_summary": "",
    "anomalies_or_notes": "",
}

# Photo ID
SCHEMAS["photo_id"] = {
    "doc_type_id": "photo_id",
    "id_type": "",
    "issuing_country": "",
    "issuing_authority": "",
    "holder_full_name": "",
    "date_of_birth": "",
    "document_number": "",
    "expiry_date": "",
    "issue_date": "",
    "address_on_id": "",
    "mrz_text": "",
    "document_summary": "",
    "anomalies_or_notes": "",
}

# Proof of Address
SCHEMAS["proof_of_address"] = {
    "doc_type_id": "proof_of_address",
    "document_type": "",
    "issuer_name": "",
    "issuer_address": "",
    "recipient_name": "",
    "recipient_address": "",
    "account_or_reference_number": "",
    "document_date": "",
    "address_effective_date": "",
    "address_lines": "",
    "document_summary": "",
    "anomalies_or_notes": "",
}

# PPSN / TRN Proof
SCHEMAS["ppsn_trn_verification"] = {
    "doc_type_id": "ppsn_trn_verification",
    "document_type": "",
    "issuing_body": "",
    "holder_name": "",
    "pps_or_trn_number": "",
    "document_date": "",
    "address_on_document": "",
    "document_summary": "",
    "anomalies_or_notes": "",
}

# Salary Certificate
SCHEMAS["salary_certificate"] = {
    "doc_type_id": "salary_certificate",
    "employer_name": "",
    "employer_address": "",
    "employee_name": "",
    "employee_address": "",
    "employee_number": "",
    "employment_status": "",
    "role_or_job_title": "",
    "start_date": "",
    "gross_annual_salary": "",
    "basic_salary": "",
    "variable_pay_description": "",
    "variable_pay_amount": "",
    "overtime_regular": "",
    "bonus_regular": "",
    "other_allowances": "",
    "confirmation_of_employment": "",
    "signed_by_name": "",
    "signed_by_position": "",
    "signature_date": "",
    "document_summary": "",
    "anomalies_or_notes": "",
}

# Equity Input Proof
SCHEMAS["equity_input_proof"] = {
    "doc_type_id": "equity_input_proof",
    "document_type": "",
    "donor_or_source_name": "",
    "donor_or_source_address": "",
    "recipient_name": "",
    "amount": "",
    "currency": "",
    "relationship_to_applicant": "",
    "conditions_or_repayment_expectations": "",
    "source_of_funds_description": "",
    "supporting_reference_numbers": "",
    "document_date": "",
    "document_summary": "",
    "anomalies_or_notes": "",
}

# Rent Evidence
SCHEMAS["rent_evidence"] = {
    "doc_type_id": "rent_evidence",
    "document_type": "",
    "landlord_name": "",
    "landlord_address": "",
    "tenant_name": "",
    "tenant_address": "",
    "property_address": "",
    "rent_amount": "",
    "currency": "",
    "payment_frequency": "",
    "lease_start_date": "",
    "lease_end_date": "",
    "is_ongoing_tenancy": "",
    "reference_number": "",
    "document_date": "",
    "document_summary": "",
    "anomalies_or_notes": "",
}

# Valuation Report
SCHEMAS["valuation_report"] = {
    "doc_type_id": "valuation_report",
    "valuer_name": "",
    "valuer_firm": "",
    "valuer_contact_details": "",
    "property_address": "",
    "property_type": "",
    "valuation_amount": "",
    "currency": "",
    "valuation_date": "",
    "report_reference": "",
    "lender_name": "",
    "instructions_date": "",
    "special_assumptions": "",
    "property_condition_summary": "",
    "marketability_comment": "",
    "document_summary": "",
    "anomalies_or_notes": "",
}


# ==========================================
# 2. SCHEMA LOADER (supports folder overrides)
# ==========================================
def load_schema_for_doc_type(doc_type_id: str) -> Dict[str, Any]:
    """
    Load schema for a given doc_type_id.
    Priority:
      1) ./schemas/{doc_type_id}.json if exists
      2) built-in SCHEMAS[doc_type_id]
      3) GENERIC_DOC_TEMPLATE
    """
    schema_path = os.path.join("schemas", f"{doc_type_id}.json")
    if os.path.exists(schema_path):
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("doc_type_id", doc_type_id)
            return data
        except Exception as e:  # noqa: BLE001
            print(f"[schema] Failed to load {schema_path}: {e}")

    if doc_type_id in SCHEMAS:
        base = dict(SCHEMAS[doc_type_id])
        base["doc_type_id"] = doc_type_id
        return base

    base = dict(GENERIC_DOC_TEMPLATE)
    base["doc_type_id"] = doc_type_id
    return base


# ==========================================
# 3. UTILITIES
# ==========================================
def load_document_as_images(path: str) -> List[Image.Image]:
    """
    If PDF → convert each page to an image.
    If image → return a single-page list.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        pages = convert_from_path(path, dpi=200)
        return pages
    img = Image.open(path)
    img.load()
    img = img.convert("RGB")
    return [img]


def image_to_base64_png(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def ensure_keys(template: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(data)
    for k, v in template.items():
        if k not in out:
            out[k] = [] if isinstance(v, list) else ""
    return out


def merge_page_results(page_results: List[Dict[str, Any]], base_template: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge across pages: first non-empty wins.
    """

    def is_empty(v: Any) -> bool:
        return v is None or v == "" or (isinstance(v, list) and len(v) == 0)

    merged = {k: "" if not isinstance(v, list) else [] for k, v in base_template.items()}
    for res in page_results:
        for k, v in res.items():
            if k not in merged:
                merged[k] = v
            elif is_empty(merged[k]) and not is_empty(v):
                merged[k] = v
    return merged


# ==========================================
# 4. CORE: OPENAI JSON-MODE VISION HELPER
# ==========================================
def openai_vision_json(
    image: Image.Image,
    template: Dict[str, Any],
    system_prompt: str,
    user_instructions: str,
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    """
    Use OpenAI Vision (gpt-4o-mini) with JSON mode to fill 'template'.
    Returns a Python dict.
    """
    b64 = image_to_base64_png(image)
    template_json = json.dumps(template, indent=2)

    full_user_text = f"""{user_instructions}

JSON_TEMPLATE:
{template_json}
"""

    resp = client.chat.completions.create(
        model=OPENAI_VISION_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": full_user_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            },
        ],
        temperature=0.0,
        max_tokens=max_tokens,
    )

    content = resp.choices[0].message.content
    if isinstance(content, list):
        text = "".join(p.text for p in content if hasattr(p, "text"))
    else:
        text = content

    data = json.loads(text)
    return ensure_keys(template, data)


# ==========================================
# 5. STEP 1: CLASSIFY DOCUMENT TYPE
# ==========================================
def classify_document(pages: List[Image.Image]) -> Dict[str, Any]:
    """
    Use first page to classify into MORTGAGE_DOC_TYPES.
    Returns dict: {doc_type_id, doc_title, confidence, rationale}
    """
    first_page = pages[0]
    b64 = image_to_base64_png(first_page)

    system_prompt = "You are a strict JSON-only mortgage document classifier for an Irish lender."
    user_text = f"""
You are given the first page of a mortgage-related document.

Classify it into ONE of the following doc types:

{DOC_TYPE_CHOICES_TEXT}

Return ONLY a JSON object with:
{{
  "doc_type_id": "<one of the keys above, e.g. 'current_acct_statements'>",
  "doc_title": "<human readable title>",
  "confidence": <number between 0 and 1>,
  "rationale": "<short explanation>"
}}
"""

    resp = client.chat.completions.create(
        model=OPENAI_VISION_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            },
        ],
        temperature=0.0,
        max_tokens=700,
    )

    content = resp.choices[0].message.content
    if isinstance(content, list):
        text = "".join(p.text for p in content if hasattr(p, "text"))
    else:
        text = content

    result = json.loads(text)
    result.setdefault("doc_type_id", "unknown")
    result.setdefault("doc_title", "Unknown")
    result.setdefault("confidence", 0.0)
    result.setdefault("rationale", "")
    return result


# ==========================================
# 6. STEP 2: EXTRACTION (MULTI-SCHEMA)
# ==========================================
def extract_with_schema_all_pages(
    pages: List[Image.Image],
    classification: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Use the classified doc_type_id to pick a schema, then extract that schema per page.
    """
    doc_type_id = classification.get("doc_type_id", "unknown")
    base_template = load_schema_for_doc_type(doc_type_id)

    page_results: List[Dict[str, Any]] = []

    print(f"[agent] Using schema for doc_type_id='{doc_type_id}' with {len(base_template)} fields.")
    print("[agent] Running OpenAI JSON-mode extraction per page...")
    for i, page in enumerate(pages, start=1):
        print(f"   - Page {i} / {len(pages)}")

        system_prompt = "You are a precise JSON-only extractor for mortgage documents."
        user_instructions = f"""
You are given a page of a mortgage-related document.

Document type id: {doc_type_id}

Instructions:
- Extract fields into JSON_TEMPLATE exactly.
- Do NOT add or remove keys.
- If a field is not visible or not clearly readable, leave it as \"\" or null.
- Dates should be YYYY-MM-DD if possible.
- Amounts should be numeric or string with currency if visible.
"""

        page_data = openai_vision_json(
            image=page,
            template=base_template,
            system_prompt=system_prompt,
            user_instructions=user_instructions,
            max_tokens=2000,
        )
        page_results.append(page_data)

    merged = merge_page_results(page_results, base_template)
    return {
        "schema": base_template,
        "page_extractions": page_results,
        "merged": merged,
    }


# ==========================================
# 7. STEP 3: EVALUATION + REFINEMENT LOOP
# ==========================================
def evaluate_and_refine(
    pages: List[Image.Image],
    schema_template: Dict[str, Any],
    extracted: Dict[str, Any],
    doc_type_id: str,
    max_iters: int = 3,
) -> Dict[str, Any]:
    """
    Evaluation loop:
    - Judge sees first page + doc_type_id + schema_template + current extracted JSON.
    - Returns {passed, score, issues, fixed_output}.
    - If not passed, uses fixed_output as new extraction and repeats.
    """
    current_extracted = dict(extracted)
    last_eval: Optional[Dict[str, Any]] = None
    first_page = pages[0]

    for i in range(1, max_iters + 1):
        print(f"[agent] Evaluation iteration {i}...")

        eval_template = {
            "passed": False,
            "score": 0.0,
            "issues": [],
            "fixed_output": schema_template,
        }

        system_prompt = "You are a rigorous evaluator for mortgage document extraction. Always return JSON."
        user_instructions = f"""
You are evaluating an extracted JSON for a mortgage document.

doc_type_id: "{doc_type_id}"

You are given:
- The first page of the document as an image.
- JSON_TEMPLATE describing the evaluation output format.
- The current extracted JSON (fields follow the extraction schema):

{json.dumps(current_extracted, indent=2)}

Your tasks:
- Check if extracted values are plausible given the document image and doc_type_id.
- Identify missing or obviously wrong fields.
- If problems exist, correct them in 'fixed_output' as best as you can from the image.
- If a value truly cannot be read, leave it as \"\" or null.
- Do NOT add or remove keys from the extraction template.

Return ONLY a JSON object matching JSON_TEMPLATE (including 'fixed_output').
"""

        eval_result = openai_vision_json(
            image=first_page,
            template=eval_template,
            system_prompt=system_prompt,
            user_instructions=user_instructions,
            max_tokens=2000,
        )

        eval_result.setdefault("passed", False)
        eval_result.setdefault("score", 0.0)
        eval_result.setdefault("issues", [])
        if "fixed_output" not in eval_result:
            eval_result["fixed_output"] = current_extracted

        fixed = ensure_keys(schema_template, eval_result["fixed_output"])
        eval_result["fixed_output"] = fixed
        eval_result["iteration"] = i

        last_eval = eval_result
        print(f"   passed: {eval_result['passed']}, score: {eval_result['score']}")
        if not eval_result["passed"]:
            print("   issues:", eval_result.get("issues", []))
            current_extracted = fixed
        else:
            print("[agent] Evaluation passed, stopping loop.")
            break

    return {
        "final_extracted": current_extracted,
        "evaluation": last_eval,
    }


# ==========================================
# 8. ORCHESTRATOR: FULL PIPELINE
# ==========================================
def run_full_pipeline(
    path: str,
    override_doc_type_id: Optional[str] = None,
    max_eval_iters: int = 3,
) -> Dict[str, Any]:
    """
    Full pipeline, optionally forcing a doc_type_id instead of using classifier.
    Returns a dict with classification, schema_used, page_extractions, extracted_initial,
    extracted_final, evaluation.
    """
    print(f"[agent] Loading document: {path}")
    pages = load_document_as_images(path)
    print(f"[agent] Loaded {len(pages)} page(s).")

    if override_doc_type_id:
        print(f"[agent] Using user-selected doc_type_id='{override_doc_type_id}' (skipping classifier).")
        doc_type_id = override_doc_type_id
        classification = {
            "doc_type_id": doc_type_id,
            "doc_title": MORTGAGE_DOC_TYPES.get(doc_type_id, doc_type_id),
            "confidence": 0.99,
            "rationale": "User-selected template, classifier bypassed.",
        }
    else:
        print("[agent] Classifying document type...")
        classification = classify_document(pages)
        print("   Classification:", json.dumps(classification, indent=2))
        doc_type_id = classification.get("doc_type_id", "unknown")

    schema = load_schema_for_doc_type(doc_type_id)

    extraction_result = extract_with_schema_all_pages(
        pages=pages,
        classification=classification,
    )

    merged_extracted = extraction_result["merged"]

    eval_result = evaluate_and_refine(
        pages=pages,
        schema_template=schema,
        extracted=merged_extracted,
        doc_type_id=doc_type_id,
        max_iters=max_eval_iters,
    )

    return {
        "classification": classification,
        "schema_used": schema,
        "page_extractions": extraction_result["page_extractions"],
        "extracted_initial": merged_extracted,
        "extracted_final": eval_result["final_extracted"],
        "evaluation": eval_result["evaluation"],
    }


# ==========================================
# 9. NEW: AGENTIC OCR PIPELINE WITH AUTO-ASSESSMENT
# ==========================================
def run_agentic_pipeline(
    path: str,
    override_doc_type_id: Optional[str] = None,
    use_evaluator: bool = True,
    required_fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    🧠 NEW: Enhanced OCR pipeline with agentic field assessment and flagging

    Features:
    - Field-level confidence scoring
    - Automatic assessment of unfilled/invalid fields
    - Targeted retry for flagged fields
    - Comprehensive quality reporting
    - Validation rules per field type

    Args:
        path: Path to document (PDF or image)
        override_doc_type_id: Force specific document type (skip classification)
        use_evaluator: Use separate evaluator agent for quality check
        required_fields: List of field names that are required

    Returns:
        Enhanced result dictionary with:
        - classification: Document classification
        - extracted_data: Final extracted field values
        - confidence_scores: Confidence per field (0-1)
        - assessment_report: Detailed field status report
        - evaluation: Optional evaluator feedback
        - flagged_fields: List of fields needing attention
    """
    if not AGENTIC_OCR_AVAILABLE:
        print("[mortgage_core] ERROR: Agentic OCR system not available. Falling back to standard pipeline.")
        return run_full_pipeline(path, override_doc_type_id)

    print("=" * 60)
    print("🧠 AGENTIC OCR PIPELINE WITH AUTO-ASSESSMENT")
    print("=" * 60)

    # Load document
    print(f"[pipeline] Loading document: {path}")
    pages = load_document_as_images(path)
    print(f"[pipeline] Loaded {len(pages)} page(s)")

    # Classify or use override
    if override_doc_type_id:
        print(f"[pipeline] Using doc_type_id='{override_doc_type_id}' (user-selected)")
        doc_type_id = override_doc_type_id
        classification = {
            "doc_type_id": doc_type_id,
            "doc_title": MORTGAGE_DOC_TYPES.get(doc_type_id, doc_type_id),
            "confidence": 0.99,
            "rationale": "User-selected template",
        }
    else:
        print("[pipeline] Classifying document...")
        classification = classify_document(pages)
        doc_type_id = classification.get("doc_type_id", "unknown")
        print(f"[pipeline] Classified as: {doc_type_id} (confidence: {classification.get('confidence', 0):.2f})")

    # Load schema
    schema = load_schema_for_doc_type(doc_type_id)
    print(f"[pipeline] Loaded schema with {len(schema)} fields")

    # Create metadata map for field validation
    metadata_map = create_metadata_from_schema_hints(
        schema=schema,
        default_required_fields=required_fields or [],
    )

    # Initialize agentic OCR components
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    extractor = OpenAIVisionExtractor(api_key=api_key, model=OPENAI_VISION_MODEL)
    assessor = FieldAssessor(min_confidence_threshold=0.6)
    agent = AgenticOCR(extractor=extractor, assessor=assessor, max_retry_attempts=3)

    # Run agentic extraction
    print("\n" + "=" * 60)
    result = agent.extract_document(
        pages=pages,
        schema=schema,
        metadata_map=metadata_map,
        doc_type_id=doc_type_id,
    )
    print("=" * 60)

    # Print summary
    assessment = result["assessment_report"]
    print(f"\n📊 EXTRACTION SUMMARY:")
    print(f"   Total Fields: {assessment['total_fields']}")
    print(f"   Filled: {assessment['filled_fields']} ({assessment['completion_rate']:.1f}%)")
    print(f"   Unfilled: {assessment['unfilled_fields']}")
    print(f"   Low Confidence: {assessment['low_confidence_fields']}")
    print(f"   Invalid: {assessment['invalid_fields']}")
    print(f"   Average Confidence: {assessment['average_confidence']:.2f}")
    print(f"   Quality Score: {assessment['quality_score']:.1f}/100")

    if assessment['flagged_field_names']:
        print(f"\n⚠️  FLAGGED FIELDS ({len(assessment['flagged_field_names'])}):")
        for field_name in assessment['flagged_field_names'][:10]:  # Show first 10
            field_detail = assessment['field_details'].get(field_name, {})
            status = field_detail.get('status', 'unknown')
            conf = field_detail.get('confidence', 0.0)
            print(f"   - {field_name}: {status} (confidence: {conf:.2f})")

    # Optional: Run evaluator agent for additional quality check
    evaluation = None
    if use_evaluator and pages:
        print("\n[pipeline] Running evaluator agent...")
        evaluator = OpenAIEvaluatorAgent(api_key=api_key, model=OPENAI_VISION_MODEL)
        evaluation = evaluator.evaluate_extraction(
            image=pages[0],
            schema=schema,
            extracted_data=result["extracted_data"],
            assessment_report=assessment,
        )

        if evaluation.get("critical_issues"):
            print(f"   ⚠️  Critical issues found: {len(evaluation['critical_issues'])}")
            for issue in evaluation['critical_issues'][:3]:
                print(f"      - {issue}")

        if evaluation.get("suggestions"):
            print(f"   💡 Suggestions: {len(evaluation['suggestions'])}")

    # Compile final result
    final_result = {
        "classification": classification,
        "schema_used": schema,
        "extracted_data": result["extracted_data"],
        "confidence_scores": result["confidence_scores"],
        "assessment_report": assessment,
        "evaluation": evaluation,
        "flagged_fields": assessment['flagged_field_names'],
        "quality_metrics": {
            "completion_rate": assessment['completion_rate'],
            "quality_score": assessment['quality_score'],
            "average_confidence": assessment['average_confidence'],
        },
        "total_pages": len(pages),
        "doc_type_id": doc_type_id,
        "timestamp": result["timestamp"],
    }

    print("\n✅ Agentic OCR pipeline complete!")
    return final_result
