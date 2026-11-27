from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase
from .couverture import calculer_couverture_ssuap
from .incendie import calculer_couverture_inc
from .incendie import analyser_periode_inc
from .incendie import alertes_inc
from .couverture import alertes_ssuap
from django.template.loader import render_to_string

def agent(
    chef_ssuap=False,
    equipier_ssuap=False,
    permis_pl=False,
):
    codes = set()
    if chef_ssuap:
        codes.add("chef_ssuap")
    if equipier_ssuap:
        codes.add("equipier_ssuap")
    if permis_pl:
        codes.add("permis_pl")
    return SimpleNamespace(codes_competences=codes)


class TestsCouvertureSSUAP(SimpleTestCase):

    def setUp(self):
        super().setUp()

        def competence_fictive(profil, code, date_reference=None):
            return code in profil.codes_competences

        self._patch_ssuap = patch(
            "planning.couverture.possede_competence",
            side_effect=competence_fictive,
        )
        self._patch_inc = patch(
            "planning.incendie.possede_competence",
            side_effect=competence_fictive,
        )

        self._patch_ssuap.start()
        self.addCleanup(self._patch_ssuap.stop)

        self._patch_inc.start()
        self.addCleanup(self._patch_inc.stop)


    def test_chef_pl_et_deux_equipiers(self):
        profils = [
            agent(chef_ssuap=True, permis_pl=True),
            agent(equipier_ssuap=True),
            agent(equipier_ssuap=True),
        ]

        resultat = calculer_couverture_ssuap(profils)
        self.assertTrue(resultat["couvert"])

    def test_equipier_pl(self):
        profils = [
            agent(chef_ssuap=True),
            agent(equipier_ssuap=True, permis_pl=True),
            agent(equipier_ssuap=True),
        ]

        resultat = calculer_couverture_ssuap(profils)
        self.assertTrue(resultat["couvert"])

    def test_deux_agents_insuffisants(self):
        profils = [
            agent(chef_ssuap=True, permis_pl=True),
            agent(equipier_ssuap=True),
        ]

        resultat = calculer_couverture_ssuap(profils)
        self.assertFalse(resultat["couvert"])

    def test_absence_permis_pl(self):
        profils = [
            agent(chef_ssuap=True),
            agent(equipier_ssuap=True),
            agent(equipier_ssuap=True),
        ]

        resultat = calculer_couverture_ssuap(profils)

        self.assertFalse(resultat["couvert"])
        self.assertIn(
            "Conducteur PL",
            resultat["roles_manquants"],
        )

    def test_chef_peut_etre_equipier(self):
        profils = [
            agent(chef_ssuap=True, permis_pl=True),
            agent(chef_ssuap=True),
            agent(equipier_ssuap=True),
        ]

        resultat = calculer_couverture_ssuap(profils)
        self.assertTrue(resultat["couvert"])

    def test_trois_chefs_dont_un_pl(self):
        profils = [
            agent(chef_ssuap=True, permis_pl=True),
            agent(chef_ssuap=True),
            agent(chef_ssuap=True),
        ]

        resultat = calculer_couverture_ssuap(profils)
        self.assertTrue(resultat["couvert"])

    def test_agent_unique_ne_compte_pas_trois_fois(self):
        profils = [
            agent(
                chef_ssuap=True,
                equipier_ssuap=True,
                permis_pl=True,
            ),
        ]

        resultat = calculer_couverture_ssuap(profils)
        self.assertFalse(resultat["couvert"])

    def test_pl_hors_equipage_ne_suffit_pas(self):
        profils = [
            agent(chef_ssuap=True),
            agent(equipier_ssuap=True),
            agent(equipier_ssuap=True),
            agent(permis_pl=True),
        ]

        resultat = calculer_couverture_ssuap(profils)
        self.assertFalse(resultat["couvert"])

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch

from .couverture import analyser_periode_ssuap


class TestsPeriodesSSUAP(SimpleTestCase):

    def test_changement_de_couverture_pendant_une_garde(self):
        paris = ZoneInfo("Europe/Paris")
        debut = datetime(2026, 11, 23, 21, 0, tzinfo=paris)

        def resultat_a_un_instant(instant):
            minutes = (instant - debut).total_seconds() / 60

            if 120 <= minutes < 300:
                return {
                    "couvert": True,
                    "nombre_agents": 3,
                    "roles_manquants": [],
                    "qualifications_absentes": [],
                }

            return {
                "couvert": False,
                "nombre_agents": 2,
                "roles_manquants": ["Équipier SSUAP n° 2"],
                "qualifications_absentes": [],
            }

        class DisponibiliteFictive:
            def __init__(self, debut, fin):
                self.debut = debut
                self.fin = fin

        disponibilite = DisponibiliteFictive(
            debut + timedelta(hours=2),
            debut + timedelta(hours=5),
        )

        with (
            patch(
                "planning.couverture.Disponibilite.objects.filter",
                return_value=[disponibilite],
            ),
            patch(
                "planning.couverture.couverture_ssuap_a_un_instant",
                side_effect=resultat_a_un_instant,
            ),
        ):
            periodes = analyser_periode_ssuap(
                debut,
                debut + timedelta(hours=9),
            )

        self.assertEqual(len(periodes), 3)
        self.assertFalse(periodes[0]["couvert"])
        self.assertTrue(periodes[1]["couvert"])
        self.assertFalse(periodes[2]["couvert"])

        self.assertEqual(
            periodes[1]["fin"] - periodes[1]["debut"],
            timedelta(hours=3),
        )

