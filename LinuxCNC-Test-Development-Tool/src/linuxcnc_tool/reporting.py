"""PDF report export."""
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
from reportlab.lib.units import mm

def create_pdf(path: str, title: str, report_text: str) -> None:
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    story = [Paragraph(title, styles["Title"]),
             Paragraph(f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}", styles["Normal"]),
             Spacer(1, 8*mm),
             Preformatted(report_text, styles["Code"], maxLineLength=105)]
    doc.build(story)
