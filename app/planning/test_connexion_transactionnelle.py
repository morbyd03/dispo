from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db import connection, OperationalError
from django.test import TransactionTestCase
from django.urls import reverse

from .securite_sessions import CLE_VERSION_SESSION
from .services.securite import revoquer_acces_compte


class ConnexionTransactionnelleTests(TransactionTestCase):

    def setUp(self):
        self.mot_de_passe = "MotDePasseTest!4826"

        self.agent = get_user_model().objects.create_user(
            username="00123",
            password=self.mot_de_passe,
        )

        self.url = reverse("login")

    def connecter(self, mot_de_passe=None):
        return self.client.post(
            self.url,
            {
                "username": self.agent.username,
                "password": (
                    mot_de_passe or self.mot_de_passe
                ),
            },
            secure=True,
        )

    def test_authentification_dans_transaction(self):
        original = ModelBackend.authenticate
        observations = []

        def authentifier(backend, *args, **kwargs):
            observations.append(connection.in_atomic_block)

            return original(
                backend, *args, **kwargs
            )

        with patch.object(
            ModelBackend,
            "authenticate",
            authentifier,
        ):
            reponse = self.connecter()

        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(observations)
        self.assertTrue(all(observations))

        self.assertEqual(
            self.client.session["_auth_user_id"],
            str(self.agent.pk),
        )

    def test_version_securite_dans_transaction(self):
        from .services.securite import version_securite_compte

        observations = []

        def verifier(utilisateur_id):
            observations.append(connection.in_atomic_block)

            return version_securite_compte(utilisateur_id)

        with patch(
            "planning.securite_sessions.version_securite_compte",
            side_effect=verifier,
        ):
            reponse = self.connecter()

        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(observations)
        self.assertTrue(all(observations))

    def test_connexion_apres_revocation(self):
        revoquer_acces_compte(self.agent.pk)

        reponse = self.connecter()

        self.assertEqual(reponse.status_code, 302)

        self.assertEqual(
            self.client.session[CLE_VERSION_SESSION],
            1,
        )

    def test_mot_de_passe_incorrect(self):
        reponse = self.connecter("Incorrect")

        self.assertEqual(reponse.status_code, 200)

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_compte_inactif(self):
        self.agent.is_active = False
        self.agent.save(update_fields=["is_active"])

        reponse = self.connecter()

        self.assertEqual(reponse.status_code, 200)

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_conflit_transactionnel(self):
        with patch.object(
            ModelBackend,
            "authenticate",
            side_effect=OperationalError("Conflit simule"),
        ):
            reponse = self.connecter()

        self.assertEqual(reponse.status_code, 503)

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_consultation_formulaire(self):
        reponse = self.client.get(
            self.url,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
