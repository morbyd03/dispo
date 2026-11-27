import csv
import io

from django.core.exceptions import ValidationError


COLONNES_OBLIGATOIRES = {
    "matricule",
    "nom",
    "prenom",
    "grade",
}

COLONNES_FACULTATIVES = {
    "email",
    "telephone",
    "fonction",
}

TAILLE_MAXIMALE = 2 * 1024 * 1024
LIGNES_MAXIMALES = 1000


def lire_csv_agents(contenu):
    if not isinstance(contenu, bytes):
        raise ValidationError("Format de fichier invalide.")

    if len(contenu) > TAILLE_MAXIMALE:
        raise ValidationError("Le fichier CSV est trop volumineux.")

    try:
        texte = contenu.decode("utf-8-sig")
    except UnicodeDecodeError as erreur:
        raise ValidationError(
            "Le fichier doit être encodé en UTF-8."
        ) from erreur

    if not texte.strip():
        raise ValidationError("Le fichier CSV est vide.")

    try:
        dialecte = csv.Sniffer().sniff(
            texte.splitlines()[0],
            delimiters=";,",
        )

        lecteur = csv.reader(
            io.StringIO(texte, newline=""),
            dialect=dialecte,
            strict=True,
        )

        colonnes = [
            colonne.strip().lower()
            for colonne in next(lecteur)
        ]

        if len(colonnes) != len(set(colonnes)):
            raise ValidationError("Colonnes CSV en doublon.")

        manquantes = COLONNES_OBLIGATOIRES - set(colonnes)

        if manquantes:
            raise ValidationError(
                "Colonnes obligatoires manquantes : "
                + ", ".join(sorted(manquantes))
            )

        lignes = []

        for valeurs in lecteur:
            numero = lecteur.line_num

            if not any(valeur.strip() for valeur in valeurs):
                continue

            if len(valeurs) != len(colonnes):
                raise ValidationError(
                    f"Ligne {numero} : nombre de colonnes incorrect."
                )

            if len(lignes) >= LIGNES_MAXIMALES:
                raise ValidationError(
                    "Le fichier contient trop de lignes."
                )

            lignes.append({
                "ligne": numero,
                "donnees": dict(zip(
                    colonnes,
                    [valeur.strip() for valeur in valeurs],
                )),
            })

    except (csv.Error, StopIteration) as erreur:
        raise ValidationError(
            "Structure du fichier CSV invalide."
        ) from erreur

    if not lignes:
        raise ValidationError("Aucun agent dans le fichier.")

    return {
        "colonnes": colonnes,
        "lignes": lignes,
    }


def normaliser_fragment_email(valeur):
    import re
    import unicodedata

    valeur = valeur.lower()
    valeur = valeur.replace("œ", "oe").replace("æ", "ae")

    valeur = unicodedata.normalize("NFKD", valeur)

    valeur = "".join(
        caractere for caractere in valeur
        if not unicodedata.combining(caractere)
    )

    valeur = re.sub(r"['’]", "", valeur)
    valeur = re.sub(r"\s+", "-", valeur)
    valeur = re.sub(r"[^a-z0-9-]", "", valeur)
    valeur = re.sub(r"-+", "-", valeur)

    return valeur.strip("-")


def generer_email_agent(
    *,
    nom,
    prenom,
    matricule,
    modele,
):
    from ..identites import (
        normaliser_email,
        normaliser_nom,
        normaliser_prenom,
        normaliser_matricule,
    )
    from string import Formatter

    if not isinstance(modele, str) or not modele.strip():
        raise ValidationError(
            "Aucun modèle de génération d'e-mail configuré."
        )

    fragments = {
        "nom": normaliser_fragment_email(normaliser_nom(nom)),
        "prenom": normaliser_fragment_email(normaliser_prenom(prenom)),
        "matricule": normaliser_matricule(matricule),
    }

    try:
        for _, champ, formatage, conversion in Formatter().parse(modele):
            if champ is not None:
                if (
                    champ not in fragments
                    or formatage
                    or conversion
                    or not fragments[champ]
                ):
                    raise ValueError("Champ invalide")

        email = modele.format(**fragments)

    except (ValueError, KeyError) as erreur:
        raise ValidationError(
            "Modèle de génération d'e-mail invalide."
        ) from erreur

    return normaliser_email(email)


