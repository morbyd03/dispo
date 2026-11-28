from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection, OperationalError
from django.test import TransactionTestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .securite_jetons import generateur_jetons_compte


class ReinitialisationTransactionnelleTests(TransactionTestCase):

    def setUp(self):
        self.ancien = "AncienTest!4826"
        self.nouveau = "NouveauTest!7392"

        self.agent = get_user_model().objects.create_user(
            username="00123",
            email="agent@example.com",
            password=self.ancien,
        )

        self.lien = reverse(
            "password_reset_confirm",
            kwargs={
                "uidb64": urlsafe_base64_encode(
                    force_bytes(self.agent.pk)
                ),
                "token": generateur_jetons_compte.make_token(
                    self.agent
                ),
            },
        )

        reponse = self.client.get(
            self.lien,
            secure=True,
            follow=True,
        )

        self.assertTrue(reponse.context["validlink"])

        self.destination = reponse.request["PATH_INFO"]

    def soumettre(self):
        return self.client.post(
            self.destination,
            {
                "new_password1": self.nouveau,
                "new_password2": self.nouveau,
            },
            secure=True,
        )

    def test_verification_jeton_dans_transaction(self):
        original = generateur_jetons_compte.check_token
        observations = []

        def verifier(*args, **kwargs):
            observations.append(connection.in_atomic_block)
            return original(*args, **kwargs)

        with patch.object(
            generateur_jetons_compte,
            "check_token",
            side_effect=verifier,
        ):
            reponse = self.soumettre()

        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(observations)
        self.assertTrue(all(observations))

        self.agent.refresh_from_db()

        self.assertTrue(
            self.agent.check_password(self.nouveau)
        )

    def test_annulation_si_erreur_apres_enregistrement(self):
        from django.contrib.auth.forms import SetPasswordForm

        original = SetPasswordForm.save

        def enregistrer_puis_echouer(formulaire, *args, **kwargs):
            original(formulaire, *args, **kwargs)
            raise OperationalError("Conflit simule")

        with patch.object(
            SetPasswordForm,
            "save",
            enregistrer_puis_echouer,
        ):
            reponse = self.soumettre()

        self.assertEqual(reponse.status_code, 503)

        self.agent.refresh_from_db()

        self.assertTrue(
            self.agent.check_password(self.ancien)
        )

        self.assertFalse(
            self.agent.check_password(self.nouveau)
        )

    def test_conflit_verification_jeton(self):
        with patch.object(
            generateur_jetons_compte,
            "check_token",
            side_effect=OperationalError("Conflit simule"),
        ):
            reponse = self.soumettre()

        self.assertEqual(reponse.status_code, 503)

        self.agent.refresh_from_db()

        self.assertTrue(
            self.agent.check_password(self.ancien)
        )
