from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from ..identites import (
    verifier_matricule_unique,
    verifier_email_unique,
    normaliser_nom,
    normaliser_prenom,
)
from ..models import Grade, ProfilAgent, FonctionAgent


def verifier_identifiant(valeur):
    if isinstance(valeur, bool):
        raise ValidationError("Identifiant invalide.")

    if isinstance(valeur, int):
        identifiant = valeur
    elif isinstance(valeur, str):
        valeur = valeur.strip()

        if not valeur.isascii() or not valeur.isdigit():
            raise ValidationError("Identifiant invalide.")

        if len(valeur) > 19:
            raise ValidationError("Identifiant invalide.")

        identifiant = int(valeur)
    else:
        raise ValidationError("Identifiant invalide.")

    if not 0 < identifiant <= 9223372036854775807:
        raise ValidationError("Identifiant invalide.")

    return identifiant


def verifier_profil(grade_id, telephone, fonctions_ids, profil=None):
    telephone = str(telephone or "").strip()

    if len(telephone) > 30:
        raise ValidationError(
            "Le numéro de téléphone est trop long."
        )

    grade_id = verifier_identifiant(grade_id)

    grade = Grade.objects.filter(pk=grade_id).first()

    if grade is not None and not grade.active:
        if profil is None or profil.grade_id != grade.pk:
            grade = None

    if grade is None:
        raise ValidationError(
            "Un grade actif est obligatoire."
        )

    try:
        fonctions_ids = {
            verifier_identifiant(identifiant) for identifiant in fonctions_ids
        }
    except (TypeError, ValueError):
        raise ValidationError(
            "Identifiants de fonctions invalides."
        )

    fonctions = list(
        FonctionAgent.objects.filter(pk__in=fonctions_ids)
    )

    anciennes_fonctions = (
        set(profil.fonctions.values_list("pk", flat=True))
        if profil is not None else set()
    )

    fonctions = [
        fonction for fonction in fonctions
        if fonction.active or fonction.pk in anciennes_fonctions
    ]

    if len(fonctions) != len(fonctions_ids):
        raise ValidationError(
            "Une ou plusieurs fonctions sont invalides ou inactives."
        )

    return grade, telephone, fonctions


def creer_agent(
    *,
    matricule,
    nom,
    prenom,
    email,
    grade_id,
    telephone="",
    actif=True,
    fonctions_ids=(),
):
    try:
        with transaction.atomic():
            matricule = verifier_matricule_unique(matricule)
            email = verifier_email_unique(email)
            nom = normaliser_nom(nom)
            prenom = normaliser_prenom(prenom)
            grade, telephone, fonctions = verifier_profil(
                grade_id, telephone, fonctions_ids
            )

            utilisateur = get_user_model().objects.create_user(
                username=matricule,
                first_name=prenom,
                last_name=nom,
                email=email,
                password=None,
                is_active=actif,
                is_staff=False,
                is_superuser=False,
            )

            profil = ProfilAgent.objects.create(
                utilisateur=utilisateur,
                grade=grade,
                telephone=telephone,
            )

            profil.fonctions.set(fonctions)

            return profil

    except IntegrityError as erreur:
        raise ValidationError(
            "Impossible de créer cet agent : conflit de données."
        ) from erreur


def modifier_agent(
    *,
    profil_id,
    nom,
    prenom,
    grade_id,
    telephone,
    fonctions_ids,
):
    try:
        with transaction.atomic():
            profil_id = verifier_identifiant(profil_id)

            profil = ProfilAgent.objects.select_related(
                "utilisateur"
            ).filter(pk=profil_id).first()

            if profil is None:
                raise ValidationError(
                    "Ce profil agent n'existe pas."
                )

            nom = normaliser_nom(nom)
            prenom = normaliser_prenom(prenom)

            grade, telephone, fonctions = verifier_profil(
                grade_id, telephone, fonctions_ids, profil=profil
            )

            utilisateur = profil.utilisateur

            utilisateur.last_name = nom
            utilisateur.first_name = prenom

            utilisateur.save(
                update_fields=["last_name", "first_name"]
            )

            profil.grade = grade
            profil.telephone = telephone

            profil.save(
                update_fields=["grade", "telephone"]
            )

            profil.fonctions.set(fonctions)

            return profil

    except IntegrityError as erreur:
        raise ValidationError(
            "Impossible de modifier cet agent : conflit de données."
        ) from erreur
