from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.db import transaction

from .models import CompetenceAgent


@transaction.atomic
def enregistrer_droits_agent(agent, formulaire, utilisateur):

    if not utilisateur.has_perm("auth.change_user"):
        raise PermissionDenied

    if not (
        utilisateur.is_superuser
        or utilisateur.groups.filter(
            name="Administrateurs Dispo"
        ).exists()
    ):
        raise PermissionDenied

    if (
        agent.is_superuser
        or agent.is_staff
        or agent.pk == utilisateur.pk
    ):
        raise PermissionDenied

    if (
        not utilisateur.is_superuser
        and agent.groups.filter(
            name="Administrateurs Dispo"
        ).exists()
    ):
        raise PermissionDenied

    selection = set(
        formulaire.cleaned_data["competences"]
        .values_list("pk", flat=True)
    )

    existantes = CompetenceAgent.objects.filter(
        agent=agent,
        competence__active=True,
    )

    actuelles = set(
        existantes.values_list("competence_id", flat=True)
    )

    a_ajouter = selection - actuelles
    a_retirer = actuelles - selection

    if a_ajouter:
        if not utilisateur.has_perm("planning.add_competenceagent"):
            raise PermissionDenied

        for competence_id in a_ajouter:
            CompetenceAgent.objects.create(
                agent=agent,
                competence_id=competence_id,
                valide_par=utilisateur,
                date_validation=formulaire.cleaned_data[
                    f"date_validation_{competence_id}"
                ],
                date_expiration=formulaire.cleaned_data[
                    f"date_expiration_{competence_id}"
                ],
            )

    for attribution in existantes.filter(
        competence_id__in=selection & actuelles
    ):
        competence_id = attribution.competence_id

        debut = formulaire.cleaned_data[
            f"date_validation_{competence_id}"
        ]
        fin = formulaire.cleaned_data[
            f"date_expiration_{competence_id}"
        ]

        if (
            attribution.date_validation != debut
            or attribution.date_expiration != fin
        ):
            if not utilisateur.has_perm(
                "planning.change_competenceagent"
            ):
                raise PermissionDenied

            attribution.date_validation = debut
            attribution.date_expiration = fin

            attribution.save(
                update_fields=[
                    "date_validation",
                    "date_expiration",
                ]
            )

    if a_retirer:
        if not utilisateur.has_perm("planning.delete_competenceagent"):
            raise PermissionDenied

        existantes.filter(
            competence_id__in=a_retirer
        ).delete()

    if utilisateur.is_superuser:
        groupe = Group.objects.get(
            name="Administrateurs Dispo"
        )

        if formulaire.cleaned_data["administrateur_dispo"]:
            agent.groups.add(groupe)
        else:
            agent.groups.remove(groupe)
