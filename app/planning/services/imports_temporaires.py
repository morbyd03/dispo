from datetime import timedelta
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from ..models import ImportAgentTemporaire

from .import_agents import (
    TAILLE_MAXIMALE,
    DUREE_CONFIRMATION_IMPORT,
    verifier_autorisation_import,
    preparer_confirmation_import,
)

from .securite import version_securite_compte


@transaction.atomic
def preparer_import_temporaire(
    *,
    contenu,
    utilisateur_id,
):
    utilisateur = verifier_autorisation_import(
        utilisateur_id
    )

    if not isinstance(contenu, bytes):
        raise ValidationError(
            "Format de fichier invalide."
        )

    if not contenu:
        raise ValidationError(
            "Le fichier est vide."
        )

    if len(contenu) > TAILLE_MAXIMALE:
        raise ValidationError(
            "Le fichier depasse la taille maximale autorisee."
        )

    maintenant = timezone.now()

    preparation = preparer_confirmation_import(
        contenu=contenu,
        utilisateur_id=utilisateur.pk,
    )

    previsualisation = preparation["previsualisation"]

    changements_email = any(
        ligne["changement_email"]
        for ligne in previsualisation["lignes"]
    )

    ImportAgentTemporaire.objects.filter(
        expire_le__lte=maintenant
    ).delete()

    ImportAgentTemporaire.objects.filter(
        utilisateur=utilisateur
    ).delete()

    resultat = {
        "previsualisation": previsualisation,
        "identifiant": None,
        "confirmable": False,
        "changements_email": changements_email,
    }

    if (
        not previsualisation["valide"]
        or not preparation["jeton"]
        or changements_email
    ):
        return resultat

    temporaire = ImportAgentTemporaire.objects.create(
        utilisateur=utilisateur,
        identifiant=uuid4().hex,
        contenu=contenu,
        jeton=preparation["jeton"],
        version_securite=version_securite_compte(
            utilisateur.pk
        ),
        expire_le=maintenant + timedelta(
            seconds=DUREE_CONFIRMATION_IMPORT
        ),
    )

    resultat["identifiant"] = temporaire.identifiant
    resultat["confirmable"] = True

    return resultat


def obtenir_import_temporaire(
    *,
    utilisateur_id,
    identifiant,
):
    utilisateur = verifier_autorisation_import(
        utilisateur_id
    )

    if (
        not isinstance(identifiant, str)
        or len(identifiant) != 32
        or any(c not in "0123456789abcdef" for c in identifiant)
    ):
        raise ValidationError(
            "Identifiant d'import invalide."
        )

    temporaire = ImportAgentTemporaire.objects.filter(
        utilisateur=utilisateur,
        identifiant=identifiant,
    ).first()

    if temporaire is None:
        raise ValidationError(
            "Import temporaire introuvable."
        )

    if temporaire.expire_le <= timezone.now():
        raise ValidationError(
            "Cette previsualisation a expire."
        )

    if temporaire.version_securite != version_securite_compte(
        utilisateur.pk
    ):
        raise ValidationError(
            "Cette previsualisation a ete revoquee."
        )

    return temporaire


@transaction.atomic
def confirmer_import_temporaire(
    *,
    utilisateur_id,
    identifiant,
    confirmer_retraits=False,
):
    from .import_agents import executer_import_agents

    if type(confirmer_retraits) is not bool:
        raise ValidationError(
            "Confirmation des retraits invalide."
        )

    temporaire = obtenir_import_temporaire(
        utilisateur_id=utilisateur_id,
        identifiant=identifiant,
    )

    bilan = executer_import_agents(
        contenu=bytes(temporaire.contenu),
        utilisateur_id=utilisateur_id,
        jeton=temporaire.jeton,
        confirmer_retraits=confirmer_retraits,
    )

    temporaire.delete()

    return bilan


@transaction.atomic
def annuler_import_temporaire(
    *,
    utilisateur_id,
    identifiant,
):
    utilisateur = verifier_autorisation_import(
        utilisateur_id
    )

    nombre, _ = ImportAgentTemporaire.objects.filter(
        utilisateur=utilisateur,
        identifiant=identifiant,
    ).delete()

    return nombre > 0


@transaction.atomic
def purger_imports_temporaires():
    maintenant = timezone.now()

    nombre, _ = ImportAgentTemporaire.objects.filter(
        expire_le__lte=maintenant
    ).delete()

    temporaires = ImportAgentTemporaire.objects.select_related(
        "utilisateur"
    )

    for temporaire in temporaires:
        utilisateur = temporaire.utilisateur

        if (
            not utilisateur.is_active
            or not utilisateur.is_superuser
            or temporaire.version_securite
            != version_securite_compte(utilisateur.pk)
        ):
            supprimes, _ = temporaire.delete()
            nombre += supprimes

    return nombre
