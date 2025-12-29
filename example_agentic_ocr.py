#!/usr/bin/env python3
"""
Example: Agentic OCR with Field Assessment and Flagging

This script demonstrates how to use the agentic OCR system to:
1. Extract fields from a document
2. Auto-assess field quality
3. Flag unfilled/low-confidence/invalid fields
4. Get comprehensive quality metrics
"""

import json
import os
import sys

from mortgage_core import run_agentic_pipeline


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_field_status(field_name: str, field_detail: dict, show_value: bool = False):
    """Print formatted field status"""
    status = field_detail.get("status", "unknown")
    confidence = field_detail.get("confidence", 0.0)
    value = field_detail.get("value", "")
    notes = field_detail.get("notes", "")

    # Status emoji
    status_emoji = {
        "filled": "✅",
        "unfilled": "⚠️",
        "low_confidence": "⚠️",
        "invalid": "❌",
        "needs_review": "🔍",
    }
    emoji = status_emoji.get(status, "❓")

    # Print
    print(f"  {emoji} {field_name:<30} {status:<15} (conf: {confidence:.2f})", end="")
    if show_value and value:
        print(f" → {str(value)[:30]}", end="")
    if notes:
        print(f"\n     Note: {notes}", end="")
    print()


def main():
    """Main example function"""

    # Check API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("\nSet it with:")
        print("  export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)

    # Get document path from command line or use default
    if len(sys.argv) > 1:
        doc_path = sys.argv[1]
    else:
        print("Usage: python example_agentic_ocr.py <document_path>")
        print("\nExample:")
        print("  python example_agentic_ocr.py bank_statement.pdf")
        sys.exit(1)

    # Verify file exists
    if not os.path.exists(doc_path):
        print(f"❌ Error: File not found: {doc_path}")
        sys.exit(1)

    print_section("🧠 AGENTIC OCR EXAMPLE")
    print(f"\nDocument: {doc_path}")

    # Optional: Define required fields for this document type
    required_fields = [
        "account_number",
        "iban",
        "account_holder_name",
        "opening_balance",
        "closing_balance",
    ]

    print("\n📋 Configuration:")
    print(f"  - Required fields: {len(required_fields)}")
    print(f"  - Evaluator enabled: Yes")
    print(f"  - Max retry attempts: 3")

    # Run agentic OCR pipeline
    try:
        result = run_agentic_pipeline(
            path=doc_path,
            # override_doc_type_id="current_acct_statements",  # Optional: force doc type
            use_evaluator=True,  # Enable evaluator agent
            required_fields=required_fields,
        )
    except Exception as e:
        print(f"\n❌ Error during OCR: {e}")
        sys.exit(1)

    # Extract key results
    classification = result.get("classification", {})
    assessment = result.get("assessment_report", {})
    quality_metrics = result.get("quality_metrics", {})
    flagged_fields = result.get("flagged_fields", [])
    evaluation = result.get("evaluation")

    # Display Classification
    print_section("📄 DOCUMENT CLASSIFICATION")
    print(f"  Type: {classification.get('doc_type_id')}")
    print(f"  Title: {classification.get('doc_title')}")
    print(f"  Confidence: {classification.get('confidence', 0):.2%}")
    print(f"  Rationale: {classification.get('rationale')}")

    # Display Quality Metrics
    print_section("📊 QUALITY METRICS")
    print(f"  Quality Score:     {quality_metrics.get('quality_score', 0):.1f}/100")
    print(f"  Completion Rate:   {quality_metrics.get('completion_rate', 0):.1f}%")
    print(f"  Avg Confidence:    {quality_metrics.get('average_confidence', 0):.2f}")
    print()
    print(f"  Total Fields:      {assessment.get('total_fields', 0)}")
    print(f"  ✅ Filled:         {assessment.get('filled_fields', 0)}")
    print(f"  ⚠️  Unfilled:       {assessment.get('unfilled_fields', 0)}")
    print(f"  ⚠️  Low Confidence: {assessment.get('low_confidence_fields', 0)}")
    print(f"  ❌ Invalid:        {assessment.get('invalid_fields', 0)}")

    # Display Flagged Fields
    if flagged_fields:
        print_section(f"⚠️  FLAGGED FIELDS ({len(flagged_fields)})")
        print("  These fields need attention:\n")

        field_details = assessment.get("field_details", {})
        for field_name in flagged_fields[:15]:  # Show first 15
            field_detail = field_details.get(field_name, {})
            print_field_status(field_name, field_detail, show_value=False)

        if len(flagged_fields) > 15:
            print(f"\n  ... and {len(flagged_fields) - 15} more")

    # Display All Fields (Sample)
    print_section("📋 ALL FIELDS (Sample)")
    print("  Showing first 10 fields:\n")

    field_details = assessment.get("field_details", {})
    for i, (field_name, field_detail) in enumerate(field_details.items()):
        if i >= 10:
            break
        print_field_status(field_name, field_detail, show_value=True)

    if len(field_details) > 10:
        print(f"\n  ... and {len(field_details) - 10} more fields")

    # Display Evaluator Feedback
    if evaluation:
        print_section("🔍 EVALUATOR FEEDBACK")
        print(f"  Overall Quality: {evaluation.get('overall_quality', 'unknown')}")

        critical_issues = evaluation.get("critical_issues", [])
        if critical_issues:
            print(f"\n  ⚠️  Critical Issues ({len(critical_issues)}):")
            for issue in critical_issues[:5]:
                print(f"    - {issue}")

        suggestions = evaluation.get("suggestions", [])
        if suggestions:
            print(f"\n  💡 Suggestions ({len(suggestions)}):")
            for suggestion in suggestions[:5]:
                print(f"    - {suggestion}")

        should_retry = evaluation.get("should_retry", False)
        if should_retry:
            print("\n  🔄 Evaluator recommends retry with adjusted parameters")

    # Save detailed results to file
    output_file = "ocr_result.json"
    print_section("💾 SAVING RESULTS")
    print(f"  Saving detailed results to: {output_file}")

    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"  ✅ Saved successfully")

    # Summary
    print_section("✅ SUMMARY")

    quality_score = quality_metrics.get("quality_score", 0)
    if quality_score >= 80:
        print("  🎉 Excellent extraction quality!")
    elif quality_score >= 60:
        print("  👍 Good extraction quality")
    elif quality_score >= 40:
        print("  ⚠️  Fair extraction - review flagged fields")
    else:
        print("  ❌ Poor extraction - manual review recommended")

    print(f"\n  Quality Score: {quality_score:.1f}/100")
    print(f"  Flagged Fields: {len(flagged_fields)}")

    if flagged_fields:
        print("\n  Next steps:")
        print("  1. Review flagged fields in detail")
        print("  2. Check if better image quality would help")
        print("  3. Verify document type matches schema")
        print("  4. Consider manual data entry for critical unfilled fields")

    print()


if __name__ == "__main__":
    main()
