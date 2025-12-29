"""
🧠 Gradio Interface for Agentic OCR System
Simple web UI for document processing with field assessment and flagging
"""

import os
import json
from typing import Dict, Any, Tuple

import gradio as gr
import pandas as pd

# Import agentic OCR system
from mortgage_core import (
    MORTGAGE_DOC_TYPES,
    run_agentic_pipeline,
    load_document_as_images,
)


def format_quality_score(score: float) -> str:
    """Format quality score with color and emoji"""
    if score >= 80:
        return f"🎉 {score:.1f}/100 (Excellent)"
    elif score >= 60:
        return f"👍 {score:.1f}/100 (Good)"
    elif score >= 40:
        return f"⚠️ {score:.1f}/100 (Fair)"
    else:
        return f"❌ {score:.1f}/100 (Poor)"


def format_field_status(status: str) -> str:
    """Format field status with emoji"""
    status_map = {
        "filled": "✅ Filled",
        "unfilled": "⚠️ Unfilled",
        "low_confidence": "⚠️ Low Confidence",
        "invalid": "❌ Invalid",
        "needs_review": "🔍 Needs Review",
    }
    return status_map.get(status, status)


def process_document(
    pdf_file,
    doc_type: str,
    use_evaluator: bool,
    required_fields_text: str,
    api_key: str,
    progress=gr.Progress(),
) -> Tuple[str, str, str, pd.DataFrame, str]:
    """
    Process document with agentic OCR

    Returns:
        - Summary HTML
        - Quality metrics HTML
        - Flagged fields HTML
        - Field details DataFrame
        - Raw JSON
    """
    # Validate API key
    if not api_key or not api_key.strip():
        return (
            "❌ Error: OpenAI API key is required",
            "",
            "",
            pd.DataFrame(),
            "",
        )

    # Set API key
    os.environ["OPENAI_API_KEY"] = api_key.strip()

    # Validate file
    if pdf_file is None:
        return (
            "❌ Error: Please upload a document",
            "",
            "",
            pd.DataFrame(),
            "",
        )

    try:
        progress(0.1, desc="Loading document...")

        # Parse required fields
        required_fields = None
        if required_fields_text and required_fields_text.strip():
            required_fields = [
                f.strip()
                for f in required_fields_text.split(",")
                if f.strip()
            ]

        # Determine doc type
        override_doc_type = None if doc_type == "Auto-detect" else doc_type

        progress(0.2, desc="Running agentic OCR...")

        # Run agentic OCR
        result = run_agentic_pipeline(
            path=pdf_file.name,
            override_doc_type_id=override_doc_type,
            use_evaluator=use_evaluator,
            required_fields=required_fields,
        )

        progress(0.9, desc="Formatting results...")

        # Extract data
        classification = result.get("classification", {})
        assessment = result.get("assessment_report", {})
        quality_metrics = result.get("quality_metrics", {})
        flagged_fields = result.get("flagged_fields", [])
        field_details = assessment.get("field_details", {})

        # Build summary HTML
        summary_html = f"""
        <div style="padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; margin-bottom: 20px;">
            <h2 style="margin: 0 0 10px 0;">📄 Document Analysis Complete</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px;">
                <div><strong>Document Type:</strong> {classification.get('doc_title', 'Unknown')}</div>
                <div><strong>Classification Confidence:</strong> {classification.get('confidence', 0):.0%}</div>
                <div><strong>Total Pages:</strong> {result.get('total_pages', 0)}</div>
                <div><strong>Total Fields:</strong> {assessment.get('total_fields', 0)}</div>
            </div>
        </div>
        """

        # Build quality metrics HTML
        quality_score = quality_metrics.get("quality_score", 0)
        completion_rate = quality_metrics.get("completion_rate", 0)
        avg_confidence = quality_metrics.get("average_confidence", 0)

        quality_html = f"""
        <div style="padding: 20px; background: #f8f9fa; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="margin-top: 0;">📊 Quality Metrics</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-top: 15px;">
                <div style="text-align: center; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="font-size: 28px; font-weight: bold; color: {'#10b981' if quality_score >= 60 else '#ef4444'};">
                        {quality_score:.1f}/100
                    </div>
                    <div style="color: #6b7280; margin-top: 5px;">Quality Score</div>
                </div>
                <div style="text-align: center; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="font-size: 28px; font-weight: bold; color: {'#10b981' if completion_rate >= 70 else '#ef4444'};">
                        {completion_rate:.1f}%
                    </div>
                    <div style="color: #6b7280; margin-top: 5px;">Completion Rate</div>
                </div>
                <div style="text-align: center; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="font-size: 28px; font-weight: bold; color: {'#10b981' if avg_confidence >= 0.7 else '#ef4444'};">
                        {avg_confidence:.2f}
                    </div>
                    <div style="color: #6b7280; margin-top: 5px;">Avg Confidence</div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 10px; margin-top: 15px;">
                <div style="text-align: center;">
                    <div style="font-size: 24px; color: #10b981;">✅ {assessment.get('filled_fields', 0)}</div>
                    <div style="font-size: 12px; color: #6b7280;">Filled</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; color: #f59e0b;">⚠️ {assessment.get('unfilled_fields', 0)}</div>
                    <div style="font-size: 12px; color: #6b7280;">Unfilled</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; color: #f59e0b;">⚠️ {assessment.get('low_confidence_fields', 0)}</div>
                    <div style="font-size: 12px; color: #6b7280;">Low Confidence</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; color: #ef4444;">❌ {assessment.get('invalid_fields', 0)}</div>
                    <div style="font-size: 12px; color: #6b7280;">Invalid</div>
                </div>
            </div>
        </div>
        """

        # Build flagged fields HTML
        if flagged_fields:
            flagged_html = f"""
            <div style="padding: 20px; background: #fef3c7; border-radius: 10px; border-left: 4px solid #f59e0b;">
                <h3 style="margin-top: 0; color: #92400e;">⚠️ Flagged Fields ({len(flagged_fields)})</h3>
                <p style="color: #78350f; margin-bottom: 15px;">These fields need attention:</p>
                <div style="display: grid; gap: 10px;">
            """
            for field_name in flagged_fields[:15]:  # Show first 15
                field_info = field_details.get(field_name, {})
                status = field_info.get("status", "unknown")
                confidence = field_info.get("confidence", 0.0)
                notes = field_info.get("notes", "")

                flagged_html += f"""
                <div style="background: white; padding: 10px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{field_name}</strong>
                        <span style="margin-left: 10px; color: #6b7280;">{format_field_status(status)}</span>
                        {f'<div style="font-size: 12px; color: #6b7280; margin-top: 4px;">{notes}</div>' if notes else ''}
                    </div>
                    <div style="text-align: right;">
                        <div style="font-weight: bold; color: {'#10b981' if confidence >= 0.7 else '#ef4444'};">
                            {confidence:.2f}
                        </div>
                        <div style="font-size: 11px; color: #6b7280;">confidence</div>
                    </div>
                </div>
                """
            if len(flagged_fields) > 15:
                flagged_html += f'<div style="text-align: center; color: #78350f; padding: 10px;">... and {len(flagged_fields) - 15} more</div>'
            flagged_html += "</div></div>"
        else:
            flagged_html = """
            <div style="padding: 20px; background: #d1fae5; border-radius: 10px; border-left: 4px solid #10b981;">
                <h3 style="margin-top: 0; color: #065f46;">✅ All Fields Look Good!</h3>
                <p style="color: #047857;">No fields were flagged for review.</p>
            </div>
            """

        # Build DataFrame for field details
        df_data = []
        for field_name, field_info in field_details.items():
            df_data.append(
                {
                    "Field Name": field_name,
                    "Value": str(field_info.get("value", ""))[:50],  # Truncate long values
                    "Confidence": f"{field_info.get('confidence', 0):.2f}",
                    "Status": format_field_status(field_info.get("status", "unknown")),
                }
            )

        df = pd.DataFrame(df_data)

        # Format raw JSON
        raw_json = json.dumps(
            {
                "classification": classification,
                "extracted_data": result.get("extracted_data", {}),
                "confidence_scores": result.get("confidence_scores", {}),
                "assessment_report": assessment,
                "quality_metrics": quality_metrics,
            },
            indent=2,
        )

        progress(1.0, desc="Complete!")

        return (
            summary_html,
            quality_html,
            flagged_html,
            df,
            raw_json,
        )

    except Exception as e:
        import traceback

        error_msg = f"❌ Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        return (
            f'<div style="padding: 20px; background: #fee2e2; color: #991b1b; border-radius: 10px;">{error_msg}</div>',
            "",
            "",
            pd.DataFrame(),
            "",
        )


