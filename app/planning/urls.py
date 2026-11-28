from django.urls import path

from . import views
from . import gestion_agents
from . import import_export_agents
from . import profil

urlpatterns = [
    path(
        "agents/importer/confirmer/",
        import_export_agents.confirmer_import_agents,
        name="confirmer_import_agents",
    ),
    path(
        "agents/importer/annuler/",
        import_export_agents.annuler_import_agents,
        name="annuler_import_agents",
    ),
    path(
        "agents/importer/",
        import_export_agents.import_agents,
        name="import_agents",
    ),
    path(
        "agents/exporter/",
        import_export_agents.export_agents,
        name="export_agents",
    ),
    path(
        "agents/exporter/telecharger/",
        import_export_agents.telecharger_export_agents,
        name="telecharger_export_agents",
    ),
    path(
        "agents/<int:pk>/droits/",
        gestion_agents.droits_agent,
        name="droits_agent",
    ),
    path(
        "agents/<int:pk>/qualifications/",
        gestion_agents.qualifications_agent,
        name="qualifications_agent",
    ),
    path(
        "profil/mot-de-passe/",
        profil.ChangerMotDePasse.as_view(),
        name="changer_mot_de_passe",
    ),

    path(
        "profil/",
        profil.mon_profil,
        name="mon_profil",
    ),

    path(
        "agents/<int:pk>/reinitialiser/",
        gestion_agents.reinitialiser_agent,
        name="reinitialiser_agent",
    ),

    path(
        "agents/<int:pk>/modifier/",
        gestion_agents.modifier_agent,
        name="modifier_agent",
    ),

    path(
        "agents/ajouter/",
        gestion_agents.ajouter_agent,
        name="ajouter_agent",
    ),

    path(
        "agents/",
        gestion_agents.liste_agents,
        name="liste_agents",
    ),

    path(
        "",
        views.mes_disponibilites,
        name="mes_disponibilites",
    ),
    path(
        "ajouter/",
        views.ajouter_disponibilite,
        name="ajouter_disponibilite",
    ),
    path(
        "modifier/<int:pk>/",
         views.modifier_disponibilite,
         name="modifier_disponibilite",
    ),
    path(
            "supprimer/<int:pk>/",
            views.supprimer_disponibilite,
            name="supprimer_disponibilite",
    ),

    path(
            "planning/",
            views.planning_hebdomadaire,
            name="planning_hebdomadaire",
    ),

    path(
        "copier-journee/",
        views.copier_journee_disponibilites,
        name="copier_journee",
    ),

    path(
        "api/couverture-ssuap/",
        views.couverture_ssuap_calendrier,
        name="couverture_ssuap_calendrier",
    ),

]
