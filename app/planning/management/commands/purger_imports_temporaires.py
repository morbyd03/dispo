from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError

from ...services.imports_temporaires import (
    purger_imports_temporaires,
)


class Command(BaseCommand):
    help = (
        "Supprime les imports temporaires expires, "
        "revoques ou devenus non autorises."
    )

    def handle(self, *args, **options):
        try:
            nombre = purger_imports_temporaires()

        except OperationalError as erreur:
            raise CommandError(
                "Impossible de purger les imports temporaires."
            ) from erreur

        self.stdout.write(
            self.style.SUCCESS(
                f"Imports temporaires supprimes : {nombre}"
            )
        )
