import uuid
from django.db import transaction
from django.utils import timezone

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from django.utils import timezone
from pathlib import Path
from django.conf import settings

from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF


from acl.models import Hods
from ctp.models import Attempt, Certificate


@transaction.atomic
def grade_processor(attempt: Attempt) -> Attempt:
    """
    Grades an attempt, calculates score & percentage,
    and generates a certificate if passed.
    """

    if attempt.completed_at and attempt.passed:
        return attempt  # already graded

    answers = attempt.answers.select_related(
        "question"
    )

    total_marks = 0
    score = 0

    for answer in answers:
        marks = answer.question.marks
        total_marks += marks
        if answer.is_correct:
            score += marks

    percentage = (score / total_marks) * 100 if total_marks > 0 else 0

    attempt.score = score
    attempt.percentage = round(percentage, 2)
    attempt.passed = percentage >= attempt.test.pass_mark
    attempt.completed_at = timezone.now()
    attempt.save()

    if attempt.passed:
        generate_certificate(attempt)

    return attempt


def generate_certificate(attempt: Attempt) -> Certificate:
    """
    Generates a PDF certificate for a passed attempt.
    """

    if hasattr(attempt, "certificate"):
        return attempt.certificate  # avoid duplicates

    cert_number = generate_certificate_number()

    certificates_dir = Path(settings.MEDIA_ROOT) / "certificates"
    certificates_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"{cert_number}.pdf"
    file_path = certificates_dir / file_name

    def get_hod(attempt):
        hod = Hods.objects.filter(department=attempt.test.training.department).first()
        if hod:
            return f"{hod.hod.first_name.capitalize()} {hod.hod.last_name.capitalize()}"
        return ""
    
    build_certificate_pdf(
        file_path=file_path,
        learner_name=f"{attempt.learner.first_name.capitalize()} {attempt.learner.last_name.capitalize()}",
        course_title=attempt.test.training.title,
        certificate_code=cert_number,
        org_name="Aga Khan Hospital, Kisumu",
        hod_name=get_hod(attempt),
        hod_department=attempt.test.training.department.name,
        logo_path=settings.BASE_DIR / "ctp/assets/logo.png",
        # signature_path=settings.BASE_DIR / "assets/signature.png",
        issue_date=attempt.completed_at.date(),
    )


    certificate = Certificate.objects.create(
        attempt=attempt,
        certificate_number=cert_number,
        pdf=f"certificates/{file_name}",
    )

    return certificate

def generate_certificate_number() -> str:
    return f"CERT-{uuid.uuid4().hex[:10].upper()}"

def draw_qr_code(c, verification_url, x, y, size=80):
    qr_code = qr.QrCodeWidget(verification_url)
    bounds = qr_code.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]

    d = Drawing(
        size,
        size,
        transform=[size / width, 0, 0, size / height, 0, 0],
    )
    d.add(qr_code)
    renderPDF.draw(d, c, x, y)


def build_certificate_pdf(
    file_path,
    learner_name,
    course_title,
    certificate_code,
    org_name,
    hod_name,
    hod_department,
    logo_path,
    signature_path=None,
    issue_date=None, ):
    issue_date = issue_date or timezone.now().date()

    c = canvas.Canvas(str(file_path), pagesize=landscape(A4))
    width, height = landscape(A4)

    red = HexColor("#d32f2f")

    # ------------------------------------------------
    # Outer red border
    # ------------------------------------------------
    margin = 15 * mm
    c.setStrokeColor(red)
    c.setLineWidth(2)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)

    # ------------------------------------------------
    # Header
    # ------------------------------------------------
    if logo_path and Path(logo_path).exists():
        logo_width = 25 * mm
        c.drawImage(
            ImageReader(logo_path),
            width / 2 - logo_width / 2,
            height - 45 * mm,
            width=logo_width,
            preserveAspectRatio=True,
            mask="auto"
        )

    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, height - 55 * mm, org_name)

    # Date & Certificate code
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(
        margin + 5 * mm,
        height - 30 * mm,
        f"Date of Completion: {issue_date.strftime('%d %B %Y')}"
    )

    c.drawRightString(
        width - margin - 5 * mm,
        height - 30 * mm,
        f"Certificate Code: {certificate_code}"
    )

    # ------------------------------------------------
    # Main Title
    # ------------------------------------------------
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width / 2, height - 80 * mm, "Certificate of Completion")

    c.setFont("Helvetica-Oblique", 13)
    c.drawCentredString(
        width / 2,
        height - 95 * mm,
        "For successfully completing the following eLearning Module:"
    )

    # ------------------------------------------------
    # Course title with red lines
    # ------------------------------------------------
    y_course = height - 115 * mm

    top_offset = 25
    bottom_offset = 19

    c.line(width / 2 - 80 * mm, y_course + top_offset,
        width / 2 + 80 * mm, y_course + top_offset)

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, y_course, course_title)

    c.line(width / 2 - 80 * mm, y_course - bottom_offset,
        width / 2 + 80 * mm, y_course - bottom_offset)

    # ------------------------------------------------
    # Presented to
    # ------------------------------------------------
    c.setFont("Helvetica-Oblique", 14)
    c.drawCentredString(width / 2, height - 130 * mm, "Presented to:")

    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 140 * mm, learner_name)

    # ------------------------------------------------
    # Signature & Authority
    # ------------------------------------------------
    if signature_path and Path(signature_path).exists():
        c.drawImage(
            ImageReader(signature_path),
            width / 2 - 25 * mm,
            45 * mm,
            width=50 * mm,
            height=20 * mm,
            mask="auto"
        )

    # ------------------------------------------------
    # QR Code
    # ------------------------------------------------

    qr_size = 35 * mm
    qr_y = 32 * mm  # adjust if you want it higher or lower

    verification_url = f"https://apps.akhskenya.org:9014/certificate/verify/{certificate_code}"

    draw_qr_code(
        c,
        verification_url,
        x=width / 2 - qr_size / 2,
        y=qr_y,
        size=qr_size
    )
    
    # Signature line

    c.setStrokeColor(red)
    c.line(width / 2 - 40 * mm, 30 * mm, width / 2 + 40 * mm, 30 * mm)

    c.setFont("Helvetica-Oblique", 12)
    c.drawCentredString(width / 2, 25 * mm, hod_name)
    c.drawCentredString(width / 2, 19 * mm, hod_department)

    c.showPage()
    c.save()
