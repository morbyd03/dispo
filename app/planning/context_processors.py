from django.contrib.auth.models import AnonymousUser
from django.conf import settings

from .autorisations import (
    peut_consulter_gestion_agents,
    peut_gerer_qualifications,
)


def personnalisation(request):
    utilisateur = getattr(request, "user", None)
    if utilisateur is None:
        utilisateur = AnonymousUser()

    return {
        "dispo_acces_gestion_agents": (
            peut_consulter_gestion_agents(utilisateur)
        ),
        "dispo_acces_qualifications": (
            peut_gerer_qualifications(utilisateur)
        ),
        "dispo_preproduction": settings.DISPO_PREPRODUCTION,
        "dispo_name": settings.DISPO_NAME,
        "dispo_centre": settings.DISPO_CENTRE,
        "dispo_logo": settings.DISPO_LOGO_STATIC,
    }
