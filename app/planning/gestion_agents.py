import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .autorisations import (
    peut_consulter_gestion_agents,
    peut_gerer_qualifications,
    est_administrateur_dispo,
    exiger_administrateur_dispo,
    exiger_permission,
    exiger_gestion_compte,
)
from .models import ProfilAgent
from .formulaires_agents import AgentForm, AgentModificationForm
from .services.agents import (
    creer_agent,
    modifier_agent as modifier_profil_agent,
    modifier_statut_agent,
)
from .activation_agents import (
    envoyer_activation_agent,
    envoyer_reinitialisation_agent,
)


logger = logging.getLogger(__name__)


def verifier_acces_gestion(utilisateur, permission):
    exiger_administrateur_dispo(utilisateur)
    exiger_permission(utilisateur, permission)


def obtenir_profil_modifiable(request, pk):
    verifier_acces_gestion(
        request.user, "auth.change_user"
    )

    profil = get_object_or_404(
        ProfilAgent.objects.select_related(
            "utilisateur", "grade"
        ),
        pk=pk,
    )

    exiger_gestion_compte(
        request.user, profil.utilisateur
    )

    return profil


@login_required
def liste_agents(request):
    acces_administratif = peut_consulter_gestion_agents(
        request.user
    )

    acces_qualifications = peut_gerer_qualifications(
        request.user
    )

    if not acces_administratif and not acces_qualifications:
        raise PermissionDenied("Accès interdit.")

    profils = list(
        ProfilAgent.objects
        .select_related("utilisateur", "grade")
        .prefetch_related(
            "fonctions",
            "attributions_competences__competence",
        )
        .order_by(
            "utilisateur__last_name",
            "utilisateur__first_name",
            "utilisateur__username",
        )
    )

    peut_modifier = (
        acces_administratif
        and request.user.has_perm("auth.change_user")
    )

    from .services.competences import verifier_cible_qualification

    for profil in profils:
        profil.qualifications_autorisees = False

        if peut_gerer_qualifications(request.user):
            try:
                verifier_cible_qualification(
                    request.user,
                    profil,
                )
            except PermissionDenied:
                pass
            else:
                profil.qualifications_autorisees = True

        profil.modification_autorisee = False

        if peut_modifier:
            try:
                exiger_gestion_compte(
                    request.user,
                    profil.utilisateur,
                )
            except PermissionDenied:
                pass
            else:
                profil.modification_autorisee = True

    return render(
        request,
        "planning/gestion_agents.html",
        {
            "profils": profils,
            "acces_administratif": acces_administratif,
            "peut_ajouter": (
                est_administrateur_dispo(request.user)
                and request.user.has_perm("auth.add_user")
            ),
        },
    )


@login_required
def ajouter_agent(request):
    verifier_acces_gestion(
        request.user, "auth.add_user"
    )

    if request.method == "POST":
        formulaire = AgentForm(request.POST)

        if formulaire.is_valid():
            try:
                creer_agent(
                    auteur_id=request.user.pk,
                    **formulaire.donnees_creation(),
                )
            except ValidationError as erreur:
                formulaire.add_error(None, erreur)
            else:
                messages.success(
                    request,
                    "Agent créé. Aucun e-mail d'activation "
                    "n'a été envoyé automatiquement.",
                )

                return redirect("liste_agents")
    else:
        formulaire = AgentForm()

    return render(
        request,
        "planning/ajouter_agent.html",
        {"formulaire": formulaire},
    )


@login_required
def modifier_agent(request, pk):
    profil = obtenir_profil_modifiable(request, pk)

    if request.method == "POST":
        formulaire = AgentModificationForm(
            request.POST,
            profil=profil,
        )

        if formulaire.is_valid():
            try:
                with transaction.atomic():
                    modifier_profil_agent(
                        auteur_id=request.user.pk,
                        profil_id=profil.pk,
                        **formulaire.donnees_profil(),
                    )

                    modifier_statut_agent(
                        auteur_id=request.user.pk,
                        profil_id=profil.pk,
                        actif=formulaire.cleaned_data["actif"],
                    )

            except ValidationError as erreur:
                formulaire.add_error(None, erreur)
            else:
                messages.success(
                    request,
                    "Les informations de l'agent ont été modifiées.",
                )

                return redirect("liste_agents")
    else:
        formulaire = AgentModificationForm(
            profil=profil,
        )

    return render(
        request,
        "planning/modifier_agent.html",
        {
            "formulaire": formulaire,
            "profil": profil,
            "agent": profil.utilisateur,
        },
    )


