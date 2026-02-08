"""PDF preview and download component."""
from __future__ import annotations
import base64
import streamlit as st


def render_pdf_preview(pdf_bytes: bytes, filename: str = "document.pdf", height: int = 600):
    """Render an inline PDF preview with download button.

    Args:
        pdf_bytes: Raw PDF file bytes
        filename: Download filename
        height: Preview iframe height in pixels
    """
    b64 = base64.b64encode(pdf_bytes).decode("utf-8")

    # Download button
    st.download_button(
        label="📥 Download PDF",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
    )

    # Inline preview
    pdf_display = f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="{height}" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)
