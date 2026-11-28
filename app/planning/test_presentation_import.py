from copy import deepcopy

from django.test import TestCase

from .models import Grade, FonctionAgent, Competence
from .services.presentation_import import presenter_import_agents


class PresentationImportTests(TestCase):

    def setUp(self):
        self.grade = Grade.objects.get(code="SAP1")

        self.fonction = FonctionAgent.objects.create(
            nom="Fonction de test",
        )

        self.competence = Competence.objects.create(
            code="qualification_test",
            nom="Qualification de test",
        )

        self.ligne = {
            "ligne": 2,
            "action": "modifier",
            "matricule": "000123",
            "nom": "Dupont",
            "prenom": "Jean",
            "email": "jean@example.com",
            "grade_id": self.grade.pk,
            "telephone": "",
            "fonctions_ids": [self.fonction.pk],
            "changements": {},
            "operations_qualifications": [],
            "changement_email": False,
        }

        self.previsualisation = {
            "lignes": [self.ligne],
        }

    def presenter(self):
        return presenter_import_agents(
            self.previsualisation
        )[0]

    def test_libelles_referentiel(self):
        ligne = self.presenter()

        self.assertEqual(ligne["grade"], self.grade.nom)
        self.assertEqual(ligne["fonctions"], self.fonction.nom)

    def test_conservation_matricule(self):
        self.assertEqual(
            self.presenter()["matricule"],
            "000123",
        )

    def test_valeurs_absentes(self):
        self.ligne["grade_id"] = None
        self.ligne["fonctions_ids"] = []

        ligne = self.presenter()

        self.assertEqual(ligne["grade"], "—")
        self.assertEqual(ligne["telephone"], "—")
        self.assertEqual(ligne["fonctions"], "—")

    def test_creation(self):
        self.ligne["action"] = "creer"

        self.assertEqual(
            self.presenter()["action"],
            "Création",
        )

    def test_rattachement(self):
        self.ligne["action"] = "rattacher"

        self.assertEqual(
            self.presenter()["action"],
            "Rattachement",
        )

    def test_agent_inchange(self):
        self.assertEqual(
            self.presenter()["action"],
            "Inchangé",
        )

    def test_modification_profil(self):
        self.ligne["changements"] = {
            "nom": {
                "avant": "Martin",
                "apres": "Dupont",
            },
        }

        ligne = self.presenter()

        self.assertEqual(
            ligne["action"],
            "Modification du profil",
        )

        self.assertEqual(
            ligne["changements"],
            [{
                "champ": "Nom",
                "avant": "Martin",
                "apres": "Dupont",
            }],
        )

    def test_modification_grade(self):
        self.ligne["changements"] = {
            "grade_id": {
                "avant": None,
                "apres": self.grade.pk,
            },
        }

        changement = self.presenter()["changements"][0]

        self.assertEqual(changement["champ"], "Grade")
        self.assertEqual(changement["avant"], "—")
        self.assertEqual(changement["apres"], self.grade.nom)

    def test_modification_fonctions(self):
        self.ligne["changements"] = {
            "fonctions_ids": {
                "avant": [],
                "apres": [self.fonction.pk],
            },
        }

        changement = self.presenter()["changements"][0]

        self.assertEqual(changement["champ"], "Fonctions")
        self.assertEqual(changement["avant"], "—")
        self.assertEqual(changement["apres"], self.fonction.nom)

    def test_attribution_qualification(self):
        self.ligne["operations_qualifications"] = [{
            "action": "attribuer",
            "competence_id": self.competence.pk,
        }]

        ligne = self.presenter()

        self.assertEqual(
            ligne["action"],
            "Qualifications uniquement",
        )

        self.assertEqual(
            ligne["operations"],
            [{
                "action": "attribuer",
                "competence": self.competence.nom,
            }],
        )

    def test_retrait_qualification(self):
        self.ligne["operations_qualifications"] = [{
            "action": "retirer",
            "competence_id": self.competence.pk,
            "attribution_id": 1,
        }]

        operation = self.presenter()["operations"][0]

        self.assertEqual(operation["action"], "retirer")
        self.assertEqual(
            operation["competence"],
            self.competence.nom,
        )

    def test_changement_email(self):
        self.ligne["changement_email"] = True

        self.assertTrue(
            self.presenter()["changement_email"]
        )

    def test_previsualisation_non_modifiee(self):
        original = deepcopy(self.previsualisation)

        self.presenter()

        self.assertEqual(
            self.previsualisation,
            original,
        )

    def test_nombre_requetes_constant(self):
        self.previsualisation["lignes"] = [
            deepcopy(self.ligne)
            for _ in range(100)
        ]

        with self.assertNumQueries(3):
            resultat = presenter_import_agents(
                self.previsualisation
            )

        self.assertEqual(len(resultat), 100)

    def test_previsualisation_vide(self):
        self.assertEqual(
            presenter_import_agents({"lignes": []}),
            [],
        )
