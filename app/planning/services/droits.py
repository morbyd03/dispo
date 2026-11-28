from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.db import transaction

from ..autorisations import (
    GROUPE_ADMINISTRATEURS,
    PERMISSIONS_ADMINISTRATEURS,
    PERMISSIONS_DELEGATION_QUALIFICATIONS,
    exiger_superutilisateur,
    exiger_gestion_compte,
)
from ..models import ProfilAgent
from .agents import charger_auteur, verifier_identifiant
from .journal import journaliser


def permissions_delegables():
    return {
        identifiant: Permission.objects.get(
            content_type__app_label=identifiant.split(".", 1)[0],
            codename=identifiant.split(".", 1)[1],
        )
        for identifiant in PERMISSIONS_DELEGATION_QUALIFICATIONS
    }


def etat_droits_agent(utilisateur):
    permissions = permissions_delegables()

    return {
        "administrateur_dispo": utilisateur.groups.filter(
            name=GROUPE_ADMINISTRATEURS,
        ).exists(),
        "delegations": sorted(
            identifiant
            for identifiant, permission in permissions.items()
            if utilisateur.user_permissions.filter(
                pk=permission.pk
            ).exists()
        ),
    }


@transaction.atomic
def modifier_droits_agent(
    *,
    auteur_id,
    profil_id,
    administrateur_dispo,
    delegations=(),
):
    auteur = charger_auteur(auteur_id)
    exiger_superutilisateur(auteur)

    if not isinstance(administrateur_dispo, bool):
        raise ValidationError("Statut administrateur invalide.")

    if not isinstance(delegations, (list, tuple, set, frozenset)):
        raise ValidationError("Liste de delegations invalide.")

    if any(
        not isinstance(permission, str)
        or permission not in PERMISSIONS_DELEGATION_QUALIFICATIONS
        for permission in delegations
    ):
        raise ValidationError("Permission non delegable.")

    profil_id = verifier_identifiant(profil_id)

    profil = (
        ProfilAgent.objects
        .select_related("utilisateur")
        .filter(pk=profil_id)
        .first()
    )

    if profil is None:
        raise ValidationError("Profil agent inexistant.")

    utilisateur = profil.utilisateur

    exiger_gestion_compte(auteur, utilisateur)

    groupe = Group.objects.filter(
        name=GROUPE_ADMINISTRATEURS
    ).first()

    if groupe is None:
        raise ValidationError(
            "Le groupe administrateur doit etre initialise."
        )

    permissions_groupe = {
        f"{application}.{code}"
        for application, code in groupe.permissions.values_list(
            "content_type__app_label",
            "codename",
        )
    }

    if permissions_groupe != set(PERMISSIONS_ADMINISTRATEURS):
        raise ValidationError(
            "Le groupe administrateur contient des permissions "
            "non conformes. Relancez initialiser_dispo."
        )

    avant = etat_droits_agent(utilisateur)

    apres = {
        "administrateur_dispo": administrateur_dispo,
        "delegations": sorted(set(delegations)),
    }

    if avant == apres:
        return False

    if administrateur_dispo:
        utilisateur.groups.add(groupe)
    else:
        utilisateur.groups.remove(groupe)

    for identifiant, permission in permissions_delegables().items():
        if identifiant in apres["delegations"]:
            utilisateur.user_permissions.add(permission)
        else:
            utilisateur.user_permissions.remove(permission)

    journaliser(
        auteur=auteur,
        action="agent.modifier_droits",
        objet=profil,
        details={
            "avant": avant,
            "apres": apres,
        },
    )

    return True


SIGNATURE_DROITS = "planning.droits_agent.v1"
DUREE_CONFIRMATION_DROITS = 1800


def empreinte_droits_agent(profil):
    import hashlib
    import json

    utilisateur = profil.utilisateur

    etat = {
        "profil_id": profil.pk,
        "utilisateur_id": utilisateur.pk,
        "actif": utilisateur.is_active,
        "staff": utilisateur.is_staff,
        "superutilisateur": utilisateur.is_superuser,
        "groupes": list(
            utilisateur.groups.order_by("pk")
            .values_list("pk", "name")
        ),
        "permissions_individuelles": list(
            utilisateur.user_permissions.order_by("pk")
            .values_list("pk", flat=True)
        ),
        "permissions_groupes": list(
            Permission.objects.filter(
                group__user=utilisateur,
            ).order_by("pk")
            .values_list("pk", flat=True)
            .distinct()
        ),
    }

    contenu = json.dumps(
        etat,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(contenu).hexdigest()


def preparer_confirmation_droits(*, auteur_id, profil):
    from django.core import signing

    auteur = charger_auteur(auteur_id)

    exiger_superutilisateur(auteur)
    exiger_gestion_compte(auteur, profil.utilisateur)

    return signing.dumps(
        {
            "auteur_id": auteur.pk,
            "profil_id": profil.pk,
            "empreinte": empreinte_droits_agent(profil),
        },
        salt=SIGNATURE_DROITS,
    )


def verifier_confirmation_droits(*, auteur_id, profil, jeton):
    from django.core import signing
    from hmac import compare_digest

    auteur = charger_auteur(auteur_id)

    exiger_superutilisateur(auteur)
    exiger_gestion_compte(auteur, profil.utilisateur)

    if not isinstance(jeton, str) or not jeton:
        raise ValidationError(
            "Confirmation des droits manquante."
        )

    try:
        donnees = signing.loads(
            jeton,
            salt=SIGNATURE_DROITS,
            max_age=DUREE_CONFIRMATION_DROITS,
        )
    except signing.SignatureExpired as erreur:
        raise ValidationError(
            "Le formulaire a expiré. Rechargez la fiche."
        ) from erreur
    except signing.BadSignature as erreur:
        raise ValidationError(
            "Confirmation des droits invalide."
        ) from erreur

    if (
        not isinstance(donnees, dict)
        or donnees.get("auteur_id") != auteur.pk
        or donnees.get("profil_id") != profil.pk
        or not isinstance(donnees.get("empreinte"), str)
    ):
        raise ValidationError(
            "Confirmation des droits invalide."
        )

    actuelle = empreinte_droits_agent(profil)

    if not compare_digest(
        actuelle,
        donnees["empreinte"],
    ):
        raise ValidationError(
            "Les droits du compte ont changé depuis "
            "l'ouverture du formulaire. Rechargez la fiche."
        )


@transaction.atomic
def confirmer_modification_droits(
    *,
    auteur_id,
    profil_id,
    jeton,
    administrateur_dispo,
    delegations=(),
):
    auteur = charger_auteur(auteur_id)
    exiger_superutilisateur(auteur)

    profil_id = verifier_identifiant(profil_id)

    profil = (
        ProfilAgent.objects
        .select_related("utilisateur")
        .filter(pk=profil_id)
        .first()
    )

    if profil is None:
        raise ValidationError("Profil agent inexistant.")

    verifier_confirmation_droits(
        auteur_id=auteur.pk,
        profil=profil,
        jeton=jeton,
    )

    return modifier_droits_agent(
        auteur_id=auteur.pk,
        profil_id=profil.pk,
        administrateur_dispo=administrateur_dispo,
        delegations=delegations,
    )
