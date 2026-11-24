from datetime import datetime, time, timedelta

from django.utils import timezone


def periodes_surveillance(debut, fin):
    """
    Retourne les périodes de surveillance comprises
    entre deux instants.

    Lundi-jeudi : 21h à 6h.
    Vendredi 21h à lundi 6h : continu.
    """

    if timezone.is_naive(debut) or timezone.is_naive(fin):
        raise ValueError("Les dates doivent être horodatées.")

    if fin <= debut:
        raise ValueError("La fin doit être après le début.")

    fuseau = timezone.get_current_timezone()
    jour = timezone.localtime(debut, fuseau).date() - timedelta(days=3)
    dernier_jour = timezone.localtime(fin, fuseau).date()

    periodes = []

    while jour <= dernier_jour:
        if jour.weekday() in (0, 1, 2, 3):
            debut_garde = timezone.make_aware(
                datetime.combine(jour, time(21, 0)),
                fuseau,
            )
            fin_garde = timezone.make_aware(
                datetime.combine(
                    jour + timedelta(days=1),
                    time(6, 0),
                ),
                fuseau,
            )

        elif jour.weekday() == 4:
            debut_garde = timezone.make_aware(
                datetime.combine(jour, time(21, 0)),
                fuseau,
            )
            fin_garde = timezone.make_aware(
                datetime.combine(
                    jour + timedelta(days=3),
                    time(6, 0),
                ),
                fuseau,
            )

        else:
            jour += timedelta(days=1)
            continue

        debut_effectif = max(debut, debut_garde)
        fin_effective = min(fin, fin_garde)

        if debut_effectif < fin_effective:
            periodes.append({
                "debut": debut_effectif,
                "fin": fin_effective,
            })

        jour += timedelta(days=1)

    return periodes
