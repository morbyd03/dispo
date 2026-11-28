from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, Client
from django.urls import reverse

from .models import (
    Grade,
    ProfilAgent,
    Competence,
    CompetenceAgent,
    JournalAction,
)
from .services.competences import empreinte_qualifications


class InterfacesQualificationsTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="admin",
            is_superuser=True,
            is_staff=True,
        )

        self.agent = User.objects.create_user(
            username="00123",
            first_name="Jean",
            last_name="Dupont",
        )

        self.validateur = User.objects.create_user(
            username="validateur",
        )

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.agent,
            grade=Grade.objects.get(code="SAP1"),
        )

        self.competence = Competence.objects.get(
            code="cod1",
        )

        self.pk = self.competence.pk

        self.url = reverse(
            "qualifications_agent",
            args=[self.profil.pk],
        )

        self.client.force_login(self.admin)

    def autoriser(self, codename):
        self.validateur.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="planning",
                codename=codename,
            )
        )

    def attribuer(self):
        return CompetenceAgent.objects.create(
            profil=self.profil,
            competence=self.competence,
            valide_par=self.admin,
            date_validation=date(2027, 1, 1),
            date_expiration=date(2027, 12, 31),
        )

    def soumettre(self, donnees=None, empreinte=None):
        contenu = {
            "empreinte": (
                empreinte
                if empreinte is not None
                else empreinte_qualifications(self.profil)
            ),
        }

        contenu.update(donnees or {})

        return self.client.post(
            self.url,
            contenu,
            secure=True,
        )

    def test_affichage(self):
        reponse = self.client.get(
            self.url,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Jean Dupont")
        self.assertContains(reponse, self.competence.nom)
        self.assertContains(
            reponse,
            empreinte_qualifications(self.profil),
        )

    def test_lien_depuis_liste_agents(self):
        reponse = self.client.get(
            reverse("liste_agents"),
            secure=True,
        )

        self.assertContains(reponse, self.url)

    def test_attribution(self):
        reponse = self.soumettre({
            f"competence_{self.pk}": "on",
            f"date_validation_{self.pk}": "2027-01-01",
        })

        self.assertEqual(reponse.status_code, 302)

        attribution = CompetenceAgent.objects.get(
            profil=self.profil,
            competence=self.competence,
        )

        self.assertEqual(attribution.valide_par, self.admin)
        self.assertEqual(
            attribution.date_validation,
            date(2027, 1, 1),
        )

        self.assertTrue(
            JournalAction.objects.filter(
                action="competence.attribuer",
            ).exists()
        )

    def test_modification_dates(self):
        attribution = self.attribuer()

        reponse = self.soumettre({
            f"competence_{self.pk}": "on",
            f"date_validation_{self.pk}": "2027-01-01",
            f"date_expiration_{self.pk}": "2028-12-31",
        })

        self.assertEqual(reponse.status_code, 302)

        attribution.refresh_from_db()

        self.assertEqual(
            attribution.date_expiration,
            date(2028, 12, 31),
        )

    def test_retrait(self):
        attribution = self.attribuer()

        reponse = self.soumettre()

        self.assertEqual(reponse.status_code, 302)

        self.assertFalse(
            CompetenceAgent.objects.filter(
                pk=attribution.pk,
            ).exists()
        )

        self.assertTrue(
            JournalAction.objects.filter(
                action="competence.retirer",
            ).exists()
        )

    def test_dates_invalides(self):
        reponse = self.soumettre({
            f"competence_{self.pk}": "on",
            f"date_validation_{self.pk}": "2027-12-31",
            f"date_expiration_{self.pk}": "2027-01-01",
        })

        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.context["formulaire"].errors)
        self.assertFalse(CompetenceAgent.objects.exists())

    def test_competence_inactive_preservee(self):
        attribution = self.attribuer()

        self.competence.active = False
        self.competence.save(update_fields=["active"])

        reponse = self.soumettre()

        self.assertEqual(reponse.status_code, 302)

        self.assertTrue(
            CompetenceAgent.objects.filter(
                pk=attribution.pk,
            ).exists()
        )

    def test_agent_ordinaire_refuse(self):
        self.client.force_login(self.agent)

        self.assertEqual(
            self.client.get(
                self.url, secure=True
            ).status_code,
            403,
        )

        self.assertEqual(
            self.soumettre().status_code,
            403,
        )

    def test_validateur_delegue_autorise(self):
        self.autoriser("add_competenceagent")
        self.client.force_login(self.validateur)

        reponse = self.soumettre({
            f"competence_{self.pk}": "on",
        })

        self.assertEqual(reponse.status_code, 302)

        attribution = CompetenceAgent.objects.get(
            profil=self.profil,
        )

        self.assertEqual(
            attribution.valide_par,
            self.validateur,
        )

    def test_retrait_non_autorise(self):
        attribution = self.attribuer()

        self.autoriser("add_competenceagent")
        self.client.force_login(self.validateur)

        reponse = self.soumettre()

        self.assertEqual(reponse.status_code, 302)

        self.assertTrue(
            CompetenceAgent.objects.filter(
                pk=attribution.pk,
            ).exists()
        )

    def test_auto_attribution_refusee(self):
        self.agent.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="planning",
                codename="add_competenceagent",
            )
        )

        self.client.force_login(self.agent)

        self.assertEqual(
            self.soumettre({
                f"competence_{self.pk}": "on",
            }).status_code,
            403,
        )

    def test_formulaire_obsolete_refuse(self):
        empreinte = empreinte_qualifications(self.profil)

        attribution = self.attribuer()

        reponse = self.soumettre(
            empreinte=empreinte,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.context["formulaire"].errors)

        self.assertTrue(
            CompetenceAgent.objects.filter(
                pk=attribution.pk,
            ).exists()
        )

    def test_empreinte_absente_refusee(self):
        reponse = self.client.post(
            self.url,
            {f"competence_{self.pk}": "on"},
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.context["formulaire"].errors)
        self.assertFalse(CompetenceAgent.objects.exists())

    def test_protection_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)

        reponse = client.post(
            self.url,
            {
                "empreinte": empreinte_qualifications(
                    self.profil
                ),
                f"competence_{self.pk}": "on",
            },
            secure=True,
        )

        self.assertEqual(reponse.status_code, 403)
        self.assertFalse(CompetenceAgent.objects.exists())

    def test_liste_accessible_au_validateur_delegue(self):
        self.autoriser("add_competenceagent")
        self.client.force_login(self.validateur)

        reponse = self.client.get(
            reverse("liste_agents"),
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, self.url)
        self.assertContains(reponse, "Gestion des qualifications")

        self.assertFalse(
            reponse.context["acces_administratif"]
        )

    def test_validateur_sans_lien_modification(self):
        self.autoriser("change_competenceagent")
        self.client.force_login(self.validateur)

        reponse = self.client.get(
            reverse("liste_agents"),
            secure=True,
        )

        self.assertNotContains(
            reponse,
            reverse("modifier_agent", args=[self.profil.pk]),
        )

    def test_validateur_sans_lien_creation(self):
        self.autoriser("add_competenceagent")
        self.client.force_login(self.validateur)

        reponse = self.client.get(
            reverse("liste_agents"),
            secure=True,
        )

        self.assertNotContains(
            reponse,
            reverse("ajouter_agent"),
        )

    def test_validateur_ne_peut_pas_modifier_profil(self):
        self.autoriser("change_competenceagent")
        self.client.force_login(self.validateur)

        url = reverse(
            "modifier_agent",
            args=[self.profil.pk],
        )

        self.assertEqual(
            self.client.get(url, secure=True).status_code,
            403,
        )

        self.assertEqual(
            self.client.post(url, {}, secure=True).status_code,
            403,
        )

    def test_validateur_ne_peut_pas_creer_agent(self):
        self.autoriser("add_competenceagent")
        self.client.force_login(self.validateur)

        url = reverse("ajouter_agent")

        self.assertEqual(
            self.client.get(url, secure=True).status_code,
            403,
        )

        self.assertEqual(
            self.client.post(url, {}, secure=True).status_code,
            403,
        )

    def test_validateur_ne_peut_pas_reinitialiser_compte(self):
        self.autoriser("change_competenceagent")
        self.client.force_login(self.validateur)

        reponse = self.client.post(
            reverse(
                "reinitialiser_agent",
                args=[self.profil.pk],
            ),
            secure=True,
        )

        self.assertEqual(reponse.status_code, 403)

    def test_agent_ordinaire_sans_acces_liste(self):
        self.client.force_login(self.agent)

        reponse = self.client.get(
            reverse("liste_agents"),
            secure=True,
        )

        self.assertEqual(reponse.status_code, 403)
