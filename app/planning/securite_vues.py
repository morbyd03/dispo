import logging

from django.contrib.auth import logout
from django.contrib.auth.views import (
    LoginView,
    PasswordResetConfirmView,
    PasswordChangeView,
)
from django.db import transaction, OperationalError
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters

from .securite_jetons import generateur_jetons_compte
from .securite_sessions import actualiser_utilisateur_session


logger = logging.getLogger(__name__)


def reponse_conflit_securite():
    return HttpResponse(
        "Le service est temporairement indisponible. "
        "Rechargez la page avant de recommencer.",
        status=503,
        content_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Retry-After": "5",
        },
    )


def abandonner_session_securite(request):
    try:
        logout(request)

    except OperationalError:
        logger.exception(
            "Impossible de supprimer la session apres un conflit"
        )

        request.session.clear()


class TransactionSecuriteMixin:

    @method_decorator(sensitive_post_parameters())
    def dispatch(self, request, *args, **kwargs):

        if request.method != "POST":
            return super().dispatch(request, *args, **kwargs)

        try:
            with transaction.atomic():
                return super().dispatch(
                    request, *args, **kwargs
                )

        except OperationalError:
            logger.exception(
                "Echec transactionnel : %s",
                type(self).__name__,
            )

            abandonner_session_securite(request)

            return reponse_conflit_securite()


class ReinitialisationMotDePasseSecurisee(
    TransactionSecuriteMixin,
    PasswordResetConfirmView,
):
    token_generator = generateur_jetons_compte


class ConnexionSecurisee(
    TransactionSecuriteMixin,
    LoginView,
):
    pass


class ChangementMotDePasseSecurise(
    TransactionSecuriteMixin,
    PasswordChangeView,
):

    def post(self, request, *args, **kwargs):
        if not actualiser_utilisateur_session(request):
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(
                request.get_full_path()
            )

        return super().post(request, *args, **kwargs)
