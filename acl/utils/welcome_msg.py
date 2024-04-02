from acl.models import Sendmail, User

def main():
    subject = "Welcome To Quotation System [PSMDQS]. "

    def set_message(instance):
        message = f"[Platform Access Details]\n\nDear {instance.first_name}, \n\n These are the credentials to MMD's Quote Request System. Username is your  email which is : {instance.email}\n and password is: welcome@123\n To Access the system use this link: http://172.20.0.42/\nIf you encounter any challenge while navigating the platform, please contact IT department at 54030.\n\nKind Regards\nPSMDQS-AKHK\n(System Generated)"
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