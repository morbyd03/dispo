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


class VerificationPrevisualisationTests(TestCase):

    def setUp(self):
        from .services.import_agents import (
            previsualiser_import_agents,
            empreinte_previsualisation,
        )

        self.contenu = (
            b"matricule;nom;prenom;grade;email;cod1\n"
            b"000123;Dupont;Jean;SAP1;jean@example.com;1\n"
        )

        self.resultat = previsualiser_import_agents(
            self.contenu
        )

        self.empreinte = empreinte_previsualisation(
            self.resultat
        )

    def verifier(self):
        from .services.import_agents import (
            verifier_previsualisation_import,
        )

        return verifier_previsualisation_import(
            contenu=self.contenu,
            empreinte_attendue=self.empreinte,
        )

    def test_empreinte_stable(self):
        from .services.import_agents import (
            previsualiser_import_agents,
            empreinte_previsualisation,
        )

        nouvelle = previsualiser_import_agents(
            self.contenu
        )

        self.assertEqual(
            empreinte_previsualisation(nouvelle),
            self.empreinte,
        )

    def test_previsualisation_valide(self):
        self.assertEqual(
            self.verifier(),
            self.resultat,
        )

    def test_fichier_modifie(self):
        self.contenu = self.contenu.replace(
            b"Dupont",
            b"Martin",
        )

        with self.assertRaises(ValidationError):
            self.verifier()

    def test_compte_cree_entretemps(self):
        from django.contrib.auth import get_user_model

        get_user_model().objects.create(
            username="000123",
            email="jean@example.com",
        )

        with self.assertRaises(ValidationError):
            self.verifier()

    def test_grade_desactive_entretemps(self):
        from .models import Grade

        Grade.objects.filter(
            code="SAP1"
        ).update(active=False)

        with self.assertRaises(ValidationError):
            self.verifier()

    def test_collision_email_entretemps(self):
        from django.contrib.auth import get_user_model

        get_user_model().objects.create(
            username="999999",
            email="jean@example.com",
        )

        with self.assertRaises(ValidationError):
            self.verifier()

    def test_empreinte_invalide(self):
        for valeur in (None, "", "invalide", "z" * 64):
            with self.subTest(valeur=valeur):
                self.empreinte = valeur

                with self.assertRaises(ValidationError):
                    self.verifier()

    def test_absence_ecriture(self):
        from django.contrib.auth import get_user_model
        from .models import ProfilAgent, JournalAction

        self.verifier()

        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(ProfilAgent.objects.exists())
        self.assertFalse(JournalAction.objects.exists())


