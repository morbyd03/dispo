from itertools import permutations
from django.utils import timezone
from .models import Disponibilite, ProfilAgent
from .qualifications import possede_competence
from .surveillance import periodes_surveillance
from .decoupage import changements_de_jour

ROLES_INC = (
    "Chef d'agrès INC",
    "Conducteur PL + COD1",
    "Équipier INC n° 1",
    "Équipier INC n° 2",
)


def calculer_couverture_inc(profils, date_reference=None):
    """
    Vérifie si quatre agents distincts peuvent
    constituer un équipage incendie.
    """
    profils = list(profils)

    def qualifie(profil, code):
        return possede_competence(profil, code, date_reference)


    def peut_occuper(profil, role):
        if role == "Chef d'agrès INC":
            return qualifie(profil, "chef_inc")

        if role == "Conducteur PL + COD1":
            return qualifie(profil, "permis_pl") and qualifie(profil, "cod1")

        if role.startswith("Équipier INC"):
            return qualifie(profil, "equipier_inc")

        return False

    qualifications_absentes = []

    if not any(qualifie(profil, "chef_inc") for profil in profils):
        qualifications_absentes.append("Chef d'agrès INC")

    if not any(
        qualifie(profil, "permis_pl") and qualifie(profil, "cod1")
        for profil in profils
    ):
        qualifications_absentes.append("Conducteur PL + COD1")

    if not any(qualifie(profil, "equipier_inc") for profil in profils):
        qualifications_absentes.append("Équipier INC")

    # Recherche d'un équipage complet.
    for equipe in permutations(profils, 4):
        if all(
            peut_occuper(profil, role)
            for profil, role in zip(equipe, ROLES_INC)
        ):
            return {
                "couvert": True,
                "roles_manquants": [],
                "qualifications_absentes": [],
            }

    # Recherche de la meilleure affectation partielle.
    meilleure_affectation = ()

    for nombre in range(1, min(len(profils), 4) + 1):
        for roles in permutations(ROLES_INC, nombre):
            for agents in permutations(profils, nombre):
                if all(
                    peut_occuper(profil, role)
                    for profil, role in zip(agents, roles)
                ):
                    if nombre > len(meilleure_affectation):
                        meilleure_affectation = roles

    return {
        "couvert": False,
        "roles_manquants": [
            role
            for role in ROLES_INC
            if role not in meilleure_affectation
        ],
        "qualifications_absentes": qualifications_absentes,
    }

def couverture_inc_a_un_instant(instant):
    """
    Calcule la couverture incendie à un instant donné.
    Une disponibilité est active si debut <= instant < fin.
    """

    if timezone.is_naive(instant):
        raise ValueError(
            "L'instant doit contenir un fuseau horaire."
        )

    agents_disponibles = (
        Disponibilite.objects
        .filter(debut__lte=instant, fin__gt=instant)
        .values_list("agent_id", flat=True)
        .distinct()
    )

    profils = ProfilAgent.objects.filter(
        utilisateur_id__in=agents_disponibles,
        utilisateur__is_active=True,
    )

    resultat = calculer_couverture_inc(
        profils,
        timezone.localtime(instant).date(),
    )

    return {
        "instant": instant,
        "nombre_agents": profils.count(),
        "couvert": resultat["couvert"],
        "roles_manquants": resultat["roles_manquants"],
        "qualifications_absentes": resultat["qualifications_absentes"],
    }

def analyser_periode_inc(debut, fin):
    """
    Analyse la couverture incendie entre deux instants,
    en tenant compte de chaque changement de disponibilité.
    """

    if timezone.is_naive(debut) or timezone.is_naive(fin):
        raise ValueError("Les dates doivent contenir un fuseau horaire.")

    if fin <= debut:
        raise ValueError("La fin doit être postérieure au début.")

    disponibilites = Disponibilite.objects.filter(
        debut__lt=fin,
        fin__gt=debut,
    )

    instants = {debut, fin}
    instants.update(changements_de_jour(debut, fin))

    for disponibilite in disponibilites:
        if debut < disponibilite.debut < fin:
            instants.add(disponibilite.debut)

        if debut < disponibilite.fin < fin:
            instants.add(disponibilite.fin)

    instants = sorted(instants)
    periodes = []

    for index in range(len(instants) - 1):
        debut_intervalle = instants[index]
        fin_intervalle = instants[index + 1]

        resultat = couverture_inc_a_un_instant(debut_intervalle)

        periode = {
            "debut": debut_intervalle,
            "fin": fin_intervalle,
            "couvert": resultat["couvert"],
            "nombre_agents": resultat["nombre_agents"],
            "roles_manquants": resultat["roles_manquants"],
        "qualifications_absentes": resultat["qualifications_absentes"],
        }

        if periodes and all(
            periodes[-1][cle] == periode[cle]
            for cle in (
                "couvert",
                "nombre_agents",
                "roles_manquants",
                "qualifications_absentes",
                "qualifications_absentes",
            )
        ):
            periodes[-1]["fin"] = fin_intervalle
        else:
            periodes.append(periode)

    return periodes


def alertes_inc(debut, fin):
    """
    Retourne les périodes de surveillance
    où la couverture incendie est insuffisante.
    """

    alertes = []

    for surveillance in periodes_surveillance(debut, fin):
        periodes = analyser_periode_inc(
            surveillance["debut"],
            surveillance["fin"],
        )

        for periode in periodes:
            if periode["couvert"]:
                continue

            alerte = {
                "debut": periode["debut"],
                "fin": periode["fin"],
                "nombre_agents": periode["nombre_agents"],
                "roles_manquants": periode["roles_manquants"],
                "qualifications_absentes": periode["qualifications_absentes"],
                "qualifications_absentes": periode["qualifications_absentes"],
            }

            if (
                alertes
                and alertes[-1]["fin"] == alerte["debut"]
                and alertes[-1]["nombre_agents"] == alerte["nombre_agents"]
                and alertes[-1]["roles_manquants"] == alerte["roles_manquants"]
                and alertes[-1]["qualifications_absentes"] == alerte["qualifications_absentes"]
                and alertes[-1]["qualifications_absentes"] == alerte["qualifications_absentes"]
            ):
                alertes[-1]["fin"] = alerte["fin"]
            else:
                alertes.append(alerte)

    return alertes
