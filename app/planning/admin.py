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

    def save_model(self, request, obj, form, change):
        if not change or form.changed_data:
            obj.valide_par = request.user

        super().save_model(request, obj, form, change)
