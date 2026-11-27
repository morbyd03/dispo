from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from .models import Grade, ProfilAgent
from .services.agents import creer_agent


class CreationAgentTests(TestCase):

    def setUp(self):
        self.auteur = get_user_model().objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.grade = Grade.objects.get(code="SAP1")

        self.donnees = {
            "auteur_id": self.auteur.pk,
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

        self.assertEqual(get_user_model().objects.exclude(pk=self.auteur.pk).count(), 0)

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

        self.assertEqual(get_user_model().objects.exclude(pk=self.auteur.pk).count(), 1)

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

        self.assertEqual(get_user_model().objects.exclude(pk=self.auteur.pk).count(), 0)
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

        self.assertEqual(get_user_model().objects.exclude(pk=self.auteur.pk).count(), 0)

    def test_fonction_inexistante(self):
        with self.assertRaises(ValidationError):
            creer_agent(
                **self.donnees,
                fonctions_ids=[999999],
            )

        self.assertEqual(get_user_model().objects.exclude(pk=self.auteur.pk).count(), 0)

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


class ModificationAgentTests(TestCase):

    def setUp(self):
        self.auteur = get_user_model().objects.create(
            username="administrateur",
            is_superuser=True,
        )

        from .models import FonctionAgent

        self.grade = Grade.objects.get(code="SAP1")
        self.nouveau_grade = Grade.objects.get(code="CPL")

        self.fonction = FonctionAgent.objects.create(
            nom="Responsable matériel"
        )

        self.profil = creer_agent(
            auteur_id=self.auteur.pk,
            matricule="000123",
            nom="Dupont",
            prenom="Jean",
            email="jean.dupont@example.com",
            grade_id=self.grade.pk,
        )

        self.donnees = {
            "auteur_id": self.auteur.pk,
            "profil_id": self.profil.pk,
            "nom": "Durand",
            "prenom": "Jean-Pierre",
            "grade_id": self.nouveau_grade.pk,
            "telephone": "0600000000",
            "fonctions_ids": [self.fonction.pk],
        }

    def test_modification(self):
        from .services.agents import modifier_agent

        profil = modifier_agent(**self.donnees)

        self.assertEqual(profil.utilisateur.last_name, "Durand")
        self.assertEqual(profil.utilisateur.first_name, "Jean-Pierre")
        self.assertEqual(profil.grade, self.nouveau_grade)
        self.assertEqual(profil.telephone, "0600000000")
        self.assertEqual(profil.fonctions.count(), 1)
        self.assertEqual(profil.pk, self.profil.pk)

    def test_preservation_du_compte(self):
        from .services.agents import modifier_agent
        from django.contrib.auth.models import Group

        compte = self.profil.utilisateur
        compte.set_password("MotDePasseFictif123!")
        compte.save(update_fields=["password"])

        groupe = Group.objects.create(name="Groupe fictif")
        compte.groups.add(groupe)

        mot_de_passe = compte.password

        modifier_agent(**self.donnees)
        compte.refresh_from_db()

        self.assertEqual(compte.username, "000123")
        self.assertEqual(compte.email, "jean.dupont@example.com")
        self.assertEqual(compte.password, mot_de_passe)
        self.assertTrue(compte.is_active)
        self.assertFalse(compte.is_staff)
        self.assertFalse(compte.is_superuser)
        self.assertTrue(compte.groups.filter(pk=groupe.pk).exists())

    def test_preservation_des_donnees_operationnelles(self):
        from datetime import timedelta
        from django.utils import timezone
        from .models import Competence, CompetenceAgent, Disponibilite
        from .services.agents import modifier_agent

        competence = Competence.objects.get(code="cod1")

        attribution = CompetenceAgent.objects.create(
            profil=self.profil,
            competence=competence,
        )

        debut = timezone.now()

        disponibilite = Disponibilite.objects.create(
            profil=self.profil,
            debut=debut,
            fin=debut + timedelta(hours=9),
        )

        modifier_agent(**self.donnees)

        attribution.refresh_from_db()
        disponibilite.refresh_from_db()

        self.assertEqual(attribution.profil_id, self.profil.pk)
        self.assertEqual(disponibilite.profil_id, self.profil.pk)
        self.assertEqual(CompetenceAgent.objects.count(), 1)
        self.assertEqual(Disponibilite.objects.count(), 1)

    def test_profil_inexistant(self):
        from .services.agents import modifier_agent

        self.donnees["profil_id"] = 999999

        with self.assertRaises(ValidationError):
            modifier_agent(**self.donnees)

    def test_grade_invalide(self):
        from .services.agents import modifier_agent

        self.donnees["grade_id"] = None

        with self.assertRaises(ValidationError):
            modifier_agent(**self.donnees)

        self.profil.utilisateur.refresh_from_db()
        self.assertEqual(self.profil.utilisateur.last_name, "Dupont")

    def test_annulation_transaction(self):
        from .services.agents import modifier_agent

        with patch(
            "planning.services.agents.ProfilAgent.save",
            side_effect=IntegrityError("Erreur simulee"),
        ):
            with self.assertRaises(ValidationError):
                modifier_agent(**self.donnees)

        self.profil.refresh_from_db()

        self.assertEqual(self.profil.utilisateur.last_name, "Dupont")
        self.assertEqual(self.profil.grade, self.grade)
        self.assertEqual(self.profil.telephone, "")
        self.assertFalse(self.profil.fonctions.exists())

    def test_conservation_grade_inactif(self):
        from .services.agents import modifier_agent

        self.grade.active = False
        self.grade.save(update_fields=["active"])

        self.donnees["grade_id"] = self.grade.pk

        profil = modifier_agent(**self.donnees)

        self.assertEqual(profil.grade_id, self.grade.pk)

    def test_nouveau_grade_inactif_refuse(self):
        from .services.agents import modifier_agent

        self.nouveau_grade.active = False
        self.nouveau_grade.save(update_fields=["active"])

        with self.assertRaises(ValidationError):
            modifier_agent(**self.donnees)

    def test_conservation_fonction_inactive(self):
        from .services.agents import modifier_agent

        self.profil.fonctions.add(self.fonction)

        self.fonction.active = False
        self.fonction.save(update_fields=["active"])

        profil = modifier_agent(**self.donnees)

        self.assertTrue(
            profil.fonctions.filter(pk=self.fonction.pk).exists()
        )

    def test_nouvelle_fonction_inactive_refusee(self):
        from .services.agents import modifier_agent

        self.fonction.active = False
        self.fonction.save(update_fields=["active"])

        with self.assertRaises(ValidationError):
            modifier_agent(**self.donnees)

    def test_retrait_fonction_inactive(self):
        from .services.agents import modifier_agent

        self.profil.fonctions.add(self.fonction)

        self.fonction.active = False
        self.fonction.save(update_fields=["active"])

        self.donnees["fonctions_ids"] = []

        profil = modifier_agent(**self.donnees)

        self.assertFalse(profil.fonctions.exists())


class ValidationIdentifiantsTests(TestCase):

    def test_identifiants_valides(self):
        from .services.agents import verifier_identifiant

        for valeur in (1, "1", " 1 ", "001"):
            with self.subTest(valeur=valeur):
                self.assertEqual(verifier_identifiant(valeur), 1)

    def test_identifiants_invalides(self):
        from .services.agents import verifier_identifiant

        for valeur in (
            None, True, False, 0, -1,
            1.5, 1.0, "", "abc", "1.5",
            "-1", "１２３", 2**63,
        ):
            with self.subTest(valeur=valeur):
                with self.assertRaises(ValidationError):
                    verifier_identifiant(valeur)


class RattachementProfilTests(TestCase):

    def setUp(self):
        self.auteur = get_user_model().objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.grade = Grade.objects.get(code="SAP1")

        self.compte = get_user_model().objects.create_user(
            username="000123",
            first_name="Jean",
            last_name="Dupont",
            email="jean.dupont@example.com",
            password="MotDePasseFictif123!",
        )

        self.donnees = {
            "auteur_id": self.auteur.pk,
            "utilisateur_id": self.compte.pk,
            "grade_id": self.grade.pk,
        }

    def test_rattachement(self):
        from .services.agents import rattacher_profil_agent

        profil = rattacher_profil_agent(**self.donnees)

        self.assertEqual(profil.utilisateur_id, self.compte.pk)
        self.assertEqual(profil.grade, self.grade)
        self.assertEqual(get_user_model().objects.exclude(pk=self.auteur.pk).count(), 1)
        self.assertEqual(ProfilAgent.objects.count(), 1)

    def test_preservation_compte(self):
        from .services.agents import rattacher_profil_agent
        from django.contrib.auth.models import Group

        groupe = Group.objects.create(name="Groupe fictif")
        self.compte.groups.add(groupe)

        mot_de_passe = self.compte.password

        rattacher_profil_agent(**self.donnees)

        self.compte.refresh_from_db()

        self.assertEqual(self.compte.password, mot_de_passe)
        self.assertEqual(self.compte.username, "000123")
        self.assertTrue(self.compte.is_active)
        self.assertTrue(self.compte.groups.filter(pk=groupe.pk).exists())

    def test_profil_deja_existant(self):
        from .services.agents import rattacher_profil_agent

        rattacher_profil_agent(**self.donnees)

        with self.assertRaises(ValidationError):
            rattacher_profil_agent(**self.donnees)

        self.assertEqual(ProfilAgent.objects.count(), 1)

    def test_compte_inexistant(self):
        from .services.agents import rattacher_profil_agent

        self.donnees["utilisateur_id"] = 999999

        with self.assertRaises(ValidationError):
            rattacher_profil_agent(**self.donnees)

    def test_compte_privilegie(self):
        from .services.agents import rattacher_profil_agent

        self.compte.is_superuser = True
        self.compte.save(update_fields=["is_superuser"])

        with self.assertRaises(ValidationError):
            rattacher_profil_agent(**self.donnees)

        self.assertFalse(ProfilAgent.objects.exists())

    def test_identite_incomplete(self):
        from .services.agents import rattacher_profil_agent

        self.compte.email = ""
        self.compte.save(update_fields=["email"])

        with self.assertRaises(ValidationError):
            rattacher_profil_agent(**self.donnees)

        self.assertFalse(ProfilAgent.objects.exists())

    def test_grade_obligatoire(self):
        from .services.agents import rattacher_profil_agent

        self.donnees["grade_id"] = None

        with self.assertRaises(ValidationError):
            rattacher_profil_agent(**self.donnees)

        self.assertFalse(ProfilAgent.objects.exists())

    def test_preservation_compte_inactif(self):
        from .services.agents import rattacher_profil_agent

        self.compte.is_active = False
        self.compte.save(update_fields=["is_active"])

        profil = rattacher_profil_agent(**self.donnees)

        self.assertFalse(profil.utilisateur.is_active)

    def test_compte_staff_refuse(self):
        from .services.agents import rattacher_profil_agent

        self.compte.is_staff = True
        self.compte.save(update_fields=["is_staff"])

        with self.assertRaises(ValidationError):
            rattacher_profil_agent(**self.donnees)

        self.assertFalse(ProfilAgent.objects.exists())

    def test_annulation_rattachement(self):
        from .services.agents import rattacher_profil_agent

        with patch(
            "planning.services.agents.ProfilAgent.objects.create",
            side_effect=IntegrityError("Erreur simulee"),
        ):
            with self.assertRaises(ValidationError):
                rattacher_profil_agent(**self.donnees)

        self.assertEqual(get_user_model().objects.exclude(pk=self.auteur.pk).count(), 1)
        self.assertFalse(ProfilAgent.objects.exists())


class SecuriteServicesAgentsTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.agent = User.objects.create(
            username="000124",
            first_name="Paul",
            last_name="Martin",
            email="paul@example.com",
        )

        self.grade = Grade.objects.get(code="SAP1")

        self.donnees = {
            "auteur_id": self.admin.pk,
            "matricule": "000123",
            "nom": "Dupont",
            "prenom": "Jean",
            "email": "jean@example.com",
            "grade_id": self.grade.pk,
        }

    def test_auteur_obligatoire(self):
        del self.donnees["auteur_id"]

        with self.assertRaises(TypeError):
            creer_agent(**self.donnees)

    def test_creation_par_agent_refusee(self):
        from django.core.exceptions import PermissionDenied

        self.donnees["auteur_id"] = self.agent.pk

        with self.assertRaises(PermissionDenied):
            creer_agent(**self.donnees)

        self.assertFalse(ProfilAgent.objects.exists())

    def test_auteur_inactif_refuse(self):
        from django.core.exceptions import PermissionDenied

        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            creer_agent(**self.donnees)

    def test_administrateur_sans_permission_refuse(self):
        from django.contrib.auth.models import Group
        from django.core.exceptions import PermissionDenied

        groupe, _ = Group.objects.get_or_create(
            name="Administrateurs Dispo"
        )

        self.agent.groups.add(groupe)
        self.donnees["auteur_id"] = self.agent.pk

        with self.assertRaises(PermissionDenied):
            creer_agent(**self.donnees)

    def test_administrateur_autorise(self):
        from django.contrib.auth.models import Group, Permission

        groupe, _ = Group.objects.get_or_create(
            name="Administrateurs Dispo"
        )

        permission = Permission.objects.get(
            content_type__app_label="auth",
            codename="add_user",
        )

        groupe.permissions.add(permission)
        self.agent.groups.add(groupe)

        self.donnees["auteur_id"] = self.agent.pk

        profil = creer_agent(**self.donnees)

        self.assertEqual(profil.utilisateur.username, "000123")

    def test_permission_seule_insuffisante(self):
        from django.contrib.auth.models import Permission
        from django.core.exceptions import PermissionDenied

        permission = Permission.objects.get(
            content_type__app_label="auth",
            codename="add_user",
        )

        self.agent.user_permissions.add(permission)
        self.donnees["auteur_id"] = self.agent.pk

        with self.assertRaises(PermissionDenied):
            creer_agent(**self.donnees)

    def test_modification_non_autorisee(self):
        from django.core.exceptions import PermissionDenied
        from .services.agents import modifier_agent

        profil = creer_agent(**self.donnees)

        with self.assertRaises(PermissionDenied):
            modifier_agent(
                auteur_id=self.agent.pk,
                profil_id=profil.pk,
                nom="Modifie",
                prenom="Jean",
                grade_id=self.grade.pk,
                telephone="",
                fonctions_ids=[],
            )

        profil.utilisateur.refresh_from_db()
        self.assertEqual(profil.utilisateur.last_name, "Dupont")

    def test_rattachement_non_autorise(self):
        from django.core.exceptions import PermissionDenied
        from .services.agents import rattacher_profil_agent

        with self.assertRaises(PermissionDenied):
            rattacher_profil_agent(
                auteur_id=self.agent.pk,
                utilisateur_id=self.agent.pk,
                grade_id=self.grade.pk,
            )

        self.assertFalse(ProfilAgent.objects.exists())

    def test_statut_non_booleen_refuse(self):
        with self.assertRaises(ValidationError):
            creer_agent(**self.donnees, actif="false")

    def test_liste_fonctions_invalide(self):
        with self.assertRaises(ValidationError):
            creer_agent(**self.donnees, fonctions_ids="123")
