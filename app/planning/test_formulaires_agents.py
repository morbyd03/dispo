from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Grade, FonctionAgent, ProfilAgent
from .formulaires_agents import (
    AgentForm,
    AgentModificationForm,
)


class FormulairesAgentsTests(TestCase):

    def setUp(self):
        self.grade = Grade.objects.get(code="SAP1")

        self.fonction = FonctionAgent.objects.create(
            nom="Responsable matériel",
        )

        self.donnees = {
            "matricule": "00123",
            "nom": "Dupont",
            "prenom": "Jean",
            "email": "Jean.Dupont@example.com",
            "grade": self.grade.pk,
            "telephone": "0600000000",
            "fonctions": [self.fonction.pk],
            "actif": "on",
        }

    def creer_profil(self):
        utilisateur = get_user_model().objects.create_user(
            username="00123",
            first_name="Jean",
            last_name="Dupont",
            email="jean.dupont@example.com",
        )

        profil = ProfilAgent.objects.create(
            utilisateur=utilisateur,
            grade=self.grade,
        )

        profil.fonctions.add(self.fonction)

        return profil

    def test_creation_valide(self):
        formulaire = AgentForm(self.donnees)

        self.assertTrue(
            formulaire.is_valid(),
            formulaire.errors,
        )

        donnees = formulaire.donnees_creation()

        self.assertEqual(donnees["matricule"], "00123")
        self.assertEqual(
            donnees["email"],
            "jean.dupont@example.com",
        )
        self.assertEqual(donnees["grade_id"], self.grade.pk)
        self.assertEqual(
            donnees["fonctions_ids"],
            [self.fonction.pk],
        )

    def test_champs_obligatoires(self):
        for champ in (
            "matricule",
            "nom",
            "prenom",
            "email",
            "grade",
        ):
            with self.subTest(champ=champ):
                donnees = self.donnees.copy()
                donnees.pop(champ)

                formulaire = AgentForm(donnees)

                self.assertFalse(formulaire.is_valid())
                self.assertIn(champ, formulaire.errors)

    def test_matricule_invalide(self):
        self.donnees["matricule"] = "ABC123"

        formulaire = AgentForm(self.donnees)

        self.assertFalse(formulaire.is_valid())
        self.assertIn("matricule", formulaire.errors)

    def test_grade_inactif_refuse(self):
        self.grade.active = False
        self.grade.save(update_fields=["active"])

        formulaire = AgentForm(self.donnees)

        self.assertFalse(formulaire.is_valid())
        self.assertIn("grade", formulaire.errors)

    def test_fonction_inactive_refusee(self):
        self.fonction.active = False
        self.fonction.save(update_fields=["active"])

        formulaire = AgentForm(self.donnees)

        self.assertFalse(formulaire.is_valid())
        self.assertIn("fonctions", formulaire.errors)

    def test_identifiants_proteges(self):
        profil = self.creer_profil()

        self.donnees["matricule"] = "00999"
        self.donnees["email"] = "autre@example.com"

        formulaire = AgentModificationForm(
            self.donnees,
            profil=profil,
        )

        self.assertTrue(
            formulaire.is_valid(),
            formulaire.errors,
        )

        self.assertEqual(
            formulaire.cleaned_data["matricule"],
            "00123",
        )

        self.assertEqual(
            formulaire.cleaned_data["email"],
            "jean.dupont@example.com",
        )

        self.assertNotIn(
            "matricule",
            formulaire.donnees_profil(),
        )

        self.assertNotIn(
            "email",
            formulaire.donnees_profil(),
        )

    def test_conservation_grade_et_fonction_inactifs(self):
        profil = self.creer_profil()

        self.grade.active = False
        self.grade.save(update_fields=["active"])

        self.fonction.active = False
        self.fonction.save(update_fields=["active"])

        formulaire = AgentModificationForm(
            self.donnees,
            profil=profil,
        )

        self.assertTrue(
            formulaire.is_valid(),
            formulaire.errors,
        )

    def test_formulaire_sans_ecriture_en_base(self):
        formulaire = AgentForm(self.donnees)

        self.assertTrue(formulaire.is_valid())
        formulaire.donnees_creation()

        self.assertFalse(ProfilAgent.objects.exists())

        self.assertFalse(
            get_user_model().objects.filter(
                username="00123"
            ).exists()
        )
