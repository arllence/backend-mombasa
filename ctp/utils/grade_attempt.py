import uuid
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from pathlib import Path

from .models import Attempt, Certificate


@transaction.atomic
def grade_attempt(attempt: Attempt) -> Attempt:
    """
    Grades an attempt, calculates score & percentage,
    and generates a certificate if passed.
    """

    if attempt.completed_at:
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

    _build_certificate_pdf(
        file_path=file_path,
        learner_name=attempt.learner.email,
        test_title=attempt.test.title,
        score=attempt.percentage,
        cert_number=cert_number,
    )

    certificate = Certificate.objects.create(
        attempt=attempt,
        certificate_number=cert_number,
        pdf=f"certificates/{file_name}",
    )

    return certificate

def generate_certificate_number() -> str:
    return f"CERT-{uuid.uuid4().hex[:10].upper()}"

def _build_certificate_pdf(
    file_path,
    learner_name,
    test_title,
    score,
    cert_number,
):
    c = canvas.Canvas(str(file_path), pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width / 2, height - 150, "Certificate of Completion")

    # Body
    c.setFont("Helvetica", 14)
    c.drawCentredString(
        width / 2,
        height - 220,
        "This certifies that"
    )

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(
        width / 2,
        height - 260,
        learner_name
    )

    c.setFont("Helvetica", 14)
    c.drawCentredString(
        width / 2,
        height - 310,
        f"has successfully passed the test"
    )

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(
        width / 2,
        height - 350,
        test_title
    )

    # Score
    c.setFont("Helvetica", 12)
    c.drawCentredString(
        width / 2,
        height - 410,
        f"Final Score: {score}%"
    )

    # Footer
    c.setFont("Helvetica", 10)
    c.drawString(50, 80, f"Certificate No: {cert_number}")
    c.drawRightString(
        width - 50,
        80,
        f"Issued on: {timezone.now().date()}"
    )

    c.showPage()
    c.save()
