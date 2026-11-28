from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.db import transaction

from planning.autorisations import (
    GROUPE_ADMINISTRATEURS,
    PERMISSIONS_ADMINISTRATEURS,
)


class Command(BaseCommand):
    help = "Initialise les droits administrateurs de Dispo."

    @transaction.atomic
    def handle(self, *args, **options):
        groupe, _ = Group.objects.get_or_create(
            name=GROUPE_ADMINISTRATEURS
        )

        permissions = []

        for identifiant in PERMISSIONS_ADMINISTRATEURS:
            application, code = identifiant.split(".", 1)

            permission = Permission.objects.get(
                content_type__app_label=application,
                codename=code,
            )

            permissions.append(permission)

        groupe.permissions.set(permissions)

        self.stdout.write(
            self.style.SUCCESS(
                "Groupe Administrateurs Dispo initialise."
            )
        )
