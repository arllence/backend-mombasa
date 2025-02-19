import datetime
import time
import requests
from django.db.models import Q
from acl import models
from django.core.mail import send_mail, EmailMessage, BadHeaderError
# exec(open('acl/utils/cron_mailer.py').read())

def get_emails():
    print("into get emails")
    emails = models.Sendmail.objects.filter(Q(status='PENDING') | Q(status='FAILED'))
    print("got emails", len(emails))
    main(emails)

def main(emails):
    print("Main starting...")
    count = 0
      
    for target in emails:
		
        count += 1
        is_html = target.is_html
        subject = target.subject
        message = target.message
        email = target.email
        timestamp = str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))


        if not is_html:
            try:
                send_mail(subject, message, 'notification@akhskenya.org', email, fail_silently=False)
                target.status = "SENT"
                target.save()
                print(f'{count}-{timestamp}-<200>-{str(email)}: Email sent successfully.')
            except BadHeaderError:
                print(f'{count}-{timestamp}-<400>-{str(email)}: Invalid header found.')
            except Exception as e:
                print(f'<500>-{timestamp}-An error occurred: {str(e)}')
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
                print(f'(HTML)-<200>-{timestamp}-{str(email)}: Email sent successfully.')
            except Exception as e:
                print(f'(HTML)-<500>-{timestamp}-An error occurred: {str(e)}')
			
        time.sleep(1)
# get_emails()
