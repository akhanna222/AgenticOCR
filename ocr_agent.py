"""
🧠 Robust Agentic OCR System with Field Assessment & Flagging

Key Features:
- Field-level confidence scoring
- Automatic field assessment (unfilled, low-confidence, invalid)
- Validation rules engine
- Multi-pass extraction with targeted retry
- Comprehensive field status reporting
- Provider-agnostic design
"""

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from PIL import Image


# ==========================================
# 1. FIELD STATUS DEFINITIONS
# ==========================================
class FieldStatus(Enum):
    """Status of an extracted field"""
    FILLED = "filled"  # Field has valid data with good confidence
    UNFILLED = "unfilled"  # Field is empty or null
    LOW_CONFIDENCE = "low_confidence"  # Field has data but confidence < threshold
    INVALID = "invalid"  # Field has data but fails validation rules
    NEEDS_REVIEW = "needs_review"  # Field flagged for manual review


class FieldType(Enum):
    """Type of field for validation"""
    TEXT = "text"
    NUMBER = "number"
    CURRENCY = "currency"
    DATE = "date"
    EMAIL = "email"
    PHONE = "phone"
    IBAN = "iban"
    ADDRESS = "address"
    PERCENTAGE = "percentage"
    BOOLEAN = "boolean"


# ==========================================
# 2. FIELD METADATA & RESULT STRUCTURES
# ==========================================
@dataclass
class FieldMetadata:
    """Metadata about a field in the schema"""
    name: str
    field_type: FieldType = FieldType.TEXT
    required: bool = False
    validation_rules: List[str] = field(default_factory=list)
    min_confidence: float = 0.6
    description: str = ""


@dataclass
class FieldResult:
    """Result of extracting a single field"""
    name: str
    value: Any
    confidence: float = 0.0
    status: FieldStatus = FieldStatus.UNFILLED
    validation_errors: List[str] = field(default_factory=list)
    extraction_attempts: int = 1
    source_page: Optional[int] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "confidence": self.confidence,
            "status": self.status.value,
            "validation_errors": self.validation_errors,
            "extraction_attempts": self.extraction_attempts,
            "source_page": self.source_page,
            "notes": self.notes,
        }


@dataclass
class ExtractionReport:
    """Comprehensive report of extraction results"""
    total_fields: int = 0
    filled_fields: int = 0
    unfilled_fields: int = 0
    low_confidence_fields: int = 0
    invalid_fields: int = 0
    needs_review_fields: int = 0
    average_confidence: float = 0.0
    flagged_field_names: List[str] = field(default_factory=list)
    field_results: Dict[str, FieldResult] = field(default_factory=dict)

    def completion_rate(self) -> float:
        """Calculate percentage of successfully filled fields"""
        if self.total_fields == 0:
            return 0.0
        return (self.filled_fields / self.total_fields) * 100

    def quality_score(self) -> float:
        """Calculate overall quality score (0-100)"""
        if self.total_fields == 0:
            return 0.0

        # Weight factors
        filled_weight = 0.5
        confidence_weight = 0.3
        validation_weight = 0.2

        filled_score = (self.filled_fields / self.total_fields) * 100
        confidence_score = self.average_confidence * 100
        validation_score = ((self.total_fields - self.invalid_fields) / self.total_fields) * 100

        return (
            filled_score * filled_weight +
            confidence_score * confidence_weight +
            validation_score * validation_weight
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_fields": self.total_fields,
            "filled_fields": self.filled_fields,
            "unfilled_fields": self.unfilled_fields,
            "low_confidence_fields": self.low_confidence_fields,
            "invalid_fields": self.invalid_fields,
            "needs_review_fields": self.needs_review_fields,
            "average_confidence": round(self.average_confidence, 3),
            "completion_rate": round(self.completion_rate(), 2),
            "quality_score": round(self.quality_score(), 2),
            "flagged_field_names": self.flagged_field_names,
            "field_details": {k: v.to_dict() for k, v in self.field_results.items()},
        }


