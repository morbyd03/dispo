from django.db import transaction
from django.db.models import F
from django.utils import timezone

from ..models import SecuriteCompte


def version_securite_compte(utilisateur_id):
    version = (
        SecuriteCompte.objects
        .filter(utilisateur_id=utilisateur_id)
        .values_list("version", flat=True)
        .first()
    )

    return version if version is not None else 0


@transaction.atomic
def revoquer_acces_compte(utilisateur_id):
    securite, _ = SecuriteCompte.objects.get_or_create(
        utilisateur_id=utilisateur_id,
    )

    SecuriteCompte.objects.filter(
        pk=securite.pk,
    ).update(
        version=F("version") + 1,
        modifie_le=timezone.now(),
    )

    securite.refresh_from_db()

    return securite.version
