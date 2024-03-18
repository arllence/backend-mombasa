import time
import requests
from django.db.models import Q
from acl import models
from django.core.mail import send_mail
# exec(open('communication/utils/mailgun_sdk.py').read())

def get_emails():
    print("into get emails")
    emails = models.Sendmail.objects.filter(Q(status='PENDING') | Q(status='FAILED'))[:70]
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

			
		send_mail(subject, message, 'notification@akhskenya.org', email)
			
		time.sleep(1)
# get_emails()
