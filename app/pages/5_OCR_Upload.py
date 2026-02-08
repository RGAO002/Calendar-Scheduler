import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.components.sidebar import render_student_selector

st.set_page_config(page_title="OCR Upload - Evlin", layout="wide")
st.title("🔍 OCR Document Upload")

render_student_selector()
st.markdown("---")

st.markdown("""
Upload a document (PDF, PNG, JPG) to extract text using OCR.
The extracted text can be used to generate practice problems or course materials.
""")

uploaded_file = st.file_uploader(
    "Choose a file",
    type=["pdf", "png", "jpg", "jpeg", "tiff"],
    help="Supported formats: PDF, PNG, JPG, JPEG, TIFF",
)

if uploaded_file:
    st.markdown(f"**File:** {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📄 Original")
        if uploaded_file.type == "application/pdf":
            import base64
            b64 = base64.b64encode(uploaded_file.read()).decode()
            uploaded_file.seek(0)
            st.markdown(
                f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="500"></iframe>',
                unsafe_allow_html=True,
            )
        else:
            st.image(uploaded_file, use_container_width=True)

    with col2:
        st.subheader("📝 Extracted Text")

        if st.button("Extract Text", type="primary"):
            with st.spinner("Processing document with OCR..."):
                try:
                    from ocr.processor import OCRProcessor

                    processor = OCRProcessor()
                    file_bytes = uploaded_file.read()
                    uploaded_file.seek(0)

                    result = processor.process(file_bytes, uploaded_file.name)

                    st.success(f"Extraction complete! Method: {result.method}, Confidence: {result.confidence:.1f}%")

                    # Store in session state for editing
                    st.session_state["ocr_result"] = result.text
                    st.session_state["ocr_method"] = result.method

                except Exception as e:
                    st.error(f"OCR Error: {e}")
                    st.info("Make sure OCR dependencies are installed: `pip install easyocr PyMuPDF`")

        # Display extracted text
        if "ocr_result" in st.session_state:
            extracted = st.text_area(
                "Edit extracted text:",
                value=st.session_state["ocr_result"],
                height=400,
            )

            col_save, col_generate = st.columns(2)
            with col_save:
                if st.button("💾 Save to Library"):
                    try:
                        from services.minio_client import get_minio, ensure_bucket
                        from db.queries import insert_ocr_document
                        import io
                        import uuid

                        # Upload original to MinIO
                        ensure_bucket("evlin-uploads")
                        file_bytes = uploaded_file.read()
                        uploaded_file.seek(0)
                        obj_key = f"ocr/{uuid.uuid4()}/{uploaded_file.name}"
                        get_minio().put_object(
                            "evlin-uploads", obj_key,
                            io.BytesIO(file_bytes), len(file_bytes),
                        )

                        # Save record to Supabase
                        insert_ocr_document({
                            "original_filename": uploaded_file.name,
                            "minio_key": obj_key,
                            "extracted_text": extracted,
                            "confidence": 95.0 if st.session_state.get("ocr_method") == "pymupdf" else 85.0,
                            "status": "completed",
                        })
                        st.success("Saved to library!")
                    except Exception as e:
                        st.error(f"Save error: {e}")

            with col_generate:
                if st.button("📝 Generate Problems from Text"):
                    st.info("Navigate to the PDF Generator page to create practice problems from this text.")

# OCR History
st.markdown("---")
st.subheader("📋 Recent OCR Documents")
try:
    from db.queries import get_ocr_documents
    docs = get_ocr_documents(limit=10)
    if docs:
        for doc in docs:
            with st.expander(f"{doc['original_filename']} — {doc['created_at'][:10]}"):
                st.caption(f"Status: {doc['status']} | Confidence: {doc.get('confidence', 'N/A')}%")
                if doc.get("extracted_text"):
                    st.text(doc["extracted_text"][:500] + ("..." if len(doc.get("extracted_text", "")) > 500 else ""))
    else:
        st.caption("No OCR documents yet.")
except Exception:
    st.caption("OCR history unavailable.")
