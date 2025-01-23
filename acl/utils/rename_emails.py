from acl.models import User
# exec(open('acl/utils/rename_emails.py').read())

def main():
    count = 0
    users = User.objects.filter(email__icontains='mailinator.com')
    for user in users:
        count += 1
        email = user.email
        email = email.split('@')[0]
        user.email = email
        user.save()
        print(count, email)


main()