def analyser_colonnes_import(colonnes):
    from ..models import Competence

    colonnes_standard = (
        COLONNES_OBLIGATOIRES | COLONNES_FACULTATIVES
    )

    qualifications = {}

    for competence in Competence.objects.all():
        code = competence.code.lower()

        if code in qualifications:
            raise ValidationError(
                f"Code de qualification ambigu : {code}."
            )

        qualifications[code] = competence

    colonnes_qualifications = {}

    for colonne in colonnes:
        if colonne in colonnes_standard:
            if colonne in qualifications:
                raise ValidationError(
                    f"Collision entre qualification et colonne réservée : {colonne}."
                )

            continue

        competence = qualifications.get(colonne)

        if competence is None:
            raise ValidationError(
                f"Colonne inconnue : {colonne}."
            )

        if not competence.active:
            raise ValidationError(
                f"Qualification inactive : {colonne}."
            )

        colonnes_qualifications[colonne] = competence.pk

    return colonnes_qualifications


def analyser_qualifications_import(donnees, colonnes_qualifications):
    qualifications = {}

    for colonne, competence_id in colonnes_qualifications.items():
        valeur = donnees.get(colonne, "").strip()

        if valeur == "":
            continue

        if valeur not in ("0", "1"):
            raise ValidationError(
                f"Valeur invalide pour {colonne} : utiliser 0, 1 ou laisser vide."
            )

        qualifications[competence_id] = valeur == "1"

    return qualifications


def analyser_identite_import(donnees, modele_email=None):
    from django.contrib.auth import get_user_model

    from ..identites import (
        normaliser_matricule,
        normaliser_nom,
        normaliser_prenom,
        normaliser_email,
        verifier_email_unique,
    )
    from ..models import Grade, ProfilAgent

    matricule = normaliser_matricule(donnees["matricule"])
    nom = normaliser_nom(donnees["nom"])
    prenom = normaliser_prenom(donnees["prenom"])

    code_grade = donnees["grade"].strip().upper()

    grade = Grade.objects.filter(
        code=code_grade,
        active=True,
    ).first()

    if grade is None:
        raise ValidationError(
            f"Grade inconnu ou inactif : {code_grade}."
        )

    utilisateur = get_user_model().objects.filter(
        username=matricule,
    ).first()

    profil = None

    if utilisateur is not None:
        if utilisateur.is_staff or utilisateur.is_superuser:
            raise ValidationError(
                "Ce matricule correspond à un compte protégé."
            )

        profil = ProfilAgent.objects.filter(
            utilisateur=utilisateur,
        ).first()

    email = donnees.get("email", "").strip()
    email_genere = False

    if not email and utilisateur is not None:
        email = utilisateur.email

    if not email:
        email = generer_email_agent(
            nom=nom,
            prenom=prenom,
            matricule=matricule,
            modele=modele_email,
        )
        email_genere = True

    email = normaliser_email(email)

    verifier_email_unique(
        email,
        utilisateur_id=utilisateur.pk if utilisateur else None,
    )

    if utilisateur is None:
        action = "creer"
    elif profil is None:
        action = "rattacher"
    else:
        action = "modifier"

    return {
        "action": action,
        "matricule": matricule,
        "nom": nom,
        "prenom": prenom,
        "email": email,
        "email_genere": email_genere,
        "changement_email": (
            utilisateur is not None
            and utilisateur.email != email
        ),
        "grade_id": grade.pk,
        "grade": grade.code,
        "utilisateur_id": utilisateur.pk if utilisateur else None,
        "profil_id": profil.pk if profil else None,
    }