# ==========================================
# 3. FIELD VALIDATORS
# ==========================================
class FieldValidator:
    """Validation rules for different field types"""

    @staticmethod
    def is_empty(value: Any) -> bool:
        """Check if value is empty"""
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        if isinstance(value, list):
            return len(value) == 0
        return False

    @staticmethod
    def validate_date(value: str) -> Tuple[bool, Optional[str]]:
        """Validate date format (YYYY-MM-DD, DD/MM/YYYY, etc.)"""
        if FieldValidator.is_empty(value):
            return True, None  # Empty is valid, just unfilled

        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            r'^\d{2}/\d{2}/\d{4}$',  # DD/MM/YYYY
            r'^\d{2}-\d{2}-\d{4}$',  # DD-MM-YYYY
            r'^[A-Za-z]{3}\s+\d{1,2},?\s+\d{4}$',  # Jan 1, 2024
        ]

        for pattern in date_patterns:
            if re.match(pattern, str(value).strip()):
                return True, None

        return False, f"Invalid date format: {value}"

    @staticmethod
    def validate_number(value: Any) -> Tuple[bool, Optional[str]]:
        """Validate numeric value"""
        if FieldValidator.is_empty(value):
            return True, None

        try:
            # Remove common currency symbols and commas
            clean_value = str(value).replace(',', '').replace('€', '').replace('$', '').replace('£', '').strip()
            float(clean_value)
            return True, None
        except ValueError:
            return False, f"Invalid number: {value}"

    @staticmethod
    def validate_currency(value: str) -> Tuple[bool, Optional[str]]:
        """Validate currency amount"""
        if FieldValidator.is_empty(value):
            return True, None

        # Match patterns like: 1,234.56, €1234.56, $1,234, etc.
        pattern = r'^[€$£]?\s*\d{1,3}(,?\d{3})*(\.\d{2})?$'
        if re.match(pattern, str(value).strip()):
            return True, None

        return False, f"Invalid currency format: {value}"

    @staticmethod
    def validate_email(value: str) -> Tuple[bool, Optional[str]]:
        """Validate email address"""
        if FieldValidator.is_empty(value):
            return True, None

        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, str(value).strip()):
            return True, None

        return False, f"Invalid email format: {value}"

    @staticmethod
    def validate_phone(value: str) -> Tuple[bool, Optional[str]]:
        """Validate phone number"""
        if FieldValidator.is_empty(value):
            return True, None

        # Remove common separators
        clean_value = re.sub(r'[\s\-\(\)\.]', '', str(value))
        # Check if it's a reasonable length and contains only digits and +
        if re.match(r'^\+?\d{7,15}$', clean_value):
            return True, None

        return False, f"Invalid phone format: {value}"

    @staticmethod
    def validate_iban(value: str) -> Tuple[bool, Optional[str]]:
        """Validate IBAN format (basic check)"""
        if FieldValidator.is_empty(value):
            return True, None

        # Remove spaces
        clean_value = str(value).replace(' ', '').upper()
        # IBAN: 2 letter country code + 2 check digits + up to 30 alphanumeric
        if re.match(r'^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$', clean_value):
            return True, None

        return False, f"Invalid IBAN format: {value}"

    @staticmethod
    def validate_by_type(value: Any, field_type: FieldType) -> Tuple[bool, Optional[str]]:
        """Validate based on field type"""
        validators = {
            FieldType.DATE: FieldValidator.validate_date,
            FieldType.NUMBER: FieldValidator.validate_number,
            FieldType.CURRENCY: FieldValidator.validate_currency,
            FieldType.EMAIL: FieldValidator.validate_email,
            FieldType.PHONE: FieldValidator.validate_phone,
            FieldType.IBAN: FieldValidator.validate_iban,
        }

        validator = validators.get(field_type)
        if validator:
            return validator(value)

        # For TEXT, ADDRESS, BOOLEAN, PERCENTAGE - basic validation
        if FieldValidator.is_empty(value):
            return True, None

        return True, None


