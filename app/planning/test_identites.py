from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from .identites import (
    normaliser_matricule,
    normaliser_email,
    normaliser_nom,
    normaliser_prenom,
)


class IdentitesTests(SimpleTestCase):

    def test_matricule(self):
        self.assertEqual(normaliser_matricule(" 003631 "), "003631")

        for valeur in ("", None, "ABC123", "12 34", "12.34", "１２３"):
            with self.subTest(valeur=valeur):
                with self.assertRaises(ValidationError):
                    normaliser_matricule(valeur)

    def test_email(self):
        self.assertEqual(
            normaliser_email(" Agent@EXAMPLE.COM "),
            "agent@example.com",
        )

        for valeur in ("", None, "agent", "agent@", "é@example.com"):
            with self.subTest(valeur=valeur):
                with self.assertRaises(ValidationError):
                    normaliser_email(valeur)

    def test_nom(self):
        self.assertEqual(
            normaliser_nom("  Le   Gall "),
            "Le Gall",
        )
        self.assertEqual(normaliser_nom("D'Évrard"), "D'Évrard")

        with self.assertRaises(ValidationError):
            normaliser_nom(" ")

    def test_prenom(self):
        self.assertEqual(
            normaliser_prenom(" Jean-François "),
            "Jean-François",
        )

        with self.assertRaises(ValidationError):
            normaliser_prenom(" ")

    def test_longueurs(self):
        for fonction in (
            normaliser_matricule,
            normaliser_nom,
            normaliser_prenom,
        ):
            with self.assertRaises(ValidationError):
                fonction("1" * 151)

        with self.assertRaises(ValidationError):
            normaliser_email("a" * 250 + "@example.com")


from django.contrib.auth import get_user_model
from django.test import TestCase

from .identites import (
    verifier_matricule_unique,
    verifier_email_unique,
)


class UniciteIdentitesTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.agent = get_user_model().objects.create(
            username="000123",
            email=" Agent@EXAMPLE.COM ",
        )

    def test_matricule_disponible(self):
        self.assertEqual(
            verifier_matricule_unique("000124"),
            "000124",
        )

    def test_matricule_existant(self):
        with self.assertRaises(ValidationError):
            verifier_matricule_unique("000123")

    def test_matricule_inchange(self):
        self.assertEqual(
            verifier_matricule_unique(
                "000123", self.agent.pk
            ),
            "000123",
        )

    def test_email_disponible(self):
        self.assertEqual(
            verifier_email_unique("autre@example.com"),
            "autre@example.com",
        )

    def test_email_existant(self):
        with self.assertRaises(ValidationError):
            verifier_email_unique("agent@example.com")

    def test_email_inchange(self):
        self.assertEqual(
            verifier_email_unique(
                "AGENT@example.com", self.agent.pk
            ),
            "agent@example.com",
        )
