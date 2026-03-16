from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.templates.models import NoteTemplate
from apps.templates.specialty_configs import ALL_SPECIALTY_TEMPLATES


class Command(BaseCommand):
    help = "Seed the database with specialty-specific clinical note templates"

    def add_arguments(self, parser):
        parser.add_argument(
            "--admin-email",
            type=str,
            default="",
            help="Email of the admin user to set as template creator. If empty, uses first admin.",
        )

    def handle(self, *args, **options):
        admin_email = options["admin_email"]
        if admin_email:
            try:
                admin_user = User.objects.get(email=admin_email)
            except User.DoesNotExist:
                self.stderr.write(f"User with email '{admin_email}' not found.")
                return
        else:
            admin_user = User.objects.filter(role="admin").first()
            if not admin_user:
                admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                self.stderr.write(
                    "No admin user found. Create one first or pass --admin-email."
                )
                return

        created_count = 0
        skipped_count = 0

        for template_data in ALL_SPECIALTY_TEMPLATES:
            name = template_data["name"]
            if NoteTemplate.objects.filter(name=name).exists():
                self.stdout.write(f"  Skipped (exists): {name}")
                skipped_count += 1
                continue

            NoteTemplate.objects.create(
                name=name,
                description=template_data["description"],
                specialty=template_data["specialty"],
                note_type=template_data["note_type"],
                schema=template_data["schema"],
                tags=template_data["tags"],
                created_by=admin_user,
                practice=admin_user.practice,
                visibility="public",
                status="published",
            )
            self.stdout.write(f"  Created: {name}")
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {created_count} created, {skipped_count} skipped."
            )
        )