def analyser_profil_import(donnees, identite):
    from ..models import FonctionAgent, ProfilAgent
    from .agents import verifier_profil

    profil = None

    if identite["profil_id"] is not None:
        profil = ProfilAgent.objects.get(
            pk=identite["profil_id"]
        )

    telephone = donnees.get("telephone", "").strip()

    if not telephone and profil is not None:
        telephone = profil.telephone

    fonctions_ids = set()

    if profil is not None:
        fonctions_ids = set(
            profil.fonctions.values_list("pk", flat=True)
        )

    fonctions_saisies = donnees.get("fonction", "").strip()

    if fonctions_saisies:
        fonctions_ids = set()

        catalogue = {}

        for fonction in FonctionAgent.objects.all():
            cle = fonction.nom.strip().casefold()

            if cle in catalogue:
                raise ValidationError(
                    "Le catalogue contient des fonctions ambiguës."
                )

            catalogue[cle] = fonction

        for nom in fonctions_saisies.split("|"):
            nom = nom.strip()

            if not nom:
                raise ValidationError(
                    "Nom de fonction vide."
                )

            fonction = catalogue.get(nom.casefold())

            if fonction is None:
                raise ValidationError(
                    f"Fonction inconnue : {nom}."
                )

            fonctions_ids.add(fonction.pk)

    grade, telephone, fonctions = verifier_profil(
        identite["grade_id"],
        telephone,
        fonctions_ids,
        profil=profil,
    )

    return {
        "telephone": telephone,
        "fonctions_ids": sorted(
            fonction.pk for fonction in fonctions
        ),
        "fonctions": sorted(
            fonction.nom for fonction in fonctions
        ),
    }


def previsualiser_import_agents(contenu, modele_email=None):
    fichier = lire_csv_agents(contenu)

    colonnes_qualifications = analyser_colonnes_import(
        fichier["colonnes"]
    )

    resultat = {
        "lignes": [],
        "erreurs": [],
        "avertissements": [],
        "bilan": {
            "creer": 0,
            "rattacher": 0,
            "modifier": 0,
        },
        "valide": False,
    }

    matricules = {}
    emails = {}

    for ligne in fichier["lignes"]:
        numero = ligne["ligne"]
        donnees = ligne["donnees"]

        try:
            identite = analyser_identite_import(
                donnees,
                modele_email=modele_email,
            )

            profil = analyser_profil_import(
                donnees,
                identite,
            )

            qualifications = analyser_qualifications_import(
                donnees,
                colonnes_qualifications,
            )

            matricule = identite["matricule"]
            email = identite["email"]

            if matricule in matricules:
                raise ValidationError(
                    "Matricule en doublon avec la ligne "
                    f"{matricules[matricule]}."
                )

            if email in emails:
                raise ValidationError(
                    "Adresse e-mail en doublon avec la ligne "
                    f"{emails[email]}."
                )

            matricules[matricule] = numero
            emails[email] = numero

            proposition = {
                "ligne": numero,
                **identite,
                **profil,
                "qualifications": qualifications,
            }

            proposition.update(
                analyser_changements_import(proposition)
            )

            resultat["lignes"].append(proposition)

            resultat["bilan"][identite["action"]] += 1

            if identite["email_genere"]:
                resultat["avertissements"].append({
                    "ligne": numero,
                    "message": "Adresse e-mail générée, à vérifier.",
                })

            if identite["changement_email"]:
                resultat["avertissements"].append({
                    "ligne": numero,
                    "message": (
                        "Changement d'adresse e-mail détecté. "
                        "Une validation distincte sera nécessaire."
                    ),
                })

        except ValidationError as erreur:
            resultat["erreurs"].append({
                "ligne": numero,
                "messages": erreur.messages,
            })

    resultat["valide"] = not resultat["erreurs"]

    return resultat


