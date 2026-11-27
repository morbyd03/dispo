from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from .services.import_agents import lire_csv_agents


class LectureImportAgentsTests(SimpleTestCase):

    def test_csv_point_virgule(self):
        resultat = lire_csv_agents(
            b"matricule;nom;prenom;grade\n"
            b"000123;Dupont;Jean;SAP1\n"
        )

        donnees = resultat["lignes"][0]["donnees"]

        self.assertEqual(donnees["matricule"], "000123")
        self.assertEqual(donnees["grade"], "SAP1")

    def test_csv_virgule(self):
        resultat = lire_csv_agents(
            b"matricule,nom,prenom,grade\n"
            b"000123,Dupont,Jean,SAP1\n"
        )

        self.assertEqual(len(resultat["lignes"]), 1)

    def test_utf8_bom_et_accents(self):
        contenu = (
            "matricule;nom;prenom;grade\n"
            "000123;D'Évrard;François;CPL\n"
        ).encode("utf-8-sig")

        resultat = lire_csv_agents(contenu)
        donnees = resultat["lignes"][0]["donnees"]

        self.assertEqual(donnees["nom"], "D'Évrard")
        self.assertEqual(donnees["prenom"], "François")

    def test_colonne_obligatoire_manquante(self):
        with self.assertRaises(ValidationError):
            lire_csv_agents(
                b"matricule;nom;prenom\n"
                b"000123;Dupont;Jean\n"
            )

    def test_colonnes_dupliquees(self):
        with self.assertRaises(ValidationError):
            lire_csv_agents(
                b"matricule;nom;prenom;grade;nom\n"
                b"000123;Dupont;Jean;SAP1;Dupont\n"
            )

    def test_ligne_incomplete(self):
        with self.assertRaises(ValidationError):
            lire_csv_agents(
                b"matricule;nom;prenom;grade\n"
                b"000123;Dupont;Jean\n"
            )

    def test_fichier_vide(self):
        with self.assertRaises(ValidationError):
            lire_csv_agents(b"")

    def test_fichier_sans_agent(self):
        with self.assertRaises(ValidationError):
            lire_csv_agents(
                b"matricule;nom;prenom;grade\n"
            )

    def test_encodage_invalide(self):
        with self.assertRaises(ValidationError):
            lire_csv_agents(b"\xff\xfe")

    def test_colonne_qualification_conservee(self):
        resultat = lire_csv_agents(
            b"matricule;nom;prenom;grade;cod1\n"
            b"000123;Dupont;Jean;SAP1;1\n"
        )

        self.assertEqual(
            resultat["lignes"][0]["donnees"]["cod1"],
            "1",
        )


class GenerationEmailTests(SimpleTestCase):

    def generer(self, **modifications):
        from .services.import_agents import generer_email_agent

        donnees = {
            "nom": "Dupont",
            "prenom": "Jean",
            "matricule": "000123",
            "modele": "{prenom}.{nom}@example.com",
        }

        donnees.update(modifications)

        return generer_email_agent(**donnees)

    def test_generation_standard(self):
        self.assertEqual(
            self.generer(),
            "jean.dupont@example.com",
        )

    def test_accents(self):
        self.assertEqual(
            self.generer(prenom="François", nom="Évrard"),
            "francois.evrard@example.com",
        )

    def test_noms_composes(self):
        self.assertEqual(
            self.generer(prenom="Jean-Pierre", nom="Le Gall"),
            "jean-pierre.le-gall@example.com",
        )

    def test_apostrophe(self):
        self.assertEqual(
            self.generer(nom="D’Évrard"),
            "jean.devrard@example.com",
        )

    def test_ligatures(self):
        self.assertEqual(
            self.generer(nom="Lœuil"),
            "jean.loeuil@example.com",
        )

    def test_modele_personnalise(self):
        self.assertEqual(
            self.generer(
                modele="{matricule}@autre.example.com"
            ),
            "000123@autre.example.com",
        )

    def test_modele_absent(self):
        with self.assertRaises(ValidationError):
            self.generer(modele="")

    def test_modele_invalide(self):
        for modele in (
            "{inconnu}@example.com",
            "{nom.__class__}@example.com",
            "{nom!r}@example.com",
            "{nom:>20}@example.com",
            "{prenom",
            "{nom}",
        ):
            with self.subTest(modele=modele):
                with self.assertRaises(ValidationError):
                    self.generer(modele=modele)


