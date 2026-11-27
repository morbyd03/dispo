from django.core.exceptions import ValidationError
from django.core.validators import validate_email


def normaliser_matricule(valeur):
    matricule = str(valeur or "").strip()

    if not matricule:
        raise ValidationError("Le matricule est obligatoire.")

    if len(matricule) > 150:
        raise ValidationError("Le matricule est trop long.")

    if not matricule.isascii() or not matricule.isdigit():
        raise ValidationError(
            "Le matricule doit contenir uniquement des chiffres."
        )

    return matricule


def normaliser_email(valeur):
    email = str(valeur or "").strip().lower()

    if not email:
        raise ValidationError("L'adresse e-mail est obligatoire.")

    if not email.isascii():
        raise ValidationError(
            "L'adresse e-mail doit utiliser des caracteres ASCII."
        )

    if len(email) > 254:
        raise ValidationError("L'adresse e-mail est trop longue.")

    validate_email(email)

    return email


def normaliser_nom(valeur):
    nom = " ".join(str(valeur or "").split())

    if not nom:
        raise ValidationError("Le nom est obligatoire.")

    if len(nom) > 150:
        raise ValidationError("Le nom est trop long.")

    return nom


def normaliser_prenom(valeur):
    prenom = " ".join(str(valeur or "").split())

    if not prenom:
        raise ValidationError("Le prenom est obligatoire.")

    if len(prenom) > 150:
        raise ValidationError("Le prenom est trop long.")

    return prenom


def verifier_matricule_unique(valeur, utilisateur_id=None):
    from django.contrib.auth import get_user_model

    matricule = normaliser_matricule(valeur)

    comptes = get_user_model().objects.filter(
        username=matricule
    )

    if utilisateur_id is not None:
        comptes = comptes.exclude(pk=utilisateur_id)

    if comptes.exists():
        raise ValidationError(
            "Ce matricule est déjà utilisé."
        )

    return matricule


def verifier_email_unique(valeur, utilisateur_id=None):
    from django.contrib.auth import get_user_model
    from django.db.models.functions import Lower, Trim

    email = normaliser_email(valeur)

    comptes = get_user_model().objects.annotate(
        email_normalise=Lower(Trim("email"))
    ).filter(email_normalise=email)

    if utilisateur_id is not None:
        comptes = comptes.exclude(pk=utilisateur_id)

    if comptes.exists():
        raise ValidationError(
            "Cette adresse e-mail est déjà utilisée."
        )

    return email