class ConfirmationImportAgentsTests(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        self.admin = User.objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.autre_admin = User.objects.create(
            username="administrateur2",
            is_superuser=True,
        )

        self.agent = User.objects.create(
            username="999999"
        )

        self.contenu = (
            b"matricule;nom;prenom;grade;email\n"
            b"000123;Dupont;Jean;SAP1;jean@example.com\n"
        )

    def preparer(self, utilisateur=None):
        from .services.import_agents import (
            preparer_confirmation_import,
        )

        return preparer_confirmation_import(
            contenu=self.contenu,
            utilisateur_id=(utilisateur or self.admin).pk,
        )

    def verifier(self, jeton, utilisateur=None):
        from .services.import_agents import (
            verifier_confirmation_import,
        )

        return verifier_confirmation_import(
            contenu=self.contenu,
            utilisateur_id=(utilisateur or self.admin).pk,
            jeton=jeton,
        )

    def test_confirmation_valide(self):
        preparation = self.preparer()

        self.assertIsNotNone(preparation["jeton"])

        self.assertEqual(
            self.verifier(preparation["jeton"]),
            preparation["previsualisation"],
        )

    def test_preparation_non_autorisee(self):
        from django.core.exceptions import PermissionDenied

        with self.assertRaises(PermissionDenied):
            self.preparer(self.agent)

    def test_confirmation_autre_utilisateur(self):
        from django.core.exceptions import PermissionDenied

        preparation = self.preparer()

        with self.assertRaises(PermissionDenied):
            self.verifier(
                preparation["jeton"],
                self.autre_admin,
            )

    def test_jeton_altere(self):
        preparation = self.preparer()

        with self.assertRaises(ValidationError):
            self.verifier(preparation["jeton"] + "x")

    def test_jeton_expire(self):
        import time
        from unittest.mock import patch

        preparation = self.preparer()

        with patch(
            "django.core.signing.time.time",
            return_value=time.time() + 1801,
        ):
            with self.assertRaises(ValidationError):
                self.verifier(preparation["jeton"])

    def test_fichier_modifie(self):
        preparation = self.preparer()

        self.contenu += b"\n"

        with self.assertRaises(ValidationError):
            self.verifier(preparation["jeton"])

    def test_retrait_autorisation(self):
        from django.core.exceptions import PermissionDenied

        preparation = self.preparer()

        self.admin.is_superuser = False
        self.admin.save(update_fields=["is_superuser"])

        with self.assertRaises(PermissionDenied):
            self.verifier(preparation["jeton"])

    def test_compte_desactive(self):
        from django.core.exceptions import PermissionDenied

        preparation = self.preparer()

        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            self.verifier(preparation["jeton"])

    def test_import_invalide_sans_jeton(self):
        self.contenu = self.contenu.replace(
            b"SAP1",
            b"INCONNU",
        )

        preparation = self.preparer()

        self.assertFalse(
            preparation["previsualisation"]["valide"]
        )
        self.assertIsNone(preparation["jeton"])

    def test_absence_ecriture(self):
        from .models import ProfilAgent, JournalAction

        preparation = self.preparer()
        self.verifier(preparation["jeton"])

        self.assertFalse(ProfilAgent.objects.exists())
        self.assertFalse(JournalAction.objects.exists())


class ConcurrenceImportAgentsTests(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
        from .models import (
            Grade,
            ProfilAgent,
            Competence,
            CompetenceAgent,
        )
        from .services.import_agents import (
            preparer_confirmation_import,
        )

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
            telephone="0600000000",
        )

        self.attribution = CompetenceAgent.objects.create(
            profil=self.profil,
            competence=Competence.objects.get(code="cod1"),
        )

        self.contenu = (
            b"matricule;nom;prenom;grade;cod1\n"
            b"000123;Dupont;Jean;SAP1;0\n"
        )

        preparation = preparer_confirmation_import(
            contenu=self.contenu,
            utilisateur_id=self.admin.pk,
        )

        self.jeton = preparation["jeton"]

    def verifier(self):
        from .services.import_agents import (
            verifier_confirmation_import,
        )

        return verifier_confirmation_import(
            contenu=self.contenu,
            utilisateur_id=self.admin.pk,
            jeton=self.jeton,
        )

    def test_etat_initial_inchange(self):
        self.assertTrue(self.verifier()["valide"])

    def test_desactivation_agent(self):
        self.agent.is_active = False
        self.agent.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            self.verifier()

    def test_modification_dates_qualification(self):
        from datetime import date

        self.attribution.date_expiration = date(2027, 1, 1)
        self.attribution.save(update_fields=["date_expiration"])

        with self.assertRaises(ValidationError):
            self.verifier()

    def test_modification_validateur(self):
        self.attribution.valide_par = self.admin
        self.attribution.save(update_fields=["valide_par"])

        with self.assertRaises(ValidationError):
            self.verifier()

    def test_ajout_autre_qualification(self):
        from .models import Competence, CompetenceAgent

        CompetenceAgent.objects.create(
            profil=self.profil,
            competence=Competence.objects.get(code="fdf1"),
        )

        with self.assertRaises(ValidationError):
            self.verifier()

    def test_modification_telephone(self):
        self.profil.telephone = "0612345678"
        self.profil.save(update_fields=["telephone"])

        with self.assertRaises(ValidationError):
            self.verifier()

    def test_modification_fonctions(self):
        from .models import FonctionAgent

        fonction = FonctionAgent.objects.create(
            nom="Fonction de test"
        )

        self.profil.fonctions.add(fonction)

        with self.assertRaises(ValidationError):
            self.verifier()


class ConsommationConfirmationTests(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model

        self.admin = get_user_model().objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.contenu = (
            b"matricule;nom;prenom;grade;email\n"
            b"000123;Dupont;Jean;SAP1;jean@example.com\n"
        )

    def preparer(self):
        from .services.import_agents import (
            preparer_confirmation_import,
        )

        return preparer_confirmation_import(
            contenu=self.contenu,
            utilisateur_id=self.admin.pk,
        )

    def consommer(self, jeton):
        from .services.import_agents import (
            consommer_confirmation_import,
        )

        return consommer_confirmation_import(
            contenu=self.contenu,
            utilisateur_id=self.admin.pk,
            jeton=jeton,
        )

    def test_jetons_distincts(self):
        premier = self.preparer()
        second = self.preparer()

        self.assertNotEqual(
            premier["jeton"],
            second["jeton"],
        )

    def test_consommation_confirmation(self):
        from .models import ConfirmationImport

        preparation = self.preparer()

        resultat = self.consommer(preparation["jeton"])

        self.assertTrue(resultat["valide"])

        confirmation = ConfirmationImport.objects.get()

        self.assertEqual(confirmation.auteur, self.admin)
        self.assertEqual(len(confirmation.empreinte), 64)

    def test_rejeu_interdit(self):
        from .models import ConfirmationImport

        preparation = self.preparer()

        self.consommer(preparation["jeton"])

        with self.assertRaises(ValidationError):
            self.consommer(preparation["jeton"])

        self.assertEqual(
            ConfirmationImport.objects.count(),
            1,
        )

    def test_annulation_transactionnelle(self):
        from django.db import transaction
        from .models import ConfirmationImport

        preparation = self.preparer()

        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.consommer(preparation["jeton"])
                raise RuntimeError("Erreur simulee")

        self.assertFalse(
            ConfirmationImport.objects.exists()
        )

        self.consommer(preparation["jeton"])

        self.assertEqual(
            ConfirmationImport.objects.count(),
            1,
        )

    def test_jeton_invalide_non_consomme(self):
        from .models import ConfirmationImport

        with self.assertRaises(ValidationError):
            self.consommer("jeton-invalide")

        self.assertFalse(
            ConfirmationImport.objects.exists()
        )

    def test_verification_apres_consommation(self):
        from .services.import_agents import (
            verifier_confirmation_import,
        )

        preparation = self.preparer()

        self.consommer(preparation["jeton"])

        with self.assertRaises(ValidationError):
            verifier_confirmation_import(
                contenu=self.contenu,
                utilisateur_id=self.admin.pk,
                jeton=preparation["jeton"],
            )

    def test_unicite_en_base(self):
        from django.db import IntegrityError, transaction
        from .models import ConfirmationImport

        ConfirmationImport.objects.create(
            empreinte="a" * 64,
            auteur=self.admin,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ConfirmationImport.objects.create(
                    empreinte="a" * 64,
                    auteur=self.admin,
                )


class ExecutionImportAgentsTests(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model

        self.User = get_user_model()

        self.admin = self.User.objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.contenu = (
            b"matricule;nom;prenom;grade;email;cod1\n"
            b"000123;Dupont;Jean;SAP1;jean@example.com;1\n"
            b"000124;Martin;Paul;CPL;paul@example.com;0\n"
        )

    def preparer(self):
        from .services.import_agents import (
            preparer_confirmation_import,
        )

        preparation = preparer_confirmation_import(
            contenu=self.contenu,
            utilisateur_id=self.admin.pk,
        )

        self.assertTrue(
            preparation["previsualisation"]["valide"]
        )

        return preparation["jeton"]

    def executer(self, jeton):
        from .services.import_agents import (
            executer_import_agents,
        )

        return executer_import_agents(
            contenu=self.contenu,
            utilisateur_id=self.admin.pk,
            jeton=jeton,
        )

    def test_creation_collective(self):
        from .models import ProfilAgent

        bilan = self.executer(self.preparer())

        self.assertEqual(bilan["creations"], 2)
        self.assertEqual(ProfilAgent.objects.count(), 2)
        self.assertEqual(self.User.objects.count(), 3)

    def test_attribution_qualifications(self):
        from .models import CompetenceAgent

        bilan = self.executer(self.preparer())

        self.assertEqual(
            bilan["qualifications_attribuees"],
            1,
        )

        attribution = CompetenceAgent.objects.get()

        self.assertEqual(
            attribution.profil.utilisateur.username,
            "000123",
        )
        self.assertEqual(attribution.valide_par, self.admin)

    def test_comptes_sans_mot_de_passe(self):
        self.executer(self.preparer())

        for utilisateur in self.User.objects.exclude(
            pk=self.admin.pk
        ):
            self.assertFalse(
                utilisateur.has_usable_password()
            )
            self.assertFalse(utilisateur.is_staff)
            self.assertFalse(utilisateur.is_superuser)

    def test_journalisation(self):
        from .models import JournalAction

        self.executer(self.preparer())

        self.assertEqual(
            JournalAction.objects.filter(
                action="agent.importer"
            ).count(),
            2,
        )

        self.assertEqual(
            JournalAction.objects.filter(
                action="competence.attribuer"
            ).count(),
            1,
        )

    def test_rejeu_interdit(self):
        from .models import ConfirmationImport

        jeton = self.preparer()

        self.executer(jeton)

        with self.assertRaises(ValidationError):
            self.executer(jeton)

        self.assertEqual(self.User.objects.count(), 3)
        self.assertEqual(
            ConfirmationImport.objects.count(),
            1,
        )

    def test_annulation_complete(self):
        from unittest.mock import patch
        from django.db import IntegrityError
        from .models import (
            ProfilAgent,
            CompetenceAgent,
            JournalAction,
            ConfirmationImport,
        )

        jeton = self.preparer()

        with patch(
            "planning.services.journal.JournalAction.objects.create",
            side_effect=IntegrityError("Erreur simulee"),
        ):
            with self.assertRaises(ValidationError):
                self.executer(jeton)

        self.assertEqual(self.User.objects.count(), 1)
        self.assertFalse(ProfilAgent.objects.exists())
        self.assertFalse(CompetenceAgent.objects.exists())
        self.assertFalse(JournalAction.objects.exists())
        self.assertFalse(ConfirmationImport.objects.exists())

        bilan = self.executer(jeton)

        self.assertEqual(bilan["creations"], 2)

    def test_import_mixte_creation_rattachement(self):
        from .models import ProfilAgent, ConfirmationImport

        compte = self.User.objects.create(
            username="000124",
            first_name="Paul",
            last_name="Martin",
            email="paul@example.com",
        )

        bilan = self.executer(self.preparer())

        self.assertEqual(bilan["creations"], 1)
        self.assertEqual(bilan["rattachements"], 1)
        self.assertEqual(self.User.objects.count(), 3)
        self.assertEqual(ProfilAgent.objects.count(), 2)

        profil = ProfilAgent.objects.get(utilisateur=compte)

        self.assertEqual(profil.grade.code, "CPL")
        self.assertEqual(ConfirmationImport.objects.count(), 1)

    def test_aucun_email_envoye(self):
        from django.core import mail

        self.executer(self.preparer())

        self.assertEqual(len(mail.outbox), 0)


class ModificationImportAgentsTests(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
        from .models import Grade, ProfilAgent

        User = get_user_model()

        self.admin = User.objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.agent = User.objects.create_user(
            username="000123",
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
            password="mot-de-passe-fictif",
            is_active=False,
        )

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.agent,
            grade=Grade.objects.get(code="SAP1"),
            telephone="0600000000",
        )

        self.contenu = (
            b"matricule;nom;prenom;grade;email;telephone;cod1\n"
            b"000123;Dupont;Jean;CPL;jean@example.com;0612345678;1\n"
        )

    def executer(self):
        from .services.import_agents import (
            preparer_confirmation_import,
            executer_import_agents,
        )

        preparation = preparer_confirmation_import(
            contenu=self.contenu,
            utilisateur_id=self.admin.pk,
        )

        self.assertTrue(
            preparation["previsualisation"]["valide"]
        )

        return executer_import_agents(
            contenu=self.contenu,
            utilisateur_id=self.admin.pk,
            jeton=preparation["jeton"],
        )

    def test_modification_profil(self):
        bilan = self.executer()

        self.profil.refresh_from_db()

        self.assertEqual(bilan["creations"], 0)
        self.assertEqual(bilan["modifications"], 1)
        self.assertEqual(self.profil.grade.code, "CPL")
        self.assertEqual(
            self.profil.telephone,
            "0612345678",
        )

    def test_preservation_compte(self):
        ancien_mot_de_passe = self.agent.password

        self.executer()

        self.agent.refresh_from_db()

        self.assertEqual(
            self.agent.password,
            ancien_mot_de_passe,
        )
        self.assertEqual(self.agent.username, "000123")
        self.assertEqual(self.agent.email, "jean@example.com")
        self.assertFalse(self.agent.is_active)
        self.assertFalse(self.agent.is_staff)
        self.assertFalse(self.agent.is_superuser)

    def test_attribution_qualification(self):
        from .models import CompetenceAgent

        bilan = self.executer()

        self.assertEqual(
            bilan["qualifications_attribuees"],
            1,
        )

        self.assertTrue(
            CompetenceAgent.objects.filter(
                profil=self.profil,
                competence__code="cod1",
            ).exists()
        )

    def test_import_sans_changement(self):
        from .models import JournalAction

        self.contenu = self.contenu.replace(
            b"CPL;jean@example.com;0612345678;1",
            b"SAP1;jean@example.com;0600000000;",
        )

        bilan = self.executer()

        self.assertEqual(bilan["modifications"], 0)
        self.assertEqual(bilan["inchanges"], 1)
        self.assertFalse(JournalAction.objects.exists())

    def test_changement_email_refuse(self):
        from .models import ConfirmationImport

        self.contenu = self.contenu.replace(
            b"jean@example.com",
            b"nouveau@example.com",
        )

        with self.assertRaises(ValidationError):
            self.executer()

        self.agent.refresh_from_db()
        self.profil.refresh_from_db()

        self.assertEqual(self.agent.email, "jean@example.com")
        self.assertEqual(self.profil.grade.code, "SAP1")
        self.assertFalse(ConfirmationImport.objects.exists())

    def test_retrait_qualification_non_confirme(self):
        from .models import (
            Competence,
            CompetenceAgent,
            ConfirmationImport,
        )

        CompetenceAgent.objects.create(
            profil=self.profil,
            competence=Competence.objects.get(code="cod1"),
        )

        self.contenu = self.contenu.replace(
            b";1\n",
            b";0\n",
        )

        with self.assertRaises(ValidationError):
            self.executer()

        self.assertEqual(CompetenceAgent.objects.count(), 1)
        self.assertFalse(ConfirmationImport.objects.exists())

    def test_journalisation_modification(self):
        from .models import JournalAction

        self.executer()

        journal = JournalAction.objects.get(
            action="agent.importer"
        )

        self.assertEqual(journal.auteur, self.admin)
        self.assertEqual(
            journal.details["operation"],
            "modifier",
        )
        self.assertIn(
            "grade_id",
            journal.details["changements"],
        )


class RattachementImportAgentsTests(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        self.admin = User.objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.agent = User.objects.create_user(
            username="000123",
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
            password="mot-de-passe-fictif",
            is_active=False,
        )

        self.contenu = (
            b"matricule;nom;prenom;grade;email;cod1\n"
            b"000123;Dupont;Jean;CPL;jean@example.com;1\n"
        )

    def executer(self):
        from .services.import_agents import (
            preparer_confirmation_import,
            executer_import_agents,
        )

        preparation = preparer_confirmation_import(
            contenu=self.contenu,
            utilisateur_id=self.admin.pk,
        )

        self.assertTrue(
            preparation["previsualisation"]["valide"]
        )

        return executer_import_agents(
            contenu=self.contenu,
            utilisateur_id=self.admin.pk,
            jeton=preparation["jeton"],
        )

    def test_rattachement_profil(self):
        from .models import ProfilAgent

        bilan = self.executer()

        profil = ProfilAgent.objects.get(
            utilisateur=self.agent
        )

        self.assertEqual(bilan["rattachements"], 1)
        self.assertEqual(bilan["creations"], 0)
        self.assertEqual(profil.grade.code, "CPL")

    def test_conservation_compte_historique(self):
        ancien_mot_de_passe = self.agent.password
        ancien_identifiant = self.agent.pk

        self.executer()

        self.agent.refresh_from_db()

        self.assertEqual(self.agent.pk, ancien_identifiant)
        self.assertEqual(self.agent.password, ancien_mot_de_passe)
        self.assertEqual(self.agent.username, "000123")
        self.assertEqual(self.agent.email, "jean@example.com")
        self.assertFalse(self.agent.is_active)

    def test_attribution_qualification(self):
        from .models import CompetenceAgent

        bilan = self.executer()

        attribution = CompetenceAgent.objects.get()

        self.assertEqual(
            attribution.profil.utilisateur,
            self.agent,
        )

        self.assertEqual(
            bilan["qualifications_attribuees"],
            1,
        )

    def test_journalisation_rattachement(self):
        from .models import JournalAction

        self.executer()

        journal = JournalAction.objects.get(
            action="agent.importer"
        )

        self.assertEqual(
            journal.details["operation"],
            "rattacher",
        )

        self.assertEqual(journal.auteur, self.admin)

    def test_changement_email_refuse(self):
        from .models import ProfilAgent, ConfirmationImport

        self.contenu = self.contenu.replace(
            b"jean@example.com",
            b"nouveau@example.com",
        )

        with self.assertRaises(ValidationError):
            self.executer()

        self.assertFalse(ProfilAgent.objects.exists())
        self.assertFalse(ConfirmationImport.objects.exists())

    def test_annulation_rattachement(self):
        from unittest.mock import patch
        from django.db import IntegrityError
        from .models import (
            ProfilAgent,
            JournalAction,
            ConfirmationImport,
        )

        with patch(
            "planning.services.journal.JournalAction.objects.create",
            side_effect=IntegrityError("Erreur simulee"),
        ):
            with self.assertRaises(ValidationError):
                self.executer()

        self.assertFalse(ProfilAgent.objects.exists())
        self.assertFalse(JournalAction.objects.exists())
        self.assertFalse(ConfirmationImport.objects.exists())

        self.agent.refresh_from_db()
        self.assertEqual(self.agent.username, "000123")


class RetraitsImportAgentsTests(TestCase):

    def setUp(self):
        from datetime import date
        from django.contrib.auth import get_user_model
        from .models import (
            Grade,
            ProfilAgent,
            Competence,
            CompetenceAgent,
        )

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
            date_validation=date(2026, 1, 1),
            date_expiration=date(2027, 1, 1),
        )

        self.contenu = (
            b"matricule;nom;prenom;grade;cod1\n"
            b"000123;Dupont;Jean;SAP1;0\n"
        )

    def preparer(self):
        from .services.import_agents import (
            preparer_confirmation_import,
        )

        preparation = preparer_confirmation_import(
            contenu=self.contenu,
            utilisateur_id=self.admin.pk,
        )

        self.assertTrue(
            preparation["previsualisation"]["valide"]
        )

        return preparation["jeton"]

    def executer(self, jeton, confirmation=False):
        from .services.import_agents import (
            executer_import_agents,
        )

        return executer_import_agents(
            contenu=self.contenu,
            utilisateur_id=self.admin.pk,
            jeton=jeton,
            confirmer_retraits=confirmation,
        )

    def test_retrait_confirme(self):
        from .models import CompetenceAgent

        bilan = self.executer(
            self.preparer(),
            confirmation=True,
        )

        self.assertEqual(
            bilan["qualifications_retirees"],
            1,
        )
        self.assertFalse(CompetenceAgent.objects.exists())

    def test_retrait_non_confirme(self):
        from .models import (
            CompetenceAgent,
            ConfirmationImport,
        )

        with self.assertRaises(ValidationError):
            self.executer(self.preparer())

        self.assertEqual(CompetenceAgent.objects.count(), 1)
        self.assertFalse(ConfirmationImport.objects.exists())

    def test_confirmation_non_booleenne(self):
        for valeur in ("true", "1", 1, None):
            with self.subTest(valeur=valeur):
                with self.assertRaises(ValidationError):
                    self.executer(
                        self.preparer(),
                        confirmation=valeur,
                    )

    def test_qualification_conservee_si_cellule_vide(self):
        from .models import CompetenceAgent

        self.contenu = self.contenu.replace(
            b";0\n",
            b";\n",
        )

        bilan = self.executer(self.preparer())

        self.assertEqual(
            bilan["qualifications_retirees"],
            0,
        )
        self.assertEqual(CompetenceAgent.objects.count(), 1)

    def test_journalisation_retrait(self):
        from .models import JournalAction

        self.executer(
            self.preparer(),
            confirmation=True,
        )

        journal = JournalAction.objects.get(
            action="competence.retirer"
        )

        self.assertEqual(journal.auteur, self.admin)
        self.assertEqual(
            journal.details["date_validation"],
            "2026-01-01",
        )
        self.assertEqual(
            journal.details["date_expiration"],
            "2027-01-01",
        )

    def test_annulation_retrait(self):
        from unittest.mock import patch
        from django.db import IntegrityError
        from .models import (
            CompetenceAgent,
            JournalAction,
            ConfirmationImport,
        )

        jeton = self.preparer()

        with patch(
            "planning.services.journal.JournalAction.objects.create",
            side_effect=IntegrityError("Erreur simulee"),
        ):
            with self.assertRaises(ValidationError):
                self.executer(jeton, confirmation=True)

        self.assertEqual(CompetenceAgent.objects.count(), 1)
        self.assertFalse(JournalAction.objects.exists())
        self.assertFalse(ConfirmationImport.objects.exists())

    def test_confirmation_apres_refus(self):
        jeton = self.preparer()

        with self.assertRaises(ValidationError):
            self.executer(jeton)

        bilan = self.executer(
            jeton,
            confirmation=True,
        )

        self.assertEqual(
            bilan["qualifications_retirees"],
            1,
        )
