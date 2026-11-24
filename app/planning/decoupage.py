from datetime import datetime, time, timedelta

from django.utils import timezone


def changements_de_jour(debut, fin):
    """
    Retourne les passages à minuit local strictement
    compris entre debut et fin.
    """
    if timezone.is_naive(debut) or timezone.is_naive(fin):
        raise ValueError("Les dates doivent contenir un fuseau horaire.")

    if fin <= debut:
        raise ValueError("La fin doit être postérieure au début.")

    fuseau = timezone.get_current_timezone()
    jour = timezone.localtime(debut, fuseau).date() + timedelta(days=1)
    dernier_jour = timezone.localtime(fin, fuseau).date()

    instants = set()

    while jour <= dernier_jour:
        minuit = timezone.make_aware(
            datetime.combine(jour, time.min),
            fuseau,
        )

        if debut < minuit < fin:
            instants.add(minuit)

        jour += timedelta(days=1)

    return instants
