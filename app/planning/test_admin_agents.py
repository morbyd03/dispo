from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase

from .admin import AgentUserAdmin, CompetenceAgentInline
from .models import CompetenceAgent


class TestsAdministrationAgents(TestCase):

    def test_competences_visibles_dans_fiche_agent(self):
        User = get_user_model()
        administration = admin.site._registry[User]

        self.assertIsInstance(administration, AgentUserAdmin)
        self.assertIn(
            CompetenceAgentInline,
            administration.inlines,
        )

    def test_validateur_renseigne_automatiquement(self):
        User = get_user_model()

        administrateur = User.objects.create_superuser(
            username="test_admin_validateur",
            password="MotDePasseTest123!",
        )

        agent = User.objects.create_user(
            username="test_agent_competence",
        )

        from .models import Competence

        competence = Competence.objects.create(
            code="test-admin",
            nom="Compétence de test administration",
        )

        attribution = CompetenceAgent(
            agent=agent,
            competence=competence,
        )

        class FauxFormset:
            model = CompetenceAgent
            deleted_objects = []

            def save(self, commit=True):
                return [attribution]

            def save_m2m(self):
                pass

        class FausseRequete:
            user = administrateur

        administration = admin.site._registry[User]

        administration.save_formset(
            FausseRequete(),
            None,
            FauxFormset(),
            True,
        )

        attribution.refresh_from_db()

        self.assertEqual(
            attribution.valide_par,
            administrateur,
        )
