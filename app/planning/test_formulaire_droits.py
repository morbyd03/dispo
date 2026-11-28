from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.test import TestCase

from .autorisations import GROUPE_ADMINISTRATEURS
from .formulaires_agents import DroitsAgentForm
from .models import Grade, ProfilAgent


class FormulaireDroitsTests(TestCase):

    def setUp(self):
        self.agent = get_user_model().objects.create_user(
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

    def formulaire(self, donnees=None):
        return DroitsAgentForm(
            donnees,
            profil=self.profil,
        )

    def test_initial_agent_ordinaire(self):
        formulaire = self.formulaire()

        self.assertFalse(
            formulaire.initial["administrateur_dispo"]
        )

        self.assertEqual(
            formulaire.initial["delegations"],
            [],
        )

    def test_initial_administrateur(self):
        self.agent.groups.add(self.groupe)

        formulaire = self.formulaire()

        self.assertTrue(
            formulaire.initial["administrateur_dispo"]
        )

    def test_initial_delegation(self):
        permission = Permission.objects.get(
            content_type__app_label="planning",
            codename="add_competenceagent",
        )

        self.agent.user_permissions.add(permission)

        formulaire = self.formulaire()

        self.assertEqual(
            formulaire.initial["delegations"],
            ["planning.add_competenceagent"],
        )

    def test_attribution_administrateur(self):
        formulaire = self.formulaire({
            "administrateur_dispo": "on",
        })

        self.assertTrue(formulaire.is_valid())

        self.assertEqual(
            formulaire.donnees_droits(),
            {
                "administrateur_dispo": True,
                "delegations": [],
            },
        )

    def test_delegation_independante(self):
        formulaire = self.formulaire({
            "delegations": [
                "planning.add_competenceagent",
                "planning.change_competenceagent",
            ],
        })

        self.assertTrue(formulaire.is_valid())

        self.assertFalse(
            formulaire.donnees_droits()["administrateur_dispo"]
        )

        self.assertEqual(
            len(formulaire.donnees_droits()["delegations"]),
            2,
        )

    def test_retrait_des_droits(self):
        self.agent.groups.add(self.groupe)

        formulaire = self.formulaire({})

        self.assertTrue(formulaire.is_valid())

        self.assertEqual(
            formulaire.donnees_droits(),
            {
                "administrateur_dispo": False,
                "delegations": [],
            },
        )

    def test_permission_interdite(self):
        formulaire = self.formulaire({
            "delegations": ["auth.delete_user"],
        })

        self.assertFalse(formulaire.is_valid())

    def test_champs_privilegies_ignores(self):
        formulaire = self.formulaire({
            "is_superuser": "on",
            "is_staff": "on",
            "auteur_id": "999",
        })

        self.assertTrue(formulaire.is_valid())

        self.assertEqual(
            formulaire.donnees_droits(),
            {
                "administrateur_dispo": False,
                "delegations": [],
            },
        )

    def test_aucune_ecriture_en_base(self):
        formulaire = self.formulaire({
            "administrateur_dispo": "on",
            "delegations": [
                "planning.add_competenceagent",
            ],
        })

        self.assertTrue(formulaire.is_valid())
        formulaire.donnees_droits()

        self.assertFalse(self.agent.groups.exists())
        self.assertFalse(self.agent.user_permissions.exists())
