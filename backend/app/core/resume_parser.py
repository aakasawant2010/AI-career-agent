from io import BytesIO

from docx import Document
from pypdf import PdfReader


def parse_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))

    text = []

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text.append(page_text)

    return "\n".join(text).strip()


def parse_docx(file_bytes: bytes) -> str:
    document = Document(BytesIO(file_bytes))

    text = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            text.append(paragraph.text)

    return "\n".join(text).strip()


def parse_resume(
    file_bytes: bytes,
    file_type: str,
) -> str:
    file_type = file_type.lower()

    if file_type == "pdf":
        return parse_pdf(file_bytes)

    if file_type == "docx":
        return parse_docx(file_bytes)

    raise ValueError(
        "Unsupported file type. Only PDF and DOCX are supported."
    )