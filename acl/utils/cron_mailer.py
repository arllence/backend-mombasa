import time
import requests
from django.db.models import Q
from acl import models
from django.core.mail import send_mail, BadHeaderError
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

        subject = target.subject
        message = target.message
        email = target.email


            
        # send = send_mail(subject, message, 'notification@akhskenya.org', email)
        try:
            send_mail(subject, message, 'notification@akhskenya.org', email, fail_silently=False)
            target.status = "SENT"
            target.save()
            print(f'{count}-<200>-{email[0]}: Email sent successfully.')
        except BadHeaderError:
            print(f'{count}-<400>-{email[0]}: Invalid header found.')
        except Exception as e:
            print(f'<500>-An error occurred: {str(e)}')
			
        time.sleep(1)
# get_emails()