def agent_inc(
    chef_inc=False,
    equipier_inc=False,
    permis_pl=False,
    cod1=False,
):
    codes = set()
    if chef_inc:
        codes.add("chef_inc")
    if equipier_inc:
        codes.add("equipier_inc")
    if permis_pl:
        codes.add("permis_pl")
    if cod1:
        codes.add("cod1")
    return SimpleNamespace(codes_competences=codes)


class TestsCouvertureINC(SimpleTestCase):

    def setUp(self):
        super().setUp()

        def competence_fictive(profil, code, date_reference=None):
            return code in profil.codes_competences

        self._patch_ssuap = patch(
            "planning.couverture.possede_competence",
            side_effect=competence_fictive,
        )
        self._patch_inc = patch(
            "planning.incendie.possede_competence",
            side_effect=competence_fictive,
        )

        self._patch_ssuap.start()
        self.addCleanup(self._patch_ssuap.stop)

        self._patch_inc.start()
        self.addCleanup(self._patch_inc.stop)


    def test_equipage_complet(self):
        profils = [
            agent_inc(chef_inc=True),
            agent_inc(permis_pl=True, cod1=True),
            agent_inc(equipier_inc=True),
            agent_inc(equipier_inc=True),
        ]

        resultat = calculer_couverture_inc(profils)

        self.assertTrue(resultat["couvert"])
        self.assertEqual(resultat["roles_manquants"], [])

    def test_quatre_agents_distincts(self):
        profils = [
            agent_inc(chef_inc=True, permis_pl=True, cod1=True),
            agent_inc(equipier_inc=True),
            agent_inc(equipier_inc=True),
        ]

        resultat = calculer_couverture_inc(profils)

        self.assertFalse(resultat["couvert"])

    def test_cod1_obligatoire(self):
        profils = [
            agent_inc(chef_inc=True),
            agent_inc(permis_pl=True),
            agent_inc(equipier_inc=True),
            agent_inc(equipier_inc=True),
        ]

        resultat = calculer_couverture_inc(profils)

        self.assertFalse(resultat["couvert"])
        self.assertIn(
            "Conducteur PL + COD1",
            resultat["roles_manquants"],
        )

    def test_agents_polyvalents(self):
        profils = [
            agent_inc(chef_inc=True, equipier_inc=True),
            agent_inc(permis_pl=True, cod1=True, equipier_inc=True),
            agent_inc(equipier_inc=True),
            agent_inc(equipier_inc=True),
        ]

        resultat = calculer_couverture_inc(profils)

        self.assertTrue(resultat["couvert"])

class TestsPeriodesINC(SimpleTestCase):

    def test_changement_de_couverture_pendant_une_garde(self):
        paris = ZoneInfo("Europe/Paris")
        debut = datetime(2026, 11, 23, 21, 0, tzinfo=paris)

        def resultat_a_un_instant(instant):
            minutes = (instant - debut).total_seconds() / 60

            if 120 <= minutes < 300:
                return {
                    "couvert": True,
                    "nombre_agents": 4,
                    "roles_manquants": [],
                    "qualifications_absentes": [],
                }

            return {
                "couvert": False,
                "nombre_agents": 3,
                "roles_manquants": ["Équipier INC n° 2"],
                "qualifications_absentes": [],
            }

        class DisponibiliteFictive:
            def __init__(self, debut, fin):
                self.debut = debut
                self.fin = fin

        disponibilite = DisponibiliteFictive(
            debut + timedelta(hours=2),
            debut + timedelta(hours=5),
        )

        with (
            patch(
                "planning.incendie.Disponibilite.objects.filter",
                return_value=[disponibilite],
            ),
            patch(
                "planning.incendie.couverture_inc_a_un_instant",
                side_effect=resultat_a_un_instant,
            ),
        ):
            periodes = analyser_periode_inc(
                debut,
                debut + timedelta(hours=9),
            )

        self.assertEqual(len(periodes), 3)

        self.assertFalse(periodes[0]["couvert"])
        self.assertTrue(periodes[1]["couvert"])
        self.assertFalse(periodes[2]["couvert"])

        self.assertEqual(
            periodes[1]["fin"] - periodes[1]["debut"],
            timedelta(hours=3),
        )

