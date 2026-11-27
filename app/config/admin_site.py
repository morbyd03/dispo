from django.contrib.admin import AdminSite


class AdministrationTechnique(AdminSite):

    site_header = "Dispo - Administration technique"
    site_title = "Dispo - Administration"
    index_title = "Administration technique"

    def has_permission(self, request):
        return (
            super().has_permission(request)
            and request.user.is_superuser
        )
