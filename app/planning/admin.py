from django.contrib import admin

from .models import (
    Grade,
    FonctionAgent,
    ProfilAgent,
    Competence,
    CompetenceAgent,
)


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("code", "nom", "ordre", "active")
    list_filter = ("active",)
    search_fields = ("code", "nom")


@admin.register(FonctionAgent)
class FonctionAgentAdmin(admin.ModelAdmin):
    list_display = ("nom", "active")
    list_filter = ("active",)
    search_fields = ("nom",)


@admin.register(ProfilAgent)
class ProfilAgentAdmin(admin.ModelAdmin):
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
class CompetenceAdmin(admin.ModelAdmin):
    list_display = ("code", "nom", "categorie", "active")
    list_filter = ("categorie", "active")
    search_fields = ("code", "nom", "description")

    def get_readonly_fields(self, request, obj=None):
        return ("code",) if obj else ()


@admin.register(CompetenceAgent)
class CompetenceAgentAdmin(admin.ModelAdmin):
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

    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


from .models import JournalAction


@admin.register(JournalAction)
class JournalActionAdmin(admin.ModelAdmin):
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
    actions = None

    def has_view_permission(self, request, obj=None):
        return (
            request.user.is_active
            and request.user.is_superuser
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
