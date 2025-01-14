import logging
import random
from django.contrib.auth.models import Group
from acl.models import AccountActivity, User
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
    
# def users_with_role(role_name):

    # selected_users = get_user_model().objects.filter(groups__name=role.name)
    # user_info = serializers.UsersSerializer(selected_users, many=True)
    # return Response(user_info.data, status=status.HTTP_200_OK)


def log_account_activity(actor, recipient, activity, remarks):
    create_activity = {
        "recipient": recipient,
        "actor": actor,
        "activity": activity,
        "remarks": remarks,

    }
    new_activity = AccountActivity.objects.create(**create_activity)



def award_role(role,account_id):
    try:
        record_instance = get_user_model().objects.get(id=account_id)
        group = Group.objects.get(name=role)  
        record_instance.groups.add(group)
        return True
    except Exception as e:
        logger.error(e)
        return False

def revoke_role(role,account_id):
    try:
        record_instance = get_user_model().objects.get(id=account_id)
        group = Group.objects.get(name=role)  
        record_instance.groups.remove(group)
        return True
    except Exception as e:
        logger.error(e)
        return False

def password_generator():
        # generate password
        lower = "abcdefghijklmnpqrstuvwxyz"
        upper = "ABCDEFGHIJKLMNPQRSTUVWXYZ"
        numbers = "123456789"
        symbols = "$@!?"

        sample_lower = random.sample(lower,2)
        sample_upper = random.sample(upper,4)
        sample_numbers = random.sample(numbers,2)
        sample_symbols = random.sample(symbols,1)

        # all = sample_lower + sample_upper + sample_numbers + sample_symbols
        all = sample_upper + sample_numbers

        random.shuffle(all)

        password = "".join(all)
        return password


