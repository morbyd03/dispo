from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from .formulaires_import_export import (
    ImportAgentsForm,
    ConfirmationImportAgentsForm,
    AnnulationImportAgentsForm,
)

from .services.import_agents import TAILLE_MAXIMALE


class FormulairesImportExportTests(SimpleTestCase):

    def formulaire_import(self, nom, contenu):
        return ImportAgentsForm(
            data={},
            files={
                "fichier": SimpleUploadedFile(
                    nom,
                    contenu,
                    content_type="text/csv",
                )
            },
        )

    def test_fichier_valide(self):
        formulaire = self.formulaire_import(
            "agents.csv",
            b"matricule;nom;prenom;grade;email\n",
        )

        self.assertTrue(formulaire.is_valid())

    def test_extension_majuscule(self):
        formulaire = self.formulaire_import(
            "agents.CSV",
            b"contenu",
        )

        self.assertTrue(formulaire.is_valid())

    def test_extension_invalide(self):
        formulaire = self.formulaire_import(
            "agents.xlsx",
            b"contenu",
        )

        self.assertFalse(formulaire.is_valid())

    def test_fichier_absent(self):
        formulaire = ImportAgentsForm(
            data={},
            files={},
        )

        self.assertFalse(formulaire.is_valid())

    def test_fichier_vide(self):
        formulaire = self.formulaire_import(
            "agents.csv",
            b"",
        )

        self.assertFalse(formulaire.is_valid())

    def test_fichier_trop_volumineux(self):
        formulaire = self.formulaire_import(
            "agents.csv",
            b"x" * (TAILLE_MAXIMALE + 1),
        )

        self.assertFalse(formulaire.is_valid())

    def test_taille_maximale_acceptee(self):
        formulaire = self.formulaire_import(
            "agents.csv",
            b"x" * TAILLE_MAXIMALE,
        )

        self.assertTrue(formulaire.is_valid())

    def test_confirmation_valide(self):
        formulaire = ConfirmationImportAgentsForm(
            data={
                "identifiant": "a" * 32,
                "confirmer_import": "on",
            }
        )

        self.assertTrue(formulaire.is_valid())
        self.assertFalse(
            formulaire.cleaned_data["confirmer_retraits"]
        )

    def test_confirmation_explicite_obligatoire(self):
        formulaire = ConfirmationImportAgentsForm(
            data={
                "identifiant": "a" * 32,
            }
        )

        self.assertFalse(formulaire.is_valid())

    def test_confirmation_retraits(self):
        formulaire = ConfirmationImportAgentsForm(
            data={
                "identifiant": "a" * 32,
                "confirmer_import": "on",
                "confirmer_retraits": "on",
            }
        )

        self.assertTrue(formulaire.is_valid())
        self.assertIs(
            formulaire.cleaned_data["confirmer_retraits"],
            True,
        )

    def test_identifiants_invalides(self):
        for identifiant in (
            "",
            "x" * 32,
            "a" * 31,
            "a" * 33,
        ):
            with self.subTest(identifiant=identifiant):
                formulaire = ConfirmationImportAgentsForm(
                    data={
                        "identifiant": identifiant,
                        "confirmer_import": "on",
                    }
                )

                self.assertFalse(formulaire.is_valid())

    def test_annulation_valide(self):
        formulaire = AnnulationImportAgentsForm(
            data={"identifiant": "a" * 32}
        )

        self.assertTrue(formulaire.is_valid())

    def test_annulation_invalide(self):
        formulaire = AnnulationImportAgentsForm(
            data={"identifiant": "invalide"}
        )

        self.assertFalse(formulaire.is_valid())
