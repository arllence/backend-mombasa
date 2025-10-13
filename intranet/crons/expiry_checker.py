from acl.models import Sendmail
from intranet.models import PlatformAdmin, Document, GeneralDocument, QipsDocument, TrackNotification
from django.db.models import  Q
from datetime import datetime, date, timezone

def KeepEmailTrack(document, emails):
    raw = {
            'recipients': emails,
        }
    model_name = document._meta.model_name.lower()
    if model_name == 'document':
        raw['document'] = document
    elif model_name == 'qipsdocument':
        raw['qips_document'] = document
    elif model_name == 'generaldocument':
        raw['general_document'] = document
    else:
        print(f"[{str(datetime.now(timezone.utc))}] : Unsupported model type")
        raise ValueError(f"Unsupported model type: {model_name}")
        
    TrackNotification.objects.create(
        **raw
    )

    print(f"[{str(datetime.now(timezone.utc))}] : Email Track Saved")


def SetSendMail(emails, subject, message):
    mail = {
                "email" : list(set(emails)), 
                "subject" : subject,
                "message" : message,
                "is_html": False
            }
    Sendmail.objects.create(**mail)

def sendExpiredEmail(document):
    file_name = "Untitled"
    for attr in ["original_file_name", "file_name", "title"]:
        file_name = getattr(document, attr, None)
        if file_name:
            break
    emails = list(PlatformAdmin.objects.all().values_list('admin__email', flat=True))
    emails.append(document.uploaded_by.email)
    subject = f"[INTRANET] Document Expired"
    message = f"Hello. \nDocument: {file_name} is passed it's expiry date \n which is {str(document.expiry_date.strftime('%m/%d/%Y'))}.\nDocument Link: http://172.20.0.42:8003{document.document.url}\n\nRegards,\nINTRANET"

    SetSendMail(emails, subject, message)  

    print(f"[{str(datetime.now(timezone.utc))}] : Expiry Email Sent")

def sendReminderEmail(document, days):
    file_name = "Untitled"
    for attr in ["original_file_name", "file_name", "title"]:
        file_name = getattr(document, attr, None)
        if file_name:
            break
    emails = list(PlatformAdmin.objects.all().values_list('admin__email', flat=True))
    emails.append(document.uploaded_by.email)
    subject = f"[INTRANET] Document Soon Expiring"
    message = f"Hello. \nDocument: {file_name} is expiring in {str(days)} days \n which is on {str(document.expiry_date.strftime('%m/%d/%Y'))}.\nDocument Link: http://172.20.0.42:8003{document.document.url}\n\nRegards,\nINTRANET"

    SetSendMail(emails, subject, message)  
    KeepEmailTrack(document, emails)

    print(f"[{str(datetime.now(timezone.utc))}] : Reminder Email Sent")


def fetchDocuments():
    documents = Document.objects.filter(is_expired=False)
    qips_documents = QipsDocument.objects.filter(is_expired=False)
    general_documents = GeneralDocument.objects.filter(is_expired=False)

    processDocuments(documents)
    processDocuments(qips_documents)
    processDocuments(general_documents)


def processDocuments(documents):
    now = datetime.now(timezone.utc)
    today = date.today()

    print(f"[{str(now)}] : Document Processor called")

    for document in documents:
        if not document.expiry_date:
            continue

        remaining_days = (document.expiry_date - today).days

        if remaining_days < 0:
            document.is_expired = True
            document.save()
            sendExpiredEmail(document)
            continue  # Skip further processing for expired documents

        if remaining_days in [90, 60]:
            sendReminderEmail(document, remaining_days)
            continue

        if remaining_days < 31:
            last_email = TrackNotification.objects.filter(
                Q(document=document.id) | 
                Q(qips_document=document.id) | 
                Q(general_document=document.id)
            ).order_by('-date_created').first()

            if not last_email or (now - last_email.date_created).days > 6:
                sendReminderEmail(document, remaining_days)