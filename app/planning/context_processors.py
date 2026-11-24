from django.conf import settings


def personnalisation(request):
    return {
        "dispo_name": settings.DISPO_NAME,
        "dispo_centre": settings.DISPO_CENTRE,
        "dispo_logo": settings.DISPO_LOGO_STATIC,
    }