def analyser_changements_import(ligne):
    from django.contrib.auth import get_user_model

    from ..models import ProfilAgent, CompetenceAgent

    changements = {}
    etat_initial = {
        "utilisateur": None,
        "profil": None,
        "qualifications": [],
    }
    qualifications_existantes = {}

    if ligne["utilisateur_id"] is not None:
        utilisateur = get_user_model().objects.get(
            pk=ligne["utilisateur_id"]
        )

        etat_initial["utilisateur"] = {
            "id": utilisateur.pk,
            "matricule": utilisateur.username,
            "nom": utilisateur.last_name,
            "prenom": utilisateur.first_name,
            "email": utilisateur.email,
            "actif": utilisateur.is_active,
            "staff": utilisateur.is_staff,
            "superutilisateur": utilisateur.is_superuser,
        }

        for champ, avant, apres in (
            ("nom", utilisateur.last_name, ligne["nom"]),
            ("prenom", utilisateur.first_name, ligne["prenom"]),
            ("email", utilisateur.email, ligne["email"]),
        ):
            if avant != apres:
                changements[champ] = {
                    "avant": avant,
                    "apres": apres,
                }

    if ligne["profil_id"] is not None:
        profil = ProfilAgent.objects.get(
            pk=ligne["profil_id"]
        )

        fonctions_actuelles = sorted(
            profil.fonctions.values_list("pk", flat=True)
        )

        etat_initial["profil"] = {
            "id": profil.pk,
            "grade_id": profil.grade_id,
            "telephone": profil.telephone,
            "fonctions_ids": fonctions_actuelles,
        }

        for champ, avant, apres in (
            ("grade_id", profil.grade_id, ligne["grade_id"]),
            ("telephone", profil.telephone, ligne["telephone"]),
            ("fonctions_ids", fonctions_actuelles, ligne["fonctions_ids"]),
        ):
            if avant != apres:
                changements[champ] = {
                    "avant": avant,
                    "apres": apres,
                }

        qualifications_existantes = {
            attribution.competence_id: attribution
            for attribution in CompetenceAgent.objects.filter(
                profil=profil
            )
        }

    from .competences import etat_attribution

    etat_initial["qualifications"] = [
        {
            "id": attribution.pk,
            **etat_attribution(attribution),
        }
        for attribution in sorted(
            qualifications_existantes.values(),
            key=lambda attribution: attribution.pk,
        )
    ]

    operations_qualifications = []

    for competence_id, souhaitee in ligne["qualifications"].items():
        existante = qualifications_existantes.get(
            competence_id
        )

        if souhaitee and existante is None:
            operations_qualifications.append({
                "action": "attribuer",
                "competence_id": competence_id,
            })

        elif not souhaitee and existante is not None:
            operations_qualifications.append({
                "action": "retirer",
                "competence_id": competence_id,
                "attribution_id": existante.pk,
            })

    return {
        "changements": changements,
        "etat_initial": etat_initial,
        "operations_qualifications": operations_qualifications,
        "confirmation_retraits": any(
            operation["action"] == "retirer"
            for operation in operations_qualifications
        ),
    }


def empreinte_previsualisation(resultat):
    import hashlib
    import json

    contenu = json.dumps(
        resultat,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        contenu.encode("utf-8")
    ).hexdigest()


def verifier_previsualisation_import(
    *,
    contenu,
    empreinte_attendue,
    modele_email=None,
):
    from hmac import compare_digest

    if (
        not isinstance(empreinte_attendue, str)
        or len(empreinte_attendue) != 64
        or any(
            caractere not in "0123456789abcdef"
            for caractere in empreinte_attendue
        )
    ):
        raise ValidationError(
            "Empreinte de prévisualisation invalide."
        )

    resultat = previsualiser_import_agents(
        contenu,
        modele_email=modele_email,
    )

    if not resultat["valide"]:
        raise ValidationError(
            "L'import contient des erreurs."
        )

    empreinte_actuelle = empreinte_previsualisation(
        resultat
    )

    if not compare_digest(
        empreinte_actuelle,
        empreinte_attendue,
    ):
        raise ValidationError(
            "Les données ont changé depuis la prévisualisation. "
            "Veuillez renouveler la prévisualisation."
        )

    return resultat


DUREE_CONFIRMATION_IMPORT = 1800
SIGNATURE_IMPORT = "planning.import_agents.v1"


def verifier_autorisation_import(utilisateur_id):
    from django.contrib.auth import get_user_model
    from django.core.exceptions import PermissionDenied
    from .agents import verifier_identifiant

    utilisateur_id = verifier_identifiant(utilisateur_id)

    utilisateur = get_user_model().objects.filter(
        pk=utilisateur_id,
        is_active=True,
    ).first()

    if utilisateur is None or not utilisateur.is_superuser:
        raise PermissionDenied(
            "Vous ne disposez pas des droits d'import."
        )

    return utilisateur


