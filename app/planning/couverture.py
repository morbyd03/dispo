from itertools import permutations
from django.utils import timezone
from .surveillance import periodes_surveillance
from .decoupage import changements_de_jour
from .models import Disponibilite, ProfilAgent
from .qualifications import possede_competence
from itertools import permutations


ROLES_SSUAP = (
    "Chef d'agrès SSUAP",
    "Conducteur PL",
    "Équipier SSUAP",
)

def calculer_couverture_ssuap(profils, date_reference=None):
    profils = list(profils)

    def qualifie(profil, code):
        return possede_competence(profil, code, date_reference)


    def est_chef(profil):
        return qualifie(profil, "chef_ssuap")

    def est_equipier(profil):
        return qualifie(profil, "equipier_ssuap") or qualifie(profil, "chef_ssuap")

    qualifications_absentes = []

    if not any(est_chef(profil) for profil in profils):
        qualifications_absentes.append("Chef d'agrès SSUAP")

    if not any(est_equipier(profil) for profil in profils):
        qualifications_absentes.append("Équipier SSUAP")

    if not any(
        qualifie(profil, "permis_pl") and est_equipier(profil)
        for profil in profils
    ):
        qualifications_absentes.append("Conducteur PL")

    # Recherche d'un équipage complet de 3 agents distincts.
    for chef, equipier1, equipier2 in permutations(profils, 3):
        if (
            est_chef(chef)
            and est_equipier(equipier1)
            and est_equipier(equipier2)
            and (
                qualifie(chef, "permis_pl")
                or qualifie(equipier1, "permis_pl")
                or qualifie(equipier2, "permis_pl")
            )
        ):
            return {
                "couvert": True,
                "roles_manquants": [],
                "qualifications_absentes":[],
            }

    # Recherche de la meilleure affectation partielle.
    # Les trois places sont distinctes.
    roles = (
        "Chef d'agrès SSUAP",
        "Équipier SSUAP n° 1",
        "Équipier SSUAP n° 2",
    )

    def peut_occuper(profil, role):
        if role == "Chef d'agrès SSUAP":
            return est_chef(profil)
        return est_equipier(profil)

    meilleure_affectation = ()

    for nombre in range(1, min(len(profils), 3) + 1):
        for roles_choisis in permutations(roles, nombre):
            for agents in permutations(profils, nombre):
                if all(
                    peut_occuper(profil, role)
                    for profil, role in zip(agents, roles_choisis)
                ):
                    if nombre > len(meilleure_affectation):
                        meilleure_affectation = roles_choisis

    roles_manquants = [
        role for role in roles
        if role not in meilleure_affectation
    ]

    # Le permis PL doit être porté par un membre
    # pouvant intégrer l'équipage.
    conducteur_possible = any(
        qualifie(profil, "permis_pl")
        and (est_chef(profil) or est_equipier(profil))
        for profil in profils
    )

    if not conducteur_possible:
        roles_manquants.append("Conducteur PL")

    return {
        "couvert": False,
        "roles_manquants": roles_manquants,
        "qualifications_absentes": qualifications_absentes,
    }


def couverture_ssuap_a_un_instant(instant):
    """
    Calcule la couverture SSUAP à un instant donné.

    Une disponibilité est active si :
        debut <= instant < fin
    """

    if timezone.is_naive(instant):
        raise ValueError(
            "L'instant doit contenir un fuseau horaire."
        )

    agents_disponibles = (
        Disponibilite.objects
        .filter(
            debut__lte=instant,
            fin__gt=instant,
        )
        .values_list("agent_id", flat=True)
        .distinct()
    )

    profils = ProfilAgent.objects.filter(
        utilisateur_id__in=agents_disponibles,
        utilisateur__is_active=True,
    )

    resultat = calculer_couverture_ssuap(
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

def analyser_periode_ssuap(debut, fin):
    """
    Découpe une période aux changements de disponibilité
    et calcule la couverture SSUAP sur chaque intervalle.
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

        resultat = couverture_ssuap_a_un_instant(
            debut_intervalle
        )

        periode = {
            "debut": debut_intervalle,
            "fin": fin_intervalle,
            "couvert": resultat["couvert"],
            "nombre_agents": resultat["nombre_agents"],
            "roles_manquants": resultat["roles_manquants"],
        "qualifications_absentes": resultat["qualifications_absentes"],
        }

        # Fusionner les intervalles consécutifs
        # dont le résultat opérationnel est identique.
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


def alertes_ssuap(debut, fin):
    """
    Retourne les périodes de surveillance
    pendant lesquelles la couverture SSUAP
    est insuffisante.
    """

    alertes = []

    for surveillance in periodes_surveillance(debut, fin):

        periodes = analyser_periode_ssuap(
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

            # Fusionner les alertes consécutives
            # lorsqu'elles décrivent le même manque.
            if (
                alertes
                and alertes[-1]["fin"] == alerte["debut"]
                and alertes[-1]["nombre_agents"]
                    == alerte["nombre_agents"]
                and alertes[-1]["roles_manquants"]
                    == alerte["roles_manquants"]
                and alertes[-1]["qualifications_absentes"] == alerte["qualifications_absentes"]
                and alertes[-1]["qualifications_absentes"] == alerte["qualifications_absentes"]
            ):
                alertes[-1]["fin"] = alerte["fin"]
            else:
                alertes.append(alerte)

    return alertes
