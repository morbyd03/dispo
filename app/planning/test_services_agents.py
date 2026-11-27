from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from .models import Grade, ProfilAgent
from .services.agents import creer_agent


class CreationAgentTests(TestCase):

    def setUp(self):
        self.grade = Grade.objects.get(code="SAP1")

        self.donnees = {
            "matricule": "000123",
            "nom": "Dupont",
            "prenom": "Jean",
            "email": "jean.dupont@example.com",
            "grade_id": self.grade.pk,
        }

    def test_creation(self):
        profil = creer_agent(**self.donnees)
        compte = profil.utilisateur

        self.assertEqual(compte.username, "000123")
        self.assertEqual(compte.last_name, "Dupont")
        self.assertEqual(compte.first_name, "Jean")
        self.assertEqual(
            compte.email, "jean.dupont@example.com"
        )
        self.assertEqual(profil.grade, self.grade)
        self.assertEqual(ProfilAgent.objects.count(), 1)

    def test_securite_initiale(self):
        compte = creer_agent(**self.donnees).utilisateur

        self.assertFalse(compte.has_usable_password())
        self.assertFalse(compte.is_staff)
        self.assertFalse(compte.is_superuser)
        self.assertFalse(compte.groups.exists())
        self.assertFalse(compte.user_permissions.exists())

    def test_grade_obligatoire(self):
        self.donnees["grade_id"] = None

        with self.assertRaises(ValidationError):
            creer_agent(**self.donnees)

        self.assertEqual(get_user_model().objects.count(), 0)

    def test_grade_inactif(self):
        self.grade.active = False
        self.grade.save(update_fields=["active"])

        with self.assertRaises(ValidationError):
            creer_agent(**self.donnees)

    def test_matricule_duplique(self):
        creer_agent(**self.donnees)

        with self.assertRaises(ValidationError):
            creer_agent(**self.donnees)

        self.assertEqual(ProfilAgent.objects.count(), 1)

    def test_email_duplique(self):
        creer_agent(**self.donnees)
        self.donnees["matricule"] = "000124"

        with self.assertRaises(ValidationError):
            creer_agent(**self.donnees)

        self.assertEqual(get_user_model().objects.count(), 1)

    def test_creation_inactive(self):
        profil = creer_agent(**self.donnees, actif=False)
        self.assertFalse(profil.utilisateur.is_active)

    def test_annulation_transaction(self):
        with patch(
            "planning.services.agents.ProfilAgent.objects.create",
            side_effect=IntegrityError("Erreur simulee"),
        ):
            with self.assertRaises(ValidationError):
                creer_agent(**self.donnees)

        self.assertEqual(get_user_model().objects.count(), 0)
        self.assertEqual(ProfilAgent.objects.count(), 0)

    def test_creation_sans_fonction(self):
        profil = creer_agent(**self.donnees)
        self.assertFalse(profil.fonctions.exists())

    def test_creation_plusieurs_fonctions(self):
        from .models import FonctionAgent

        f1 = FonctionAgent.objects.create(nom="Responsable matériel")
        f2 = FonctionAgent.objects.create(nom="Responsable formation")

        profil = creer_agent(
            **self.donnees,
            fonctions_ids=[f1.pk, f2.pk],
        )

        self.assertEqual(
            set(profil.fonctions.values_list("pk", flat=True)),
            {f1.pk, f2.pk},
        )

    def test_fonction_inactive(self):
        from .models import FonctionAgent

        fonction = FonctionAgent.objects.create(
            nom="Fonction inactive",
            active=False,
        )

        with self.assertRaises(ValidationError):
            creer_agent(
                **self.donnees,
                fonctions_ids=[fonction.pk],
            )

        self.assertEqual(get_user_model().objects.count(), 0)

    def test_fonction_inexistante(self):
        with self.assertRaises(ValidationError):
            creer_agent(
                **self.donnees,
                fonctions_ids=[999999],
            )

        self.assertEqual(get_user_model().objects.count(), 0)

    def test_fonction_dupliquee(self):
        from .models import FonctionAgent

        fonction = FonctionAgent.objects.create(
            nom="Responsable matériel"
        )

        profil = creer_agent(
            **self.donnees,
            fonctions_ids=[fonction.pk, fonction.pk],
        )

        self.assertEqual(profil.fonctions.count(), 1)
