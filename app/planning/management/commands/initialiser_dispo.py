from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.db import transaction


class Command(BaseCommand):
    help = "Initialise les droits administrateurs de Dispo."

    @transaction.atomic
    def handle(self, *args, **options):

        groupe, cree = Group.objects.get_or_create(
            name="Administrateurs Dispo"
        )

        permissions = {
            "auth": [
                "add_user",
                "change_user",
                "view_user",
            ],
            "planning": [
                "add_competenceagent",
                "change_competenceagent",
                "delete_competenceagent",
                "view_competenceagent",
            ],
        }

        for application, codes in permissions.items():
            for code in codes:
                permission = Permission.objects.get(
                    content_type__app_label=application,
                    codename=code,
                )
                groupe.permissions.add(permission)

        self.stdout.write(
            self.style.SUCCESS(
                "Groupe Administrateurs Dispo initialise."
            )
        )
