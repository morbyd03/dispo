from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase

from .models import Grade
from .services.agents import (
    creer_agent,
    modifier_statut_agent,
)
from .services.securite import revoquer_acces_compte
from .securite_jetons import generateur_jetons_compte


class SecuriteJetonsTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(
            username="admin",
            is_superuser=True,
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

    def jeton(self):
        self.agent.refresh_from_db()

        return generateur_jetons_compte.make_token(
            self.agent
        )

    def verifier(self, jeton):
        self.agent.refresh_from_db()

        return generateur_jetons_compte.check_token(
            self.agent,
            jeton,
        )

    def modifier_statut(self, actif):
        modifier_statut_agent(
            auteur_id=self.admin.pk,
            profil_id=self.profil.pk,
            actif=actif,
        )

    def test_jeton_activation_valide(self):
        self.assertFalse(
            self.agent.has_usable_password()
        )

        self.assertTrue(self.verifier(self.jeton()))

    def test_jeton_reinitialisation_valide(self):
        self.agent.set_password("MotDePasseTest!4826")
        self.agent.save(update_fields=["password"])

        self.assertTrue(self.verifier(self.jeton()))

    def test_revocation_explicite(self):
        jeton = self.jeton()

        revoquer_acces_compte(self.agent.pk)

        self.assertFalse(self.verifier(jeton))

    def test_desactivation(self):
        jeton = self.jeton()

        self.modifier_statut(False)

        self.assertFalse(self.verifier(jeton))

    def test_jeton_invalide_pendant_desactivation(self):
        self.modifier_statut(False)

        self.assertFalse(
            self.verifier(self.jeton())
        )

    def test_ancien_jeton_ne_revient_pas(self):
        jeton = self.jeton()

        self.modifier_statut(False)
        self.modifier_statut(True)

        self.assertFalse(self.verifier(jeton))

    def test_nouveau_jeton_apres_reactivation(self):
        self.modifier_statut(False)
        self.modifier_statut(True)

        self.assertTrue(
            self.verifier(self.jeton())
        )

    def test_changement_mot_de_passe(self):
        jeton = self.jeton()

        self.agent.set_password("NouveauTest!7392")
        self.agent.save(update_fields=["password"])

        self.assertFalse(self.verifier(jeton))

    def test_changement_email(self):
        jeton = self.jeton()

        self.agent.email = "autre@example.com"
        self.agent.save(update_fields=["email"])

        self.assertFalse(self.verifier(jeton))

    def test_jeton_altere(self):
        self.assertFalse(
            self.verifier(self.jeton() + "x")
        )

    def test_jeton_expire(self):
        jeton = self.jeton()

        with self.settings(PASSWORD_RESET_TIMEOUT=-1):
            self.assertFalse(self.verifier(jeton))

    def test_ancien_generateur_refuse(self):
        jeton = default_token_generator.make_token(
            self.agent
        )

        self.assertFalse(self.verifier(jeton))

    def test_compte_technique_sans_profil(self):
        jeton = generateur_jetons_compte.make_token(
            self.admin
        )

        self.assertTrue(
            generateur_jetons_compte.check_token(
                self.admin, jeton
            )
        )

        revoquer_acces_compte(self.admin.pk)

        self.assertFalse(
            generateur_jetons_compte.check_token(
                self.admin, jeton
            )
        )

    def test_statut_inchange_preserve_jeton(self):
        jeton = self.jeton()

        self.modifier_statut(True)

        self.assertTrue(self.verifier(jeton))
