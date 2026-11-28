from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .autorisations import GROUPE_ADMINISTRATEURS
from .models import (
    Grade,
    FonctionAgent,
    ProfilAgent,
    Competence,
    CompetenceAgent,
)


class ProfilPersonnelTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.agent = User.objects.create_user(
            username="00123",
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )

        self.admin = User.objects.create_user(
            username="admin",
            is_superuser=True,
            is_staff=True,
        )

        self.grade = Grade.objects.get(code="SAP1")

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.agent,
            grade=self.grade,
            telephone="0600000000",
        )

        self.fonction = FonctionAgent.objects.create(
            nom="Responsable matériel",
        )

        self.profil.fonctions.add(self.fonction)

        self.competence = Competence.objects.get(
            code="cod1",
        )

        self.url = reverse("mon_profil")

        self.client.force_login(self.agent)

    def consulter(self):
        return self.client.get(self.url, secure=True)

    def autoriser(self, application, codename):
        self.agent.user_permissions.add(
            Permission.objects.get(
                content_type__app_label=application,
                codename=codename,
            )
        )

    def attribuer(self, debut=None, fin=None):
        return CompetenceAgent.objects.create(
            profil=self.profil,
            competence=self.competence,
            date_validation=debut,
            date_expiration=fin,
        )

    def test_informations_personnelles(self):
        reponse = self.consulter()

        self.assertEqual(reponse.status_code, 200)

        for valeur in (
            "00123",
            "Dupont",
            "Jean",
            self.grade.nom,
            self.fonction.nom,
            "0600000000",
            "jean@example.com",
        ):
            self.assertContains(reponse, valeur)

    def test_superutilisateur_sans_profil(self):
        self.client.force_login(self.admin)

        reponse = self.consulter()

        self.assertEqual(reponse.status_code, 200)
        self.assertIsNone(reponse.context["profil"])
        self.assertContains(
            reponse,
            "Ce compte ne possède pas de profil opérationnel.",
        )

    def test_compte_ordinaire_sans_profil(self):
        utilisateur = get_user_model().objects.create_user(
            username="sans-profil",
        )

        self.client.force_login(utilisateur)

        reponse = self.consulter()

        self.assertEqual(reponse.status_code, 200)
        self.assertIsNone(reponse.context["profil"])

    def test_qualification_valide(self):
        self.attribuer()

        reponse = self.consulter()

        self.assertContains(reponse, self.competence.nom)

        self.assertEqual(
            reponse.context["competences"][0].etat_validite,
            "Valide",
        )

    def test_qualification_expiree(self):
        self.attribuer(
            fin=timezone.localdate() - timedelta(days=1),
        )

        reponse = self.consulter()

        self.assertEqual(
            reponse.context["competences"][0].etat_validite,
            "Expirée",
        )

    def test_qualification_valide_jour_expiration(self):
        self.attribuer(fin=timezone.localdate())

        reponse = self.consulter()

        self.assertEqual(
            reponse.context["competences"][0].etat_validite,
            "Valide",
        )

    def test_qualification_future(self):
        self.attribuer(
            debut=timezone.localdate() + timedelta(days=1),
        )

        reponse = self.consulter()

        self.assertEqual(
            reponse.context["competences"][0].etat_validite,
            "À venir",
        )

    def test_qualification_archivee(self):
        self.attribuer()

        self.competence.active = False
        self.competence.save(update_fields=["active"])

        reponse = self.consulter()

        self.assertEqual(
            reponse.context["competences"][0].etat_validite,
            "Archivée",
        )

    def test_menu_agent_ordinaire(self):
        reponse = self.consulter()

        self.assertNotContains(
            reponse, reverse("liste_agents")
        )

    def test_menu_permission_vue_seule(self):
        self.autoriser("auth", "view_user")

        reponse = self.consulter()

        self.assertNotContains(
            reponse, reverse("liste_agents")
        )

    def test_menu_validateur_delegue(self):
        self.autoriser(
            "planning", "add_competenceagent"
        )

        reponse = self.consulter()

        self.assertContains(
            reponse, reverse("liste_agents")
        )

        self.assertContains(
            reponse, "Gestion des qualifications"
        )

    def test_menu_administrateur_dispo(self):
        groupe, _ = Group.objects.get_or_create(
            name=GROUPE_ADMINISTRATEURS
        )

        self.agent.groups.add(groupe)

        self.autoriser("auth", "view_user")

        reponse = self.consulter()

        self.assertContains(
            reponse, reverse("liste_agents")
        )

        self.assertContains(
            reponse, "Gestion des agents"
        )

    def test_menu_superutilisateur(self):
        self.client.force_login(self.admin)

        reponse = self.consulter()

        self.assertContains(
            reponse, reverse("liste_agents")
        )

    def test_profil_accessible_uniquement_connecte(self):
        self.client.logout()

        self.assertEqual(
            self.consulter().status_code,
            302,
        )