def create_gradio_interface():
    """Create Gradio interface for agentic OCR"""

    # Get document types for dropdown
    doc_type_choices = ["Auto-detect"] + list(MORTGAGE_DOC_TYPES.keys())

    with gr.Blocks(
        theme=gr.themes.Soft(),
        title="🧠 Agentic OCR System",
        css="""
        .gradio-container {
            max-width: 1200px !important;
        }
        """,
    ) as demo:
        gr.Markdown(
            """
        # 🧠 Agentic OCR System
        ### Intelligent Document Processing with Field Assessment & Flagging

        Upload a document to extract fields with **automatic quality assessment**, **confidence scoring**,
        and **intelligent flagging** of unfilled or low-confidence fields.
        """
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📤 Upload & Configure")

                # File upload
                file_input = gr.File(
                    label="Upload Document (PDF or Image)",
                    file_types=[".pdf", ".png", ".jpg", ".jpeg"],
                    type="filepath",
                )

                # API Key
                api_key_input = gr.Textbox(
                    label="OpenAI API Key",
                    placeholder="sk-...",
                    type="password",
                    info="Your OpenAI API key (required)",
                )

                # Document type
                doc_type_input = gr.Dropdown(
                    choices=doc_type_choices,
                    value="Auto-detect",
                    label="Document Type",
                    info="Select document type or auto-detect",
                )

                # Required fields
                required_fields_input = gr.Textbox(
                    label="Required Fields (Optional)",
                    placeholder="account_number, iban, account_holder_name",
                    info="Comma-separated list of required field names",
                    lines=2,
                )

                # Use evaluator
                use_evaluator_input = gr.Checkbox(
                    value=True,
                    label="Use Evaluator Agent",
                    info="Run additional quality check (slower but more thorough)",
                )

                # Process button
                process_btn = gr.Button(
                    "🚀 Process Document",
                    variant="primary",
                    size="lg",
                )

            with gr.Column(scale=2):
                gr.Markdown("### 📊 Results")

                # Summary
                summary_output = gr.HTML(label="Summary")

                # Quality metrics
                quality_output = gr.HTML(label="Quality Metrics")

                # Flagged fields
                flagged_output = gr.HTML(label="Flagged Fields")

        # Detailed results tabs
        with gr.Tabs():
            with gr.Tab("📋 All Fields"):
                fields_table = gr.Dataframe(
                    headers=["Field Name", "Value", "Confidence", "Status"],
                    label="Field Details",
                    wrap=True,
                )

            with gr.Tab("📄 Raw JSON"):
                json_output = gr.Code(
                    label="Raw JSON Result",
                    language="json",
                    lines=20,
                )

        # Examples
        gr.Markdown("### 💡 Tips")
        gr.Markdown(
            """
        - **Quality Score**: Overall extraction quality (0-100). Aim for 60+.
        - **Completion Rate**: Percentage of fields successfully filled.
        - **Confidence Score**: How certain the AI is about each field (0-1).
        - **Flagged Fields**: Fields that need your attention (unfilled, low confidence, or invalid).
        - **Required Fields**: Specify critical fields to ensure they're checked.
        """
        )

        # Wire up the process button
        process_btn.click(
            fn=process_document,
            inputs=[
                file_input,
                doc_type_input,
                use_evaluator_input,
                required_fields_input,
                api_key_input,
            ],
            outputs=[
                summary_output,
                quality_output,
                flagged_output,
                fields_table,
                json_output,
            ],
        )

    return demo


# For Google Colab
def launch_gradio(share=True, debug=False):
    """Launch Gradio interface"""
    demo = create_gradio_interface()
    demo.launch(share=share, debug=debug)


if __name__ == "__main__":
    demo = create_gradio_interface()
    demo.launch()
