from django.utils import timezone

from .surveillance import periodes_surveillance
from .couverture import analyser_periode_ssuap
from .incendie import analyser_periode_inc


def determiner_statut(periodes):
    """
    Détermine le statut de couverture d'une garde.
    """

    if all(periode["couvert"] for periode in periodes):
        return "couvert"

    if any(periode["couvert"] for periode in periodes):
        return "partiel"

    return "non_couvert"

def calculer_duree_couverte(periodes):
    """
    Calcule le nombre total de minutes
    pendant lesquelles un équipage complet est disponible.
    """

    secondes = sum(
        (periode["fin"] - periode["debut"]).total_seconds()
        for periode in periodes
        if periode["couvert"]
    )

    return round(secondes / 60)

# TODO — Amélioration future de l'interface :
# Ajouter une barre de progression dans le planning hebdomadaire
# pour visualiser le pourcentage de couverture de chaque garde.
#
# Calculer séparément les pourcentages SSUAP et INC :
#     pourcentage = minutes_couvertes / minutes_totales * 100
#
# Affichage envisagé :
# - Vert   : 100 % de couverture
# - Orange : couverture partielle (entre 0 et 100 %)
# - Rouge  : 0 % de couverture
#
# Afficher les barres sous les durées de couverture existantes
# dans planning/templates/planning/planning_hebdomadaire.html.
#
# Priorité : facultative, à réaliser ultérieurement.

def synthese_gardes(debut, fin):
    """
    Prépare une synthèse SSUAP et INC
    pour chaque période de surveillance.
    """

    gardes = []

    for surveillance in periodes_surveillance(debut, fin):
        debut_garde = surveillance["debut"]
        fin_garde = surveillance["fin"]

        periodes_ssuap = analyser_periode_ssuap(
            debut_garde,
            fin_garde,
        )

        periodes_inc = analyser_periode_inc(
            debut_garde,
            fin_garde,
        )
        duree_totale = round(
            (fin_garde - debut_garde).total_seconds() / 60
        )
        gardes.append({
            "debut": timezone.localtime(debut_garde),
            "fin": timezone.localtime(fin_garde),

            "statut_ssuap": determiner_statut(periodes_ssuap),
            "statut_inc": determiner_statut(periodes_inc),

            "minutes_totales": duree_totale,
            "minutes_ssuap": calculer_duree_couverte(periodes_ssuap),
            "minutes_inc": calculer_duree_couverte(periodes_inc),
        })

    return gardes
