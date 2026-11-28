from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Grade, SecuriteCompte
from .services.agents import (
    creer_agent,
    modifier_statut_agent,
)
from .services.securite import (
    version_securite_compte,
    revoquer_acces_compte,
)


class SecuriteComptesTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="admin",
            is_superuser=True,
        )

        self.profil = creer_agent(
            auteur_id=self.admin.pk,
            matricule="00123",
            nom="Dupont",
            prenom="Jean",
            email="jean@example.com",
            grade_id=Grade.objects.get(code="SAP1").pk,
        )

        self.agent = self.profil.utilisateur

        self.agent.set_password("MotDePasseTest!4826")
        self.agent.save(update_fields=["password"])

    def version(self):
        return version_securite_compte(self.agent.pk)

    def modifier_statut(self, actif):
        return modifier_statut_agent(
            auteur_id=self.admin.pk,
            profil_id=self.profil.pk,
            actif=actif,
        )

    def test_version_initiale(self):
        self.assertEqual(self.version(), 0)
        self.assertFalse(SecuriteCompte.objects.exists())

    def test_premiere_revocation(self):
        self.assertEqual(
            revoquer_acces_compte(self.agent.pk),
            1,
        )

        self.assertEqual(self.version(), 1)

    def test_revocations_successives(self):
        for version in range(1, 6):
            self.assertEqual(
                revoquer_acces_compte(self.agent.pk),
                version,
            )

        self.assertEqual(SecuriteCompte.objects.count(), 1)

    def test_revocation_compte_technique(self):
        self.assertEqual(
            revoquer_acces_compte(self.admin.pk),
            1,
        )

        self.assertEqual(self.version(), 0)

    def test_desactivation(self):
        self.modifier_statut(False)

        self.assertEqual(self.version(), 1)

        self.agent.refresh_from_db()
        self.assertFalse(self.agent.is_active)

    def test_desactivation_reactivation(self):
        self.modifier_statut(False)
        self.modifier_statut(True)

        self.assertEqual(self.version(), 2)

        self.agent.refresh_from_db()
        self.assertTrue(self.agent.is_active)

    def test_statut_inchange(self):
        self.assertFalse(self.modifier_statut(True))
        self.assertEqual(self.version(), 0)

        self.modifier_statut(False)

        self.assertFalse(self.modifier_statut(False))
        self.assertEqual(self.version(), 1)

    def test_conservation_mot_de_passe(self):
        ancien = self.agent.password

        self.modifier_statut(False)
        self.modifier_statut(True)

        self.agent.refresh_from_db()

        self.assertEqual(self.agent.password, ancien)
        self.assertTrue(
            self.agent.check_password(
                "MotDePasseTest!4826"
            )
        )

    def test_annulation_si_journalisation_echoue(self):
        with patch(
            "planning.services.journal.journaliser",
            side_effect=RuntimeError("Erreur simulee"),
        ):
            with self.assertRaises(RuntimeError):
                self.modifier_statut(False)

        self.agent.refresh_from_db()

        self.assertTrue(self.agent.is_active)
        self.assertEqual(self.version(), 0)
        self.assertFalse(SecuriteCompte.objects.exists())
