from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from .models import (
    Grade,
    ProfilAgent,
    Competence,
    CompetenceAgent,
    FonctionAgent,
)

from .services.export_agents import (
    exporter_agents_csv,
    securiser_cellule_csv,
)

from .services.import_agents import lire_csv_agents


class ExportAgentsTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.agent = User.objects.create(
            username="000123",
            first_name="François",
            last_name="Évrard",
            email="francois@example.com",
        )

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.agent,
            grade=Grade.objects.get(code="SAP1"),
            telephone="0600000000",
        )

        self.competence = Competence.objects.get(
            code="cod1"
        )

        CompetenceAgent.objects.create(
            profil=self.profil,
            competence=self.competence,
        )

    def exporter(self):
        return exporter_agents_csv(
            utilisateur_id=self.admin.pk,
        )

    def lire(self):
        return lire_csv_agents(self.exporter())

    def test_encodage_utf8_bom(self):
        self.assertTrue(
            self.exporter().startswith(b"\xef\xbb\xbf")
        )

    def test_identite_agent(self):
        donnees = self.lire()["lignes"][0]["donnees"]

        self.assertEqual(donnees["matricule"], "000123")
        self.assertEqual(donnees["nom"], "Évrard")
        self.assertEqual(donnees["prenom"], "François")
        self.assertEqual(donnees["grade"], "SAP1")
        self.assertEqual(donnees["telephone"], "0600000000")

    def test_exclusion_comptes_sans_profil(self):
        self.assertEqual(len(self.lire()["lignes"]), 1)

    def test_qualifications(self):
        donnees = self.lire()["lignes"][0]["donnees"]

        self.assertEqual(donnees["cod1"], "1")
        self.assertEqual(donnees["fdf1"], "0")

    def test_qualification_personnalisee(self):
        Competence.objects.create(
            code="qualification-test",
            nom="Qualification de test",
        )

        self.assertIn(
            "qualification-test",
            self.lire()["colonnes"],
        )

    def test_exclusion_qualification_inactive(self):
        self.competence.active = False
        self.competence.save(update_fields=["active"])

        self.assertNotIn(
            "cod1",
            self.lire()["colonnes"],
        )

    def test_fonctions_multiples(self):
        for nom in ("Fonction A", "Fonction B"):
            fonction = FonctionAgent.objects.create(
                nom=nom
            )
            self.profil.fonctions.add(fonction)

        donnees = self.lire()["lignes"][0]["donnees"]

        self.assertEqual(
            donnees["fonction"],
            "Fonction A|Fonction B",
        )

    def test_export_non_autorise(self):
        with self.assertRaises(PermissionDenied):
            exporter_agents_csv(
                utilisateur_id=self.agent.pk,
            )

    def test_absence_donnees_authentification(self):
        colonnes = self.lire()["colonnes"]

        for colonne in (
            "password",
            "is_superuser",
            "is_staff",
            "last_login",
        ):
            self.assertNotIn(colonne, colonnes)

    def test_protection_formules_csv(self):
        for valeur in (
            "=1+1",
            "+123",
            "-123",
            "@test",
        ):
            with self.subTest(valeur=valeur):
                self.assertEqual(
                    securiser_cellule_csv(valeur),
                    "'" + valeur,
                )

    def test_mode_export_invalide(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            exporter_agents_csv(
                utilisateur_id=self.admin.pk,
                mode="inconnu",
            )

    def test_telephone_international_consultation(self):
        self.profil.telephone = "+33612345678"
        self.profil.save(update_fields=["telephone"])

        donnees = self.lire()["lignes"][0]["donnees"]

        self.assertEqual(
            donnees["telephone"],
            "'+33612345678",
        )

    def test_telephone_international_reimport(self):
        self.profil.telephone = "+33612345678"
        self.profil.save(update_fields=["telephone"])

        contenu = exporter_agents_csv(
            utilisateur_id=self.admin.pk,
            mode="reimport",
        )

        donnees = lire_csv_agents(
            contenu
        )["lignes"][0]["donnees"]

        self.assertEqual(
            donnees["telephone"],
            "+33612345678",
        )

    def test_previsualisation_export(self):
        from .services.import_agents import (
            previsualiser_import_agents,
        )

        contenu = exporter_agents_csv(
            utilisateur_id=self.admin.pk,
            mode="reimport",
        )

        resultat = previsualiser_import_agents(contenu)

        self.assertTrue(resultat["valide"])

        ligne = resultat["lignes"][0]

        self.assertEqual(ligne["changements"], {})
        self.assertEqual(
            ligne["operations_qualifications"],
            [],
        )
        self.assertFalse(ligne["confirmation_retraits"])

    def test_cycle_complet_export_reimport(self):
        from datetime import date

        from .models import JournalAction

        from .services.import_agents import (
            preparer_confirmation_import,
            executer_import_agents,
        )

        self.agent.set_password("mot-de-passe-fictif")
        self.agent.save(update_fields=["password"])

        ancien_mot_de_passe = self.agent.password

        self.profil.telephone = "+33612345678"
        self.profil.save(update_fields=["telephone"])

        attribution = CompetenceAgent.objects.get(
            profil=self.profil
        )

        attribution.date_validation = date(2026, 1, 1)
        attribution.date_expiration = date(2027, 1, 1)
        attribution.valide_par = self.admin

        attribution.save()

        contenu = exporter_agents_csv(
            utilisateur_id=self.admin.pk,
            mode="reimport",
        )

        preparation = preparer_confirmation_import(
            contenu=contenu,
            utilisateur_id=self.admin.pk,
        )

        self.assertTrue(
            preparation["previsualisation"]["valide"]
        )

        bilan = executer_import_agents(
            contenu=contenu,
            utilisateur_id=self.admin.pk,
            jeton=preparation["jeton"],
        )

        self.assertEqual(bilan["creations"], 0)
        self.assertEqual(bilan["rattachements"], 0)
        self.assertEqual(bilan["modifications"], 0)
        self.assertEqual(bilan["inchanges"], 1)
        self.assertEqual(bilan["qualifications_attribuees"], 0)
        self.assertEqual(bilan["qualifications_retirees"], 0)

        self.agent.refresh_from_db()
        self.profil.refresh_from_db()
        attribution.refresh_from_db()

        self.assertEqual(
            self.agent.password,
            ancien_mot_de_passe,
        )

        self.assertEqual(
            self.profil.telephone,
            "+33612345678",
        )

        self.assertEqual(
            attribution.date_validation,
            date(2026, 1, 1),
        )

        self.assertEqual(
            attribution.date_expiration,
            date(2027, 1, 1),
        )

        self.assertEqual(
            attribution.valide_par,
            self.admin,
        )

        self.assertFalse(JournalAction.objects.exists())

    def test_formule_refusee_en_reimport(self):
        from django.core.exceptions import ValidationError

        self.agent.last_name = "=1+1"
        self.agent.save(update_fields=["last_name"])

        with self.assertRaises(ValidationError):
            exporter_agents_csv(
                utilisateur_id=self.admin.pk,
                mode="reimport",
            )

    def test_formule_neutralisee_en_consultation(self):
        self.agent.last_name = "=1+1"
        self.agent.save(update_fields=["last_name"])

        donnees = self.lire()["lignes"][0]["donnees"]

        self.assertEqual(donnees["nom"], "'=1+1")

    def test_telephone_dangereux_refuse(self):
        from django.core.exceptions import ValidationError

        self.profil.telephone = "+1+1"
        self.profil.save(update_fields=["telephone"])

        with self.assertRaises(ValidationError):
            exporter_agents_csv(
                utilisateur_id=self.admin.pk,
                mode="reimport",
            )

    def test_telephone_international_preserve(self):
        self.profil.telephone = "+33612345678"
        self.profil.save(update_fields=["telephone"])

        contenu = exporter_agents_csv(
            utilisateur_id=self.admin.pk,
            mode="reimport",
        )

        donnees = lire_csv_agents(
            contenu
        )["lignes"][0]["donnees"]

        self.assertEqual(
            donnees["telephone"],
            "+33612345678",
        )

    def test_reimport_profil_sans_grade(self):
        from django.core.exceptions import ValidationError

        self.profil.grade = None
        self.profil.save(update_fields=["grade"])

        with self.assertRaises(ValidationError):
            exporter_agents_csv(
                utilisateur_id=self.admin.pk,
                mode="reimport",
            )

    def test_consultation_profil_sans_grade(self):
        self.profil.grade = None
        self.profil.save(update_fields=["grade"])

        donnees = self.lire()["lignes"][0]["donnees"]

        self.assertEqual(donnees["grade"], "")

    def test_reimport_grade_inactif(self):
        from django.core.exceptions import ValidationError

        grade = self.profil.grade
        grade.active = False
        grade.save(update_fields=["active"])

        with self.assertRaises(ValidationError):
            exporter_agents_csv(
                utilisateur_id=self.admin.pk,
                mode="reimport",
            )

    def test_reimport_compte_protege(self):
        from django.core.exceptions import ValidationError

        self.agent.is_staff = True
        self.agent.save(update_fields=["is_staff"])

        with self.assertRaises(ValidationError):
            exporter_agents_csv(
                utilisateur_id=self.admin.pk,
                mode="reimport",
            )

    def test_reimport_email_absent(self):
        from django.core.exceptions import ValidationError

        self.agent.email = ""
        self.agent.save(update_fields=["email"])

        with self.assertRaises(ValidationError):
            exporter_agents_csv(
                utilisateur_id=self.admin.pk,
                mode="reimport",
            )

    def test_reimport_fonction_inactive_conservee(self):
        fonction = FonctionAgent.objects.create(
            nom="Fonction historique",
            active=False,
        )

        self.profil.fonctions.add(fonction)

        contenu = exporter_agents_csv(
            utilisateur_id=self.admin.pk,
            mode="reimport",
        )

        donnees = lire_csv_agents(
            contenu
        )["lignes"][0]["donnees"]

        self.assertEqual(
            donnees["fonction"],
            "Fonction historique",
        )

    def test_reimport_qualification_inactive_conservee(self):
        self.competence.active = False
        self.competence.save(update_fields=["active"])

        contenu = exporter_agents_csv(
            utilisateur_id=self.admin.pk,
            mode="reimport",
        )

        self.assertNotIn(
            "cod1",
            lire_csv_agents(contenu)["colonnes"],
        )

        self.assertTrue(
            CompetenceAgent.objects.filter(
                profil=self.profil,
                competence=self.competence,
            ).exists()
        )

    def test_reimport_sans_ecriture(self):
        from .models import JournalAction, ConfirmationImport

        exporter_agents_csv(
            utilisateur_id=self.admin.pk,
            mode="reimport",
        )

        self.assertFalse(JournalAction.objects.exists())
        self.assertFalse(ConfirmationImport.objects.exists())
