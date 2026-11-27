import csv
import io
import re

from django.core.exceptions import ValidationError

from ..models import ProfilAgent, Competence
from .import_agents import (
    verifier_autorisation_import,
    analyser_colonnes_import,
)


COLONNES_EXPORT = (
    "matricule",
    "nom",
    "prenom",
    "grade",
    "email",
    "telephone",
    "fonction",
)


def securiser_cellule_csv(valeur):
    valeur = str(valeur or "")

    if valeur.lstrip().startswith(
        ("=", "+", "-", "@")
    ) or valeur.startswith(("\t", "\r", "\n")):
        return "'" + valeur

    return valeur


def exporter_agents_csv(
    *,
    utilisateur_id,
    mode="consultation",
):
    if mode not in ("consultation", "reimport"):
        raise ValidationError("Mode d'export invalide.")
    verifier_autorisation_import(utilisateur_id)

    competences = list(
        Competence.objects.filter(
            active=True
        ).order_by("code")
    )

    colonnes = list(COLONNES_EXPORT) + [
        competence.code.lower()
        for competence in competences
    ]

    analyser_colonnes_import(colonnes)

    profils = (
        ProfilAgent.objects
        .select_related("utilisateur", "grade")
        .prefetch_related(
            "fonctions",
            "attributions_competences",
        )
        .order_by(
            "utilisateur__last_name",
            "utilisateur__first_name",
            "utilisateur__username",
        )
    )

    fichier = io.StringIO(newline="")

    redacteur = csv.writer(
        fichier,
        delimiter=";",
        quoting=csv.QUOTE_ALL,
        lineterminator="\r\n",
    )

    redacteur.writerow(colonnes)

    for profil in profils:
        utilisateur = profil.utilisateur

        fonctions = list(profil.fonctions.all())

        if any("|" in fonction.nom for fonction in fonctions):
            raise ValidationError(
                "Une fonction contient un separateur incompatible."
            )

        qualifications = {
            attribution.competence_id
            for attribution in profil.attributions_competences.all()
        }

        ligne = [
            utilisateur.username,
            utilisateur.last_name,
            utilisateur.first_name,
            profil.grade.code if profil.grade else "",
            utilisateur.email,
            profil.telephone,
            "|".join(sorted(
                fonction.nom for fonction in fonctions
            )),
        ]

        if mode == "consultation":
            ligne = [
                securiser_cellule_csv(valeur)
                for valeur in ligne
            ]

        else:
            for colonne, valeur in zip(COLONNES_EXPORT, ligne):
                if securiser_cellule_csv(valeur) == valeur:
                    continue

                if (
                    colonne == "telephone"
                    and re.fullmatch(r"[+][0-9]{1,15}", valeur)
                ):
                    continue

                raise ValidationError(
                    "Export de reimport impossible : "
                    f"valeur potentiellement dangereuse dans {colonne}."
                )

        ligne.extend(
            "1" if competence.pk in qualifications else "0"
            for competence in competences
        )

        redacteur.writerow(ligne)

    contenu = fichier.getvalue().encode("utf-8-sig")

    if mode == "reimport":
        from .import_agents import previsualiser_import_agents

        resultat = previsualiser_import_agents(contenu)

        if not resultat["valide"]:
            raise ValidationError(
                "Export de reimport impossible : "
                "certains profils necessitent une regularisation."
            )

        for ligne in resultat["lignes"]:
            if (
                ligne["action"] != "modifier"
                or ligne["changements"]
                or ligne["operations_qualifications"]
            ):
                raise ValidationError(
                    "Export de reimport impossible : "
                    "le reimport modifierait les donnees existantes."
                )

    return contenu
