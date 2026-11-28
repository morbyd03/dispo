from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import Grade
from .services.agents import (
    creer_agent,
    modifier_statut_agent,
)
from .services.securite import revoquer_acces_compte
from .securite_jetons import generateur_jetons_compte


class RevocationLiensTests(TestCase):

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

        cls.ancien_mot_de_passe = "AncienTest!4826"
        cls.nouveau_mot_de_passe = "NouveauTest!7392"

        cls.agent.set_password(cls.ancien_mot_de_passe)
        cls.agent.save(update_fields=["password"])

    def lien(self):
        self.agent.refresh_from_db()

        return reverse(
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

    def modifier_statut(self, actif):
        modifier_statut_agent(
            auteur_id=self.admin.pk,
            profil_id=self.profil.pk,
            actif=actif,
        )

    def ouvrir_formulaire(self, lien=None, client=None):
        client = client or self.client

        reponse = client.get(
            lien or self.lien(),
            secure=True,
            follow=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.context["validlink"])

        return reponse.request["PATH_INFO"]

    def soumettre(self, chemin, client=None):
        client = client or self.client

        return client.post(
            chemin,
            {
                "new_password1": self.nouveau_mot_de_passe,
                "new_password2": self.nouveau_mot_de_passe,
            },
            secure=True,
            follow=True,
        )

    def verifier_mot_de_passe_inchange(self):
        self.agent.refresh_from_db()

        self.assertTrue(
            self.agent.check_password(
                self.ancien_mot_de_passe
            )
        )

        self.assertFalse(
            self.agent.check_password(
                self.nouveau_mot_de_passe
            )
        )

    def test_desactivation_avant_ouverture(self):
        lien = self.lien()

        self.modifier_statut(False)

        reponse = self.client.get(
            lien,
            secure=True,
            follow=True,
        )

        self.assertFalse(reponse.context["validlink"])

    def test_reactivation_ancien_lien_invalide(self):
        lien = self.lien()

        self.modifier_statut(False)
        self.modifier_statut(True)

        reponse = self.client.get(
            lien,
            secure=True,
            follow=True,
        )

        self.assertFalse(reponse.context["validlink"])

    def test_desactivation_formulaire_deja_ouvert(self):
        chemin = self.ouvrir_formulaire()

        self.modifier_statut(False)

        reponse = self.soumettre(chemin)

        self.assertFalse(reponse.context["validlink"])
        self.verifier_mot_de_passe_inchange()

    def test_reactivation_formulaire_deja_ouvert(self):
        chemin = self.ouvrir_formulaire()

        self.modifier_statut(False)
        self.modifier_statut(True)

        reponse = self.soumettre(chemin)

        self.assertFalse(reponse.context["validlink"])
        self.verifier_mot_de_passe_inchange()

    def test_revocation_explicite_formulaire_ouvert(self):
        chemin = self.ouvrir_formulaire()

        revoquer_acces_compte(self.agent.pk)

        reponse = self.soumettre(chemin)

        self.assertFalse(reponse.context["validlink"])
        self.verifier_mot_de_passe_inchange()

    def test_revocation_plusieurs_formulaires(self):
        lien = self.lien()

        autre_client = Client()

        chemin1 = self.ouvrir_formulaire(lien)

        chemin2 = self.ouvrir_formulaire(
            lien,
            autre_client,
        )

        revoquer_acces_compte(self.agent.pk)

        self.assertFalse(
            self.soumettre(chemin1).context["validlink"]
        )

        self.assertFalse(
            self.soumettre(
                chemin2,
                autre_client,
            ).context["validlink"]
        )

        self.verifier_mot_de_passe_inchange()

    def test_activation_interrompue(self):
        self.agent.set_unusable_password()
        self.agent.save(update_fields=["password"])

        chemin = self.ouvrir_formulaire()

        self.modifier_statut(False)
        self.modifier_statut(True)

        reponse = self.soumettre(chemin)

        self.assertFalse(reponse.context["validlink"])

        self.agent.refresh_from_db()

        self.assertFalse(
            self.agent.has_usable_password()
        )

    def test_nouveau_lien_apres_reactivation(self):
        self.modifier_statut(False)
        self.modifier_statut(True)

        chemin = self.ouvrir_formulaire()

        reponse = self.soumettre(chemin)

        self.assertEqual(reponse.status_code, 200)

        self.agent.refresh_from_db()

        self.assertTrue(
            self.agent.check_password(
                self.nouveau_mot_de_passe
            )
        )

    def test_changement_mot_de_passe_revoque_session(self):
        autre_client = Client()
        autre_client.force_login(self.agent)

        chemin = self.ouvrir_formulaire()

        self.soumettre(chemin)

        reponse = autre_client.get(
            reverse("mon_profil"),
            secure=True,
        )

        self.assertEqual(reponse.status_code, 302)

        self.assertNotIn(
            "_auth_user_id",
            autre_client.session,
        )
