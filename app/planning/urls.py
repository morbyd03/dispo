from django.urls import path

from . import views
from . import gestion_agents
from . import profil

urlpatterns = [
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
