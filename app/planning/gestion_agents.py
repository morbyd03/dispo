from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render


@login_required
@permission_required("auth.view_user", raise_exception=True)
def liste_agents(request):
    User = get_user_model()

    agents = (
        User.objects
        .prefetch_related("competences_agent__competence")
        .order_by("last_name", "first_name", "username")
    )

    peut_modifier = (
        request.user.has_perm("auth.change_user")
        and (
            request.user.is_superuser
            or request.user.groups.filter(
                name="Administrateurs Dispo"
            ).exists()
        )
    )

    for agent in agents:
        agent.modification_autorisee = (
            peut_modifier
            and not agent.is_superuser
            and not agent.is_staff
            and agent.pk != request.user.pk
            and (
                request.user.is_superuser
                or not agent.groups.filter(
                    name="Administrateurs Dispo"
                ).exists()
            )
        )

    return render(
        request,
        "planning/gestion_agents.html",
        {"agents": agents},
    )


@login_required
def ajouter_agent(request):
    from django.contrib import messages
    from django.contrib.auth.models import Group
    from django.http import HttpResponseForbidden
    from django.shortcuts import redirect

    from .formulaires_agents import AgentForm

    autorise = (
        request.user.is_superuser
        or request.user.groups.filter(
            name="Administrateurs Dispo"
        ).exists()
    )

    if not autorise or not request.user.has_perm("auth.add_user"):
        return HttpResponseForbidden("Accès interdit.")

    if request.method == "POST":
        formulaire = AgentForm(request.POST)

        if formulaire.is_valid():
            agent = formulaire.save(commit=False)
            agent.set_unusable_password()
            agent.is_staff = False
            agent.is_superuser = False
            agent.save()

            from .activation_agents import envoyer_activation_agent

            try:
                envoyer_activation_agent(request, agent)
            except Exception:
                import logging
                logging.getLogger(__name__).exception(
                    "Échec de l'envoi de l'activation pour l'agent %s",
                    agent.pk,
                )
                messages.warning(
                    request,
                    "Agent créé, mais l'e-mail d'activation n'a pas pu être envoyé."
                )
            else:
                messages.success(
                    request,
                    "Agent créé. Un e-mail d'activation a été envoyé."
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
    from django.contrib import messages
    from django.http import HttpResponseForbidden
    from django.shortcuts import get_object_or_404, redirect

    from django.db import transaction

    from .formulaires_agents import AgentModificationForm
    from .droits_agents import enregistrer_droits_agent

    autorise = (
        request.user.is_superuser
        or request.user.groups.filter(
            name="Administrateurs Dispo"
        ).exists()
    )

    if not autorise or not request.user.has_perm("auth.change_user"):
        return HttpResponseForbidden("Accès interdit.")

    User = get_user_model()
    agent = get_object_or_404(User, pk=pk)

    if (
        agent.is_superuser
        or agent.is_staff
        or (
            not request.user.is_superuser
            and agent.groups.filter(
                name="Administrateurs Dispo"
            ).exists()
        )
    ):
        return HttpResponseForbidden(
            "Ce compte est protégé et ne peut pas être modifié ici."
        )

    if agent.pk == request.user.pk:
        return HttpResponseForbidden(
            "Vous ne pouvez pas modifier votre propre compte ici."
        )

    if request.method == "POST":
        formulaire = AgentModificationForm(
            request.POST,
            instance=agent,
            utilisateur_connecte=request.user,
        )

        if formulaire.is_valid():
            with transaction.atomic():
                formulaire.save()
                enregistrer_droits_agent(
                    agent,
                    formulaire,
                    request.user,
                )
            messages.success(
                request,
                "Les informations de l'agent ont été modifiées."
            )
            return redirect("liste_agents")
    else:
        formulaire = AgentModificationForm(
            instance=agent,
            utilisateur_connecte=request.user,
        )

    return render(
        request,
        "planning/modifier_agent.html",
        {
            "formulaire": formulaire,
            "agent": agent,
        },
    )


@login_required
def reinitialiser_agent(request, pk):
    from django.contrib import messages
    from django.http import HttpResponseForbidden, HttpResponseNotAllowed
    from django.shortcuts import get_object_or_404, redirect

    from .activation_agents import envoyer_reinitialisation_agent

    autorise = (
        request.user.is_superuser
        or request.user.groups.filter(
            name="Administrateurs Dispo"
        ).exists()
    )

    if not autorise or not request.user.has_perm("auth.change_user"):
        return HttpResponseForbidden("Accès interdit.")

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    User = get_user_model()
    agent = get_object_or_404(User, pk=pk)

    if (
        agent.is_superuser
        or agent.is_staff
        or agent.pk == request.user.pk
        or (
            not request.user.is_superuser
            and agent.groups.filter(
                name="Administrateurs Dispo"
            ).exists()
        )
    ):
        return HttpResponseForbidden("Ce compte est protégé.")

    if not agent.is_active or not agent.email:
        messages.error(
            request,
            "Le compte doit être actif et posséder une adresse e-mail."
        )
    else:
        try:
            resultat = envoyer_reinitialisation_agent(request, agent)

            if resultat == 1:
                messages.success(
                    request,
                    "E-mail de réinitialisation envoyé."
                )
            else:
                messages.error(request, "Aucun e-mail envoyé.")

        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Échec de la réinitialisation pour l'agent %s",
                agent.pk,
            )
            messages.error(
                request,
                "Impossible d'envoyer l'e-mail de réinitialisation."
            )

    return redirect("modifier_agent", pk=agent.pk)