def preparer_confirmation_import(
    *,
    contenu,
    utilisateur_id,
    modele_email=None,
):
    import hashlib
    from uuid import uuid4
    from django.core import signing

    utilisateur = verifier_autorisation_import(
        utilisateur_id
    )

    resultat = previsualiser_import_agents(
        contenu,
        modele_email=modele_email,
    )

    jeton = None

    if resultat["valide"]:
        jeton = signing.dumps(
            {
                "utilisateur_id": utilisateur.pk,
                "identifiant": uuid4().hex,
                "empreinte": empreinte_previsualisation(resultat),
                "fichier": hashlib.sha256(contenu).hexdigest(),
            },
            salt=SIGNATURE_IMPORT,
        )

    return {
        "previsualisation": resultat,
        "jeton": jeton,
    }


def verifier_confirmation_import(
    *,
    contenu,
    utilisateur_id,
    jeton,
    modele_email=None,
):
    import hashlib
    from hmac import compare_digest
    from django.core import signing
    from django.core.exceptions import PermissionDenied

    utilisateur = verifier_autorisation_import(
        utilisateur_id
    )

    if not isinstance(jeton, str) or not jeton:
        raise ValidationError(
            "Jeton de confirmation invalide."
        )

    try:
        donnees = signing.loads(
            jeton,
            salt=SIGNATURE_IMPORT,
            max_age=DUREE_CONFIRMATION_IMPORT,
        )

    except signing.SignatureExpired as erreur:
        raise ValidationError(
            "La confirmation a expiré. "
            "Veuillez renouveler la prévisualisation."
        ) from erreur

    except signing.BadSignature as erreur:
        raise ValidationError(
            "Jeton de confirmation invalide."
        ) from erreur

    if donnees["utilisateur_id"] != utilisateur.pk:
        raise PermissionDenied(
            "Cette confirmation appartient à un autre utilisateur."
        )

    if not isinstance(contenu, bytes):
        raise ValidationError("Format de fichier invalide.")

    if not compare_digest(
        hashlib.sha256(contenu).hexdigest(),
        donnees["fichier"],
    ):
        raise ValidationError(
            "Le fichier ne correspond pas au fichier prévisualisé."
        )

    empreinte_confirmation = identifier_confirmation_import(donnees)

    from ..models import ConfirmationImport

    if ConfirmationImport.objects.filter(
        empreinte=empreinte_confirmation
    ).exists():
        raise ValidationError(
            "Cette confirmation a déjà été utilisée."
        )

    return verifier_previsualisation_import(
        contenu=contenu,
        empreinte_attendue=donnees["empreinte"],
        modele_email=modele_email,
    )


def identifier_confirmation_import(donnees):
    import hashlib
    from uuid import UUID

    identifiant = donnees.get("identifiant")

    if not isinstance(identifiant, str):
        raise ValidationError(
            "Identifiant de confirmation invalide."
        )

    try:
        identifiant = UUID(identifiant).hex
    except ValueError as erreur:
        raise ValidationError(
            "Identifiant de confirmation invalide."
        ) from erreur

    return hashlib.sha256(
        identifiant.encode("ascii")
    ).hexdigest()


def consommer_confirmation_import(
    *,
    contenu,
    utilisateur_id,
    jeton,
    modele_email=None,
):
    from django.core import signing
    from django.db import IntegrityError, transaction

    from ..models import ConfirmationImport

    try:
        with transaction.atomic():
            resultat = verifier_confirmation_import(
                contenu=contenu,
                utilisateur_id=utilisateur_id,
                jeton=jeton,
                modele_email=modele_email,
            )

            try:
                donnees = signing.loads(
                    jeton,
                    salt=SIGNATURE_IMPORT,
                    max_age=DUREE_CONFIRMATION_IMPORT,
                )
            except signing.BadSignature as erreur:
                raise ValidationError(
                    "Confirmation invalide ou expirée."
                ) from erreur

            ConfirmationImport.objects.create(
                empreinte=identifier_confirmation_import(donnees),
                auteur_id=donnees["utilisateur_id"],
            )

            return resultat

    except IntegrityError as erreur:
        raise ValidationError(
            "Impossible de consommer cette confirmation."
        ) from erreur