from django.test import TestCase


class ColonnesImportAgentsTests(TestCase):

    def setUp(self):
        from .models import Competence

        self.competence = Competence.objects.get(code="cod1")

        self.colonnes = [
            "matricule", "nom", "prenom", "grade"
        ]

    def analyser(self, colonnes):
        from .services.import_agents import analyser_colonnes_import

        return analyser_colonnes_import(colonnes)

    def test_colonnes_standard(self):
        self.assertEqual(
            self.analyser(self.colonnes),
            {},
        )

    def test_qualification_reconnue(self):
        self.assertEqual(
            self.analyser(self.colonnes + ["cod1"]),
            {"cod1": self.competence.pk},
        )

    def test_qualification_personnalisee(self):
        from .models import Competence

        competence = Competence.objects.create(
            code="qualification-test",
            nom="Qualification de test",
            active=True,
        )

        self.assertEqual(
            self.analyser(
                self.colonnes + ["qualification-test"]
            ),
            {"qualification-test": competence.pk},
        )

    def test_colonne_inconnue(self):
        with self.assertRaises(ValidationError):
            self.analyser(self.colonnes + ["cod11"])

    def test_qualification_inactive(self):
        self.competence.active = False
        self.competence.save(update_fields=["active"])

        with self.assertRaises(ValidationError):
            self.analyser(self.colonnes + ["cod1"])

    def test_collision_colonne_reservee(self):
        from .models import Competence

        Competence.objects.create(
            code="grade",
            nom="Qualification en collision",
        )

        with self.assertRaises(ValidationError):
            self.analyser(self.colonnes)

    def test_code_ambigu(self):
        from .models import Competence

        Competence.objects.create(
            code="COD1",
            nom="Qualification ambigue",
        )

        with self.assertRaises(ValidationError):
            self.analyser(self.colonnes + ["cod1"])

    def test_valeurs_qualifications(self):
        from .services.import_agents import (
            analyser_qualifications_import,
        )

        colonnes = {"cod1": self.competence.pk}

        for valeur, attendu in (
            ("1", {self.competence.pk: True}),
            ("0", {self.competence.pk: False}),
            ("", {}),
        ):
            with self.subTest(valeur=valeur):
                self.assertEqual(
                    analyser_qualifications_import(
                        {"cod1": valeur},
                        colonnes,
                    ),
                    attendu,
                )

    def test_valeur_qualification_invalide(self):
        from .services.import_agents import (
            analyser_qualifications_import,
        )

        with self.assertRaises(ValidationError):
            analyser_qualifications_import(
                {"cod1": "oui"},
                {"cod1": self.competence.pk},
            )


