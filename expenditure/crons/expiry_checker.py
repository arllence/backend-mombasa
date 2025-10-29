from acl.models import Sendmail
from cms.models import Contract, PlatformAdmin, TrackNotification
from django.db.models import  Q
from datetime import datetime, date, timezone

def KeepEmailTrack(contract, emails):
    TrackNotification.objects.create(
        recipients=emails,
        contract=contract
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

def sendExpiredEmail(contract):
    emails = list(PlatformAdmin.objects.all().values_list('admin__email', flat=True))
    emails.append(contract.created_by.email)
    subject = f"[CMS] Contract {contract.uid} Expired"
    message = f"Hello. \nContract of id: {contract.uid} is passed it's expiry date \n which is {str(contract.expiry_date.strftime('%m/%d/%Y'))}.\n\nRegards,\nCMS"

    SetSendMail(emails, subject, message)  

    print(f"[{str(datetime.now(timezone.utc))}] : Expiry Email Sent")

def sendReminderEmail(contract, days):
    emails = list(PlatformAdmin.objects.all().values_list('admin__email', flat=True))
    emails.append(contract.created_by.email)
    subject = f"[CMS] Contract {contract.uid} Soon Expiring"
    message = f"Hello. \nContract of id: {contract.uid} is expiring in {str(days)} days \n which is on {str(contract.expiry_date.strftime('%m/%d/%Y'))}.\n\nRegards,\nCMS"

    SetSendMail(emails, subject, message)  
    KeepEmailTrack(contract, emails)

    print(f"[{str(datetime.now(timezone.utc))}] : Reminder Email Sent")

def processContracts():
    now = datetime.now(timezone.utc)
    today = date.today()

    print(f"[{str(now)}] : Processor called")

    contracts = Contract.objects.filter(is_expired=False)

    for contract in contracts:
        remaining_days = (contract.expiry_date - today).days

        if remaining_days < 0:
            contract.is_expired = True
            contract.save()
            sendExpiredEmail(contract)
            continue  # Skip further processing for expired contracts

        if remaining_days in [90, 60]:
            sendReminderEmail(contract, remaining_days)
            continue

        if remaining_days < 31:
            last_email = TrackNotification.objects.filter(
                contract=contract).order_by('-date_created').first()

            if not last_email or (now - last_email.date_created).days > 6:
                sendReminderEmail(contract, remaining_days)