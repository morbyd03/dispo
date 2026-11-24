from django.contrib import admin
from .models import ProfilAgent


@admin.register(ProfilAgent)
class ProfilAgentAdmin(admin.ModelAdmin):
    list_display = ("utilisateur",)
    search_fields = (
        "utilisateur__username",
        "utilisateur__first_name",
        "utilisateur__last_name",
    )
    list_select_related = ("utilisateur",)


from .models import Competence, CompetenceAgent


@admin.register(Competence)
class CompetenceAdmin(admin.ModelAdmin):
    list_display = ("code", "nom", "categorie", "active")
    def get_prepopulated_fields(self, request, obj=None):
        if obj is not None:
            return {}
        return {"code": ("nom",)}

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("code",)
        return ()
    list_filter = ("categorie", "active")
    search_fields = ("nom", "description")


@admin.register(CompetenceAgent)
class CompetenceAgentAdmin(admin.ModelAdmin):
    list_display = (
        "agent",
        "competence",
        "date_validation",
        "date_expiration",
        "valide_par",
    )
    list_filter = ("competence", "date_expiration")
    search_fields = (
        "agent__username",
        "agent__first_name",
        "agent__last_name",
        "competence__nom",
    )
    autocomplete_fields = ("agent", "competence")

    def save_model(self, request, obj, form, change):
        if not change or not obj.valide_par_id:
            obj.valide_par = request.user
        super().save_model(request, obj, form, change)


# Administration unifiée des agents
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User as DjangoUser


class CompetenceAgentInline(admin.TabularInline):
    model = CompetenceAgent
    fk_name = "agent"
    extra = 0
    autocomplete_fields = ("competence",)
    fields = (
        "competence",
        "date_validation",
        "date_expiration",
        "valide_par",
    )
    readonly_fields = ("valide_par",)

class AgentUserAdmin(UserAdmin):
    inlines = (CompetenceAgentInline,)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        ProfilAgent.objects.get_or_create(utilisateur=obj)

    def save_formset(self, request, form, formset, change):
        if formset.model is CompetenceAgent:
            objets = formset.save(commit=False)

            for objet in formset.deleted_objects:
                objet.delete()

            for objet in objets:
                if objet._state.adding or not objet.valide_par_id:
                    objet.valide_par = request.user
                objet.save()

            formset.save_m2m()
        else:
            super().save_formset(request, form, formset, change)

    list_display = (
        "username",
        "last_name",
        "first_name",
        "email",
        "is_active",
        "is_staff",
    )

    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
    )


UserModel = get_user_model()

if UserModel is DjangoUser:
    admin.site.unregister(UserModel)
    admin.site.register(UserModel, AgentUserAdmin)


# Masquer les rubriques redondantes du menu d'administration.
# Les modèles et leurs données restent inchangés.
admin.site.unregister(ProfilAgent)
admin.site.unregister(CompetenceAgent)
