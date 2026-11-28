from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from .autorisations import GROUPE_ADMINISTRATEURS
from .models import Grade, FonctionAgent, ProfilAgent, JournalAction
from .services.agents import creer_agent


class InterfacesAgentsTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="admin",
            is_superuser=True,
            is_staff=True,
        )

        self.grade = Grade.objects.get(code="SAP1")

        self.fonction = FonctionAgent.objects.create(
            nom="Responsable matériel",
        )

        self.donnees = {
            "matricule": "00123",
            "nom": "Dupont",
            "prenom": "Jean",
            "email": "jean.dupont@example.com",
            "grade": self.grade.pk,
            "telephone": "0600000000",
            "fonctions": [self.fonction.pk],
            "actif": "on",
        }

        self.client.force_login(self.admin)

    def creer_profil(self):
        return creer_agent(
            auteur_id=self.admin.pk,
            matricule="00456",
            nom="Martin",
            prenom="Paul",
            email="paul.martin@example.com",
            grade_id=self.grade.pk,
        )

    def test_liste_agents(self):
        profil = self.creer_profil()

        reponse = self.client.get(
            reverse("liste_agents"),
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Martin")
        self.assertContains(reponse, "00456")
        self.assertContains(reponse, "À activer")
        self.assertContains(reponse, self.grade.nom)
        self.assertEqual(
            list(reponse.context["profils"]),
            [profil],
        )

    def test_formulaire_creation(self):
        reponse = self.client.get(
            reverse("ajouter_agent"),
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Matricule")
        self.assertContains(reponse, "Grade")

    def test_creation_agent(self):
        with patch(
            "planning.gestion_agents.envoyer_activation_agent"
        ) as envoi:
            reponse = self.client.post(
                reverse("ajouter_agent"),
                self.donnees,
                secure=True,
            )

        self.assertRedirects(
            reponse,
            reverse("liste_agents"),
            fetch_redirect_response=False,
        )

        profil = ProfilAgent.objects.get(
            utilisateur__username="00123"
        )

        self.assertEqual(profil.grade_id, self.grade.pk)
        self.assertEqual(profil.telephone, "0600000000")
        self.assertIn(self.fonction, profil.fonctions.all())
        self.assertTrue(profil.utilisateur.is_active)
        self.assertFalse(profil.utilisateur.has_usable_password())
        self.assertFalse(profil.utilisateur.is_staff)
        self.assertFalse(profil.utilisateur.is_superuser)

        envoi.assert_not_called()

    def test_creation_matricule_existant(self):
        profil = self.creer_profil()

        self.donnees["matricule"] = profil.utilisateur.username

        reponse = self.client.post(
            reverse("ajouter_agent"),
            self.donnees,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.context["formulaire"].errors)
        self.assertEqual(ProfilAgent.objects.count(), 1)

    def test_creation_email_existant(self):
        profil = self.creer_profil()

        self.donnees["email"] = profil.utilisateur.email.upper()

        reponse = self.client.post(
            reverse("ajouter_agent"),
            self.donnees,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.context["formulaire"].errors)
        self.assertEqual(ProfilAgent.objects.count(), 1)

    def test_formulaire_modification(self):
        profil = self.creer_profil()

        reponse = self.client.get(
            reverse("modifier_agent", args=[profil.pk]),
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "00456")
        self.assertContains(reponse, "paul.martin@example.com")

    def test_modification_profil(self):
        profil = self.creer_profil()

        reponse = self.client.post(
            reverse("modifier_agent", args=[profil.pk]),
            self.donnees,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 302)

        profil.refresh_from_db()
        profil.utilisateur.refresh_from_db()

        self.assertEqual(profil.utilisateur.last_name, "Dupont")
        self.assertEqual(profil.utilisateur.first_name, "Jean")
        self.assertEqual(profil.telephone, "0600000000")

        self.assertEqual(profil.utilisateur.username, "00456")
        self.assertEqual(
            profil.utilisateur.email,
            "paul.martin@example.com",
        )

        self.assertTrue(
            JournalAction.objects.filter(
                action="agent.modifier",
                objet_id=profil.pk,
            ).exists()
        )

    def test_desactivation_agent(self):
        profil = self.creer_profil()

        self.donnees.pop("actif")

        reponse = self.client.post(
            reverse("modifier_agent", args=[profil.pk]),
            self.donnees,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 302)

        profil.utilisateur.refresh_from_db()
        self.assertFalse(profil.utilisateur.is_active)

    def test_agent_ordinaire_refuse(self):
        profil = self.creer_profil()

        self.client.force_login(profil.utilisateur)

        for vue, args in (
            ("liste_agents", []),
            ("ajouter_agent", []),
            ("modifier_agent", [profil.pk]),
        ):
            with self.subTest(vue=vue):
                url = reverse(vue, args=args)

                self.assertEqual(
                    self.client.get(url, secure=True).status_code,
                    403,
                )

                self.assertEqual(
                    self.client.post(
                        url, self.donnees, secure=True
                    ).status_code,
                    403,
                )

    def test_elevation_privileges_ignoree(self):
        self.donnees.update({
            "is_superuser": "on",
            "is_staff": "on",
            "administrateur_dispo": "on",
            "auteur_id": "999",
        })

        reponse = self.client.post(
            reverse("ajouter_agent"),
            self.donnees,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 302)

        profil = ProfilAgent.objects.get(
            utilisateur__username="00123"
        )

        self.assertFalse(profil.utilisateur.is_superuser)
        self.assertFalse(profil.utilisateur.is_staff)
        self.assertFalse(profil.utilisateur.groups.exists())

        journal = JournalAction.objects.get(
            action="agent.creer",
            objet_id=profil.pk,
        )

        self.assertEqual(journal.auteur_id, self.admin.pk)

    def test_administrateur_dispo_autorise(self):
        profil = self.creer_profil()

        gestionnaire = get_user_model().objects.create_user(
            username="gestionnaire",
        )

        groupe, _ = Group.objects.get_or_create(
            name=GROUPE_ADMINISTRATEURS
        )

        groupe.permissions.add(
            *Permission.objects.filter(
                content_type__app_label="auth",
                codename__in=[
                    "view_user",
                    "add_user",
                    "change_user",
                ],
            )
        )

        gestionnaire.groups.add(groupe)

        self.client.force_login(gestionnaire)

        reponse = self.client.get(
            reverse("liste_agents"),
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)

        reponse = self.client.post(
            reverse("modifier_agent", args=[profil.pk]),
            self.donnees,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 302)

    def test_compte_privilegie_protege(self):
        profil = self.creer_profil()

        profil.utilisateur.is_staff = True
        profil.utilisateur.save(update_fields=["is_staff"])

        url = reverse("modifier_agent", args=[profil.pk])

        self.assertEqual(
            self.client.get(url, secure=True).status_code,
            403,
        )

        self.assertEqual(
            self.client.post(
                url, self.donnees, secure=True
            ).status_code,
            403,
        )

    def test_activation_exige_post(self):
        profil = self.creer_profil()

        reponse = self.client.get(
            reverse("reinitialiser_agent", args=[profil.pk]),
            secure=True,
        )

        self.assertEqual(reponse.status_code, 405)

    def test_activation_manuelle(self):
        profil = self.creer_profil()

        with patch(
            "planning.gestion_agents.envoyer_activation_agent",
            return_value=1,
        ) as envoi:
            reponse = self.client.post(
                reverse("reinitialiser_agent", args=[profil.pk]),
                secure=True,
            )

        self.assertEqual(reponse.status_code, 302)
        envoi.assert_called_once()

    def test_activation_agent_desactive_refusee(self):
        profil = self.creer_profil()

        profil.utilisateur.is_active = False
        profil.utilisateur.save(update_fields=["is_active"])

        with patch(
            "planning.gestion_agents.envoyer_activation_agent"
        ) as envoi:
            reponse = self.client.post(
                reverse("reinitialiser_agent", args=[profil.pk]),
                secure=True,
            )

        self.assertEqual(reponse.status_code, 302)
        envoi.assert_not_called()
