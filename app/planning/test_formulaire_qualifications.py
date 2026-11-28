from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from .models import (
    Grade,
    ProfilAgent,
    Competence,
    CompetenceAgent,
)
from .formulaires_agents import QualificationsAgentForm


class FormulaireQualificationsTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="admin",
            is_superuser=True,
        )

        self.agent = User.objects.create_user(
            username="00123",
        )

        self.validateur = User.objects.create_user(
            username="validateur",
        )

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.agent,
            grade=Grade.objects.get(code="SAP1"),
        )

        self.competence = Competence.objects.get(
            code="cod1"
        )

        self.pk = self.competence.pk

    def formulaire(self, donnees, validateur=None):
        return QualificationsAgentForm(
            donnees,
            profil=self.profil,
            validateur=validateur or self.admin,
        )

    def attribuer(self):
        return CompetenceAgent.objects.create(
            profil=self.profil,
            competence=self.competence,
            valide_par=self.admin,
            date_validation=date(2027, 1, 1),
            date_expiration=date(2027, 12, 31),
        )

    def autoriser(self, codename):
        self.validateur.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="planning",
                codename=codename,
            )
        )

    def test_attribution(self):
        formulaire = self.formulaire({
            f"competence_{self.pk}": "on",
        })

        self.assertTrue(
            formulaire.is_valid(),
            formulaire.errors,
        )

        self.assertEqual(
            formulaire.operations(),
            [{
                "action": "attribuer",
                "profil_id": self.profil.pk,
                "competence_id": self.pk,
                "date_validation": None,
                "date_expiration": None,
            }],
        )

        self.assertFalse(CompetenceAgent.objects.exists())

    def test_attribution_avec_dates(self):
        formulaire = self.formulaire({
            f"competence_{self.pk}": "on",
            f"date_validation_{self.pk}": "2027-01-01",
            f"date_expiration_{self.pk}": "2027-12-31",
        })

        self.assertTrue(formulaire.is_valid())

        operation = formulaire.operations()[0]

        self.assertEqual(
            operation["date_validation"],
            date(2027, 1, 1),
        )

        self.assertEqual(
            operation["date_expiration"],
            date(2027, 12, 31),
        )

    def test_dates_incoherentes(self):
        formulaire = self.formulaire({
            f"competence_{self.pk}": "on",
            f"date_validation_{self.pk}": "2027-12-31",
            f"date_expiration_{self.pk}": "2027-01-01",
        })

        self.assertFalse(formulaire.is_valid())

    def test_retrait(self):
        attribution = self.attribuer()

        formulaire = self.formulaire({})

        self.assertTrue(formulaire.is_valid())

        self.assertEqual(
            formulaire.operations(),
            [{
                "action": "retirer",
                "attribution_id": attribution.pk,
            }],
        )

    def test_modification_dates(self):
        attribution = self.attribuer()

        formulaire = self.formulaire({
            f"competence_{self.pk}": "on",
            f"date_validation_{self.pk}": "2027-01-01",
            f"date_expiration_{self.pk}": "2028-12-31",
        })

        self.assertTrue(formulaire.is_valid())

        self.assertEqual(
            formulaire.operations(),
            [{
                "action": "modifier",
                "attribution_id": attribution.pk,
                "date_validation": date(2027, 1, 1),
                "date_expiration": date(2028, 12, 31),
            }],
        )

    def test_aucun_changement(self):
        self.attribuer()

        formulaire = self.formulaire({
            f"competence_{self.pk}": "on",
            f"date_validation_{self.pk}": "2027-01-01",
            f"date_expiration_{self.pk}": "2027-12-31",
        })

        self.assertTrue(formulaire.is_valid())
        self.assertEqual(formulaire.operations(), [])

    def test_competence_inactive_preservee(self):
        self.attribuer()

        self.competence.active = False
        self.competence.save(update_fields=["active"])

        formulaire = self.formulaire({})

        self.assertTrue(formulaire.is_valid())
        self.assertEqual(formulaire.operations(), [])

    def test_attribution_non_autorisee_ignoree(self):
        formulaire = self.formulaire(
            {f"competence_{self.pk}": "on"},
            self.validateur,
        )

        self.assertTrue(formulaire.is_valid())
        self.assertEqual(formulaire.operations(), [])

    def test_retrait_non_autorise_ignore(self):
        self.attribuer()

        formulaire = self.formulaire(
            {},
            self.validateur,
        )

        self.assertTrue(formulaire.is_valid())
        self.assertEqual(formulaire.operations(), [])

    def test_modification_non_autorisee_ignoree(self):
        self.attribuer()

        formulaire = self.formulaire(
            {
                f"competence_{self.pk}": "on",
                f"date_expiration_{self.pk}": "2028-12-31",
            },
            self.validateur,
        )

        self.assertTrue(formulaire.is_valid())
        self.assertEqual(formulaire.operations(), [])

    def test_delegation_attribution(self):
        self.autoriser("add_competenceagent")

        formulaire = self.formulaire(
            {f"competence_{self.pk}": "on"},
            self.validateur,
        )

        self.assertTrue(formulaire.is_valid())

        self.assertEqual(
            formulaire.operations()[0]["action"],
            "attribuer",
        )

    def test_delegation_modification(self):
        self.attribuer()
        self.autoriser("change_competenceagent")

        formulaire = self.formulaire(
            {
                f"date_validation_{self.pk}": "2027-01-01",
                f"date_expiration_{self.pk}": "2028-12-31",
            },
            self.validateur,
        )

        self.assertTrue(formulaire.is_valid())

        self.assertEqual(
            formulaire.operations()[0]["action"],
            "modifier",
        )