# ==========================================
# 4. FIELD ASSESSOR
# ==========================================
class FieldAssessor:
    """Assesses extracted fields and assigns status flags"""

    def __init__(self, min_confidence_threshold: float = 0.6):
        self.min_confidence_threshold = min_confidence_threshold
        self.validator = FieldValidator()

    def assess_field(
        self,
        name: str,
        value: Any,
        confidence: float,
        metadata: Optional[FieldMetadata] = None,
        source_page: Optional[int] = None,
    ) -> FieldResult:
        """
        Assess a single field and return FieldResult with status

        Args:
            name: Field name
            value: Extracted value
            confidence: Confidence score (0-1)
            metadata: Optional field metadata with validation rules
            source_page: Page number where value was found

        Returns:
            FieldResult with status and validation errors
        """
        result = FieldResult(
            name=name,
            value=value,
            confidence=confidence,
            source_page=source_page,
        )

        # Check if field is empty
        if self.validator.is_empty(value):
            result.status = FieldStatus.UNFILLED
            if metadata and metadata.required:
                result.notes = "Required field is unfilled"
            return result

        # Check confidence threshold
        min_conf = metadata.min_confidence if metadata else self.min_confidence_threshold
        if confidence < min_conf:
            result.status = FieldStatus.LOW_CONFIDENCE
            result.notes = f"Confidence {confidence:.2f} below threshold {min_conf:.2f}"

        # Validate field type if metadata provided
        if metadata:
            is_valid, error = self.validator.validate_by_type(value, metadata.field_type)
            if not is_valid:
                result.status = FieldStatus.INVALID
                result.validation_errors.append(error)
                result.notes = f"Validation failed: {error}"
            elif result.status != FieldStatus.LOW_CONFIDENCE:
                result.status = FieldStatus.FILLED
        else:
            # No metadata, just check if filled and confident
            if result.status != FieldStatus.LOW_CONFIDENCE:
                result.status = FieldStatus.FILLED

        return result

    def assess_extraction(
        self,
        extracted_data: Dict[str, Any],
        confidence_scores: Dict[str, float],
        metadata_map: Optional[Dict[str, FieldMetadata]] = None,
    ) -> ExtractionReport:
        """
        Assess all fields in an extraction

        Args:
            extracted_data: Dictionary of extracted field values
            confidence_scores: Dictionary of confidence scores per field
            metadata_map: Optional mapping of field names to metadata

        Returns:
            ExtractionReport with comprehensive assessment
        """
        report = ExtractionReport()
        metadata_map = metadata_map or {}

        for field_name, value in extracted_data.items():
            # Skip metadata fields
            if field_name in ['doc_type_id', 'page_count']:
                continue

            confidence = confidence_scores.get(field_name, 0.0)
            metadata = metadata_map.get(field_name)

            field_result = self.assess_field(
                name=field_name,
                value=value,
                confidence=confidence,
                metadata=metadata,
            )

            report.field_results[field_name] = field_result
            report.total_fields += 1

            # Update counts
            if field_result.status == FieldStatus.FILLED:
                report.filled_fields += 1
            elif field_result.status == FieldStatus.UNFILLED:
                report.unfilled_fields += 1
                report.flagged_field_names.append(field_name)
            elif field_result.status == FieldStatus.LOW_CONFIDENCE:
                report.low_confidence_fields += 1
                report.flagged_field_names.append(field_name)
            elif field_result.status == FieldStatus.INVALID:
                report.invalid_fields += 1
                report.flagged_field_names.append(field_name)
            elif field_result.status == FieldStatus.NEEDS_REVIEW:
                report.needs_review_fields += 1
                report.flagged_field_names.append(field_name)

        # Calculate average confidence
        if report.total_fields > 0:
            total_confidence = sum(r.confidence for r in report.field_results.values())
            report.average_confidence = total_confidence / report.total_fields

        return report


