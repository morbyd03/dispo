from ..models import JournalAction


def journaliser(*, auteur, action, objet, details=None):
    return JournalAction.objects.create(
        auteur=auteur,
        action=action,
        type_objet=objet._meta.label_lower,
        objet_id=objet.pk,
        details=details if details is not None else {},
    )


def etat_profil_agent(profil):
    utilisateur = profil.utilisateur

    return {
        "utilisateur_id": utilisateur.pk,
        "matricule": utilisateur.username,
        "nom": utilisateur.last_name,
        "prenom": utilisateur.first_name,
        "grade_id": profil.grade_id,
        "telephone": profil.telephone,
        "fonctions_ids": sorted(
            profil.fonctions.values_list("pk", flat=True)
        ),
    }


def differences_etats(avant, apres):
    return {
        champ: {
            "avant": avant[champ],
            "apres": apres[champ],
        }
        for champ in avant
        if avant[champ] != apres[champ]
    }
