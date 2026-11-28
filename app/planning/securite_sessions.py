from django.contrib.auth import logout, get_user_model
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .services.securite import version_securite_compte


CLE_VERSION_SESSION = "dispo_version_securite"


@receiver(
    user_logged_in,
    dispatch_uid="planning.enregistrer_version_securite",
)
def enregistrer_version_securite(sender, request, user, **kwargs):
    if request is not None:
        request.session[CLE_VERSION_SESSION] = (
            version_securite_compte(user.pk)
        )


def session_securite_valide(request):
    utilisateur = request.user

    if not utilisateur.is_authenticated:
        return False

    version_session = request.session.get(
        CLE_VERSION_SESSION
    )

    return (
        utilisateur.is_active
        and type(version_session) is int
        and version_session == version_securite_compte(
            utilisateur.pk
        )
    )


def actualiser_utilisateur_session(request):
    from django.utils.crypto import constant_time_compare

    utilisateur = request.user

    if not utilisateur.is_authenticated:
        return False

    utilisateur_actualise = (
        get_user_model().objects
        .filter(pk=utilisateur.pk, is_active=True)
        .first()
    )

    if utilisateur_actualise is None:
        logout(request)
        return False

    empreinte_session = request.session.get(
        "_auth_user_hash", ""
    )

    if not constant_time_compare(
        empreinte_session,
        utilisateur_actualise.get_session_auth_hash(),
    ):
        logout(request)
        return False

    request.user = utilisateur_actualise
    request._cached_user = utilisateur_actualise

    if not session_securite_valide(request):
        logout(request)
        return False

    return True


class VerificationSecuriteSessionMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        utilisateur = request.user

        if utilisateur.is_authenticated:
            if not session_securite_valide(request):
                logout(request)

        elif "_auth_user_id" in request.session:
            logout(request)

        return self.get_response(request)
