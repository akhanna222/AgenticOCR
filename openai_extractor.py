"""
OpenAI Vision-based OCR Extractor Implementation

Implements the OCRExtractor interface using OpenAI's vision models
with enhanced confidence scoring and JSON mode.
"""

import base64
import json
from io import BytesIO
from typing import Any, Dict, Tuple

from openai import OpenAI
from PIL import Image

from ocr_agent import OCRExtractor


class OpenAIVisionExtractor(OCRExtractor):
    """
    OCR extractor using OpenAI Vision API

    Features:
    - Dual-output JSON mode (values + confidence scores)
    - Enhanced prompting for confidence estimation
    - Robust error handling
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        max_tokens: int = 2500,
        temperature: float = 0.0,
    ):
        """
        Initialize OpenAI Vision extractor

        Args:
            api_key: OpenAI API key
            model: Model identifier (gpt-4o-mini, gpt-4o, etc.)
            max_tokens: Maximum tokens for response
            temperature: Sampling temperature (0.0 for deterministic)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def extract_fields_from_image(
        self,
        image: Image.Image,
        schema: Dict[str, Any],
        system_prompt: str,
        user_instructions: str,
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Extract fields from image using OpenAI Vision

        Returns:
            Tuple of (extracted_values, confidence_scores)
        """
        # Convert image to base64
        b64_image = self._image_to_base64(image)

        # Create dual-structure template for values + confidences
        extraction_template = {
            "fields": schema,
            "confidence_scores": {k: 0.0 for k in schema.keys()},
        }

        template_json = json.dumps(extraction_template, indent=2)

        # Enhanced user prompt with confidence instructions
        full_user_text = f"""{user_instructions}

CRITICAL: You must provide TWO things for each field:
1. The extracted value in the "fields" section
2. A confidence score (0.0 to 1.0) in the "confidence_scores" section

Confidence scoring guidelines:
- 1.0 = Text is crystal clear, perfectly legible, no ambiguity
- 0.8-0.9 = Text is clear and readable with high certainty
- 0.6-0.7 = Text is readable but some minor uncertainty (slight blur, partial visibility)
- 0.4-0.5 = Text is partially visible or requires inference
- 0.2-0.3 = Text is barely visible or heavily inferred
- 0.0-0.1 = Field not visible or complete guess

JSON_TEMPLATE (you must fill both sections):
{template_json}

Return ONLY valid JSON matching this exact structure.
"""

        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": full_user_text},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{b64_image}"},
                            },
                        ],
                    },
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Parse response
            content = response.choices[0].message.content

            if isinstance(content, list):
                text = "".join(p.text for p in content if hasattr(p, "text"))
            else:
                text = content

            result = json.loads(text)

            # Extract values and confidences
            extracted_values = result.get("fields", {})
            confidence_scores = result.get("confidence_scores", {})

            # Ensure all schema fields are present
            for key in schema.keys():
                if key not in extracted_values:
                    extracted_values[key] = "" if not isinstance(schema[key], list) else []
                if key not in confidence_scores:
                    confidence_scores[key] = 0.0

            # Normalize confidence scores to 0-1 range
            confidence_scores = {
                k: max(0.0, min(1.0, float(v)))
                for k, v in confidence_scores.items()
            }

            return extracted_values, confidence_scores

        except json.JSONDecodeError as e:
            print(f"[OpenAI Extractor] JSON decode error: {e}")
            # Return empty results on error
            return self._empty_results(schema)

        except Exception as e:
            print(f"[OpenAI Extractor] API error: {e}")
            return self._empty_results(schema)

    @staticmethod
    def _image_to_base64(image: Image.Image) -> str:
        """Convert PIL Image to base64 PNG string"""
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    @staticmethod
    def _empty_results(schema: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """Return empty extraction results matching schema"""
        values = {k: ([] if isinstance(v, list) else "") for k, v in schema.items()}
        confidences = {k: 0.0 for k in schema.keys()}
        return values, confidences


class OpenAIEvaluatorAgent:
    """
    Separate agent for evaluating and refining extraction results
    Uses OpenAI to identify issues and suggest corrections
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def evaluate_extraction(
        self,
        image: Image.Image,
        schema: Dict[str, Any],
        extracted_data: Dict[str, Any],
        assessment_report: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluate extraction results and suggest improvements

        Args:
            image: Document image (first page)
            schema: Expected schema
            extracted_data: Current extraction results
            assessment_report: Field assessment report

        Returns:
            Evaluation results with suggested fixes
        """
        b64_image = OpenAIVisionExtractor._image_to_base64(image)

        # Create evaluation template
        eval_template = {
            "overall_quality": "good|fair|poor",
            "critical_issues": [],
            "suggestions": [],
            "corrected_fields": {},
            "confidence_adjustments": {},
            "should_retry": False,
        }

        flagged_fields = assessment_report.get("flagged_field_names", [])
        quality_score = assessment_report.get("quality_score", 0)

        prompt = f"""You are an expert document extraction evaluator.

CURRENT EXTRACTION RESULTS:
{json.dumps(extracted_data, indent=2)}

QUALITY ASSESSMENT:
- Quality Score: {quality_score:.1f}/100
- Flagged Fields: {', '.join(flagged_fields) if flagged_fields else 'None'}

Your task:
1. Review the document image
2. Compare it with the extracted data
3. Identify any obvious errors or missed information
4. Suggest corrections for flagged or incorrect fields

Focus especially on these flagged fields: {', '.join(flagged_fields) if flagged_fields else 'N/A'}

EVALUATION_TEMPLATE:
{json.dumps(eval_template, indent=2)}

Return ONLY valid JSON matching the template.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "You are a rigorous document extraction evaluator. Return only JSON.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{b64_image}"},
                            },
                        ],
                    },
                ],
                temperature=0.0,
                max_tokens=2000,
            )

            content = response.choices[0].message.content
            if isinstance(content, list):
                text = "".join(p.text for p in content if hasattr(p, "text"))
            else:
                text = content

            evaluation = json.loads(text)
            return evaluation

        except Exception as e:
            print(f"[Evaluator] Error: {e}")
            return {
                "overall_quality": "unknown",
                "critical_issues": [str(e)],
                "suggestions": [],
                "corrected_fields": {},
                "confidence_adjustments": {},
                "should_retry": False,
            }
