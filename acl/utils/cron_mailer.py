import datetime
import time
import requests
from django.db.models import Q
from acl import models
from django.core.mail import send_mail, EmailMessage, BadHeaderError
# exec(open('acl/utils/cron_mailer.py').read())
import re

def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def get_emails():
    timestamp = str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))
    print(f"[{timestamp}] Fetching emails ...")
    emails = models.Sendmail.objects.filter(Q(status='PENDING') | Q(status='FAILED'))

    for email in emails:
        email.status = 'FETCHED'
        email.save()

    print(f"[{timestamp}] Got {len(emails)} emails ...")

    if len(emails) > 0:
        main(emails)
    
def get_fetched():
    timestamp = str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))
    print(f"[{timestamp}] Fetching emails ...")
    emails = models.Sendmail.objects.filter(Q(status='FETCHED'))

    print(f"[{timestamp}] Got {len(emails)} emails ...")

    if len(emails) > 0:
        main(emails)

def main(emails):
    timestamp = str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))
    print(f"[{timestamp}] Main Fn Starting...")
    count = 0
      
    for target in emails:
		
        count += 1
        is_html = target.is_html
        subject = target.subject
        message = target.message
        email = target.email
        timestamp = str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))

        try:
            email = [x for x in email if is_valid_email(x)]
        except:
            print(f'(EMAIL VALIDATION)-{timestamp}-An error occurred while validating emails')

        if not is_html:
            try:
                send_mail(subject, message, 'notification@akhskenya.org', email, fail_silently=False)
                target.status = "SENT"
                target.save()
                print(f'(PLAIN)-<200>-{timestamp}-{str(email)}')
            except BadHeaderError:
                print(f'(PLAIN)-<400>-{timestamp}-{str(email)}: Invalid header found.')
            except Exception as e:
                print(f'(PLAIN)-<500>-{timestamp}-An error occurred: {str(e)}')
        else:
            email_to_send = EmailMessage(
                subject,
                message,
                'notification@akhskenya.org',
                email
            )
            email_to_send.content_subtype = 'html'  # Set the content type to HTML
            try:
                email_to_send.send(fail_silently=False)
                target.status = "SENT"
                target.save()
                print(f'(HTML)-<200>-{timestamp}-{str(email)}')
            except Exception as e:
                print(f'(HTML)-<500>-{timestamp}-An error occurred: {str(e)}')
			
        time.sleep(1)

    timestamp = str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))
    print(f">>> Sent {count} Emails | {timestamp}")


# get_emails()
