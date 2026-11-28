from datetime import date, datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import IntegrityError, transaction

from ..models import (
    ProfilAgent,
    Competence,
    CompetenceAgent,
)
from .agents import verifier_identifiant
from ..autorisations import (
    exiger_permission,
    compte_privilegie,
)
from .journal import journaliser


def verifier_date(valeur):
    if valeur is None or valeur == "":
        return None

    if isinstance(valeur, date) and not isinstance(valeur, datetime):
        return valeur

    if isinstance(valeur, str):
        try:
            return date.fromisoformat(valeur)
        except ValueError:
            pass

    raise ValidationError("Date invalide.")


def attribuer_competence(
    *,
    profil_id,
    competence_id,
    validateur_id,
    date_validation=None,
    date_expiration=None,
):
    try:
        with transaction.atomic():
            profil_id = verifier_identifiant(profil_id)
            competence_id = verifier_identifiant(competence_id)
            validateur_id = verifier_identifiant(validateur_id)

            profil = ProfilAgent.objects.filter(
                pk=profil_id
            ).first()

            if profil is None:
                raise ValidationError("Profil agent inexistant.")

            competence = Competence.objects.filter(
                pk=competence_id,
                active=True,
            ).first()

            if competence is None:
                raise ValidationError(
                    "Compétence inexistante ou inactive."
                )

            validateur = verifier_validateur(
                validateur_id, "add_competenceagent"
            )

            verifier_cible_qualification(validateur, profil)

            date_validation = verifier_date(date_validation)
            date_expiration = verifier_date(date_expiration)

            if (
                date_validation is not None
                and date_expiration is not None
                and date_expiration < date_validation
            ):
                raise ValidationError(
                    "La date d'expiration précède la validation."
                )

            if CompetenceAgent.objects.filter(
                profil=profil,
                competence=competence,
            ).exists():
                raise ValidationError(
                    "Cette compétence est déjà attribuée."
                )

            attribution = CompetenceAgent.objects.create(
                profil=profil,
                competence=competence,
                valide_par=validateur,
                date_validation=date_validation,
                date_expiration=date_expiration,
            )

            journaliser(
                auteur=validateur,
                action="competence.attribuer",
                objet=attribution,
                details=etat_attribution(attribution),
            )

            return attribution

    except IntegrityError as erreur:
        raise ValidationError(
            "Impossible d'attribuer cette compétence : conflit de données."
        ) from erreur


def verifier_validateur(validateur_id, permission):
    validateur_id = verifier_identifiant(validateur_id)

    validateur = get_user_model().objects.filter(
        pk=validateur_id,
        is_active=True,
    ).first()

    if validateur is None:
        raise ValidationError("Validateur invalide.")

    exiger_permission(validateur, f"planning.{permission}")

    return validateur


def verifier_cible_qualification(validateur, profil):
    cible = profil.utilisateur

    if validateur.pk == cible.pk:
        raise PermissionDenied(
            "Vous ne pouvez pas valider vos propres qualifications."
        )

    if cible.is_staff or cible.is_superuser:
        raise PermissionDenied("Ce compte technique est protege.")

    if compte_privilegie(cible) and not validateur.is_superuser:
        raise PermissionDenied(
            "Ce compte necessite un superutilisateur."
        )


def modifier_competence(
    *,
    attribution_id,
    validateur_id,
    date_validation,
    date_expiration,
    retourner_changement=False,
):
    try:
        with transaction.atomic():
            validateur = verifier_validateur(
                validateur_id, "change_competenceagent"
            )

            attribution_id = verifier_identifiant(attribution_id)

            attribution = CompetenceAgent.objects.filter(
                pk=attribution_id
            ).first()

            if attribution is None:
                raise ValidationError(
                    "Cette attribution n'existe pas."
                )

            verifier_cible_qualification(
                validateur, attribution.profil
            )

            date_validation = verifier_date(date_validation)
            date_expiration = verifier_date(date_expiration)

            if (
                date_validation is not None
                and date_expiration is not None
                and date_expiration < date_validation
            ):
                raise ValidationError(
                    "La date d'expiration précède la validation."
                )

            if (
                attribution.date_validation == date_validation
                and attribution.date_expiration == date_expiration
            ):
                return (attribution, False) if retourner_changement else attribution

            avant = etat_attribution(attribution)

            attribution.date_validation = date_validation
            attribution.date_expiration = date_expiration
            attribution.valide_par = validateur

            attribution.save(update_fields=[
                "date_validation",
                "date_expiration",
                "valide_par",
            ])

            journaliser(
                auteur=validateur,
                action="competence.modifier",
                objet=attribution,
                details={
                    "avant": avant,
                    "apres": etat_attribution(attribution),
                },
            )

            return (attribution, True) if retourner_changement else attribution

    except IntegrityError as erreur:
        raise ValidationError(
            "Impossible de modifier cette compétence : conflit de données."
        ) from erreur


