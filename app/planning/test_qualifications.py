from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Competence, CompetenceAgent, ProfilAgent
from .qualifications import possede_competence


class TestsValiditeCompetences(TestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.agent = User.objects.create_user(
            username="test_validite_competence"
        )
        cls.profil = ProfilAgent.objects.create(
            utilisateur=cls.agent
        )
        cls.competence, _ = Competence.objects.get_or_create(
            code="cod1",
            defaults={"nom": "COD1"},
        )

        cls.attribution = CompetenceAgent.objects.create(
            agent=cls.agent,
            competence=cls.competence,
            date_validation=date(2026, 11, 1),
            date_expiration=date(2026, 11, 22),
        )

    def test_avant_validation(self):
        self.assertFalse(
            possede_competence(
                self.profil, "cod1", date(2026, 10, 31)
            )
        )

    def test_jour_expiration(self):
        self.assertTrue(
            possede_competence(
                self.profil, "cod1", date(2026, 11, 22)
            )
        )

    def test_apres_expiration(self):
        self.assertFalse(
            possede_competence(
                self.profil, "cod1", date(2026, 11, 23)
            )
        )

    def test_competence_desactivee(self):
        self.competence.active = False
        self.competence.save(update_fields=["active"])

        self.assertFalse(
            possede_competence(
                self.profil, "cod1", date(2026, 11, 22)
            )
        )

    def test_validation_sans_date(self):
        self.attribution.date_validation = None
        self.attribution.save(update_fields=["date_validation"])

        self.assertTrue(
            possede_competence(
                self.profil, "cod1", date(2026, 11, 22)
            )
        )


class TestsExpirationPendantGarde(TestCase):

    def test_cod1_expire_a_minuit(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo

        from .incendie import analyser_periode_inc
        from .models import Disponibilite

        User = get_user_model()
        fuseau = ZoneInfo("Europe/Paris")

        debut = datetime(2026, 11, 22, 20, 0, tzinfo=fuseau)
        minuit = datetime(2026, 11, 23, 0, 0, tzinfo=fuseau)
        fin = datetime(2026, 11, 23, 8, 0, tzinfo=fuseau)

        equipe = {
            "chef": ["chef_inc"],
            "conducteur": ["permis_pl", "cod1"],
            "equipier1": ["equipier_inc"],
            "equipier2": ["equipier_inc"],
        }

        for nom, codes in equipe.items():
            agent = User.objects.create_user(
                username=f"test_minuit_{nom}"
            )
            ProfilAgent.objects.create(utilisateur=agent)

            Disponibilite.objects.create(
                agent=agent,
                debut=debut,
                fin=fin,
            )

            for code in codes:
                competence, _ = Competence.objects.get_or_create(
                    code=code,
                    defaults={"nom": code},
                )

                CompetenceAgent.objects.create(
                    agent=agent,
                    competence=competence,
                    date_validation=date(2026, 1, 1),
                    date_expiration=(
                        date(2026, 11, 22)
                        if code == "cod1"
                        else None
                    ),
                )

        periodes = analyser_periode_inc(debut, fin)

        self.assertEqual(len(periodes), 2)

        self.assertEqual(periodes[0]["debut"], debut)
        self.assertEqual(periodes[0]["fin"], minuit)
        self.assertTrue(periodes[0]["couvert"])

        self.assertEqual(periodes[1]["debut"], minuit)
        self.assertEqual(periodes[1]["fin"], fin)
        self.assertFalse(periodes[1]["couvert"])
