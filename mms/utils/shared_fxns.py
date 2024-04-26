from datetime import datetime
import string
import random
from mms.models import Quote

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

        # return difference
        return difference
        
    except Exception as e:
        print(e)
        return 'error'


def identify_file_type(ext):
    images = ['jpeg', 'jpg', 'png', 'tiff']
    videos = ['mp4','webm', 'mkv']
    files = ['pdf']

    if ext.lower() in images:
        return 'IMAGE'
    elif ext.lower() in videos:
        return 'VIDEO'
    elif ext.lower() in files:
        return 'FILE'
    else:
        return 'UNKNOWN'


def generate_unique_identifier():
    characters = string.ascii_uppercase + string.digits
    qid = ''.join(random.choices(characters, k=6))
    # qid =  "QS#" + identifier

    is_existing = Quote.objects.filter(qid=qid).exists()
    if is_existing:
        generate_unique_identifier()
    else:
        return qid

