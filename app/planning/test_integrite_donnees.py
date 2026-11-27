from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from .models import (
    ProfilAgent,
    Competence,
    CompetenceAgent,
    Disponibilite,
)


class IntegriteDonneesTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.agent = get_user_model().objects.create(
            username="000123",
            email="agent@example.com",
        )
        cls.profil = ProfilAgent.objects.create(
            utilisateur=cls.agent
        )
        cls.competence = Competence.objects.get(code="cod1")

    def test_email_unique(self):
        for email in (
            "agent@example.com",
            "AGENT@EXAMPLE.COM",
            " agent@example.com ",
        ):
            with self.subTest(email=email):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        get_user_model().objects.create(
                            username="000124",
                            email=email,
                        )

    def test_comptes_techniques_sans_email(self):
        User = get_user_model()
        User.objects.create(username="technique1")
        User.objects.create(username="technique2")

        self.assertEqual(
            User.objects.filter(email="").count(), 2
        )

    def test_disponibilite_inversee(self):
        debut = timezone.now()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Disponibilite.objects.create(
                    profil=self.profil,
                    debut=debut,
                    fin=debut - timedelta(hours=1),
                )

    def test_disponibilite_duree_nulle(self):
        debut = timezone.now()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Disponibilite.objects.create(
                    profil=self.profil,
                    debut=debut,
                    fin=debut,
                )

    def test_competence_unique(self):
        CompetenceAgent.objects.create(
            profil=self.profil,
            competence=self.competence,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CompetenceAgent.objects.create(
                    profil=self.profil,
                    competence=self.competence,
                )

    def test_dates_competence(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CompetenceAgent.objects.create(
                    profil=self.profil,
                    competence=self.competence,
                    date_validation=date(2026, 12, 1),
                    date_expiration=date(2026, 11, 1),
                )

    def test_profil_obligatoire(self):
        debut = timezone.now()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Disponibilite.objects.create(
                    debut=debut,
                    fin=debut + timedelta(hours=9),
                )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CompetenceAgent.objects.create(
                    competence=self.competence,
                )
