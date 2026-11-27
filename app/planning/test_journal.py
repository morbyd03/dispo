from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory

from .models import JournalAction


class AdministrationJournalTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.superutilisateur = User.objects.create(
            username="admin",
            is_superuser=True,
            is_staff=True,
        )

        self.agent = User.objects.create(
            username="000123"
        )

        self.staff = User.objects.create(
            username="staff",
            is_staff=True,
        )

        self.administration = admin.site._registry[JournalAction]
        self.factory = RequestFactory()

    def requete(self, utilisateur):
        requete = self.factory.get("/admin/")
        requete.user = utilisateur
        return requete

    def test_consultation_superutilisateur(self):
        self.assertTrue(
            self.administration.has_view_permission(
                self.requete(self.superutilisateur)
            )
        )

    def test_consultation_agent_refusee(self):
        self.assertFalse(
            self.administration.has_view_permission(
                self.requete(self.agent)
            )
        )

    def test_consultation_staff_refusee(self):
        self.assertFalse(
            self.administration.has_view_permission(
                self.requete(self.staff)
            )
        )

    def test_creation_interdite(self):
        self.assertFalse(
            self.administration.has_add_permission(
                self.requete(self.superutilisateur)
            )
        )

    def test_modification_interdite(self):
        self.assertFalse(
            self.administration.has_change_permission(
                self.requete(self.superutilisateur)
            )
        )

    def test_suppression_interdite(self):
        self.assertFalse(
            self.administration.has_delete_permission(
                self.requete(self.superutilisateur)
            )
        )

    def test_consultation_compte_inactif_refusee(self):
        self.superutilisateur.is_active = False

        self.assertFalse(
            self.administration.has_view_permission(
                self.requete(self.superutilisateur)
            )
        )


class AdministrationCompetencesTests(AdministrationJournalTests):

    def setUp(self):
        super().setUp()

        from .models import CompetenceAgent

        self.administration = admin.site._registry[CompetenceAgent]

    def test_consultation_staff_refusee(self):
        self.assertFalse(
            self.administration.has_view_permission(
                self.requete(self.staff)
            )
        )
