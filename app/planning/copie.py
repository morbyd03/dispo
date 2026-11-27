from datetime import datetime, time, timedelta

from django.db import transaction
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Disponibilite


@transaction.atomic
def copier_journee(profil, date_source, dates_destination):
    """
    Remplace intégralement chaque journée cible par une copie
    des disponibilités de la journée source.

    Les disponibilités débordant des journées cibles sont
    conservées hors de ces journées.
    """

    fuseau = timezone.get_current_timezone()

    def heure_locale(jour, heure):
        return forms.DateTimeField().clean(
            datetime.combine(jour, heure)
        )

    def minuit(jour):
        return timezone.make_aware(
            datetime.combine(jour, time.min),
            fuseau,
        )

    debut_source = minuit(date_source)
    fin_source = minuit(date_source + timedelta(days=1))

    disponibilites = list(
        Disponibilite.objects.filter(
            profil=profil,
            debut__lt=fin_source,
            fin__gt=debut_source,
        ).order_by("debut")
    )

    portions = []

    for dispo in disponibilites:
        debut = max(dispo.debut, debut_source)
        fin = min(dispo.fin, fin_source)

        if debut < fin:
            debut_local = timezone.localtime(debut, fuseau)
            fin_local = timezone.localtime(fin, fuseau)

            portions.append((
                debut_local.time().replace(tzinfo=None),
                fin_local.time().replace(tzinfo=None),
                fin == fin_source,
            ))

    if not portions:
        return {
            "creations": 0,
            "doublons": 0,
            "creneaux_source": 0,
        }

    creations = 0

    with transaction.atomic():
        for destination in sorted(set(dates_destination)):

            if destination == date_source:
                continue

            debut_destination = minuit(destination)
            fin_destination = minuit(
                destination + timedelta(days=1)
            )

            # Supprimer les disponibilités de l'agent
            # qui touchent la journée cible.
            existantes = list(
                Disponibilite.objects.filter(
                    profil=profil,
                    debut__lt=fin_destination,
                    fin__gt=debut_destination,
                )
            )

            for dispo in existantes:
                # Préserver la partie située avant la journée.
                avant = (
                    (dispo.debut, debut_destination)
                    if dispo.debut < debut_destination
                    else None
                )

                # Préserver la partie située après la journée.
                apres = (
                    (fin_destination, dispo.fin)
                    if dispo.fin > fin_destination
                    else None
                )

                dispo.delete()

                for segment in (avant, apres):
                    if segment:
                        Disponibilite.objects.create(
                            profil=profil,
                            debut=segment[0],
                            fin=segment[1],
                        )

            # Recréer exactement les portions de la source.
            for heure_debut, heure_fin, finit_a_minuit in portions:
                nouveau_debut = heure_locale(destination, heure_debut)

                if finit_a_minuit:
                    nouvelle_fin = fin_destination
                else:
                    nouvelle_fin = heure_locale(destination, heure_fin)

                if nouvelle_fin <= nouveau_debut:
                    raise ValidationError(
                        "La période copiée doit avoir "
                        "une durée positive."
                    )

                Disponibilite.objects.create(
                    profil=profil,
                    debut=nouveau_debut,
                    fin=nouvelle_fin,
                )

                creations += 1

    return {
        "creations": creations,
        "doublons": 0,
        "creneaux_source": len(portions),
    }
