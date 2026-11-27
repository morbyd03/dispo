from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import (
    ProfilAgent,
    Competence,
    CompetenceAgent,
)
from .services.competences import attribuer_competence


class AttributionCompetenceTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.agent = User.objects.create(
            username="000123"
        )

        self.validateur = User.objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.agent
        )

        self.competence = Competence.objects.get(code="cod1")

        self.donnees = {
            "profil_id": self.profil.pk,
            "competence_id": self.competence.pk,
            "validateur_id": self.validateur.pk,
        }

    def test_attribution(self):
        attribution = attribuer_competence(**self.donnees)

        self.assertEqual(attribution.profil, self.profil)
        self.assertEqual(attribution.competence, self.competence)
        self.assertEqual(attribution.valide_par, self.validateur)

    def test_dates_facultatives(self):
        attribution = attribuer_competence(**self.donnees)

        self.assertIsNone(attribution.date_validation)
        self.assertIsNone(attribution.date_expiration)

    def test_dates_valides(self):
        attribution = attribuer_competence(
            **self.donnees,
            date_validation="2026-01-01",
            date_expiration="2027-01-01",
        )

        self.assertEqual(
            attribution.date_validation,
            date(2026, 1, 1),
        )
        self.assertEqual(
            attribution.date_expiration,
            date(2027, 1, 1),
        )

    def test_dates_inversees(self):
        with self.assertRaises(ValidationError):
            attribuer_competence(
                **self.donnees,
                date_validation="2027-01-01",
                date_expiration="2026-01-01",
            )

        self.assertFalse(CompetenceAgent.objects.exists())

    def test_date_invalide(self):
        with self.assertRaises(ValidationError):
            attribuer_competence(
                **self.donnees,
                date_validation="2026-02-30",
            )

    def test_attribution_dupliquee(self):
        attribuer_competence(**self.donnees)

        with self.assertRaises(ValidationError):
            attribuer_competence(**self.donnees)

        self.assertEqual(CompetenceAgent.objects.count(), 1)

    def test_competence_inactive(self):
        self.competence.active = False
        self.competence.save(update_fields=["active"])

        with self.assertRaises(ValidationError):
            attribuer_competence(**self.donnees)

    def test_profil_inexistant(self):
        self.donnees["profil_id"] = 999999

        with self.assertRaises(ValidationError):
            attribuer_competence(**self.donnees)

    def test_validateur_inactif(self):
        self.validateur.is_active = False
        self.validateur.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            attribuer_competence(**self.donnees)

    def test_attribution_non_autorisee(self):
        from django.core.exceptions import PermissionDenied

        self.donnees["validateur_id"] = self.agent.pk

        with self.assertRaises(PermissionDenied):
            attribuer_competence(**self.donnees)

        self.assertFalse(CompetenceAgent.objects.exists())


class ModificationCompetenceTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.agent = User.objects.create(
            username="000123"
        )

        self.validateur = User.objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.agent
        )

        self.competence = Competence.objects.get(code="cod1")

        self.attribution = CompetenceAgent.objects.create(
            profil=self.profil,
            competence=self.competence,
            valide_par=self.validateur,
        )

        self.donnees = {
            "attribution_id": self.attribution.pk,
            "validateur_id": self.validateur.pk,
            "date_validation": "2026-01-01",
            "date_expiration": "2027-01-01",
        }

    def test_modification_dates(self):
        from .services.competences import modifier_competence

        attribution = modifier_competence(**self.donnees)

        self.assertEqual(attribution.pk, self.attribution.pk)
        self.assertEqual(attribution.profil, self.profil)
        self.assertEqual(attribution.competence, self.competence)
        self.assertEqual(
            attribution.date_expiration,
            date(2027, 1, 1),
        )
        self.assertEqual(CompetenceAgent.objects.count(), 1)

    def test_dates_inversees(self):
        from .services.competences import modifier_competence

        self.donnees["date_expiration"] = "2025-01-01"

        with self.assertRaises(ValidationError):
            modifier_competence(**self.donnees)

        self.attribution.refresh_from_db()
        self.assertIsNone(self.attribution.date_validation)

    def test_modification_non_autorisee(self):
        from django.core.exceptions import PermissionDenied
        from .services.competences import modifier_competence

        self.donnees["validateur_id"] = self.agent.pk

        with self.assertRaises(PermissionDenied):
            modifier_competence(**self.donnees)

    def test_competence_historique_inactive(self):
        from .services.competences import modifier_competence

        self.competence.active = False
        self.competence.save(update_fields=["active"])

        attribution = modifier_competence(**self.donnees)

        self.assertEqual(attribution.pk, self.attribution.pk)

    def test_nouveau_validateur(self):
        from .services.competences import modifier_competence

        nouveau = get_user_model().objects.create(
            username="administrateur2",
            is_superuser=True,
        )

        self.donnees["validateur_id"] = nouveau.pk

        attribution = modifier_competence(**self.donnees)

        self.assertEqual(attribution.valide_par, nouveau)

    def test_absence_de_modification(self):
        from .services.competences import modifier_competence

        nouveau = get_user_model().objects.create(
            username="administrateur2",
            is_superuser=True,
        )

        self.donnees["validateur_id"] = nouveau.pk
        self.donnees["date_validation"] = None
        self.donnees["date_expiration"] = None

        attribution = modifier_competence(**self.donnees)

        self.assertEqual(attribution.valide_par, self.validateur)
