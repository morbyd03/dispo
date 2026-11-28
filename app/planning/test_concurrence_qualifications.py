from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import (
    Grade,
    ProfilAgent,
    Competence,
    CompetenceAgent,
)
from .services.competences import (
    empreinte_qualifications,
    verifier_empreinte_qualifications,
)


class ConcurrenceQualificationsTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.agent = User.objects.create_user(
            username="00123",
        )

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.agent,
            grade=Grade.objects.get(code="SAP1"),
        )

        self.competence = Competence.objects.get(
            code="cod1",
        )

    def attribuer(self):
        return CompetenceAgent.objects.create(
            profil=self.profil,
            competence=self.competence,
        )

    def test_empreinte_stable(self):
        empreinte = empreinte_qualifications(self.profil)

        self.assertEqual(len(empreinte), 64)

        self.assertEqual(
            empreinte,
            empreinte_qualifications(self.profil),
        )

        verifier_empreinte_qualifications(
            self.profil,
            empreinte,
        )

    def test_attribution_concurrente(self):
        empreinte = empreinte_qualifications(self.profil)

        self.attribuer()

        with self.assertRaises(ValidationError):
            verifier_empreinte_qualifications(
                self.profil,
                empreinte,
            )

    def test_modification_dates_concurrente(self):
        attribution = self.attribuer()

        empreinte = empreinte_qualifications(self.profil)

        attribution.date_expiration = date(2027, 12, 31)

        attribution.save(
            update_fields=["date_expiration"]
        )

        with self.assertRaises(ValidationError):
            verifier_empreinte_qualifications(
                self.profil,
                empreinte,
            )

    def test_retrait_concurrent(self):
        attribution = self.attribuer()

        empreinte = empreinte_qualifications(self.profil)

        attribution.delete()

        with self.assertRaises(ValidationError):
            verifier_empreinte_qualifications(
                self.profil,
                empreinte,
            )

    def test_modification_catalogue(self):
        empreinte = empreinte_qualifications(self.profil)

        self.competence.active = False
        self.competence.save(update_fields=["active"])

        with self.assertRaises(ValidationError):
            verifier_empreinte_qualifications(
                self.profil,
                empreinte,
            )

    def test_ajout_catalogue(self):
        empreinte = empreinte_qualifications(self.profil)

        Competence.objects.create(
            code="qualification-test",
            nom="Qualification de test",
        )

        with self.assertRaises(ValidationError):
            verifier_empreinte_qualifications(
                self.profil,
                empreinte,
            )

    def test_empreinte_invalide(self):
        for valeur in (
            None,
            "",
            123,
            "a" * 63,
            "z" * 64,
            "0" * 64,
        ):
            with self.subTest(valeur=valeur):
                with self.assertRaises(ValidationError):
                    verifier_empreinte_qualifications(
                        self.profil,
                        valeur,
                    )

    def test_empreinte_autre_profil_refusee(self):
        utilisateur = get_user_model().objects.create_user(
            username="00456",
        )

        autre = ProfilAgent.objects.create(
            utilisateur=utilisateur,
            grade=self.profil.grade,
        )

        empreinte = empreinte_qualifications(autre)

        with self.assertRaises(ValidationError):
            verifier_empreinte_qualifications(
                self.profil,
                empreinte,
            )
