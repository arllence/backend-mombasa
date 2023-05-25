import logging
from django.contrib.auth.models import Group
from user_manager.models import AccountActivity, User
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.conf import settings
from django.contrib.auth import get_user_model

# Get an instance of a logger
logger = logging.getLogger(__name__)

def fetchusergroups(userid):
    userroles = []
    query_set = Group.objects.filter(user=userid)
    if query_set.count() >= 1:
        for groups in query_set:
            userroles.append(groups.name)
        return userroles
        
    else:
        return ""


def log_account_activity(actor, recipient, activity, remarks):
    create_activity = {
        "recipient": recipient,
        "actor": actor,
        "activity": activity,
        "remarks": remarks,

    }
    new_activity = AccountActivity.objects.create(**create_activity)





def sendmail(recipient,subject,message):
    try:
        message = Mail(
        from_email = settings.EMAIL_HOST,
        to_emails=recipient,
        subject = subject,
        html_content= message + 
        ''
        '<br />'
        'Thanks,<br />'
        'African Adaptation Acceleration Program <br>(AAAP)')
        sg = SendGridAPIClient(settings.EMAIL_HOST_PASSWORD)
        response = sg.send(message)
        if response.status_code == 200 or response.status_code == 201 or response.status_code == 202:
            return True
        else:
            return False
    except Exception as e:
        logger.error(e)
        return False


def award_role(role,account_id):
    role = "LEAD_" + role
    try:
        record_instance = get_user_model().objects.get(id=account_id)
        group = Group.objects.get(name=role)  
        record_instance.groups.add(group)
        return True
    except Exception as e:
        logger.error(e)
        return False

def revoke_role(role,account_id):
    if role == "EXTERNAL_EVALUATOR":
        role = "CHIEF_EVALUATOR"
    else:
        role = "LEAD_" + role
    try:
        record_instance = get_user_model().objects.get(id=account_id)
        group = Group.objects.get(name=role)  
        record_instance.groups.remove(group)
        return True
    except Exception as e:
        logger.error(e)
        return False
        


