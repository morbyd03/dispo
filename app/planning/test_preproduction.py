from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings

from planning.context_processors import personnalisation


class PreproductionTests(SimpleTestCase):

    @override_settings(DISPO_PREPRODUCTION=True)
    def test_contexte_preproduction_active(self):
        request = RequestFactory().get("/")
        contexte = personnalisation(request)
        self.assertTrue(contexte["dispo_preproduction"])

    @override_settings(DISPO_PREPRODUCTION=False)
    def test_contexte_preproduction_inactive(self):
        request = RequestFactory().get("/")
        contexte = personnalisation(request)
        self.assertFalse(contexte["dispo_preproduction"])

    def test_bandeau_visible(self):
        html = render_to_string(
            "planning/_bandeau_preproduction.html",
            {"dispo_preproduction": True},
        )
        self.assertIn("PRÉPRODUCTION", html)
        self.assertIn("dispo-preproduction-banner", html)

    def test_bandeau_absent(self):
        html = render_to_string(
            "planning/_bandeau_preproduction.html",
            {"dispo_preproduction": False},
        )
        self.assertNotIn("dispo-preproduction-banner", html)
