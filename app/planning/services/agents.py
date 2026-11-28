from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import IntegrityError, transaction

from ..autorisations import (
    exiger_administrateur_dispo,
    exiger_superutilisateur,
    exiger_permission,
    exiger_gestion_compte,
)
from ..identites import (
    verifier_matricule_unique,
    verifier_email_unique,
    normaliser_nom,
    normaliser_prenom,
)
from ..models import Grade, ProfilAgent, FonctionAgent
from .journal import (
    journaliser,
    etat_profil_agent,
    differences_etats,
)


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


def charger_auteur(auteur_id):
    auteur_id = verifier_identifiant(auteur_id)

    auteur = get_user_model().objects.filter(
        pk=auteur_id,
        is_active=True,
    ).first()

    if auteur is None:
        raise PermissionDenied("Auteur non autorise.")

    return auteur


def verifier_profil(grade_id, telephone, fonctions_ids, profil=None):
    telephone = str(telephone or "").strip()

    if len(telephone) > 30:
        raise ValidationError(
            "Le numero de telephone est trop long."
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

    if not isinstance(
        fonctions_ids, (list, tuple, set, frozenset)
    ):
        raise ValidationError("Liste de fonctions invalide.")

    fonctions_ids = {
        verifier_identifiant(identifiant)
        for identifiant in fonctions_ids
    }

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
    auteur_id,
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
            auteur = charger_auteur(auteur_id)

            exiger_administrateur_dispo(auteur)
            exiger_permission(auteur, "auth.add_user")

            if not isinstance(actif, bool):
                raise ValidationError("Statut du compte invalide.")

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

            journaliser(
                auteur=auteur,
                action="agent.creer",
                objet=profil,
                details={
                    "utilisateur_id": utilisateur.pk,
                    "grade_id": profil.grade_id,
                    "actif": utilisateur.is_active,
                },
            )

            return profil

    except IntegrityError as erreur:
        raise ValidationError(
            "Impossible de creer cet agent : conflit de donnees."
        ) from erreur


def modifier_agent(
    *,
    auteur_id,
    profil_id,
    nom,
    prenom,
    grade_id,
    telephone,
    fonctions_ids,
):
    try:
        with transaction.atomic():
            auteur = charger_auteur(auteur_id)

            exiger_administrateur_dispo(auteur)
            exiger_permission(auteur, "auth.change_user")

            profil_id = verifier_identifiant(profil_id)

            profil = ProfilAgent.objects.select_related(
                "utilisateur"
            ).filter(pk=profil_id).first()

            if profil is None:
                raise ValidationError(
                    "Ce profil agent n'existe pas."
                )

            exiger_gestion_compte(
                auteur, profil.utilisateur
            )

            nom = normaliser_nom(nom)
            prenom = normaliser_prenom(prenom)

            grade, telephone, fonctions = verifier_profil(
                grade_id,
                telephone,
                fonctions_ids,
                profil=profil,
            )

            avant = etat_profil_agent(profil)

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

            apres = etat_profil_agent(profil)

            changements = differences_etats(avant, apres)

            if changements:
                journaliser(
                    auteur=auteur,
                    action="agent.modifier",
                    objet=profil,
                    details={
                        "changements": changements,
                    },
                )

            return profil

    except IntegrityError as erreur:
        raise ValidationError(
            "Impossible de modifier cet agent : conflit de donnees."
        ) from erreur


def rattacher_profil_agent(
    *,
    auteur_id,
    utilisateur_id,
    grade_id,
    telephone="",
    fonctions_ids=(),
):
    try:
        with transaction.atomic():
            auteur = charger_auteur(auteur_id)

            exiger_superutilisateur(auteur)

            utilisateur_id = verifier_identifiant(
                utilisateur_id
            )

            utilisateur = get_user_model().objects.filter(
                pk=utilisateur_id
            ).first()

            if utilisateur is None:
                raise ValidationError(
                    "Ce compte utilisateur n'existe pas."
                )

            if ProfilAgent.objects.filter(
                utilisateur=utilisateur
            ).exists():
                raise ValidationError(
                    "Ce compte possede deja un profil agent."
                )

            if utilisateur.is_superuser or utilisateur.is_staff:
                raise ValidationError(
                    "Ce compte privilegie necessite un traitement specifique."
                )

            exiger_gestion_compte(auteur, utilisateur)

            verifier_matricule_unique(
                utilisateur.username, utilisateur.pk
            )

            verifier_email_unique(
                utilisateur.email, utilisateur.pk
            )

            normaliser_nom(utilisateur.last_name)
            normaliser_prenom(utilisateur.first_name)

            grade, telephone, fonctions = verifier_profil(
                grade_id, telephone, fonctions_ids
            )

            profil = ProfilAgent.objects.create(
                utilisateur=utilisateur,
                grade=grade,
                telephone=telephone,
            )

            profil.fonctions.set(fonctions)

            journaliser(
                auteur=auteur,
                action="agent.rattacher",
                objet=profil,
                details={
                    "utilisateur_id": utilisateur.pk,
                    "grade_id": profil.grade_id,
                },
            )

            return profil

    except IntegrityError as erreur:
        raise ValidationError(
            "Impossible de rattacher le profil : conflit de donnees."
        ) from erreur


@transaction.atomic
def modifier_statut_agent(*, auteur_id, profil_id, actif):
    from .journal import journaliser

    auteur = charger_auteur(auteur_id)

    exiger_administrateur_dispo(auteur)
    exiger_permission(auteur, "auth.change_user")

    if not isinstance(actif, bool):
        raise ValidationError("Statut du compte invalide.")

    profil_id = verifier_identifiant(profil_id)

    profil = ProfilAgent.objects.select_related(
        "utilisateur"
    ).filter(pk=profil_id).first()

    if profil is None:
        raise ValidationError("Ce profil agent n'existe pas.")

    utilisateur = profil.utilisateur

    exiger_gestion_compte(auteur, utilisateur)

    ancien_statut = utilisateur.is_active

    if ancien_statut == actif:
        return False

    utilisateur.is_active = actif
    utilisateur.save(update_fields=["is_active"])

    from .securite import revoquer_acces_compte

    revoquer_acces_compte(utilisateur.pk)

    journaliser(
        auteur=auteur,
        action="agent.activer" if actif else "agent.desactiver",
        objet=profil,
        details={
            "avant": ancien_statut,
            "apres": actif,
        },
    )

    return True