class IdentitesImportAgentsTests(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model

        self.User = get_user_model()

        self.donnees = {
            "matricule": "000123",
            "nom": "Dupont",
            "prenom": "Jean",
            "grade": "sap1",
        }

    def analyser(self):
        from .services.import_agents import analyser_identite_import

        return analyser_identite_import(
            self.donnees,
            modele_email="{prenom}.{nom}@example.com",
        )

    def test_nouvel_agent(self):
        resultat = self.analyser()

        self.assertEqual(resultat["action"], "creer")
        self.assertEqual(resultat["matricule"], "000123")
        self.assertEqual(resultat["grade"], "SAP1")
        self.assertEqual(
            resultat["email"],
            "jean.dupont@example.com",
        )
        self.assertTrue(resultat["email_genere"])
        self.assertFalse(self.User.objects.exists())

    def test_email_explicite(self):
        self.donnees["email"] = "Autre@example.com"

        resultat = self.analyser()

        self.assertEqual(
            resultat["email"],
            "autre@example.com",
        )
        self.assertFalse(resultat["email_genere"])

    def test_grade_inconnu(self):
        self.donnees["grade"] = "INCONNU"

        with self.assertRaises(ValidationError):
            self.analyser()

    def test_grade_inactif(self):
        from .models import Grade

        Grade.objects.filter(code="SAP1").update(active=False)

        with self.assertRaises(ValidationError):
            self.analyser()

    def test_collision_email(self):
        self.User.objects.create(
            username="999999",
            email="jean.dupont@example.com",
        )

        with self.assertRaises(ValidationError):
            self.analyser()

    def test_compte_historique(self):
        utilisateur = self.User.objects.create(
            username="000123",
            email="historique@example.com",
        )

        resultat = self.analyser()

        self.assertEqual(resultat["action"], "rattacher")
        self.assertEqual(
            resultat["utilisateur_id"],
            utilisateur.pk,
        )
        self.assertEqual(
            resultat["email"],
            "historique@example.com",
        )
        self.assertFalse(resultat["email_genere"])

    def test_agent_existant(self):
        from .models import ProfilAgent

        utilisateur = self.User.objects.create(
            username="000123",
            email="historique@example.com",
        )

        profil = ProfilAgent.objects.create(
            utilisateur=utilisateur,
        )

        resultat = self.analyser()

        self.assertEqual(resultat["action"], "modifier")
        self.assertEqual(resultat["profil_id"], profil.pk)

    def test_changement_email_detecte(self):
        utilisateur = self.User.objects.create(
            username="000123",
            email="historique@example.com",
        )

        self.donnees["email"] = "nouveau@example.com"

        resultat = self.analyser()

        self.assertTrue(resultat["changement_email"])

        utilisateur.refresh_from_db()

        self.assertEqual(
            utilisateur.email,
            "historique@example.com",
        )

    def test_compte_protege(self):
        self.User.objects.create(
            username="000123",
            is_superuser=True,
        )

        with self.assertRaises(ValidationError):
            self.analyser()


class ProfilsImportAgentsTests(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
        from .models import Grade, FonctionAgent, ProfilAgent

        self.grade = Grade.objects.get(code="SAP1")

        self.fonction1 = FonctionAgent.objects.create(
            nom="Fonction A"
        )

        self.fonction2 = FonctionAgent.objects.create(
            nom="Fonction B"
        )

        self.profil = ProfilAgent.objects.create(
            utilisateur=get_user_model().objects.create(
                username="000123"
            ),
            grade=self.grade,
            telephone="0600000000",
        )

        self.profil.fonctions.add(self.fonction1)

        self.identite = {
            "grade_id": self.grade.pk,
            "profil_id": None,
        }

    def analyser(self, donnees):
        from .services.import_agents import analyser_profil_import

        return analyser_profil_import(
            donnees,
            self.identite,
        )

    def test_nouvel_agent_sans_coordonnees(self):
        resultat = self.analyser({})

        self.assertEqual(resultat["telephone"], "")
        self.assertEqual(resultat["fonctions_ids"], [])

    def test_telephone(self):
        resultat = self.analyser({
            "telephone": "0612345678",
        })

        self.assertEqual(
            resultat["telephone"],
            "0612345678",
        )

    def test_telephone_trop_long(self):
        with self.assertRaises(ValidationError):
            self.analyser({"telephone": "0" * 31})

    def test_fonction_unique(self):
        resultat = self.analyser({
            "fonction": "fonction a",
        })

        self.assertEqual(
            resultat["fonctions_ids"],
            [self.fonction1.pk],
        )

    def test_fonctions_multiples(self):
        resultat = self.analyser({
            "fonction": "Fonction A|Fonction B",
        })

        self.assertEqual(
            resultat["fonctions_ids"],
            sorted([
                self.fonction1.pk,
                self.fonction2.pk,
            ]),
        )

    def test_fonction_inconnue(self):
        with self.assertRaises(ValidationError):
            self.analyser({"fonction": "Inconnue"})

    def test_fonction_inactive(self):
        self.fonction2.active = False
        self.fonction2.save(update_fields=["active"])

        with self.assertRaises(ValidationError):
            self.analyser({"fonction": "Fonction B"})

    def test_conservation_colonnes_absentes(self):
        self.identite["profil_id"] = self.profil.pk

        resultat = self.analyser({})

        self.assertEqual(
            resultat["telephone"],
            "0600000000",
        )

        self.assertEqual(
            resultat["fonctions_ids"],
            [self.fonction1.pk],
        )

    def test_conservation_cellules_vides(self):
        self.identite["profil_id"] = self.profil.pk

        resultat = self.analyser({
            "telephone": "",
            "fonction": "",
        })

        self.assertEqual(
            resultat["telephone"],
            "0600000000",
        )

        self.assertEqual(
            resultat["fonctions_ids"],
            [self.fonction1.pk],
        )

    def test_modification_sans_ecriture(self):
        self.identite["profil_id"] = self.profil.pk

        resultat = self.analyser({
            "telephone": "0612345678",
            "fonction": "Fonction B",
        })

        self.assertEqual(
            resultat["fonctions_ids"],
            [self.fonction2.pk],
        )

        self.profil.refresh_from_db()

        self.assertEqual(
            self.profil.telephone,
            "0600000000",
        )

        self.assertEqual(
            list(self.profil.fonctions.all()),
            [self.fonction1],
        )


class PrevisualisationImportAgentsTests(TestCase):

    def previsualiser(self, lignes):
        from .services.import_agents import (
            previsualiser_import_agents,
        )

        contenu = (
            "matricule;nom;prenom;grade;email;cod1\n"
            + "\n".join(lignes)
            + "\n"
        ).encode("utf-8")

        return previsualiser_import_agents(
            contenu,
            modele_email="{prenom}.{nom}@example.com",
        )

    def test_import_valide(self):
        resultat = self.previsualiser([
            "000123;Dupont;Jean;SAP1;;1",
            "000124;Martin;Paul;CPL;;0",
        ])

        self.assertTrue(resultat["valide"])
        self.assertEqual(resultat["bilan"]["creer"], 2)
        self.assertEqual(len(resultat["lignes"]), 2)
        self.assertEqual(len(resultat["avertissements"]), 2)

    def test_matricule_duplique(self):
        resultat = self.previsualiser([
            "000123;Dupont;Jean;SAP1;;1",
            "000123;Martin;Paul;CPL;;0",
        ])

        self.assertFalse(resultat["valide"])
        self.assertEqual(len(resultat["erreurs"]), 1)
        self.assertEqual(resultat["erreurs"][0]["ligne"], 3)

    def test_email_duplique(self):
        resultat = self.previsualiser([
            "000123;Dupont;Jean;SAP1;test@example.com;1",
            "000124;Martin;Paul;CPL;TEST@example.com;0",
        ])

        self.assertFalse(resultat["valide"])
        self.assertEqual(len(resultat["erreurs"]), 1)

    def test_collision_emails_generes(self):
        resultat = self.previsualiser([
            "000123;Dupont;Jean;SAP1;;1",
            "000124;Dupont;Jean;CPL;;0",
        ])

        self.assertFalse(resultat["valide"])

    def test_collecte_erreurs_multiples(self):
        resultat = self.previsualiser([
            "000123;Dupont;Jean;INCONNU;;1",
            "000124;Martin;Paul;CPL;;oui",
            "000125;Durand;Marc;SAP1;;1",
        ])

        self.assertFalse(resultat["valide"])
        self.assertEqual(len(resultat["erreurs"]), 2)
        self.assertEqual(resultat["bilan"]["creer"], 1)

    def test_qualification_reconnue(self):
        from .models import Competence

        competence = Competence.objects.get(code="cod1")

        resultat = self.previsualiser([
            "000123;Dupont;Jean;SAP1;;1",
        ])

        self.assertEqual(
            resultat["lignes"][0]["qualifications"],
            {competence.pk: True},
        )

    def test_absence_ecriture(self):
        from django.contrib.auth import get_user_model
        from .models import (
            ProfilAgent,
            CompetenceAgent,
            JournalAction,
        )

        resultat = self.previsualiser([
            "000123;Dupont;Jean;SAP1;;1",
            "000124;Martin;Paul;CPL;;0",
        ])

        self.assertTrue(resultat["valide"])
        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(ProfilAgent.objects.exists())
        self.assertFalse(CompetenceAgent.objects.exists())
        self.assertFalse(JournalAction.objects.exists())

    def test_bilan_actions(self):
        from django.contrib.auth import get_user_model
        from .models import ProfilAgent

        User = get_user_model()

        User.objects.create(
            username="000124",
            email="paul.martin@example.com",
        )

        utilisateur = User.objects.create(
            username="000125",
            email="marc.durand@example.com",
        )

        ProfilAgent.objects.create(
            utilisateur=utilisateur,
        )

        resultat = self.previsualiser([
            "000123;Dupont;Jean;SAP1;;1",
            "000124;Martin;Paul;CPL;;0",
            "000125;Durand;Marc;SAP1;;",
        ])

        self.assertTrue(resultat["valide"])
        self.assertEqual(
            resultat["bilan"],
            {
                "creer": 1,
                "rattacher": 1,
                "modifier": 1,
            },
        )

    def test_avertissement_changement_email(self):
        from django.contrib.auth import get_user_model

        get_user_model().objects.create(
            username="000123",
            email="ancien@example.com",
        )

        resultat = self.previsualiser([
            "000123;Dupont;Jean;SAP1;nouveau@example.com;1",
        ])

        self.assertTrue(resultat["valide"])
        self.assertTrue(
            resultat["lignes"][0]["changement_email"]
        )
        self.assertEqual(len(resultat["avertissements"]), 1)


class ChangementsImportAgentsTests(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
        from .models import (
            Grade,
            ProfilAgent,
            Competence,
            CompetenceAgent,
        )

        self.utilisateur = get_user_model().objects.create(
            username="000123",
            first_name="Jean",
            last_name="Dupont",
            email="jean.dupont@example.com",
        )

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.utilisateur,
            grade=Grade.objects.get(code="SAP1"),
            telephone="0600000000",
        )

        self.competence = Competence.objects.get(code="cod1")

        self.attribution = CompetenceAgent.objects.create(
            profil=self.profil,
            competence=self.competence,
        )

    def analyser(self, qualification="", telephone="", grade="SAP1"):
        from .services.import_agents import (
            previsualiser_import_agents,
        )

        contenu = (
            "matricule;nom;prenom;grade;telephone;cod1\n"
            f"000123;Dupont;Jean;{grade};{telephone};{qualification}\n"
        ).encode("utf-8")

        resultat = previsualiser_import_agents(contenu)

        self.assertTrue(resultat["valide"])

        return resultat["lignes"][0]

    def test_agent_inchange(self):
        resultat = self.analyser()

        self.assertEqual(resultat["changements"], {})
        self.assertEqual(
            resultat["operations_qualifications"],
            [],
        )
        self.assertFalse(resultat["confirmation_retraits"])

    def test_changement_telephone(self):
        resultat = self.analyser(
            telephone="0612345678"
        )

        self.assertEqual(
            resultat["changements"]["telephone"],
            {
                "avant": "0600000000",
                "apres": "0612345678",
            },
        )

    def test_changement_grade(self):
        from .models import Grade

        resultat = self.analyser(grade="CPL")

        self.assertEqual(
            resultat["changements"]["grade_id"],
            {
                "avant": self.profil.grade_id,
                "apres": Grade.objects.get(code="CPL").pk,
            },
        )

    def test_qualification_conservee(self):
        resultat = self.analyser(qualification="1")

        self.assertEqual(
            resultat["operations_qualifications"],
            [],
        )

    def test_retrait_propose(self):
        resultat = self.analyser(qualification="0")

        self.assertTrue(resultat["confirmation_retraits"])
        self.assertEqual(
            resultat["operations_qualifications"],
            [{
                "action": "retirer",
                "competence_id": self.competence.pk,
                "attribution_id": self.attribution.pk,
            }],
        )

    def test_attribution_proposee(self):
        self.attribution.delete()

        resultat = self.analyser(qualification="1")

        self.assertEqual(
            resultat["operations_qualifications"],
            [{
                "action": "attribuer",
                "competence_id": self.competence.pk,
            }],
        )

        self.assertFalse(resultat["confirmation_retraits"])

    def test_absence_ecriture(self):
        from .models import CompetenceAgent, JournalAction

        self.analyser(
            qualification="0",
            telephone="0612345678",
            grade="CPL",
        )

        self.profil.refresh_from_db()

        self.assertEqual(self.profil.grade.code, "SAP1")
        self.assertEqual(self.profil.telephone, "0600000000")
        self.assertTrue(
            CompetenceAgent.objects.filter(
                pk=self.attribution.pk
            ).exists()
        )
        self.assertFalse(JournalAction.objects.exists())
