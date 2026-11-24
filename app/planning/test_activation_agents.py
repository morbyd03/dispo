import re
from urllib.parse import urlsplit

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from planning.activation_agents import (
    envoyer_activation_agent,
    envoyer_reinitialisation_agent,
)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver"],
    SECURE_SSL_REDIRECT=False,
)
class ActivationAgentsTests(TestCase):

    def setUp(self):
        self.ancien_mot_de_passe = "Ancien-Test!4826"
        self.nouveau_mot_de_passe = "Nouveau-Test!7392"

        self.agent = get_user_model().objects.create_user(
            username="agent_test",
            first_name="Jean",
            last_name="Test",
            email="agent@example.com",
            password=self.ancien_mot_de_passe,
        )

        self.request = RequestFactory().get("/")

    def verifier_email(self):
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertEqual(message.to, [self.agent.email])
        self.assertIn(
            "identifiant de connexion : agent_test",
            message.body,
        )

    def demander_reinitialisation(self):
        reponse = self.client.post(
            reverse("password_reset"),
            {"email": self.agent.email},
        )
        self.assertEqual(reponse.status_code, 302)

    def definir_mot_de_passe(self):
        liens = re.findall(
            r"https?://[^\s]+",
            mail.outbox[0].body,
        )
        self.assertEqual(len(liens), 1)

        chemin = urlsplit(liens[0]).path

        reponse = self.client.get(chemin, follow=True)
        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.context["validlink"])

        destination = reponse.request["PATH_INFO"]

        reponse = self.client.post(
            destination,
            {
                "new_password1": self.nouveau_mot_de_passe,
                "new_password2": self.nouveau_mot_de_passe,
            },
            follow=True,
        )

        self.assertEqual(reponse.status_code, 200)

        self.agent.refresh_from_db()

        self.assertTrue(
            self.agent.check_password(
                self.nouveau_mot_de_passe
            )
        )

        reponse = self.client.get(chemin, follow=True)
        self.assertFalse(reponse.context["validlink"])

    def verifier_connexion(self):
        self.client.logout()

        reponse = self.client.post(
            reverse("login"),
            {
                "username": self.agent.username,
                "password": self.nouveau_mot_de_passe,
            },
        )

        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(
            self.client.session.get("_auth_user_id"),
            str(self.agent.pk),
        )

    def test_email_activation(self):
        envoyer_activation_agent(self.request, self.agent)
        self.verifier_email()

    def test_email_reinitialisation_administrateur(self):
        envoyer_reinitialisation_agent(
            self.request,
            self.agent,
        )
        self.verifier_email()

    def test_email_mot_de_passe_oublie(self):
        self.demander_reinitialisation()
        self.verifier_email()

    def test_parcours_activation(self):
        self.agent.set_unusable_password()
        self.agent.save(update_fields=["password"])

        envoyer_activation_agent(self.request, self.agent)

        self.definir_mot_de_passe()
        self.verifier_connexion()

    def test_parcours_reinitialisation(self):
        self.demander_reinitialisation()
        self.definir_mot_de_passe()

        self.assertFalse(
            self.agent.check_password(
                self.ancien_mot_de_passe
            )
        )

        self.verifier_connexion()