def etat_attribution(attribution):
    return {
        "profil_id": attribution.profil_id,
        "competence_id": attribution.competence_id,
        "validateur_id": attribution.valide_par_id,
        "date_validation": (
            attribution.date_validation.isoformat()
            if attribution.date_validation else None
        ),
        "date_expiration": (
            attribution.date_expiration.isoformat()
            if attribution.date_expiration else None
        ),
    }


def retirer_competence(*, attribution_id, validateur_id):
    try:
        with transaction.atomic():
            validateur = verifier_validateur(
                validateur_id, "delete_competenceagent"
            )

            attribution_id = verifier_identifiant(attribution_id)

            attribution = CompetenceAgent.objects.filter(
                pk=attribution_id
            ).first()

            if attribution is None:
                raise ValidationError(
                    "Cette attribution n'existe pas."
                )

            verifier_cible_qualification(
                validateur, attribution.profil
            )

            journaliser(
                auteur=validateur,
                action="competence.retirer",
                objet=attribution,
                details=etat_attribution(attribution),
            )

            attribution.delete()

    except IntegrityError as erreur:
        raise ValidationError(
            "Impossible de retirer cette compétence : conflit de données."
        ) from erreur


def appliquer_modifications_collectives(*, operations, validateur_id):
    if not isinstance(operations, (list, tuple)):
        raise ValidationError("Liste d'opérations invalide.")

    resultats = {
        "attributions": 0,
        "modifications": 0,
        "retraits": 0,
        "inchanges": 0,
    }

    with transaction.atomic():
        for operation in operations:
            if not isinstance(operation, dict):
                raise ValidationError("Opération invalide.")

            action = operation.get("action")

            if action == "attribuer":
                attribuer_competence(
                    profil_id=operation.get("profil_id"),
                    competence_id=operation.get("competence_id"),
                    validateur_id=validateur_id,
                    date_validation=operation.get("date_validation"),
                    date_expiration=operation.get("date_expiration"),
                )

                resultats["attributions"] += 1

            elif action == "modifier":
                if not {
                    "date_validation", "date_expiration"
                }.issubset(operation):
                    raise ValidationError(
                        "Les deux dates doivent être renseignées explicitement."
                    )

                _, changement = modifier_competence(
                    attribution_id=operation.get("attribution_id"),
                    validateur_id=validateur_id,
                    date_validation=operation["date_validation"],
                    date_expiration=operation["date_expiration"],
                    retourner_changement=True,
                )

                if changement:
                    resultats["modifications"] += 1
                else:
                    resultats["inchanges"] += 1

            elif action == "retirer":
                retirer_competence(
                    attribution_id=operation.get("attribution_id"),
                    validateur_id=validateur_id,
                )

                resultats["retraits"] += 1

            else:
                raise ValidationError("Action collective inconnue.")

    return resultats


def empreinte_qualifications(profil):
    import hashlib
    import json

    catalogue = list(
        Competence.objects.order_by("pk").values(
            "pk",
            "code",
            "nom",
            "categorie",
            "active",
        )
    )

    attributions = [
        {
            "id": attribution.pk,
            **etat_attribution(attribution),
        }
        for attribution in (
            CompetenceAgent.objects
            .filter(profil=profil)
            .order_by("pk")
        )
    ]

    etat = {
        "profil_id": profil.pk,
        "catalogue": catalogue,
        "attributions": attributions,
    }

    contenu = json.dumps(
        etat,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(contenu).hexdigest()


def verifier_empreinte_qualifications(profil, empreinte):
    from hmac import compare_digest

    if (
        not isinstance(empreinte, str)
        or len(empreinte) != 64
        or any(c not in "0123456789abcdef" for c in empreinte)
    ):
        raise ValidationError(
            "Etat initial des qualifications invalide."
        )

    actuelle = empreinte_qualifications(profil)

    if not compare_digest(actuelle, empreinte):
        raise ValidationError(
            "Les qualifications ou leur catalogue ont été "
            "modifiés depuis l'ouverture du formulaire. "
            "Rechargez la fiche avant de recommencer."
        )
