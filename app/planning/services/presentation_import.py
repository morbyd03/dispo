from ..models import Grade, FonctionAgent, Competence


LIBELLES_CHAMPS = {
    "nom": "Nom",
    "prenom": "Prénom",
    "email": "Adresse e-mail",
    "grade_id": "Grade",
    "telephone": "Téléphone",
    "fonctions_ids": "Fonctions",
}


def presenter_import_agents(previsualisation):
    grades = dict(
        Grade.objects.values_list("pk", "nom")
    )

    fonctions = dict(
        FonctionAgent.objects.values_list("pk", "nom")
    )

    competences = dict(
        Competence.objects.values_list("pk", "nom")
    )

    def libelle_grade(identifiant):
        if identifiant is None:
            return "—"

        return grades.get(
            identifiant,
            "Grade indisponible",
        )

    def libelles_fonctions(identifiants):
        return ", ".join(
            fonctions.get(
                identifiant,
                "Fonction indisponible",
            )
            for identifiant in identifiants
        ) or "—"

    def presenter_valeur(champ, valeur):
        if champ == "grade_id":
            return libelle_grade(valeur)

        if champ == "fonctions_ids":
            return libelles_fonctions(valeur)

        if valeur is None or valeur == "":
            return "—"

        return str(valeur)

    resultat = []

    for ligne in previsualisation["lignes"]:
        changements = [
            {
                "champ": LIBELLES_CHAMPS.get(champ, champ),
                "avant": presenter_valeur(
                    champ, valeurs["avant"]
                ),
                "apres": presenter_valeur(
                    champ, valeurs["apres"]
                ),
            }
            for champ, valeurs in ligne["changements"].items()
        ]

        operations = [
            {
                "action": operation["action"],
                "competence": competences.get(
                    operation["competence_id"],
                    "Compétence indisponible",
                ),
            }
            for operation in ligne["operations_qualifications"]
        ]

        if ligne["action"] == "creer":
            action = "Création"

        elif ligne["action"] == "rattacher":
            action = "Rattachement"

        elif changements:
            action = "Modification du profil"

        elif operations:
            action = "Qualifications uniquement"

        else:
            action = "Inchangé"

        resultat.append({
            "ligne": ligne["ligne"],
            "matricule": ligne["matricule"],
            "nom": ligne["nom"],
            "prenom": ligne["prenom"],
            "email": ligne["email"],
            "grade": libelle_grade(ligne["grade_id"]),
            "telephone": ligne["telephone"] or "—",
            "fonctions": libelles_fonctions(
                ligne["fonctions_ids"]
            ),
            "action": action,
            "type_action": ligne["action"],
            "changements": changements,
            "operations": operations,
            "changement_email": ligne["changement_email"],
        })

    return resultat
