from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase

from .autorisations import (
    GROUPE_ADMINISTRATEURS,
    PERMISSIONS_ADMINISTRATEURS,
    PERMISSIONS_DELEGATION_QUALIFICATIONS,
)
from .models import Grade, ProfilAgent, JournalAction
from .services.droits import (
    modifier_droits_agent,
    etat_droits_agent,
)


class ServicesDroitsTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="admin",
            is_superuser=True,
            is_staff=True,
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

        self.delegation = PERMISSIONS_DELEGATION_QUALIFICATIONS[0]

    def modifier(self, **kwargs):
        donnees = {
            "auteur_id": self.admin.pk,
            "profil_id": self.profil.pk,
            "administrateur_dispo": True,
            "delegations": [],
        }

        donnees.update(kwargs)

        return modifier_droits_agent(**donnees)

    def test_initialisation_permissions_exactes(self):
        permissions = {
            f"{application}.{code}"
            for application, code in self.groupe.permissions.values_list(
                "content_type__app_label",
                "codename",
            )
        }

        self.assertEqual(
            permissions,
            set(PERMISSIONS_ADMINISTRATEURS),
        )

    def test_initialisation_retire_permission_excedentaire(self):
        permission = Permission.objects.get(
            content_type__app_label="auth",
            codename="delete_user",
        )

        self.groupe.permissions.add(permission)

        call_command(
            "initialiser_dispo",
            stdout=StringIO(),
        )

        self.assertFalse(
            self.groupe.permissions.filter(
                pk=permission.pk
            ).exists()
        )

    def test_attribution_administrateur(self):
        self.assertTrue(self.modifier())
        self.assertIn(self.groupe, self.agent.groups.all())

        self.agent.refresh_from_db()

        self.assertFalse(self.agent.is_staff)
        self.assertFalse(self.agent.is_superuser)

    def test_retrait_administrateur(self):
        self.modifier()

        self.assertTrue(
            self.modifier(administrateur_dispo=False)
        )

        self.assertNotIn(
            self.groupe,
            self.agent.groups.all(),
        )

    def test_delegation_independante(self):
        self.modifier(
            administrateur_dispo=False,
            delegations=[self.delegation],
        )

        self.assertTrue(
            self.agent.has_perm(self.delegation)
        )

        self.assertFalse(
            self.agent.has_perm("auth.change_user")
        )

    def test_retrait_delegation(self):
        self.modifier(
            administrateur_dispo=False,
            delegations=[self.delegation],
        )

        self.modifier(
            administrateur_dispo=False,
            delegations=[],
        )

        self.assertEqual(
            etat_droits_agent(self.agent)["delegations"],
            [],
        )

    def test_permission_non_delegable(self):
        with self.assertRaises(ValidationError):
            self.modifier(
                delegations=["auth.delete_user"],
            )

        self.assertFalse(self.agent.groups.exists())

    def test_administrateur_dispo_ne_peut_pas_attribuer_droits(self):
        gestionnaire = get_user_model().objects.create_user(
            username="gestionnaire",
        )

        gestionnaire.groups.add(self.groupe)

        with self.assertRaises(PermissionDenied):
            self.modifier(auteur_id=gestionnaire.pk)

    def test_agent_ordinaire_refuse(self):
        auteur = get_user_model().objects.create_user(
            username="00456",
        )

        with self.assertRaises(PermissionDenied):
            self.modifier(auteur_id=auteur.pk)

    def test_compte_technique_protege(self):
        self.agent.is_staff = True
        self.agent.save(update_fields=["is_staff"])

        with self.assertRaises(PermissionDenied):
            self.modifier()

    def test_auto_attribution_refusee(self):
        self.profil.utilisateur = self.admin
        self.profil.save(update_fields=["utilisateur"])

        with self.assertRaises(PermissionDenied):
            self.modifier()

    def test_superutilisateur_inactif_refuse(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            self.modifier()

    def test_groupe_non_conforme_refuse(self):
        self.groupe.permissions.clear()

        with self.assertRaises(ValidationError):
            self.modifier()

        self.assertFalse(self.agent.groups.exists())

    def test_statut_invalide(self):
        with self.assertRaises(ValidationError):
            self.modifier(administrateur_dispo="oui")

    def test_conservation_autres_permissions(self):
        permission = Permission.objects.get(
            content_type__app_label="auth",
            codename="view_user",
        )

        self.agent.user_permissions.add(permission)

        self.modifier()

        self.assertIn(
            permission,
            self.agent.user_permissions.all(),
        )

    def test_conservation_autres_groupes(self):
        groupe = Group.objects.create(name="Autre groupe")

        self.agent.groups.add(groupe)

        self.modifier()
        self.modifier(administrateur_dispo=False)

        self.assertIn(groupe, self.agent.groups.all())

    def test_journalisation(self):
        self.modifier(delegations=[self.delegation])

        journal = JournalAction.objects.get(
            action="agent.modifier_droits",
            objet_id=self.profil.pk,
        )

        self.assertEqual(journal.auteur_id, self.admin.pk)

        self.assertEqual(
            journal.details["avant"],
            {
                "administrateur_dispo": False,
                "delegations": [],
            },
        )

        self.assertEqual(
            journal.details["apres"],
            {
                "administrateur_dispo": True,
                "delegations": [self.delegation],
            },
        )

    def test_aucun_changement(self):
        self.modifier()

        self.assertFalse(self.modifier())

        self.assertEqual(
            JournalAction.objects.filter(
                action="agent.modifier_droits",
            ).count(),
            1,
        )

    def test_annulation_si_journalisation_echoue(self):
        with patch(
            "planning.services.droits.journaliser",
            side_effect=RuntimeError("Erreur simulee"),
        ):
            with self.assertRaises(RuntimeError):
                self.modifier(
                    delegations=[self.delegation],
                )

        self.assertFalse(self.agent.groups.exists())
        self.assertFalse(self.agent.user_permissions.exists())
