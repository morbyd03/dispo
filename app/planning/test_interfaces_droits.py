from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase, Client
from django.urls import reverse

from .autorisations import GROUPE_ADMINISTRATEURS
from .models import Grade, ProfilAgent, JournalAction
from .services.droits import (
    etat_droits_agent,
    preparer_confirmation_droits,
)


class InterfacesDroitsTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="admin",
            is_superuser=True,
            is_staff=True,
        )

        self.agent = User.objects.create_user(
            username="00123",
            first_name="Jean",
            last_name="Dupont",
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

        self.url = reverse(
            "droits_agent",
            args=[self.profil.pk],
        )

        self.client.force_login(self.admin)

    def consulter(self):
        return self.client.get(
            self.url,
            secure=True,
        )

    def jeton(self):
        return preparer_confirmation_droits(
            auteur_id=self.admin.pk,
            profil=self.profil,
        )

    def soumettre(self, donnees=None, jeton=None):
        contenu = {
            "jeton": self.jeton() if jeton is None else jeton,
        }

        contenu.update(donnees or {})

        return self.client.post(
            self.url,
            contenu,
            secure=True,
        )

    def test_affichage(self):
        reponse = self.consulter()

        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Jean Dupont")
        self.assertContains(reponse, "Administrateur Dispo")
        self.assertContains(
            reponse, "Délégations individuelles"
        )

        self.assertTrue(reponse.context["jeton"])

    def test_lien_depuis_fiche_agent(self):
        reponse = self.client.get(
            reverse(
                "modifier_agent",
                args=[self.profil.pk],
            ),
            secure=True,
        )

        self.assertContains(reponse, self.url)

    def test_attribution_administrateur(self):
        reponse = self.soumettre({
            "administrateur_dispo": "on",
        })

        self.assertEqual(reponse.status_code, 302)
        self.assertIn(self.groupe, self.agent.groups.all())

        self.agent.refresh_from_db()

        self.assertFalse(self.agent.is_staff)
        self.assertFalse(self.agent.is_superuser)

        self.assertTrue(
            JournalAction.objects.filter(
                action="agent.modifier_droits",
                auteur=self.admin,
                objet_id=self.profil.pk,
            ).exists()
        )

    def test_retrait_administrateur(self):
        self.agent.groups.add(self.groupe)

        reponse = self.soumettre()

        self.assertEqual(reponse.status_code, 302)
        self.assertFalse(self.agent.groups.exists())

    def test_delegation_individuelle(self):
        reponse = self.soumettre({
            "delegations": [
                "planning.add_competenceagent",
            ],
        })

        self.assertEqual(reponse.status_code, 302)

        self.assertEqual(
            etat_droits_agent(self.agent),
            {
                "administrateur_dispo": False,
                "delegations": [
                    "planning.add_competenceagent",
                ],
            },
        )

    def test_permission_interdite(self):
        reponse = self.soumettre({
            "delegations": ["auth.delete_user"],
        })

        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.context["formulaire"].errors)
        self.assertFalse(self.agent.user_permissions.exists())

    def test_elevation_technique_ignoree(self):
        reponse = self.soumettre({
            "administrateur_dispo": "on",
            "is_superuser": "on",
            "is_staff": "on",
            "auteur_id": "999",
        })

        self.assertEqual(reponse.status_code, 302)

        self.agent.refresh_from_db()

        self.assertFalse(self.agent.is_superuser)
        self.assertFalse(self.agent.is_staff)

    def test_agent_ordinaire_refuse(self):
        self.client.force_login(self.agent)

        self.assertEqual(
            self.consulter().status_code,
            403,
        )

        self.assertEqual(
            self.client.post(
                self.url, {}, secure=True
            ).status_code,
            403,
        )

    def test_administrateur_dispo_refuse(self):
        gestionnaire = get_user_model().objects.create_user(
            username="gestionnaire",
        )

        gestionnaire.groups.add(self.groupe)

        self.client.force_login(gestionnaire)

        self.assertEqual(
            self.consulter().status_code,
            403,
        )

        self.assertEqual(
            self.client.post(
                self.url,
                {"administrateur_dispo": "on"},
                secure=True,
            ).status_code,
            403,
        )

        self.assertFalse(self.agent.groups.exists())

    def test_administrateur_dispo_sans_lien(self):
        gestionnaire = get_user_model().objects.create_user(
            username="gestionnaire",
        )

        gestionnaire.groups.add(self.groupe)

        self.client.force_login(gestionnaire)

        reponse = self.client.get(
            reverse(
                "modifier_agent",
                args=[self.profil.pk],
            ),
            secure=True,
        )

        self.assertNotContains(reponse, self.url)

    def test_compte_technique_protege(self):
        self.agent.is_staff = True
        self.agent.save(update_fields=["is_staff"])

        self.assertEqual(
            self.consulter().status_code,
            403,
        )

        self.assertEqual(
            self.client.post(
                self.url, {}, secure=True
            ).status_code,
            403,
        )

    def test_jeton_absent(self):
        reponse = self.soumettre(
            {"administrateur_dispo": "on"},
            jeton="",
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.context["formulaire"].errors)
        self.assertFalse(self.agent.groups.exists())

    def test_jeton_altere(self):
        reponse = self.soumettre(
            {"administrateur_dispo": "on"},
            jeton=self.jeton() + "x",
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.context["formulaire"].errors)
        self.assertFalse(self.agent.groups.exists())

    def test_formulaire_obsolete(self):
        jeton = self.jeton()

        self.agent.groups.add(self.groupe)

        reponse = self.soumettre(jeton=jeton)

        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.context["formulaire"].errors)

        self.assertIn(self.groupe, self.agent.groups.all())

        self.assertEqual(
            reponse.context["jeton"],
            jeton,
        )

    def test_aucun_changement(self):
        reponse = self.soumettre()

        self.assertEqual(reponse.status_code, 302)

        self.assertFalse(
            JournalAction.objects.filter(
                action="agent.modifier_droits",
            ).exists()
        )

    def test_protection_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)

        reponse = client.post(
            self.url,
            {
                "jeton": self.jeton(),
                "administrateur_dispo": "on",
            },
            secure=True,
        )

        self.assertEqual(reponse.status_code, 403)
        self.assertFalse(self.agent.groups.exists())

    def test_profil_inexistant(self):
        reponse = self.client.get(
            reverse("droits_agent", args=[999999]),
            secure=True,
        )

        self.assertEqual(reponse.status_code, 404)
