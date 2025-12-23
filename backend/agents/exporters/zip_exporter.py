import zipfile
import tempfile
from .txt_exporter import export_txt
from .docx_exporter import export_docx
from .pdf_exporter import export_pdf

def export_zip(resume: dict, zip_path: str):
    with tempfile.TemporaryDirectory() as tmp:
        txt = export_txt(resume)
        docx_path = f"{tmp}/resume.docx"
        pdf_path = f"{tmp}/resume.pdf"

        export_docx(resume, docx_path)
        export_pdf(resume, pdf_path)

        with zipfile.ZipFile(zip_path, "w") as z:
            z.writestr("resume.txt", txt)
            z.write(docx_path, "resume.docx")
            z.write(pdf_path, "resume.pdf")
