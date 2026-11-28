from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Grade, ProfilAgent, JournalAction
from .services.agents import (
    creer_agent,
    modifier_agent,
    rattacher_profil_agent,
)


class JournalAgentsTests(TestCase):

    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="admin",
            is_superuser=True,
        )

        self.grade = Grade.objects.get(code="SAP1")

        self.donnees = {
            "auteur_id": self.admin.pk,
            "matricule": "00123",
            "nom": "Dupont",
            "prenom": "Jean",
            "email": "jean.dupont@example.com",
            "grade_id": self.grade.pk,
        }

    def creer(self):
        return creer_agent(**self.donnees)

    def modifier(self, profil, **changements):
        donnees = {
            "auteur_id": self.admin.pk,
            "profil_id": profil.pk,
            "nom": profil.utilisateur.last_name,
            "prenom": profil.utilisateur.first_name,
            "grade_id": profil.grade_id,
            "telephone": profil.telephone,
            "fonctions_ids": list(
                profil.fonctions.values_list("pk", flat=True)
            ),
        }

        donnees.update(changements)
        return modifier_agent(**donnees)

    def test_creation_journalisee(self):
        profil = self.creer()

        journal = JournalAction.objects.get(
            action="agent.creer"
        )

        self.assertEqual(journal.auteur_id, self.admin.pk)
        self.assertEqual(journal.objet_id, profil.pk)
        self.assertNotIn("password", journal.details)
        self.assertNotIn("email", journal.details)

    def test_modification_journalisee(self):
        profil = self.creer()

        self.modifier(profil, nom="Durand")

        journal = JournalAction.objects.get(
            action="agent.modifier"
        )

        self.assertEqual(
            journal.details["changements"],
            {
                "nom": {
                    "avant": "Dupont",
                    "apres": "Durand",
                },
            },
        )

    def test_modification_sans_changement(self):
        profil = self.creer()
        self.modifier(profil)

        self.assertFalse(
            JournalAction.objects.filter(
                action="agent.modifier"
            ).exists()
        )

    def test_rattachement_journalise(self):
        utilisateur = get_user_model().objects.create_user(
            username="00456",
            first_name="Paul",
            last_name="Martin",
            email="paul.martin@example.com",
        )

        profil = rattacher_profil_agent(
            auteur_id=self.admin.pk,
            utilisateur_id=utilisateur.pk,
            grade_id=self.grade.pk,
        )

        journal = JournalAction.objects.get(
            action="agent.rattacher"
        )

        self.assertEqual(journal.objet_id, profil.pk)
        self.assertEqual(
            journal.details["utilisateur_id"],
            utilisateur.pk,
        )

    def test_annulation_creation_si_journal_echoue(self):
        with patch(
            "planning.services.agents.journaliser",
            side_effect=RuntimeError("Erreur simulee"),
        ):
            with self.assertRaises(RuntimeError):
                self.creer()

        self.assertFalse(ProfilAgent.objects.exists())

        self.assertFalse(
            get_user_model().objects.filter(
                username="00123"
            ).exists()
        )

    def test_annulation_modification_si_journal_echoue(self):
        profil = self.creer()

        with patch(
            "planning.services.agents.journaliser",
            side_effect=RuntimeError("Erreur simulee"),
        ):
            with self.assertRaises(RuntimeError):
                self.modifier(profil, nom="Durand")

        profil.utilisateur.refresh_from_db()

        self.assertEqual(
            profil.utilisateur.last_name,
            "Dupont",
        )

        self.assertFalse(
            JournalAction.objects.filter(
                action="agent.modifier"
            ).exists()
        )