@login_required
@require_POST
def reinitialiser_agent(request, pk):
    profil = obtenir_profil_modifiable(request, pk)
    agent = profil.utilisateur

    if not agent.is_active or not agent.email:
        messages.error(
            request,
            "Le compte doit être autorisé et posséder "
            "une adresse e-mail.",
        )

        return redirect("modifier_agent", pk=profil.pk)

    try:
        if agent.has_usable_password():
            resultat = envoyer_reinitialisation_agent(
                request, agent
            )
            nature = "réinitialisation"
        else:
            resultat = envoyer_activation_agent(
                request, agent
            )
            nature = "activation"

        if resultat == 1:
            messages.success(
                request,
                f"E-mail de {nature} envoyé.",
            )
        else:
            messages.error(
                request,
                "Aucun e-mail envoyé.",
            )

    except Exception:
        logger.exception(
            "Echec de l'envoi du courriel pour le profil %s",
            profil.pk,
        )

        messages.error(
            request,
            "Impossible d'envoyer l'e-mail.",
        )

    return redirect("modifier_agent", pk=profil.pk)




@login_required
def qualifications_agent(request, pk):
    from django.db import OperationalError

    from .formulaires_agents import QualificationsAgentForm
    from .services.competences import (
        empreinte_qualifications,
        verifier_empreinte_qualifications,
        verifier_cible_qualification,
        appliquer_modifications_collectives,
    )

    if not peut_gerer_qualifications(request.user):
        raise PermissionDenied("Accès interdit.")

    profil = get_object_or_404(
        ProfilAgent.objects.select_related(
            "utilisateur", "grade"
        ),
        pk=pk,
    )

    verifier_cible_qualification(
        request.user, profil
    )

    if request.method == "POST":
        empreinte = request.POST.get("empreinte", "")

        formulaire = QualificationsAgentForm(
            request.POST,
            profil=profil,
            validateur=request.user,
        )

        try:
            with transaction.atomic():
                verifier_empreinte_qualifications(
                    profil, empreinte
                )

                formulaire = QualificationsAgentForm(
                    request.POST,
                    profil=profil,
                    validateur=request.user,
                )

                if formulaire.is_valid():
                    operations = formulaire.operations()

                    if operations:
                        appliquer_modifications_collectives(
                            operations=operations,
                            validateur_id=request.user.pk,
                        )

                    messages.success(
                        request,
                        "Les qualifications ont été enregistrées.",
                    )

                    return redirect(
                        "qualifications_agent",
                        pk=profil.pk,
                    )

        except ValidationError as erreur:
            formulaire.add_error(None, erreur)

        except OperationalError:
            logger.exception(
                "Conflit lors de la modification des qualifications"
            )

            formulaire.add_error(
                None,
                "Enregistrement impossible. Rechargez "
                "la fiche avant de recommencer.",
            )

    else:
        with transaction.atomic():
            empreinte = empreinte_qualifications(profil)

            formulaire = QualificationsAgentForm(
                profil=profil,
                validateur=request.user,
            )

    return render(
        request,
        "planning/qualifications_agent.html",
        {
            "profil": profil,
            "agent": profil.utilisateur,
            "formulaire": formulaire,
            "empreinte": empreinte,
            "qualifications_inactives": (
                profil.attributions_competences
                .filter(competence__active=False)
                .select_related("competence")
            ),
        },
    )


@login_required
def droits_agent(request, pk):
    from django.db import OperationalError

    from .autorisations import exiger_superutilisateur
    from .formulaires_agents import DroitsAgentForm
    from .services.droits import (
        preparer_confirmation_droits,
        confirmer_modification_droits,
    )

    exiger_superutilisateur(request.user)

    profil = obtenir_profil_modifiable(request, pk)

    if request.method == "POST":
        jeton = request.POST.get("jeton", "")

        formulaire = DroitsAgentForm(
            request.POST,
            profil=profil,
        )

        if formulaire.is_valid():
            try:
                changement = confirmer_modification_droits(
                    auteur_id=request.user.pk,
                    profil_id=profil.pk,
                    jeton=jeton,
                    **formulaire.donnees_droits(),
                )

            except ValidationError as erreur:
                formulaire.add_error(None, erreur)

            except OperationalError:
                logger.exception(
                    "Conflit lors de la modification des droits"
                )

                formulaire.add_error(
                    None,
                    "Enregistrement impossible. "
                    "Rechargez la fiche avant de recommencer.",
                )

            else:
                if changement:
                    messages.success(
                        request,
                        "Les droits de l'agent ont été modifiés.",
                    )
                else:
                    messages.info(
                        request,
                        "Aucun changement de droits.",
                    )

                return redirect(
                    "droits_agent",
                    pk=profil.pk,
                )

    else:
        with transaction.atomic():
            profil.refresh_from_db()

            formulaire = DroitsAgentForm(
                profil=profil,
            )

            jeton = preparer_confirmation_droits(
                auteur_id=request.user.pk,
                profil=profil,
            )

    return render(
        request,
        "planning/droits_agent.html",
        {
            "profil": profil,
            "agent": profil.utilisateur,
            "formulaire": formulaire,
            "jeton": jeton,
        },
    )
