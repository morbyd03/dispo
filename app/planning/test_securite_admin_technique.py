from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.views import LoginView
from django.db import connection, OperationalError
from django.test import TransactionTestCase
from django.urls import reverse

from .securite_sessions import CLE_VERSION_SESSION
from .services.securite import revoquer_acces_compte


class SecuriteAdminTechniqueTests(TransactionTestCase):

    def setUp(self):
        User = get_user_model()

        self.mot_de_passe = "MotDePasseTest!4826"

        self.admin = User.objects.create_user(
            username="admin_technique",
            password=self.mot_de_passe,
            is_staff=True,
            is_superuser=True,
        )

        self.agent = User.objects.create_user(
            username="00123",
            password=self.mot_de_passe,
        )

    def connecter(self, utilisateur=None, technique=True):
        utilisateur = utilisateur or self.admin

        return self.client.post(
            reverse("admin:login" if technique else "login"),
            {
                "username": utilisateur.username,
                "password": self.mot_de_passe,
            },
            secure=True,
        )

    def test_connexion_technique_valide(self):
        reponse = self.connecter()

        self.assertEqual(reponse.status_code, 302)

        self.assertEqual(
            self.client.session["_auth_user_id"],
            str(self.admin.pk),
        )

        self.assertEqual(
            self.client.session[CLE_VERSION_SESSION],
            0,
        )

    def test_agent_refuse(self):
        reponse = self.connecter(self.agent)

        self.assertEqual(reponse.status_code, 200)
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_authentification_technique_transactionnelle(self):
        original = ModelBackend.authenticate
        observations = []

        def authentifier(backend, *args, **kwargs):
            observations.append(connection.in_atomic_block)

            return original(backend, *args, **kwargs)

        with patch.object(
            ModelBackend,
            "authenticate",
            authentifier,
        ):
            reponse = self.connecter()

        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(observations)
        self.assertTrue(all(observations))

    def test_revocation_session_technique(self):
        self.connecter()

        revoquer_acces_compte(self.admin.pk)

        reponse = self.client.get(
            reverse("admin:index"),
            secure=True,
        )

        self.assertEqual(reponse.status_code, 302)

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def verifier_echec_apres_connexion(self, technique):
        original = LoginView.form_valid

        def connecter_puis_echouer(vue, formulaire):
            original(vue, formulaire)

            self.assertIn(
                "_auth_user_id",
                vue.request.session,
            )

            raise OperationalError(
                "Conflit apres authentification"
            )

        with patch.object(
            LoginView,
            "form_valid",
            connecter_puis_echouer,
        ):
            reponse = self.connecter(
                technique=technique,
            )

        self.assertEqual(reponse.status_code, 503)

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

        self.assertNotIn(
            CLE_VERSION_SESSION,
            self.client.session,
        )

        self.admin.refresh_from_db()
        self.assertIsNone(self.admin.last_login)

    def test_echec_apres_connexion_technique(self):
        self.verifier_echec_apres_connexion(True)

    def test_echec_apres_connexion_fonctionnelle(self):
        with self.assertLogs(
            "planning.securite_vues",
            level="ERROR",
        ):
            self.verifier_echec_apres_connexion(False)
