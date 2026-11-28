from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import (
    ImportAgentTemporaire,
    ProfilAgent,
    ConfirmationImport,
    JournalAction,
)

from .services.import_agents import TAILLE_MAXIMALE

from .services.imports_temporaires import (
    preparer_import_temporaire,
)

from .services.securite import revoquer_acces_compte


class PreparationImportTemporaireTests(TestCase):

    def setUp(self):
        self.User = get_user_model()

        self.admin = self.User.objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.agent = self.User.objects.create(
            username="000999",
            email="agent@example.com",
        )

        self.contenu = (
            b"matricule;nom;prenom;grade;email\n"
            b"000123;Dupont;Jean;SAP1;jean@example.com\n"
        )

    def preparer(self, contenu=None):
        return preparer_import_temporaire(
            contenu=self.contenu if contenu is None else contenu,
            utilisateur_id=self.admin.pk,
        )

    def test_preparation_valide(self):
        resultat = self.preparer()

        self.assertTrue(resultat["confirmable"])
        self.assertTrue(resultat["previsualisation"]["valide"])

        temporaire = ImportAgentTemporaire.objects.get()

        self.assertEqual(
            temporaire.identifiant,
            resultat["identifiant"],
        )
        self.assertEqual(temporaire.utilisateur, self.admin)
        self.assertEqual(bytes(temporaire.contenu), self.contenu)
        self.assertTrue(temporaire.jeton)

    def test_absence_ecriture_metier(self):
        self.preparer()

        self.assertEqual(self.User.objects.count(), 2)
        self.assertFalse(ProfilAgent.objects.exists())
        self.assertFalse(ConfirmationImport.objects.exists())
        self.assertFalse(JournalAction.objects.exists())

    def test_duree_validite(self):
        avant = timezone.now()

        self.preparer()

        temporaire = ImportAgentTemporaire.objects.get()

        self.assertGreaterEqual(
            temporaire.expire_le,
            avant + timedelta(minutes=30),
        )
        self.assertLessEqual(
            temporaire.expire_le,
            timezone.now() + timedelta(minutes=30),
        )

    def test_agent_non_autorise(self):
        with self.assertRaises(PermissionDenied):
            preparer_import_temporaire(
                contenu=self.contenu,
                utilisateur_id=self.agent.pk,
            )

        self.assertFalse(ImportAgentTemporaire.objects.exists())

    def test_administrateur_inactif(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            self.preparer()

        self.assertFalse(ImportAgentTemporaire.objects.exists())

    def test_fichier_vide(self):
        with self.assertRaises(ValidationError):
            self.preparer(b"")

    def test_format_invalide(self):
        with self.assertRaises(ValidationError):
            self.preparer("contenu non binaire")

    def test_fichier_trop_volumineux(self):
        with self.assertRaises(ValidationError):
            self.preparer(b"x" * (TAILLE_MAXIMALE + 1))

    def test_email_vide(self):
        contenu = (
            b"matricule;nom;prenom;grade;email\n"
            b"000123;Dupont;Jean;SAP1;\n"
        )

        resultat = self.preparer(contenu)

        self.assertFalse(resultat["confirmable"])
        self.assertIsNone(resultat["identifiant"])
        self.assertFalse(ImportAgentTemporaire.objects.exists())

    def test_changement_email_bloquant(self):
        contenu = (
            b"matricule;nom;prenom;grade;email\n"
            b"000999;Dupont;Jean;SAP1;nouveau@example.com\n"
        )

        resultat = self.preparer(contenu)

        self.assertTrue(resultat["changements_email"])
        self.assertFalse(resultat["confirmable"])
        self.assertFalse(ImportAgentTemporaire.objects.exists())

    def test_remplacement_previsualisation(self):
        premiere = self.preparer()
        seconde = self.preparer()

        self.assertNotEqual(
            premiere["identifiant"],
            seconde["identifiant"],
        )

        self.assertEqual(ImportAgentTemporaire.objects.count(), 1)

        self.assertFalse(
            ImportAgentTemporaire.objects.filter(
                identifiant=premiere["identifiant"]
            ).exists()
        )

    def test_previsualisation_invalide_supprime_ancienne(self):
        self.preparer()

        contenu = (
            b"matricule;nom;prenom;grade;email\n"
            b"000123;Dupont;Jean;SAP1;\n"
        )

        resultat = self.preparer(contenu)

        self.assertFalse(resultat["confirmable"])
        self.assertFalse(ImportAgentTemporaire.objects.exists())

    def test_fichier_illisible_preserve_ancienne(self):
        resultat = self.preparer()

        with self.assertRaises(ValidationError):
            self.preparer(b"\xff\xfe")

        self.assertTrue(
            ImportAgentTemporaire.objects.filter(
                identifiant=resultat["identifiant"]
            ).exists()
        )

    def test_isolation_entre_administrateurs(self):
        autre = self.User.objects.create(
            username="autre_administrateur",
            is_superuser=True,
        )

        self.preparer()

        preparer_import_temporaire(
            contenu=self.contenu,
            utilisateur_id=autre.pk,
        )

        self.assertEqual(ImportAgentTemporaire.objects.count(), 2)

    def test_purge_expiration(self):
        autre = self.User.objects.create(
            username="autre_administrateur",
            is_superuser=True,
        )

        self.preparer()

        ImportAgentTemporaire.objects.update(
            expire_le=timezone.now() - timedelta(seconds=1)
        )

        preparer_import_temporaire(
            contenu=self.contenu,
            utilisateur_id=autre.pk,
        )

        self.assertFalse(
            ImportAgentTemporaire.objects.filter(
                utilisateur=self.admin
            ).exists()
        )

    def test_version_securite_enregistree(self):
        version = revoquer_acces_compte(self.admin.pk)

        self.preparer()

        temporaire = ImportAgentTemporaire.objects.get()

        self.assertEqual(
            temporaire.version_securite,
            version,
        )


from .services.imports_temporaires import (
    obtenir_import_temporaire,
    confirmer_import_temporaire,
    annuler_import_temporaire,
    purger_imports_temporaires,
)


class ConfirmationImportTemporaireTests(TestCase):

    def setUp(self):
        self.User = get_user_model()

        self.admin = self.User.objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.autre_admin = self.User.objects.create(
            username="autre_administrateur",
            is_superuser=True,
        )

        self.contenu = (
            b"matricule;nom;prenom;grade;email\n"
            b"000123;Dupont;Jean;SAP1;jean@example.com\n"
        )

        resultat = preparer_import_temporaire(
            contenu=self.contenu,
            utilisateur_id=self.admin.pk,
        )

        self.identifiant = resultat["identifiant"]

    def confirmer(self, **modifications):
        donnees = {
            "utilisateur_id": self.admin.pk,
            "identifiant": self.identifiant,
        }

        donnees.update(modifications)

        return confirmer_import_temporaire(**donnees)

    def test_confirmation_valide(self):
        bilan = self.confirmer()

        self.assertEqual(bilan["creations"], 1)

        profil = ProfilAgent.objects.get(
            utilisateur__username="000123"
        )

        self.assertEqual(
            profil.utilisateur.email,
            "jean@example.com",
        )

        self.assertFalse(
            profil.utilisateur.has_usable_password()
        )

    def test_suppression_apres_confirmation(self):
        self.confirmer()

        self.assertFalse(
            ImportAgentTemporaire.objects.exists()
        )

        self.assertEqual(
            ConfirmationImport.objects.count(),
            1,
        )

    def test_rejeu_interdit(self):
        self.confirmer()

        with self.assertRaises(ValidationError):
            self.confirmer()

        self.assertEqual(ProfilAgent.objects.count(), 1)

    def test_confirmation_autre_administrateur(self):
        with self.assertRaises(ValidationError):
            self.confirmer(
                utilisateur_id=self.autre_admin.pk
            )

        self.assertFalse(ProfilAgent.objects.exists())
        self.assertTrue(
            ImportAgentTemporaire.objects.exists()
        )

    def test_confirmation_non_autorisee(self):
        self.admin.is_superuser = False
        self.admin.save(update_fields=["is_superuser"])

        with self.assertRaises(PermissionDenied):
            self.confirmer()

        self.assertFalse(ProfilAgent.objects.exists())

    def test_compte_inactif(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            self.confirmer()

        self.assertFalse(ProfilAgent.objects.exists())

    def test_confirmation_expiree(self):
        ImportAgentTemporaire.objects.update(
            expire_le=timezone.now() - timedelta(seconds=1)
        )

        with self.assertRaises(ValidationError):
            self.confirmer()

        self.assertFalse(ProfilAgent.objects.exists())

    def test_confirmation_revoquee(self):
        revoquer_acces_compte(self.admin.pk)

        with self.assertRaises(ValidationError):
            self.confirmer()

        self.assertFalse(ProfilAgent.objects.exists())

    def test_identifiant_invalide(self):
        for identifiant in (
            None,
            "",
            123,
            "x" * 32,
            "a" * 31,
            "a" * 33,
        ):
            with self.subTest(identifiant=identifiant):
                with self.assertRaises(ValidationError):
                    self.confirmer(
                        identifiant=identifiant
                    )

    def test_identifiant_inconnu(self):
        with self.assertRaises(ValidationError):
            self.confirmer(
                identifiant="0" * 32
            )

    def test_ancienne_previsualisation_refusee(self):
        resultat = preparer_import_temporaire(
            contenu=self.contenu,
            utilisateur_id=self.admin.pk,
        )

        with self.assertRaises(ValidationError):
            self.confirmer()

        self.assertEqual(
            ImportAgentTemporaire.objects.get().identifiant,
            resultat["identifiant"],
        )

    def test_contenu_altere(self):
        ImportAgentTemporaire.objects.update(
            contenu=self.contenu.replace(
                b"Dupont", b"Martin"
            )
        )

        with self.assertRaises(ValidationError):
            self.confirmer()

        self.assertFalse(ProfilAgent.objects.exists())
        self.assertFalse(ConfirmationImport.objects.exists())

    def test_jeton_altere(self):
        ImportAgentTemporaire.objects.update(
            jeton="jeton-invalide"
        )

        with self.assertRaises(ValidationError):
            self.confirmer()

        self.assertFalse(ProfilAgent.objects.exists())
        self.assertFalse(ConfirmationImport.objects.exists())

    def test_etat_initial_modifie(self):
        self.User.objects.create(
            username="000123",
            email="jean@example.com",
        )

        with self.assertRaises(ValidationError):
            self.confirmer()

        self.assertFalse(ProfilAgent.objects.exists())
        self.assertFalse(ConfirmationImport.objects.exists())
        self.assertTrue(
            ImportAgentTemporaire.objects.exists()
        )

    def test_confirmation_retraits_non_booleenne(self):
        for valeur in ("true", "1", 1, None):
            with self.subTest(valeur=valeur):
                with self.assertRaises(ValidationError):
                    self.confirmer(
                        confirmer_retraits=valeur
                    )

        self.assertFalse(ProfilAgent.objects.exists())

    def test_annulation_transactionnelle(self):
        from unittest.mock import patch
        from django.db import OperationalError

        with patch.object(
            ImportAgentTemporaire,
            "delete",
            side_effect=OperationalError("Conflit simule"),
        ):
            with self.assertRaises(OperationalError):
                self.confirmer()

        self.assertFalse(ProfilAgent.objects.exists())
        self.assertFalse(ConfirmationImport.objects.exists())
        self.assertFalse(JournalAction.objects.exists())

        self.assertFalse(
            self.User.objects.filter(
                username="000123"
            ).exists()
        )

        self.assertTrue(
            ImportAgentTemporaire.objects.exists()
        )

    def test_aucun_courriel_envoye(self):
        from django.core import mail

        self.confirmer()

        self.assertEqual(len(mail.outbox), 0)


class RetraitsImportTemporaireTests(TestCase):

    def setUp(self):
        from .models import Grade, Competence, CompetenceAgent

        User = get_user_model()

        self.admin = User.objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.agent = User.objects.create(
            username="000123",
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.agent,
            grade=Grade.objects.get(code="SAP1"),
        )

        self.attribution = CompetenceAgent.objects.create(
            profil=self.profil,
            competence=Competence.objects.get(code="cod1"),
            valide_par=self.admin,
        )

        contenu = (
            b"matricule;nom;prenom;grade;email;cod1\n"
            b"000123;Dupont;Jean;SAP1;jean@example.com;0\n"
        )

        resultat = preparer_import_temporaire(
            contenu=contenu,
            utilisateur_id=self.admin.pk,
        )

        self.assertTrue(resultat["confirmable"])

        self.identifiant = resultat["identifiant"]

    def confirmer(self, confirmation=False):
        return confirmer_import_temporaire(
            utilisateur_id=self.admin.pk,
            identifiant=self.identifiant,
            confirmer_retraits=confirmation,
        )

    def test_retrait_confirme(self):
        from .models import CompetenceAgent

        bilan = self.confirmer(True)

        self.assertEqual(
            bilan["qualifications_retirees"], 1
        )

        self.assertEqual(bilan["qualifications_seules"], 1)
        self.assertEqual(bilan["modifications"], 0)
        self.assertEqual(bilan["inchanges"], 0)
        self.assertFalse(CompetenceAgent.objects.exists())
        self.assertFalse(ImportAgentTemporaire.objects.exists())

    def test_retrait_non_confirme(self):
        from .models import CompetenceAgent

        with self.assertRaises(ValidationError):
            self.confirmer()

        self.assertTrue(
            CompetenceAgent.objects.filter(
                pk=self.attribution.pk
            ).exists()
        )

        self.assertTrue(
            ImportAgentTemporaire.objects.exists()
        )

        self.assertFalse(ConfirmationImport.objects.exists())
        self.assertFalse(JournalAction.objects.exists())

    def test_confirmation_apres_refus(self):
        with self.assertRaises(ValidationError):
            self.confirmer()

        bilan = self.confirmer(True)

        self.assertEqual(
            bilan["qualifications_retirees"], 1
        )

        self.assertEqual(bilan["qualifications_seules"], 1)
        self.assertEqual(bilan["modifications"], 0)
        self.assertEqual(bilan["inchanges"], 0)

        self.assertFalse(ImportAgentTemporaire.objects.exists())


class AnnulationPurgeImportTemporaireTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.autre_admin = User.objects.create(
            username="autre_administrateur",
            is_superuser=True,
        )

        self.contenu = (
            b"matricule;nom;prenom;grade;email\n"
            b"000123;Dupont;Jean;SAP1;jean@example.com\n"
        )

        self.identifiant = self.preparer(self.admin)

    def preparer(self, utilisateur):
        resultat = preparer_import_temporaire(
            contenu=self.contenu,
            utilisateur_id=utilisateur.pk,
        )

        return resultat["identifiant"]

    def annuler(self, utilisateur=None, identifiant=None):
        return annuler_import_temporaire(
            utilisateur_id=(
                utilisateur or self.admin
            ).pk,
            identifiant=(
                self.identifiant
                if identifiant is None
                else identifiant
            ),
        )

    def test_annulation_volontaire(self):
        self.assertTrue(self.annuler())
        self.assertFalse(ImportAgentTemporaire.objects.exists())
        self.assertFalse(ProfilAgent.objects.exists())
        self.assertFalse(ConfirmationImport.objects.exists())

    def test_annulation_repetee(self):
        self.assertTrue(self.annuler())
        self.assertFalse(self.annuler())

    def test_annulation_autre_administrateur(self):
        self.assertFalse(
            self.annuler(utilisateur=self.autre_admin)
        )

        self.assertTrue(
            ImportAgentTemporaire.objects.exists()
        )

    def test_annulation_non_autorisee(self):
        self.admin.is_superuser = False
        self.admin.save(update_fields=["is_superuser"])

        with self.assertRaises(PermissionDenied):
            self.annuler()

        self.assertTrue(
            ImportAgentTemporaire.objects.exists()
        )

    def test_annulation_expiree(self):
        ImportAgentTemporaire.objects.update(
            expire_le=timezone.now() - timedelta(seconds=1)
        )

        self.assertTrue(self.annuler())
        self.assertFalse(ImportAgentTemporaire.objects.exists())

    def test_confirmation_apres_annulation(self):
        self.annuler()

        with self.assertRaises(ValidationError):
            confirmer_import_temporaire(
                utilisateur_id=self.admin.pk,
                identifiant=self.identifiant,
            )

    def test_purge_expiration(self):
        ImportAgentTemporaire.objects.update(
            expire_le=timezone.now() - timedelta(seconds=1)
        )

        self.assertEqual(purger_imports_temporaires(), 1)
        self.assertFalse(ImportAgentTemporaire.objects.exists())

    def test_purge_compte_inactif(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        self.assertEqual(purger_imports_temporaires(), 1)

    def test_purge_perte_autorisation(self):
        self.admin.is_superuser = False
        self.admin.save(update_fields=["is_superuser"])

        self.assertEqual(purger_imports_temporaires(), 1)

    def test_purge_revocation(self):
        revoquer_acces_compte(self.admin.pk)

        self.assertEqual(purger_imports_temporaires(), 1)

    def test_purge_preserve_import_valide(self):
        self.assertEqual(purger_imports_temporaires(), 0)
        self.assertTrue(
            ImportAgentTemporaire.objects.exists()
        )

    def test_purge_selective(self):
        autre_identifiant = self.preparer(self.autre_admin)

        ImportAgentTemporaire.objects.filter(
            utilisateur=self.admin
        ).update(
            expire_le=timezone.now() - timedelta(seconds=1)
        )

        self.assertEqual(purger_imports_temporaires(), 1)

        self.assertEqual(
            ImportAgentTemporaire.objects.get().identifiant,
            autre_identifiant,
        )

    def test_purge_repetee(self):
        revoquer_acces_compte(self.admin.pk)

        self.assertEqual(purger_imports_temporaires(), 1)
        self.assertEqual(purger_imports_temporaires(), 0)


class CommandePurgeImportTemporaireTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create(
            username="administrateur",
            is_superuser=True,
        )

        preparer_import_temporaire(
            utilisateur_id=self.admin.pk,
            contenu=(
                b"matricule;nom;prenom;grade;email\n"
                b"000123;Dupont;Jean;SAP1;jean@example.com\n"
            ),
        )

    def executer_commande(self):
        from io import StringIO
        from django.core.management import call_command

        sortie = StringIO()

        call_command(
            "purger_imports_temporaires",
            stdout=sortie,
        )

        return sortie.getvalue()

    def test_commande_purge_expiration(self):
        ImportAgentTemporaire.objects.update(
            expire_le=timezone.now() - timedelta(seconds=1)
        )

        sortie = self.executer_commande()

        self.assertIn(
            "Imports temporaires supprimes : 1",
            sortie,
        )

        self.assertFalse(
            ImportAgentTemporaire.objects.exists()
        )

    def test_commande_preserve_import_valide(self):
        sortie = self.executer_commande()

        self.assertIn(
            "Imports temporaires supprimes : 0",
            sortie,
        )

        self.assertTrue(
            ImportAgentTemporaire.objects.exists()
        )

    def test_commande_erreur_operationnelle(self):
        from unittest.mock import patch
        from django.db import OperationalError
        from django.core.management.base import CommandError

        with patch(
            "planning.management.commands."
            "purger_imports_temporaires."
            "purger_imports_temporaires",
            side_effect=OperationalError("Conflit simule"),
        ):
            with self.assertRaises(CommandError):
                self.executer_commande()

        self.assertTrue(
            ImportAgentTemporaire.objects.exists()
        )
