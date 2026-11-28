from datetime import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from .autorisations import GROUPE_ADMINISTRATEURS
from .models import (
    Grade,
    ProfilAgent,
    JournalAction,
    Disponibilite,
    Competence,
    CompetenceAgent,
)
from .services.agents import modifier_statut_agent


class StatutAgentTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="admin",
            is_superuser=True,
        )

        self.agent = User.objects.create_user(
            username="00123",
            password="mot-de-passe-test",
            email="agent@example.com",
        )

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.agent,
            grade=Grade.objects.get(code="SAP1"),
        )

    def modifier(self, actif, auteur=None):
        return modifier_statut_agent(
            auteur_id=(auteur or self.admin).pk,
            profil_id=self.profil.pk,
            actif=actif,
        )

    def test_desactivation(self):
        self.assertTrue(self.modifier(False))
        self.agent.refresh_from_db()
        self.assertFalse(self.agent.is_active)

    def test_reactivation(self):
        self.modifier(False)
        self.assertTrue(self.modifier(True))
        self.agent.refresh_from_db()
        self.assertTrue(self.agent.is_active)

    def test_journalisation(self):
        self.modifier(False)

        journal = JournalAction.objects.get()

        self.assertEqual(journal.auteur_id, self.admin.pk)
        self.assertEqual(journal.action, "agent.desactiver")
        self.assertEqual(journal.objet_id, self.profil.pk)
        self.assertEqual(
            journal.details,
            {"avant": True, "apres": False},
        )

        self.modifier(True)

        self.assertTrue(
            JournalAction.objects.filter(
                action="agent.activer"
            ).exists()
        )

    def test_statut_inchange(self):
        self.assertFalse(self.modifier(True))
        self.assertFalse(JournalAction.objects.exists())

    def test_statut_invalide(self):
        for valeur in ("false", "true", 0, 1, None):
            with self.subTest(valeur=valeur):
                with self.assertRaises(ValidationError):
                    self.modifier(valeur)

        self.agent.refresh_from_db()
        self.assertTrue(self.agent.is_active)

    def test_agent_ordinaire_refuse(self):
        auteur = get_user_model().objects.create_user(
            username="autre_agent",
        )

        with self.assertRaises(PermissionDenied):
            self.modifier(False, auteur)

    def test_auteur_inactif_refuse(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            self.modifier(False)

    def test_administrateur_autorise(self):
        auteur = get_user_model().objects.create_user(
            username="gestionnaire",
        )

        groupe, _ = Group.objects.get_or_create(
            name=GROUPE_ADMINISTRATEURS
        )

        groupe.permissions.add(
            Permission.objects.get(
                content_type__app_label="auth",
                codename="change_user",
            )
        )

        auteur.groups.add(groupe)

        self.assertTrue(self.modifier(False, auteur))

    def test_compte_technique_protege(self):
        self.agent.is_staff = True
        self.agent.save(update_fields=["is_staff"])

        with self.assertRaises(PermissionDenied):
            self.modifier(False)

    def test_auto_desactivation_refusee(self):
        self.agent.is_superuser = True
        self.agent.save(update_fields=["is_superuser"])

        with self.assertRaises(PermissionDenied):
            self.modifier(False, self.agent)

    def test_conservation_des_donnees(self):
        mot_de_passe = self.agent.password

        dispo = Disponibilite.objects.create(
            profil=self.profil,
            debut=timezone.make_aware(datetime(2027, 1, 4, 21)),
            fin=timezone.make_aware(datetime(2027, 1, 5, 6)),
        )

        qualification = CompetenceAgent.objects.create(
            profil=self.profil,
            competence=Competence.objects.get(code="cod1"),
            valide_par=self.admin,
        )

        self.modifier(False)
        self.modifier(True)

        self.agent.refresh_from_db()

        self.assertEqual(self.agent.password, mot_de_passe)
        self.assertEqual(self.agent.email, "agent@example.com")

        self.assertTrue(
            Disponibilite.objects.filter(pk=dispo.pk).exists()
        )

        self.assertTrue(
            CompetenceAgent.objects.filter(
                pk=qualification.pk
            ).exists()
        )

    def test_annulation_si_journalisation_echoue(self):
        with patch(
            "planning.services.journal.journaliser",
            side_effect=RuntimeError("Erreur simulee"),
        ):
            with self.assertRaises(RuntimeError):
                self.modifier(False)

        self.agent.refresh_from_db()

        self.assertTrue(self.agent.is_active)
        self.assertFalse(JournalAction.objects.exists())
