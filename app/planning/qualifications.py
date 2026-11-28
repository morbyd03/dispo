from django.db.models import Q
from django.utils import timezone

from .models import CompetenceAgent


def etat_validite_competence(attribution, date_reference=None):
    if date_reference is None:
        date_reference = timezone.localdate()

    if not attribution.competence.active:
        return "archivee"

    if (
        attribution.date_validation
        and attribution.date_validation > date_reference
    ):
        return "future"

    if (
        attribution.date_expiration
        and attribution.date_expiration < date_reference
    ):
        return "expiree"

    return "valide"


def qualifications_valides(profil, date_reference=None):
    if date_reference is None:
        date_reference = timezone.localdate()

    return CompetenceAgent.objects.filter(
        profil=profil,
        competence__active=True,
    ).filter(
        Q(date_validation__isnull=True)
        | Q(date_validation__lte=date_reference)
    ).filter(
        Q(date_expiration__isnull=True)
        | Q(date_expiration__gte=date_reference)
    )


def possede_competence(profil, code, date_reference=None):
    return qualifications_valides(
        profil,
        date_reference,
    ).filter(
        competence__code=code,
    ).exists()
