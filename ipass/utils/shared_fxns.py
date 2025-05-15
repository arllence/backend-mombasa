from datetime import datetime
import string
import random
from ipass.models import Patient

def find_date_difference(start_date,end_date,period):
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Calculate the difference

        if period == 'days':
            difference = end_date - start_date
            difference = difference.days
        elif period == 'weeks':
            difference = (end_date - start_date).days // 7
        elif period == 'months':
            difference = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
        elif period == 'years':
            difference = end_date.year - start_date.year
        elif period == 'hours':
            difference = (end_date - start_date).total_seconds() // 3600
        elif period == 'minutes':
            difference = (end_date - start_date).total_seconds() // 60

        return difference
        
    except Exception as e:
        print(e)
        return 'error'


def generate_unique_identifier():
    characters = string.ascii_uppercase + string.digits
    uid = ''.join(random.choices(characters, k=6))

    is_existing = Patient.objects.filter(uid=uid).exists()
    if is_existing:
        generate_unique_identifier()
    else:
        return uid