# ==========================================
# 5. AGENTIC OCR EXTRACTOR (Provider Interface)
# ==========================================
class OCRExtractor:
    """
    Abstract interface for OCR extraction providers
    Implement this for OpenAI, Claude, Gemini, etc.
    """

    def extract_fields_from_image(
        self,
        image: Image.Image,
        schema: Dict[str, Any],
        system_prompt: str,
        user_instructions: str,
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Extract fields from image and return values + confidence scores

        Returns:
            Tuple of (extracted_values, confidence_scores)
        """
        raise NotImplementedError("Subclass must implement extract_fields_from_image")


# ==========================================
# 6. AGENTIC OCR ORCHESTRATOR
# ==========================================
class AgenticOCR:
    """
    Main OCR orchestrator with agentic capabilities:
    - Multi-pass extraction
    - Field assessment
    - Targeted retry for flagged fields
    - Quality reporting
    """

    def __init__(
        self,
        extractor: OCRExtractor,
        assessor: Optional[FieldAssessor] = None,
        max_retry_attempts: int = 3,
    ):
        self.extractor = extractor
        self.assessor = assessor or FieldAssessor()
        self.max_retry_attempts = max_retry_attempts

    def extract_document(
        self,
        pages: List[Image.Image],
        schema: Dict[str, Any],
        metadata_map: Optional[Dict[str, FieldMetadata]] = None,
        doc_type_id: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Full agentic extraction pipeline:
        1. Initial extraction from all pages
        2. Assess field quality
        3. Retry flagged fields with focused prompts
        4. Generate comprehensive report

        Args:
            pages: List of document page images
            schema: Template schema to fill
            metadata_map: Optional field metadata for validation
            doc_type_id: Document type identifier

        Returns:
            Complete extraction result with assessment
        """
        print(f"[OCR Agent] Starting extraction for {len(pages)} page(s)")

        # Pass 1: Initial extraction from all pages
        print("[OCR Agent] Pass 1: Initial extraction...")
        all_extractions = []
        all_confidences = []

        for page_num, page in enumerate(pages, start=1):
            print(f"  - Extracting page {page_num}/{len(pages)}")

            extracted, confidences = self.extractor.extract_fields_from_image(
                image=page,
                schema=schema,
                system_prompt="You are a precise OCR extraction agent. Extract fields accurately and indicate confidence.",
                user_instructions=f"""
Extract all visible fields from this document page into the provided schema.

For each field, you must provide:
1. The extracted value
2. A confidence score (0.0 to 1.0) indicating your certainty

Rules:
- If a field is not visible on this page, leave it empty
- If text is unclear or partially visible, extract what you can and lower the confidence
- Dates should be in YYYY-MM-DD format when possible
- Numbers should be clean (no extra characters)
- DO NOT add or remove fields from the schema
"""
            )

            all_extractions.append(extracted)
            all_confidences.append(confidences)

        # Merge results across pages (first non-empty wins)
        merged_data = self._merge_extractions(all_extractions, schema)
        merged_confidences = self._merge_confidences(all_confidences)

        # Pass 2: Assess quality
        print("[OCR Agent] Pass 2: Assessing field quality...")
        report = self.assessor.assess_extraction(
            extracted_data=merged_data,
            confidence_scores=merged_confidences,
            metadata_map=metadata_map,
        )

        print(f"  - Completion rate: {report.completion_rate():.1f}%")
        print(f"  - Quality score: {report.quality_score():.1f}")
        print(f"  - Flagged fields: {len(report.flagged_field_names)}")

        # Pass 3: Retry flagged fields
        if report.flagged_field_names and self.max_retry_attempts > 1:
            print(f"[OCR Agent] Pass 3: Retrying {len(report.flagged_field_names)} flagged field(s)...")
            merged_data, merged_confidences = self._retry_flagged_fields(
                pages=pages,
                schema=schema,
                current_data=merged_data,
                current_confidences=merged_confidences,
                flagged_fields=report.flagged_field_names,
                metadata_map=metadata_map,
            )

            # Re-assess after retry
            report = self.assessor.assess_extraction(
                extracted_data=merged_data,
                confidence_scores=merged_confidences,
                metadata_map=metadata_map,
            )

            print(f"  - Updated completion rate: {report.completion_rate():.1f}%")
            print(f"  - Updated quality score: {report.quality_score():.1f}")

        return {
            "extracted_data": merged_data,
            "confidence_scores": merged_confidences,
            "assessment_report": report.to_dict(),
            "doc_type_id": doc_type_id,
            "total_pages": len(pages),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _merge_extractions(
        self,
        extractions: List[Dict[str, Any]],
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Merge multiple page extractions (first non-empty wins)"""
        merged = {k: ([] if isinstance(v, list) else "") for k, v in schema.items()}

        for extraction in extractions:
            for key, value in extraction.items():
                if key in merged:
                    current = merged[key]
                    # Only update if current is empty and new value is not
                    if self._is_empty(current) and not self._is_empty(value):
                        merged[key] = value

        return merged

    def _merge_confidences(
        self,
        all_confidences: List[Dict[str, float]],
    ) -> Dict[str, float]:
        """Merge confidence scores (take max across pages)"""
        merged = {}

        for confidences in all_confidences:
            for key, conf in confidences.items():
                if key not in merged or conf > merged[key]:
                    merged[key] = conf

        return merged

    def _retry_flagged_fields(
        self,
        pages: List[Image.Image],
        schema: Dict[str, Any],
        current_data: Dict[str, Any],
        current_confidences: Dict[str, float],
        flagged_fields: List[str],
        metadata_map: Optional[Dict[str, FieldMetadata]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """Retry extraction for flagged fields with focused prompts"""

        for attempt in range(2, self.max_retry_attempts + 1):
            print(f"    Retry attempt {attempt}/{self.max_retry_attempts}")

            # Create focused schema with only flagged fields
            focused_schema = {k: v for k, v in schema.items() if k in flagged_fields}

            if not focused_schema:
                break

            # Try first page with focused extraction
            extracted, confidences = self.extractor.extract_fields_from_image(
                image=pages[0],
                schema=focused_schema,
                system_prompt="You are a precise OCR extraction specialist. Focus on extracting the specified fields with maximum accuracy.",
                user_instructions=f"""
FOCUSED EXTRACTION - These specific fields need attention:

{', '.join(flagged_fields)}

Previous attempt had issues:
- Some fields were unfilled
- Some had low confidence
- Some failed validation

Instructions:
- Look VERY carefully for these specific fields
- If truly not present, leave empty
- If partially visible, extract what you can see
- Provide honest confidence scores
"""
            )

            # Update current data with better results
            for field_name in flagged_fields:
                if field_name in extracted:
                    new_value = extracted[field_name]
                    new_conf = confidences.get(field_name, 0.0)
                    old_conf = current_confidences.get(field_name, 0.0)

                    # Update if new extraction is better
                    if not self._is_empty(new_value) and new_conf > old_conf:
                        current_data[field_name] = new_value
                        current_confidences[field_name] = new_conf

        return current_data, current_confidences

    @staticmethod
    def _is_empty(value: Any) -> bool:
        """Check if value is empty"""
        return FieldValidator.is_empty(value)


# ==========================================
# 7. HELPER: CREATE METADATA MAP FROM SCHEMA
# ==========================================
def create_metadata_from_schema_hints(
    schema: Dict[str, Any],
    default_required_fields: Optional[List[str]] = None,
) -> Dict[str, FieldMetadata]:
    """
    Create FieldMetadata map from schema structure
    Can be enhanced to read from schema annotations

    Args:
        schema: Document schema
        default_required_fields: List of field names that are required

    Returns:
        Dictionary mapping field names to FieldMetadata
    """
    metadata_map = {}
    default_required_fields = default_required_fields or []

    # Field type inference heuristics
    def infer_type(field_name: str) -> FieldType:
        name_lower = field_name.lower()

        if 'date' in name_lower:
            return FieldType.DATE
        if any(x in name_lower for x in ['amount', 'balance', 'salary', 'pay', 'income']):
            return FieldType.CURRENCY
        if 'email' in name_lower:
            return FieldType.EMAIL
        if 'phone' in name_lower or 'tel' in name_lower:
            return FieldType.PHONE
        if 'iban' in name_lower:
            return FieldType.IBAN
        if 'address' in name_lower:
            return FieldType.ADDRESS
        if any(x in name_lower for x in ['rate', 'percent', 'ratio']):
            return FieldType.PERCENTAGE
        if any(x in name_lower for x in ['count', 'number', 'year', 'age']):
            return FieldType.NUMBER

        return FieldType.TEXT

    for field_name in schema.keys():
        if field_name == 'doc_type_id':
            continue

        metadata_map[field_name] = FieldMetadata(
            name=field_name,
            field_type=infer_type(field_name),
            required=field_name in default_required_fields,
            min_confidence=0.6,
        )

    return metadata_map
