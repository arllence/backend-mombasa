from django.db import transaction
from acl.models import TrackUser

def get_client_info(request, app, uid):
    def get_ip():
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    client_info = {
        'ip_address': get_ip(),
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        'accept': request.META.get('HTTP_ACCEPT', ''),
        'accept_language': request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
        'referrer': request.META.get('HTTP_REFERER', ''),
        'method': request.method,
        'path': request.path,
        'cookies': request.COOKIES,
        'session_key': request.session.session_key,
        'is_authenticated': request.user.is_authenticated,
        'email': request.user.email if request.user.is_authenticated else None,
        # Optional: Custom headers
        'device_id': request.META.get('HTTP_X_DEVICE_ID'),
        'app_version': request.META.get('HTTP_X_APP_VERSION'),
    }
    # return client_info

    with transaction.atomic():
        raw = {
            "ip": get_ip(),
            "uid": uid,
            "app": app.upper(),
            "data": client_info
        }
        TrackUser.objects.create(**raw)

