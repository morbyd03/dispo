from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.test import TestCase
from django.urls import reverse

from .models import Grade, ProfilAgent, JournalAction
from .autorisations import GROUPE_ADMINISTRATEURS


class InterfaceExportAgentsTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.superutilisateur = User.objects.create(
            username="superadministrateur",
            is_superuser=True,
        )

        self.administrateur = User.objects.create(
            username="administrateur",
        )

        self.administrateur.groups.add(
            Group.objects.get_or_create(
                name=GROUPE_ADMINISTRATEURS
            )[0]
        )

        self.agent = User.objects.create(
            username="000123",
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.agent,
            grade=Grade.objects.get(code="SAP1"),
        )

        self.url = reverse("export_agents")

        self.url_telechargement = reverse(
            "telecharger_export_agents"
        )

    def connecter(self, utilisateur=None):
        self.client.force_login(
            utilisateur or self.superutilisateur
        )

    def telecharger(self, mode="consultation"):
        return self.client.get(
            self.url_telechargement,
            {"mode": mode},
            secure=True,
        )

    def test_page_export(self):
        self.connecter()

        reponse = self.client.get(
            self.url,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertTemplateUsed(
            reponse, "planning/export_agents.html"
        )
        self.assertContains(reponse, "Exporter les agents")
        self.assertContains(reponse, "?mode=consultation")
        self.assertContains(reponse, "?mode=reimport")

    def test_page_non_connecte(self):
        reponse = self.client.get(
            self.url,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 302)

    def test_telechargement_non_connecte(self):
        reponse = self.telecharger()

        self.assertEqual(reponse.status_code, 302)

    def test_agent_interdit(self):
        self.connecter(self.agent)

        for url in (self.url, self.url_telechargement):
            with self.subTest(url=url):
                reponse = self.client.get(
                    url,
                    secure=True,
                )

                self.assertEqual(reponse.status_code, 403)

    def test_administrateur_dispo_interdit(self):
        self.connecter(self.administrateur)

        for url in (self.url, self.url_telechargement):
            with self.subTest(url=url):
                reponse = self.client.get(
                    url,
                    secure=True,
                )

                self.assertEqual(reponse.status_code, 403)

    def test_compte_desactive(self):
        self.connecter()

        self.superutilisateur.is_active = False
        self.superutilisateur.save(
            update_fields=["is_active"]
        )

        reponse = self.telecharger()

        self.assertEqual(reponse.status_code, 302)

    def test_export_consultation(self):
        self.connecter()

        reponse = self.telecharger()

        self.assertEqual(reponse.status_code, 200)

        self.assertEqual(
            reponse["Content-Type"],
            "text/csv; charset=utf-8",
        )

        self.assertEqual(
            reponse["Content-Disposition"],
            'attachment; filename="agents-dispo-consultation.csv"',
        )

        self.assertTrue(
            reponse.content.startswith(b"\xef\xbb\xbf")
        )

        self.assertIn(b'"000123"', reponse.content)
        self.assertIn(b'"jean@example.com"', reponse.content)

    def test_export_reimport(self):
        self.connecter()

        reponse = self.telecharger("reimport")

        self.assertEqual(reponse.status_code, 200)

        self.assertEqual(
            reponse["Content-Disposition"],
            'attachment; filename="agents-dispo-reimport.csv"',
        )

    def test_mode_par_defaut(self):
        self.connecter()

        reponse = self.client.get(
            self.url_telechargement,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)

        self.assertIn(
            "consultation.csv",
            reponse["Content-Disposition"],
        )

    def test_mode_invalide(self):
        self.connecter()

        reponse = self.telecharger("inconnu")

        self.assertEqual(reponse.status_code, 400)

    def test_absence_cache_page(self):
        self.connecter()

        reponse = self.client.get(
            self.url,
            secure=True,
        )

        self.assertIn(
            "no-store",
            reponse["Cache-Control"],
        )

    def test_absence_cache_telechargement(self):
        self.connecter()

        reponse = self.telecharger()

        self.assertIn(
            "no-store",
            reponse["Cache-Control"],
        )

        self.assertEqual(
            reponse["X-Content-Type-Options"],
            "nosniff",
        )

    def test_methode_post_refusee(self):
        self.connecter()

        for url in (self.url, self.url_telechargement):
            with self.subTest(url=url):
                reponse = self.client.post(
                    url,
                    secure=True,
                )

                self.assertEqual(reponse.status_code, 405)

    def test_absence_ecriture_metier(self):
        self.connecter()

        nombre_agents = get_user_model().objects.count()

        self.telecharger("consultation")
        self.telecharger("reimport")

        self.assertEqual(
            get_user_model().objects.count(),
            nombre_agents,
        )

        self.assertEqual(ProfilAgent.objects.count(), 1)
        self.assertFalse(JournalAction.objects.exists())

    def test_erreur_validation(self):
        self.connecter()

        with patch(
            "planning.import_export_agents.exporter_agents_csv",
            side_effect=ValidationError("Export impossible."),
        ):
            reponse = self.telecharger("reimport")

        self.assertRedirects(
            reponse,
            self.url,
            fetch_redirect_response=False,
        )

        destination = self.client.get(
            self.url,
            secure=True,
        )

        self.assertEqual(destination.status_code, 200)
        self.assertContains(destination, "Export impossible.")

    def test_erreur_operationnelle(self):
        self.connecter()

        with patch(
            "planning.import_export_agents.exporter_agents_csv",
            side_effect=OperationalError("Conflit simule"),
        ):
            reponse = self.telecharger()

        self.assertEqual(reponse.status_code, 503)
        self.assertEqual(reponse["Retry-After"], "5")

        self.assertIn(
            "no-store",
            reponse["Cache-Control"],
        )

    def test_bouton_export_superutilisateur(self):
        self.connecter()

        reponse = self.client.get(
            reverse("liste_agents"),
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, self.url)
        self.assertContains(reponse, "Exporter les agents")


    def test_bouton_export_absent_administrateur(self):
        from django.contrib.auth.models import Permission

        permission = Permission.objects.get(
            content_type__app_label="auth",
            codename="view_user",
        )

        self.administrateur.user_permissions.add(permission)

        self.connecter(self.administrateur)

        reponse = self.client.get(
            reverse("liste_agents"),
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertNotContains(reponse, self.url)
        self.assertNotContains(reponse, "Exporter les agents")
