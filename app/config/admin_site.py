from django.contrib.admin import AdminSite
from django.db import transaction, OperationalError
from django.views.decorators.debug import sensitive_post_parameters
from django.utils.decorators import method_decorator

from planning.securite_vues import (
    abandonner_session_securite,
    reponse_conflit_securite,
)



class AdministrationTechnique(AdminSite):

    site_header = "Dispo - Administration technique"
    site_title = "Dispo - Administration"
    index_title = "Administration technique"

    def has_permission(self, request):
        return (
            super().has_permission(request)
            and request.user.is_superuser
        )


    @method_decorator(sensitive_post_parameters())
    def login(self, request, extra_context=None):
        if request.method != "POST":
            return super().login(request, extra_context)

        try:
            with transaction.atomic():
                return super().login(request, extra_context)

        except OperationalError:
            abandonner_session_securite(request)

            return reponse_conflit_securite()
