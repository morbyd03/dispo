from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.test import TestCase

from .autorisations import GROUPE_ADMINISTRATEURS
from .models import Grade, ProfilAgent
from .services.droits import (
    preparer_confirmation_droits,
    confirmer_modification_droits,
)


class ConfirmationDroitsTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="admin",
            is_superuser=True,
        )

        self.agent = User.objects.create_user(
            username="00123",
        )

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.agent,
            grade=Grade.objects.get(code="SAP1"),
        )

        call_command(
            "initialiser_dispo",
            stdout=StringIO(),
        )

        self.groupe = Group.objects.get(
            name=GROUPE_ADMINISTRATEURS,
        )

        self.jeton = preparer_confirmation_droits(
            auteur_id=self.admin.pk,
            profil=self.profil,
        )

    def confirmer(self, **kwargs):
        donnees = {
            "auteur_id": self.admin.pk,
            "profil_id": self.profil.pk,
            "jeton": self.jeton,
            "administrateur_dispo": True,
            "delegations": [],
        }

        donnees.update(kwargs)

        return confirmer_modification_droits(**donnees)

    def test_confirmation_valide(self):
        self.assertTrue(self.confirmer())

        self.assertIn(
            self.groupe,
            self.agent.groups.all(),
        )

    def test_jeton_altere(self):
        with self.assertRaises(ValidationError):
            self.confirmer(jeton=self.jeton + "x")

        self.assertFalse(self.agent.groups.exists())

    def test_jeton_absent(self):
        with self.assertRaises(ValidationError):
            self.confirmer(jeton="")

    def test_autre_superutilisateur_refuse(self):
        autre = get_user_model().objects.create_user(
            username="autre-admin",
            is_superuser=True,
        )

        with self.assertRaises(ValidationError):
            self.confirmer(auteur_id=autre.pk)

    def test_autre_profil_refuse(self):
        utilisateur = get_user_model().objects.create_user(
            username="00456",
        )

        autre = ProfilAgent.objects.create(
            utilisateur=utilisateur,
            grade=self.profil.grade,
        )

        with self.assertRaises(ValidationError):
            self.confirmer(profil_id=autre.pk)

    def test_modification_concurrente_groupe(self):
        self.agent.groups.add(self.groupe)

        with self.assertRaises(ValidationError):
            self.confirmer(administrateur_dispo=False)

        self.assertIn(
            self.groupe,
            self.agent.groups.all(),
        )

    def test_modification_concurrente_permission(self):
        permission = Permission.objects.get(
            content_type__app_label="planning",
            codename="add_competenceagent",
        )

        self.agent.user_permissions.add(permission)

        with self.assertRaises(ValidationError):
            self.confirmer()

        self.assertIn(
            permission,
            self.agent.user_permissions.all(),
        )

    def test_modification_statut_compte(self):
        self.agent.is_active = False
        self.agent.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            self.confirmer()

    def test_jeton_expire(self):
        with patch(
            "planning.services.droits.DUREE_CONFIRMATION_DROITS",
            -1,
        ):
            with self.assertRaises(ValidationError):
                self.confirmer()

    def test_ancien_jeton_apres_modification(self):
        self.confirmer()

        with self.assertRaises(ValidationError):
            self.confirmer(administrateur_dispo=False)

    def test_auteur_devenu_inactif(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            self.confirmer()

    def test_auteur_ayant_perdu_ses_droits(self):
        self.admin.is_superuser = False
        self.admin.save(update_fields=["is_superuser"])

        with self.assertRaises(PermissionDenied):
            self.confirmer()

    def test_cible_devenue_technique(self):
        self.agent.is_staff = True
        self.agent.save(update_fields=["is_staff"])

        with self.assertRaises(PermissionDenied):
            self.confirmer()