class TestsDiagnosticQualifications(SimpleTestCase):

    def setUp(self):
        super().setUp()

        def competence_fictive(profil, code, date_reference=None):
            return code in profil.codes_competences

        self._patch_ssuap = patch(
            "planning.couverture.possede_competence",
            side_effect=competence_fictive,
        )
        self._patch_inc = patch(
            "planning.incendie.possede_competence",
            side_effect=competence_fictive,
        )

        self._patch_ssuap.start()
        self.addCleanup(self._patch_ssuap.stop)

        self._patch_inc.start()
        self.addCleanup(self._patch_inc.stop)


    def test_inc_qualification_presente_mais_affectation_impossible(self):
        profils = [
            agent_inc(chef_inc=True, permis_pl=True, cod1=True),
            agent_inc(equipier_inc=True),
            agent_inc(equipier_inc=True),
        ]

        resultat = calculer_couverture_inc(profils)

        self.assertFalse(resultat["couvert"])

        # Les qualifications existent, mais les agents
        # ne peuvent pas occuper tous les postes distincts.
        self.assertEqual(
            resultat["qualifications_absentes"],
            [],
        )

    def test_inc_conducteur_non_qualifie(self):
        profils = [
            agent_inc(chef_inc=True),
            agent_inc(permis_pl=True, cod1=False),
            agent_inc(equipier_inc=True),
            agent_inc(equipier_inc=True),
        ]

        resultat = calculer_couverture_inc(profils)

        self.assertFalse(resultat["couvert"])

        self.assertIn(
            "Conducteur PL + COD1",
            resultat["qualifications_absentes"],
        )

    def test_ssuap_permis_pl_absent(self):
        profils = [
            agent(chef_ssuap=True),
            agent(equipier_ssuap=True),
            agent(equipier_ssuap=True),
        ]

        resultat = calculer_couverture_ssuap(profils)

        self.assertFalse(resultat["couvert"])

        self.assertIn(
            "Conducteur PL",
            resultat["qualifications_absentes"],
        )

class TestsTransmissionAlertes(SimpleTestCase):

    def test_qualification_absente_transmise_alerte_inc(self):
        paris = ZoneInfo("Europe/Paris")

        debut = datetime(2026, 11, 23, 21, 0, tzinfo=paris)
        fin = debut + timedelta(hours=9)

        periode_fictive = {
            "debut": debut,
            "fin": fin,
            "couvert": False,
            "nombre_agents": 3,
            "roles_manquants": ["Conducteur PL + COD1"],
            "qualifications_absentes": ["Conducteur PL + COD1"],
        }

        with patch(
            "planning.incendie.analyser_periode_inc",
            return_value=[periode_fictive],
        ):
            alertes = alertes_inc(debut, fin)

        self.assertEqual(len(alertes), 1)

        self.assertEqual(
            alertes[0]["qualifications_absentes"],
            ["Conducteur PL + COD1"],
        )

class TestsTransmissionAlertesSSUAP(SimpleTestCase):

    def test_qualification_absente_transmise_alerte_ssuap(self):
        paris = ZoneInfo("Europe/Paris")

        debut = datetime(2026, 11, 23, 21, 0, tzinfo=paris)
        fin = debut + timedelta(hours=9)

        periode_fictive = {
            "debut": debut,
            "fin": fin,
            "couvert": False,
            "nombre_agents": 3,
            "roles_manquants": ["Conducteur PL"],
            "qualifications_absentes": ["Conducteur PL"],
        }

        with patch(
            "planning.couverture.analyser_periode_ssuap",
            return_value=[periode_fictive],
        ):
            alertes = alertes_ssuap(debut, fin)

        self.assertEqual(len(alertes), 1)

        self.assertEqual(
            alertes[0]["qualifications_absentes"],
            ["Conducteur PL"],
        )

class TestsAffichageDiagnostics(SimpleTestCase):

    def test_indicateurs_visuels_ssuap_et_inc(self):
        paris = ZoneInfo("Europe/Paris")
        debut = datetime(2026, 11, 23, 21, 0, tzinfo=paris)
        fin = debut + timedelta(hours=9)

        def alerte(qualifications_absentes):
            return {
                "debut": debut,
                "fin": fin,
                "nombre_agents": 3,
                "roles_manquants": ["Conducteur PL"],
                "qualifications_absentes": qualifications_absentes,
            }

        from django.test import RequestFactory
        from django.contrib.auth.models import AnonymousUser

        requete = RequestFactory().get("/planning/")
        requete.user = AnonymousUser()

        html = render_to_string(
            "planning/planning_hebdomadaire.html",
            {
                "jours": [],
                "synthese_gardes": [],
                "alertes_ssuap": [
                    alerte(["Conducteur PL"]),
                    alerte([]),
                ],
                "alertes_inc": [
                    alerte(["Conducteur PL + COD1"]),
                    alerte([]),
                ],
            },
            request=requete,
        )

        self.assertEqual(
            html.count("Qualification absente\n"),
            2,
        )
        self.assertEqual(
            html.count("Équipage incomplet"),
            2,
        )
        self.assertEqual(
            html.count("<th>Diagnostic</th>"),
            2,
        )

from datetime import date, datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .copie import copier_journee
from .models import Disponibilite
