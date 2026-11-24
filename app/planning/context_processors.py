from django.conf import settings


def personnalisation(request):
    return {
        "dispo_preproduction": settings.DISPO_PREPRODUCTION,
        "dispo_name": settings.DISPO_NAME,
        "dispo_centre": settings.DISPO_CENTRE,
        "dispo_logo": settings.DISPO_LOGO_STATIC,
    }
