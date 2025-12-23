from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def export_pdf(resume: dict, path: str):
    c = canvas.Canvas(path, pagesize=A4)
    y = 800

    def draw(text):
        nonlocal y
        c.drawString(40, y, text)
        y -= 14

    if resume.get("summary"):
        draw(resume["summary"])
        y -= 20

    for exp in resume.get("experience", []):
        draw(exp["title"])
        y -= 10
        for b in exp.get("bullets", []):
            draw(f"- {b}")
        y -= 10

    if resume.get("skills"):
        draw("Skills:")
        draw(", ".join(resume["skills"]))

    c.save()
