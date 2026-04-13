from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile


class Command(BaseCommand):
    help = 'Create a Super Admin user for the SaaS system.'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, required=True, help='Username for the super admin')
        parser.add_argument('--email', type=str, required=True, help='Email address')
        parser.add_argument('--password', type=str, required=True, help='Password')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        if User.objects.filter(username=username).exists():
            raise CommandError(f"A user with username '{username}' already exists.")

        if User.objects.filter(email=email).exists():
            raise CommandError(f"A user with email '{email}' already exists.")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,
        )

        UserProfile.objects.create(
            user=user,
            user_type='super_admin',
        )

        self.stdout.write(
            self.style.SUCCESS(f"Super admin '{username}' created successfully.")
        )
