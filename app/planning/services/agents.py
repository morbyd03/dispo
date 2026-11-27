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


def verifier_profil(grade_id, telephone, fonctions_ids):
    telephone = str(telephone or "").strip()

    if len(telephone) > 30:
        raise ValidationError(
            "Le numéro de téléphone est trop long."
        )

    grade = Grade.objects.filter(
        pk=grade_id,
        active=True,
    ).first()

    if grade is None:
        raise ValidationError(
            "Un grade actif est obligatoire."
        )

    try:
        fonctions_ids = {
            int(identifiant) for identifiant in fonctions_ids
        }
    except (TypeError, ValueError):
        raise ValidationError(
            "Identifiants de fonctions invalides."
        )

    fonctions = list(
        FonctionAgent.objects.filter(
            pk__in=fonctions_ids,
            active=True,
        )
    )

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
