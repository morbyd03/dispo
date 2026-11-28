from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .securite_vues import ChangementMotDePasseSecurise
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone

from .autorisations import (
    est_superutilisateur,
    est_administrateur_dispo,
    peut_gerer_qualifications,
)
from .models import ProfilAgent
from .qualifications import etat_validite_competence


@login_required
def mon_profil(request):
    agent = request.user

    profil = (
        ProfilAgent.objects
        .select_related("grade")
        .prefetch_related("fonctions")
        .filter(utilisateur=agent)
        .first()
    )

    if est_superutilisateur(agent):
        role = "Superutilisateur"
    elif est_administrateur_dispo(agent):
        role = "Administrateur Dispo"
    elif peut_gerer_qualifications(agent):
        role = "Gestionnaire des qualifications"
    elif profil is not None:
        role = "Agent"
    else:
        role = "Compte sans profil opérationnel"

    competences = []

    if profil is not None:
        aujourd_hui = timezone.localdate()

        competences = list(
            profil.attributions_competences
            .select_related("competence")
            .order_by("competence__nom")
        )

        libelles = {
            "archivee": "Archivée",
            "future": "À venir",
            "expiree": "Expirée",
            "valide": "Valide",
        }

        for attribution in competences:
            attribution.etat_validite = libelles[
                etat_validite_competence(
                    attribution,
                    aujourd_hui,
                )
            ]

    return render(
        request,
        "planning/mon_profil.html",
        {
            "agent": agent,
            "profil": profil,
            "role": role,
            "competences": competences,
        },
    )


class ChangerMotDePasse(ChangementMotDePasseSecurise):
    template_name = "planning/changer_mot_de_passe.html"
    success_url = reverse_lazy("mon_profil")

    def form_valid(self, form):
        reponse = super().form_valid(form)

        messages.success(
            self.request,
            "Votre mot de passe a été modifié avec succès."
        )

        return reponse
