from django.core.mail import send_mail

subject = 'Test Email'
message = 'This is a test email sent using SMTP in Django.'
from_email = 'your-email@example.com'
recipient_list = ['recipient@example.com']

send_mail(subject, message, from_email, recipient_list)