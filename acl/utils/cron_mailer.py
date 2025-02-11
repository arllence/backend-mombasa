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


        if not is_html:
            try:
                send_mail(subject, message, 'notification@akhskenya.org', email, fail_silently=False)
                target.status = "SENT"
                target.save()
                print(f'{count}-<200>-{email[0]}: Email sent successfully.')
            except BadHeaderError:
                print(f'{count}-<400>-{email[0]}: Invalid header found.')
            except Exception as e:
                print(f'<500>-An error occurred: {str(e)}')
        else:
            email_to_send = EmailMessage(
                subject,
                message,
                'notification@akhskenya.org',
                email
            )
            email_to_send.content_subtype = 'html'  # Set the content type to HTML
            email_to_send.send(fail_silently=False)
            target.status = "SENT"
            target.save()
			
        time.sleep(1)
# get_emails()
