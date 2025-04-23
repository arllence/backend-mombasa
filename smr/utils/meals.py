import datetime
import time
from django.db.models import Q
from smr.models import Meal
from django.core.mail import send_mail, EmailMessage, BadHeaderError
# exec(open('smr/utils/meals.py').read())


from django.utils import timezone
from datetime import timedelta

def mark_past_events():
    today = timezone.now().date()
    
    # Find events that already passed and are not yet marked
    past_events = Meal.objects.filter(date_of_event__lt=today).exclude(Q(status__in=['CEO APPROVED']))
    for event in past_events:
        print(event.status, str(event.date_of_event))

    # Update their status
    # past_events.update(status='Passed')
    

    print(f"{past_events.count()} events marked as Passed.")


def mark_upcoming_events():

    start_date = timezone.now().date() + timedelta(days=1)
    end_date = start_date + timedelta(days=2)


    # Filter events happening tomorrow
    upcoming_events = Meal.objects.filter(event_date__range=(start_date, end_date))

    for event in upcoming_events:
        print(event.status, str(event.date_of_event))


    print(f"{upcoming_events.count()} events marked as Upcoming.")




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
            send_mail(subject, message, 'notification@akhskenya.org', email, fail_silently=False)
            target.status = "SENT"
            target.save()
            print(f'(PLAIN)-<200>-{timestamp}-{str(email)}')
        except BadHeaderError:
            print(f'(PLAIN)-<400>-{timestamp}-{str(email)}: Invalid header found.')
        except Exception as e:
            print(f'(PLAIN)-<500>-{timestamp}-An error occurred: {str(e)}')
        
			
        time.sleep(1)

    timestamp = str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))
    print(f">>> Sent {count} Emails | {timestamp}")


# get_emails()
