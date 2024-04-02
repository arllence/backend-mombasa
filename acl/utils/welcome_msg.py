from acl.models import Sendmail, User


def main():
    subject = "Welcome To Quotation System [PSMDQS]. "

    def set_message(instance):
        message = f"[Platform Access Details]\n\nDear {instance.first_name}, \n\nYour email is: {instance.email}\nYour password is: welcome@123\nPortal Link is: http://172.20.0.42/\nIf you encounter any challenge while navigating the platform, please let us know.\n\nKind Regards\nPSMDQS-AKHK"
        return message

    newInstances = User.objects.filter(is_defaultpassword=True)

    mails = [
        Sendmail(
            email=[instance.email], 
            subject=subject,
            message=set_message(instance),
        )
        for instance in newInstances
    ]
    Sendmail.objects.bulk_create(mails)

main()