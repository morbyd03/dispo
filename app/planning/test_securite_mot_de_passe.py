from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import PasswordChangeView
from django.db import connection, OperationalError
from django.test import Client, TransactionTestCase
from django.urls import reverse

from .securite_sessions import CLE_VERSION_SESSION
from .securite_jetons import generateur_jetons_compte


class SecuriteMotDePasseTests(TransactionTestCase):

    def setUp(self):
        self.ancien = "AncienTest!4826"
        self.nouveau = "NouveauTest!7392"

        self.agent = get_user_model().objects.create_user(
            username="00123",
            email="agent@example.com",
            password=self.ancien,
        )

        self.client.force_login(self.agent)

        self.url = reverse("changer_mot_de_passe")
        self.profil = reverse("mon_profil")

    def soumettre(self, ancien=None):
        return self.client.post(
            self.url,
            {
                "old_password": ancien or self.ancien,
                "new_password1": self.nouveau,
                "new_password2": self.nouveau,
            },
            secure=True,
        )

    def verifier_ancien_mot_de_passe(self):
        self.agent.refresh_from_db()

        self.assertTrue(
            self.agent.check_password(self.ancien)
        )

        self.assertFalse(
            self.agent.check_password(self.nouveau)
        )

    def test_changement_mot_de_passe(self):
        reponse = self.soumettre()

        self.assertEqual(reponse.status_code, 302)

        self.agent.refresh_from_db()

        self.assertTrue(
            self.agent.check_password(self.nouveau)
        )

        self.assertFalse(
            self.agent.check_password(self.ancien)
        )

    def test_session_courante_conservee(self):
        self.soumettre()

        self.assertEqual(
            self.client.session["_auth_user_id"],
            str(self.agent.pk),
        )

        self.assertEqual(
            self.client.session[CLE_VERSION_SESSION],
            0,
        )

        self.assertEqual(
            self.client.get(
                self.profil,
                secure=True,
            ).status_code,
            200,
        )

    def test_autres_sessions_revoquees(self):
        autre_client = Client()
        autre_client.force_login(self.agent)

        self.soumettre()

        reponse = autre_client.get(
            self.profil,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 302)

        self.assertNotIn(
            "_auth_user_id",
            autre_client.session,
        )

    def test_ancien_jeton_invalide(self):
        self.agent.refresh_from_db()

        jeton = generateur_jetons_compte.make_token(
            self.agent
        )

        self.assertTrue(
            generateur_jetons_compte.check_token(
                self.agent, jeton
            )
        )

        self.soumettre()

        self.agent.refresh_from_db()

        self.assertFalse(
            generateur_jetons_compte.check_token(
                self.agent, jeton
            )
        )

    def test_ancien_mot_de_passe_incorrect(self):
        reponse = self.soumettre("Incorrect")

        self.assertEqual(reponse.status_code, 200)

        self.verifier_ancien_mot_de_passe()

        self.assertIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_visiteur_anonyme_refuse(self):
        self.client.logout()

        reponse = self.soumettre()

        self.assertEqual(reponse.status_code, 302)

        self.verifier_ancien_mot_de_passe()

    def test_enregistrement_transactionnel(self):
        original = PasswordChangeForm.save
        observations = []

        def enregistrer(formulaire, *args, **kwargs):
            observations.append(connection.in_atomic_block)

            return original(
                formulaire, *args, **kwargs
            )

        with patch.object(
            PasswordChangeForm,
            "save",
            enregistrer,
        ):
            reponse = self.soumettre()

        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(observations)
        self.assertTrue(all(observations))

    def test_annulation_apres_enregistrement(self):
        original = PasswordChangeForm.save

        def enregistrer_puis_echouer(
            formulaire, *args, **kwargs
        ):
            original(formulaire, *args, **kwargs)

            raise OperationalError("Conflit simule")

        with self.assertLogs(
            "planning.securite_vues",
            level="ERROR",
        ):
            with patch.object(
                PasswordChangeForm,
                "save",
                enregistrer_puis_echouer,
            ):
                reponse = self.soumettre()

        self.assertEqual(reponse.status_code, 503)

        self.verifier_ancien_mot_de_passe()

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_annulation_apres_actualisation_session(self):
        original = PasswordChangeView.form_valid

        def modifier_puis_echouer(vue, formulaire):
            original(vue, formulaire)

            raise OperationalError(
                "Conflit apres actualisation session"
            )

        with self.assertLogs(
            "planning.securite_vues",
            level="ERROR",
        ):
            with patch.object(
                PasswordChangeView,
                "form_valid",
                modifier_puis_echouer,
            ):
                reponse = self.soumettre()

        self.assertEqual(reponse.status_code, 503)

        self.verifier_ancien_mot_de_passe()

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

        self.assertNotIn(
            CLE_VERSION_SESSION,
            self.client.session,
        )

    def simuler_changement_apres_middleware(self, operation):
        from .securite_vues import ChangementMotDePasseSecurise

        original = ChangementMotDePasseSecurise.dispatch

        def modifier_puis_traiter(
            vue, request, *args, **kwargs
        ):
            operation()

            return original(
                vue, request, *args, **kwargs
            )

        with patch.object(
            ChangementMotDePasseSecurise,
            "dispatch",
            modifier_puis_traiter,
        ):
            return self.soumettre()

    def verifier_session_refusee(self, reponse):
        self.assertEqual(reponse.status_code, 302)

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

        self.assertNotIn(
            CLE_VERSION_SESSION,
            self.client.session,
        )

    def test_revocation_apres_middleware(self):
        from .services.securite import revoquer_acces_compte

        reponse = self.simuler_changement_apres_middleware(
            lambda: revoquer_acces_compte(self.agent.pk)
        )

        self.verifier_session_refusee(reponse)
        self.verifier_ancien_mot_de_passe()

    def test_desactivation_apres_middleware(self):
        def desactiver():
            get_user_model().objects.filter(
                pk=self.agent.pk,
            ).update(is_active=False)

        reponse = self.simuler_changement_apres_middleware(
            desactiver
        )

        self.verifier_session_refusee(reponse)
        self.verifier_ancien_mot_de_passe()

    def test_mot_de_passe_modifie_apres_middleware(self):
        autre_mot_de_passe = "AutreTest!9537"

        def modifier():
            utilisateur = get_user_model().objects.get(
                pk=self.agent.pk
            )

            utilisateur.set_password(autre_mot_de_passe)
            utilisateur.save(update_fields=["password"])

        reponse = self.simuler_changement_apres_middleware(
            modifier
        )

        self.verifier_session_refusee(reponse)

        self.agent.refresh_from_db()

        self.assertTrue(
            self.agent.check_password(
                autre_mot_de_passe
            )
        )

        self.assertFalse(
            self.agent.check_password(self.nouveau)
        )

    def test_desactivation_reactivation_apres_middleware(self):
        from .services.securite import revoquer_acces_compte

        def modifier():
            utilisateurs = get_user_model().objects.filter(
                pk=self.agent.pk
            )

            utilisateurs.update(is_active=False)
            revoquer_acces_compte(self.agent.pk)

            utilisateurs.update(is_active=True)
            revoquer_acces_compte(self.agent.pk)

        reponse = self.simuler_changement_apres_middleware(
            modifier
        )

        self.verifier_session_refusee(reponse)
        self.verifier_ancien_mot_de_passe()
