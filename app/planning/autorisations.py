from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied


GROUPE_ADMINISTRATEURS = "Administrateurs Dispo"

PERMISSIONS_ADMINISTRATEURS = (
    "auth.add_user",
    "auth.change_user",
    "auth.view_user",
    "planning.add_competenceagent",
    "planning.change_competenceagent",
    "planning.delete_competenceagent",
    "planning.view_competenceagent",
)

PERMISSIONS_DELEGATION_QUALIFICATIONS = (
    "planning.add_competenceagent",
    "planning.change_competenceagent",
    "planning.delete_competenceagent",
)



def utilisateur_actif(utilisateur):
    return (
        utilisateur is not None
        and utilisateur.is_authenticated
        and utilisateur.is_active
    )


def est_superutilisateur(utilisateur):
    return (
        utilisateur_actif(utilisateur)
        and utilisateur.is_superuser
    )


def est_administrateur_dispo(utilisateur):
    if not utilisateur_actif(utilisateur):
        return False

    return (
        utilisateur.is_superuser
        or utilisateur.groups.filter(
            name=GROUPE_ADMINISTRATEURS
        ).exists()
    )


def exiger_permission(utilisateur, permission):
    if not utilisateur_actif(utilisateur):
        raise PermissionDenied("Compte non autorise.")

    if not utilisateur.has_perm(permission):
        raise PermissionDenied(
            "Vous ne disposez pas des autorisations necessaires."
        )


def exiger_administrateur_dispo(utilisateur):
    if not est_administrateur_dispo(utilisateur):
        raise PermissionDenied(
            "Cette operation necessite un administrateur Dispo."
        )


def exiger_superutilisateur(utilisateur):
    if not est_superutilisateur(utilisateur):
        raise PermissionDenied(
            "Cette operation est reservee aux superutilisateurs."
        )


def compte_privilegie(utilisateur):
    return (
        utilisateur.is_superuser
        or utilisateur.is_staff
        or utilisateur.groups.exists()
        or utilisateur.user_permissions.exists()
    )


def exiger_gestion_compte(auteur, cible):
    exiger_administrateur_dispo(auteur)

    if auteur.pk == cible.pk:
        raise PermissionDenied(
            "Vous ne pouvez pas administrer votre propre compte ici."
        )

    if cible.is_staff or cible.is_superuser:
        raise PermissionDenied(
            "Ce compte technique est protege."
        )

    if compte_privilegie(cible) and not auteur.is_superuser:
        raise PermissionDenied(
            "Ce compte necessite un superutilisateur."
        )


def peut_gerer_qualifications(utilisateur):
    return (
        utilisateur.is_authenticated
        and utilisateur.is_active
        and any(
            utilisateur.has_perm(permission)
            for permission in PERMISSIONS_DELEGATION_QUALIFICATIONS
        )
    )


def peut_consulter_gestion_agents(utilisateur):
    return (
        est_administrateur_dispo(utilisateur)
        and utilisateur.has_perm("auth.view_user")
    )
