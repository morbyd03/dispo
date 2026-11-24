from django.db.models import Q
from django.utils import timezone

from .models import CompetenceAgent


def possede_competence(profil, code, date_reference=None):
    """
    Vérifie qu'un agent possède une compétence active
    et non expirée à la date indiquée.
    """
    if date_reference is None:
        date_reference = timezone.localdate()

    return CompetenceAgent.objects.filter(
        agent=profil.utilisateur,
        competence__code=code,
        competence__active=True,
    ).filter(
        Q(date_validation__isnull=True)
        | Q(date_validation__lte=date_reference)
    ).filter(
        Q(date_expiration__isnull=True)
        | Q(date_expiration__gte=date_reference)
    ).exists()
