from io import BytesIO
import zipfile

from agents.exporters.txt_exporter import export_txt
from agents.exporters.docx_exporter import export_docx
from agents.templates.pdf_renderer import render_pdf
from agents.resume_formatter import format_resume_sections


def export_zip(
    rewritten_resume: dict,
    template_id: str,
) -> BytesIO:

    buffer = BytesIO()
    sections = format_resume_sections(rewritten_resume)

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        # PDF
        pdf = render_pdf(sections, template_id)
        z.writestr("resume.pdf", pdf.getvalue())

        # DOCX
        z.writestr("resume.docx", export_docx(rewritten_resume))

        # TXT
        z.writestr("resume.txt", export_txt(rewritten_resume))

    buffer.seek(0)
    return buffer
