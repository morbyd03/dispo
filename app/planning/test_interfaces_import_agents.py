from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import (
    ProfilAgent,
    ImportAgentTemporaire,
    ConfirmationImport,
    JournalAction,
)


class InterfaceImportAgentsTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create(
            username="superadministrateur",
            is_superuser=True,
        )

        self.agent = User.objects.create(
            username="agent",
        )

        self.url = reverse("import_agents")
        self.url_confirmation = reverse(
            "confirmer_import_agents"
        )
        self.url_annulation = reverse(
            "annuler_import_agents"
        )

        self.contenu = (
            b"matricule;nom;prenom;grade;email\n"
            b"000123;Dupont;Jean;SAP1;jean@example.com\n"
        )

    def connecter(self, utilisateur=None):
        self.client.force_login(
            utilisateur or self.admin
        )

    def analyser(self, contenu=None):
        fichier = SimpleUploadedFile(
            "agents.csv",
            self.contenu if contenu is None else contenu,
            content_type="text/csv",
        )

        return self.client.post(
            self.url,
            {"fichier": fichier},
            secure=True,
        )

    def preparer(self):
        reponse = self.analyser()

        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.context["confirmable"])

        return ImportAgentTemporaire.objects.get(
            utilisateur=self.admin
        ).identifiant

    def confirmer(self, identifiant, **options):
        donnees = {
            "identifiant": identifiant,
            "confirmer_import": "on",
        }

        donnees.update(options)

        return self.client.post(
            self.url_confirmation,
            donnees,
            secure=True,
        )

    def test_page_import(self):
        self.connecter()

        reponse = self.client.get(
            self.url,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertTemplateUsed(
            reponse, "planning/import_agents.html"
        )
        self.assertContains(reponse, "Analyser le fichier")

    def test_acces_anonyme(self):
        reponse = self.client.get(
            self.url,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 302)

    def test_acces_agent_interdit(self):
        self.connecter(self.agent)

        reponse = self.client.get(
            self.url,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 403)

    def test_analyse_agent_interdite(self):
        self.connecter(self.agent)

        reponse = self.analyser()

        self.assertEqual(reponse.status_code, 403)
        self.assertFalse(
            ImportAgentTemporaire.objects.exists()
        )

    def test_previsualisation_valide(self):
        self.connecter()

        reponse = self.analyser()

        self.assertEqual(reponse.status_code, 200)

        self.assertTemplateUsed(
            reponse,
            "planning/previsualisation_import_agents.html",
        )

        self.assertTrue(reponse.context["confirmable"])
        self.assertEqual(
            reponse.context["bilan"]["creations"], 1
        )

        self.assertContains(reponse, "000123")
        self.assertContains(reponse, "jean@example.com")
        self.assertContains(reponse, self.url_confirmation)
        self.assertContains(reponse, self.url_annulation)

    def test_previsualisation_sans_ecriture_metier(self):
        self.connecter()

        self.preparer()

        self.assertFalse(ProfilAgent.objects.exists())
        self.assertFalse(JournalAction.objects.exists())
        self.assertFalse(ConfirmationImport.objects.exists())

        self.assertEqual(
            ImportAgentTemporaire.objects.count(), 1
        )

    def test_previsualisation_invalide(self):
        self.connecter()

        reponse = self.analyser(
            b"matricule;nom;prenom;grade;email\n"
            b"000123;Dupont;Jean;SAP1;\n"
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(reponse.context["confirmable"])

        self.assertContains(reponse, "Erreurs bloquantes")
        self.assertNotContains(
            reponse, self.url_confirmation
        )

        self.assertFalse(
            ImportAgentTemporaire.objects.exists()
        )

    def test_fichier_absent(self):
        self.connecter()

        reponse = self.client.post(
            self.url,
            {},
            secure=True,
        )

        self.assertEqual(reponse.status_code, 400)
        self.assertFalse(
            ImportAgentTemporaire.objects.exists()
        )

    def test_confirmation_valide(self):
        self.connecter()

        identifiant = self.preparer()
        reponse = self.confirmer(identifiant)

        self.assertRedirects(
            reponse,
            self.url,
            fetch_redirect_response=False,
        )

        profil = ProfilAgent.objects.get()

        self.assertEqual(
            profil.utilisateur.username, "000123"
        )
        self.assertEqual(
            profil.utilisateur.email, "jean@example.com"
        )
        self.assertFalse(
            profil.utilisateur.has_usable_password()
        )
        self.assertFalse(
            ImportAgentTemporaire.objects.exists()
        )
        self.assertEqual(
            ConfirmationImport.objects.count(), 1
        )

    def test_confirmation_sans_case_cochee(self):
        self.connecter()

        identifiant = self.preparer()

        reponse = self.confirmer(
            identifiant,
            confirmer_import="",
        )

        self.assertEqual(reponse.status_code, 302)
        self.assertFalse(ProfilAgent.objects.exists())

    def test_confirmation_non_rejouable(self):
        self.connecter()

        identifiant = self.preparer()

        self.confirmer(identifiant)
        self.confirmer(identifiant)

        self.assertEqual(ProfilAgent.objects.count(), 1)
        self.assertEqual(
            ConfirmationImport.objects.count(), 1
        )

    def test_annulation(self):
        self.connecter()

        identifiant = self.preparer()

        reponse = self.client.post(
            self.url_annulation,
            {"identifiant": identifiant},
            secure=True,
        )

        self.assertRedirects(
            reponse,
            self.url,
            fetch_redirect_response=False,
        )

        self.assertFalse(
            ImportAgentTemporaire.objects.exists()
        )
        self.assertFalse(ProfilAgent.objects.exists())

    def test_confirmation_apres_annulation(self):
        self.connecter()

        identifiant = self.preparer()

        self.client.post(
            self.url_annulation,
            {"identifiant": identifiant},
            secure=True,
        )

        self.confirmer(identifiant)

        self.assertFalse(ProfilAgent.objects.exists())

    def test_methodes_get_interdites(self):
        self.connecter()

        for url in (
            self.url_confirmation,
            self.url_annulation,
        ):
            with self.subTest(url=url):
                reponse = self.client.get(
                    url,
                    secure=True,
                )

                self.assertEqual(
                    reponse.status_code, 405
                )

    def test_absence_cache_previsualisation(self):
        self.connecter()

        reponse = self.analyser()

        self.assertIn(
            "no-store",
            reponse["Cache-Control"],
        )

    def test_confirmation_autre_superutilisateur(self):
        self.connecter()
        identifiant = self.preparer()

        autre = get_user_model().objects.create(
            username="autre_superadministrateur",
            is_superuser=True,
        )

        self.connecter(autre)
        self.confirmer(identifiant)

        self.assertFalse(ProfilAgent.objects.exists())
        self.assertTrue(
            ImportAgentTemporaire.objects.filter(
                utilisateur=self.admin,
                identifiant=identifiant,
            ).exists()
        )

    def test_annulation_autre_superutilisateur(self):
        self.connecter()
        identifiant = self.preparer()

        autre = get_user_model().objects.create(
            username="autre_superadministrateur",
            is_superuser=True,
        )

        self.connecter(autre)

        self.client.post(
            self.url_annulation,
            {"identifiant": identifiant},
            secure=True,
        )

        self.assertTrue(
            ImportAgentTemporaire.objects.filter(
                utilisateur=self.admin,
                identifiant=identifiant,
            ).exists()
        )

    def test_confirmation_agent_interdite(self):
        self.connecter()
        identifiant = self.preparer()

        self.connecter(self.agent)
        reponse = self.confirmer(identifiant)

        self.assertEqual(reponse.status_code, 403)
        self.assertFalse(ProfilAgent.objects.exists())

    def test_annulation_agent_interdite(self):
        self.connecter()
        identifiant = self.preparer()

        self.connecter(self.agent)

        reponse = self.client.post(
            self.url_annulation,
            {"identifiant": identifiant},
            secure=True,
        )

        self.assertEqual(reponse.status_code, 403)
        self.assertTrue(
            ImportAgentTemporaire.objects.exists()
        )

    def test_confirmation_expiree(self):
        from datetime import timedelta
        from django.utils import timezone

        self.connecter()
        identifiant = self.preparer()

        ImportAgentTemporaire.objects.update(
            expire_le=timezone.now() - timedelta(seconds=1)
        )

        self.confirmer(identifiant)

        self.assertFalse(ProfilAgent.objects.exists())
        self.assertFalse(ConfirmationImport.objects.exists())

    def test_confirmation_csrf_obligatoire(self):
        from django.test import Client

        self.connecter()
        identifiant = self.preparer()

        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)

        reponse = client.post(
            self.url_confirmation,
            {
                "identifiant": identifiant,
                "confirmer_import": "on",
            },
            secure=True,
        )

        self.assertEqual(reponse.status_code, 403)
        self.assertFalse(ProfilAgent.objects.exists())

    def test_annulation_csrf_obligatoire(self):
        from django.test import Client

        self.connecter()
        identifiant = self.preparer()

        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)

        reponse = client.post(
            self.url_annulation,
            {"identifiant": identifiant},
            secure=True,
        )

        self.assertEqual(reponse.status_code, 403)
        self.assertTrue(
            ImportAgentTemporaire.objects.exists()
        )

    def test_analyse_csrf_obligatoire(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)

        reponse = client.post(
            self.url,
            {
                "fichier": SimpleUploadedFile(
                    "agents.csv",
                    self.contenu,
                    content_type="text/csv",
                )
            },
            secure=True,
        )

        self.assertEqual(reponse.status_code, 403)
        self.assertFalse(
            ImportAgentTemporaire.objects.exists()
        )

    def test_affichage_bilan_definitif(self):
        self.connecter()
        identifiant = self.preparer()

        self.confirmer(identifiant)

        reponse = self.client.get(
            self.url,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertContains(
            reponse, "Import termine avec succes."
        )
        self.assertContains(reponse, "Creations : 1")
        self.assertContains(
            reponse, "qualifications uniquement : 0"
        )
