from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from .models import Grade
from .services.agents import (
    creer_agent,
    modifier_statut_agent,
)
from .services.securite import revoquer_acces_compte
from .securite_sessions import CLE_VERSION_SESSION


class SecuriteSessionsTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(
            username="admin",
            is_superuser=True,
            is_staff=True,
        )

        cls.profil = creer_agent(
            auteur_id=cls.admin.pk,
            matricule="00123",
            nom="Dupont",
            prenom="Jean",
            email="jean@example.com",
            grade_id=Grade.objects.get(code="SAP1").pk,
        )

        cls.agent = cls.profil.utilisateur

        cls.mot_de_passe = "MotDePasseTest!4826"

        cls.agent.set_password(cls.mot_de_passe)
        cls.agent.save(update_fields=["password"])

    def setUp(self):
        self.client.force_login(self.agent)
        self.url = reverse("mon_profil")

    def consulter(self, client=None):
        return (client or self.client).get(
            self.url,
            secure=True,
        )

    def modifier_statut(self, actif):
        return modifier_statut_agent(
            auteur_id=self.admin.pk,
            profil_id=self.profil.pk,
            actif=actif,
        )

    def test_version_enregistree_a_la_connexion(self):
        self.assertEqual(
            self.client.session[CLE_VERSION_SESSION],
            0,
        )

        self.assertEqual(self.consulter().status_code, 200)

    def test_revocation_session(self):
        revoquer_acces_compte(self.agent.pk)

        self.assertEqual(self.consulter().status_code, 302)

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_desactivation_session(self):
        self.modifier_statut(False)

        self.assertEqual(self.consulter().status_code, 302)

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_session_ne_revient_pas_apres_reactivation(self):
        self.modifier_statut(False)
        self.modifier_statut(True)

        self.assertEqual(self.consulter().status_code, 302)

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_nouvelle_connexion_apres_reactivation(self):
        self.modifier_statut(False)
        self.modifier_statut(True)

        self.consulter()

        self.assertTrue(
            self.client.login(
                username=self.agent.username,
                password=self.mot_de_passe,
            )
        )

        self.assertEqual(
            self.client.session[CLE_VERSION_SESSION],
            2,
        )

        self.assertEqual(self.consulter().status_code, 200)

    def test_connexion_compte_desactive_refusee(self):
        self.modifier_statut(False)

        self.client.logout()

        self.assertFalse(
            self.client.login(
                username=self.agent.username,
                password=self.mot_de_passe,
            )
        )

    def test_revocation_plusieurs_sessions(self):
        autre_client = Client()
        autre_client.force_login(self.agent)

        revoquer_acces_compte(self.agent.pk)

        self.assertEqual(self.consulter().status_code, 302)

        self.assertEqual(
            self.consulter(autre_client).status_code,
            302,
        )

    def test_autre_compte_non_affecte(self):
        autre_client = Client()
        autre_client.force_login(self.admin)

        revoquer_acces_compte(self.agent.pk)

        self.assertEqual(self.consulter().status_code, 302)

        self.assertEqual(
            self.consulter(autre_client).status_code,
            200,
        )

    def test_ancienne_session_sans_version(self):
        session = self.client.session
        session.pop(CLE_VERSION_SESSION)
        session.save()

        self.assertEqual(self.consulter().status_code, 302)

    def test_version_session_invalide(self):
        session = self.client.session
        session[CLE_VERSION_SESSION] = "0"
        session.save()

        self.assertEqual(self.consulter().status_code, 302)

    def test_statut_inchange_preserve_session(self):
        self.modifier_statut(True)

        self.assertEqual(self.consulter().status_code, 200)

    def test_revocation_compte_technique(self):
        self.client.force_login(self.admin)

        self.assertEqual(self.consulter().status_code, 200)

        revoquer_acces_compte(self.admin.pk)

        self.assertEqual(self.consulter().status_code, 302)

    def test_visiteur_anonyme(self):
        self.client.logout()

        self.assertEqual(self.consulter().status_code, 302)
