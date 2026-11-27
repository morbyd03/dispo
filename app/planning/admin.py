from django.contrib import admin

from .models import (
    Grade,
    FonctionAgent,
    ProfilAgent,
    Competence,
    CompetenceAgent,
)


class AdministrationLectureSeule(admin.ModelAdmin):

    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class AdministrationReferentiel(admin.ModelAdmin):

    actions = None

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Grade)
class GradeAdmin(AdministrationReferentiel):
    list_display = ("code", "nom", "ordre", "active")
    list_filter = ("active",)
    search_fields = ("code", "nom")

    def get_readonly_fields(self, request, obj=None):
        return ("code",) if obj else ()


@admin.register(FonctionAgent)
class FonctionAgentAdmin(AdministrationReferentiel):
    list_display = ("nom", "active")
    list_filter = ("active",)
    search_fields = ("nom",)


@admin.register(ProfilAgent)
class ProfilAgentAdmin(AdministrationLectureSeule):
    list_display = ("utilisateur", "grade", "telephone")
    list_filter = ("grade", "fonctions")
    search_fields = (
        "utilisateur__username",
        "utilisateur__first_name",
        "utilisateur__last_name",
    )
    list_select_related = ("utilisateur", "grade")
    autocomplete_fields = ("utilisateur", "grade")
    filter_horizontal = ("fonctions",)


@admin.register(Competence)
class CompetenceAdmin(AdministrationReferentiel):
    list_display = ("code", "nom", "categorie", "active")
    list_filter = ("categorie", "active")
    search_fields = ("code", "nom", "description")

    def get_readonly_fields(self, request, obj=None):
        return ("code",) if obj else ()


@admin.register(CompetenceAgent)
class CompetenceAgentAdmin(AdministrationLectureSeule):
    list_display = (
        "profil",
        "competence",
        "date_validation",
        "date_expiration",
        "valide_par",
    )
    list_filter = ("competence", "date_expiration")
    search_fields = (
        "profil__utilisateur__username",
        "profil__utilisateur__first_name",
        "profil__utilisateur__last_name",
    )
    autocomplete_fields = ("profil", "competence")
    readonly_fields = ("valide_par",)



from .models import JournalAction


@admin.register(JournalAction)
class JournalActionAdmin(AdministrationLectureSeule):
    list_display = (
        "date_action",
        "auteur",
        "action",
        "type_objet",
        "objet_id",
    )

    list_filter = (
        "action",
        "type_objet",
        "date_action",
    )

    search_fields = (
        "auteur__username",
        "action",
        "type_objet",
    )

    readonly_fields = (
        "date_action",
        "auteur",
        "action",
        "type_objet",
        "objet_id",
        "details",
    )

    list_select_related = ("auteur",)
    date_hierarchy = "date_action"
    list_per_page = 50

    def has_view_permission(self, request, obj=None):
        return (
            request.user.is_active
            and request.user.is_superuser
        )


from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin


class UtilisateurTechniqueAdmin(UserAdmin):

    actions = None

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            if ProfilAgent.objects.filter(
                utilisateur_id=obj.pk
            ).exists():
                return False

        return super().has_change_permission(request, obj)

    def user_change_password(self, request, id, form_url=""):
        from django.core.exceptions import PermissionDenied

        if ProfilAgent.objects.filter(
            utilisateur_id=id
        ).exists():
            raise PermissionDenied(
                "Les mots de passe des agents doivent etre "
                "geres par les procedures dediees."
            )

        return super().user_change_password(
            request, id, form_url
        )


admin.site.unregister(get_user_model())

admin.site.register(
    get_user_model(),
    UtilisateurTechniqueAdmin,
)
