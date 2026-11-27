from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import (
    ProfilAgent,
    Competence,
    CompetenceAgent,
)
from .services.competences import attribuer_competence


class AttributionCompetenceTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.agent = User.objects.create(
            username="000123"
        )

        self.validateur = User.objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.agent
        )

        self.competence = Competence.objects.get(code="cod1")

        self.donnees = {
            "profil_id": self.profil.pk,
            "competence_id": self.competence.pk,
            "validateur_id": self.validateur.pk,
        }

    def test_attribution(self):
        attribution = attribuer_competence(**self.donnees)

        self.assertEqual(attribution.profil, self.profil)
        self.assertEqual(attribution.competence, self.competence)
        self.assertEqual(attribution.valide_par, self.validateur)

    def test_dates_facultatives(self):
        attribution = attribuer_competence(**self.donnees)

        self.assertIsNone(attribution.date_validation)
        self.assertIsNone(attribution.date_expiration)

    def test_dates_valides(self):
        attribution = attribuer_competence(
            **self.donnees,
            date_validation="2026-01-01",
            date_expiration="2027-01-01",
        )

        self.assertEqual(
            attribution.date_validation,
            date(2026, 1, 1),
        )
        self.assertEqual(
            attribution.date_expiration,
            date(2027, 1, 1),
        )

    def test_dates_inversees(self):
        with self.assertRaises(ValidationError):
            attribuer_competence(
                **self.donnees,
                date_validation="2027-01-01",
                date_expiration="2026-01-01",
            )

        self.assertFalse(CompetenceAgent.objects.exists())

    def test_date_invalide(self):
        with self.assertRaises(ValidationError):
            attribuer_competence(
                **self.donnees,
                date_validation="2026-02-30",
            )

    def test_attribution_dupliquee(self):
        attribuer_competence(**self.donnees)

        with self.assertRaises(ValidationError):
            attribuer_competence(**self.donnees)

        self.assertEqual(CompetenceAgent.objects.count(), 1)

    def test_competence_inactive(self):
        self.competence.active = False
        self.competence.save(update_fields=["active"])

        with self.assertRaises(ValidationError):
            attribuer_competence(**self.donnees)

    def test_profil_inexistant(self):
        self.donnees["profil_id"] = 999999

        with self.assertRaises(ValidationError):
            attribuer_competence(**self.donnees)

    def test_validateur_inactif(self):
        self.validateur.is_active = False
        self.validateur.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            attribuer_competence(**self.donnees)

    def test_attribution_non_autorisee(self):
        from django.core.exceptions import PermissionDenied

        self.donnees["validateur_id"] = self.agent.pk

        with self.assertRaises(PermissionDenied):
            attribuer_competence(**self.donnees)

        self.assertFalse(CompetenceAgent.objects.exists())


class ModificationCompetenceTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.agent = User.objects.create(
            username="000123"
        )

        self.validateur = User.objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.agent
        )

        self.competence = Competence.objects.get(code="cod1")

        self.attribution = CompetenceAgent.objects.create(
            profil=self.profil,
            competence=self.competence,
            valide_par=self.validateur,
        )

        self.donnees = {
            "attribution_id": self.attribution.pk,
            "validateur_id": self.validateur.pk,
            "date_validation": "2026-01-01",
            "date_expiration": "2027-01-01",
        }

    def test_modification_dates(self):
        from .services.competences import modifier_competence

        attribution = modifier_competence(**self.donnees)

        self.assertEqual(attribution.pk, self.attribution.pk)
        self.assertEqual(attribution.profil, self.profil)
        self.assertEqual(attribution.competence, self.competence)
        self.assertEqual(
            attribution.date_expiration,
            date(2027, 1, 1),
        )
        self.assertEqual(CompetenceAgent.objects.count(), 1)

    def test_dates_inversees(self):
        from .services.competences import modifier_competence

        self.donnees["date_expiration"] = "2025-01-01"

        with self.assertRaises(ValidationError):
            modifier_competence(**self.donnees)

        self.attribution.refresh_from_db()
        self.assertIsNone(self.attribution.date_validation)

    def test_modification_non_autorisee(self):
        from django.core.exceptions import PermissionDenied
        from .services.competences import modifier_competence

        self.donnees["validateur_id"] = self.agent.pk

        with self.assertRaises(PermissionDenied):
            modifier_competence(**self.donnees)

    def test_competence_historique_inactive(self):
        from .services.competences import modifier_competence

        self.competence.active = False
        self.competence.save(update_fields=["active"])

        attribution = modifier_competence(**self.donnees)

        self.assertEqual(attribution.pk, self.attribution.pk)

    def test_nouveau_validateur(self):
        from .services.competences import modifier_competence

        nouveau = get_user_model().objects.create(
            username="administrateur2",
            is_superuser=True,
        )

        self.donnees["validateur_id"] = nouveau.pk

        attribution = modifier_competence(**self.donnees)

        self.assertEqual(attribution.valide_par, nouveau)

    def test_absence_de_modification(self):
        from .services.competences import modifier_competence

        nouveau = get_user_model().objects.create(
            username="administrateur2",
            is_superuser=True,
        )

        self.donnees["validateur_id"] = nouveau.pk
        self.donnees["date_validation"] = None
        self.donnees["date_expiration"] = None

        attribution = modifier_competence(**self.donnees)

        self.assertEqual(attribution.valide_par, self.validateur)


class JournalCompetencesTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.agent = User.objects.create(
            username="000123"
        )

        self.validateur = User.objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.agent
        )

        self.competence = Competence.objects.get(code="cod1")

        self.donnees = {
            "profil_id": self.profil.pk,
            "competence_id": self.competence.pk,
            "validateur_id": self.validateur.pk,
        }

    def test_journal_attribution(self):
        from .models import JournalAction

        attribution = attribuer_competence(**self.donnees)

        journal = JournalAction.objects.get()

        self.assertEqual(journal.action, "competence.attribuer")
        self.assertEqual(journal.auteur, self.validateur)
        self.assertEqual(journal.objet_id, attribution.pk)
        self.assertEqual(
            journal.type_objet,
            "planning.competenceagent",
        )
        self.assertEqual(
            journal.details["profil_id"],
            self.profil.pk,
        )

    def test_journal_modification(self):
        from .models import JournalAction
        from .services.competences import modifier_competence

        attribution = attribuer_competence(**self.donnees)

        modifier_competence(
            attribution_id=attribution.pk,
            validateur_id=self.validateur.pk,
            date_validation="2026-01-01",
            date_expiration="2027-01-01",
        )

        journal = JournalAction.objects.get(
            action="competence.modifier"
        )

        self.assertIsNone(
            journal.details["avant"]["date_validation"]
        )
        self.assertEqual(
            journal.details["apres"]["date_validation"],
            "2026-01-01",
        )
        self.assertEqual(
            journal.details["apres"]["date_expiration"],
            "2027-01-01",
        )

    def test_absence_journal_si_inchange(self):
        from .models import JournalAction
        from .services.competences import modifier_competence

        attribution = attribuer_competence(**self.donnees)

        modifier_competence(
            attribution_id=attribution.pk,
            validateur_id=self.validateur.pk,
            date_validation=None,
            date_expiration=None,
        )

        self.assertEqual(JournalAction.objects.count(), 1)

    def test_retrait_et_conservation_journal(self):
        from .models import JournalAction
        from .services.competences import retirer_competence

        attribution = attribuer_competence(**self.donnees)
        identifiant = attribution.pk

        retirer_competence(
            attribution_id=identifiant,
            validateur_id=self.validateur.pk,
        )

        self.assertFalse(CompetenceAgent.objects.exists())

        journal = JournalAction.objects.get(
            action="competence.retirer"
        )

        self.assertEqual(journal.objet_id, identifiant)
        self.assertEqual(journal.auteur, self.validateur)
        self.assertEqual(
            journal.details["competence_id"],
            self.competence.pk,
        )
        self.assertEqual(JournalAction.objects.count(), 2)

    def test_retrait_non_autorise(self):
        from django.core.exceptions import PermissionDenied
        from .models import JournalAction
        from .services.competences import retirer_competence

        attribution = attribuer_competence(**self.donnees)

        with self.assertRaises(PermissionDenied):
            retirer_competence(
                attribution_id=attribution.pk,
                validateur_id=self.agent.pk,
            )

        self.assertEqual(CompetenceAgent.objects.count(), 1)
        self.assertEqual(JournalAction.objects.count(), 1)

    def test_annulation_attribution_si_journal_en_echec(self):
        from unittest.mock import patch
        from django.db import IntegrityError
        from .models import JournalAction

        with patch(
            "planning.services.journal.JournalAction.objects.create",
            side_effect=IntegrityError("Erreur simulee"),
        ):
            with self.assertRaises(ValidationError):
                attribuer_competence(**self.donnees)

        self.assertFalse(CompetenceAgent.objects.exists())
        self.assertFalse(JournalAction.objects.exists())

    def test_annulation_modification_si_journal_en_echec(self):
        from unittest.mock import patch
        from django.db import IntegrityError
        from .models import JournalAction
        from .services.competences import modifier_competence

        attribution = attribuer_competence(**self.donnees)

        with patch(
            "planning.services.journal.JournalAction.objects.create",
            side_effect=IntegrityError("Erreur simulee"),
        ):
            with self.assertRaises(ValidationError):
                modifier_competence(
                    attribution_id=attribution.pk,
                    validateur_id=self.validateur.pk,
                    date_validation="2026-01-01",
                    date_expiration="2027-01-01",
                )

        attribution.refresh_from_db()

        self.assertIsNone(attribution.date_validation)
        self.assertIsNone(attribution.date_expiration)
        self.assertEqual(JournalAction.objects.count(), 1)

    def test_annulation_retrait_si_journal_en_echec(self):
        from unittest.mock import patch
        from django.db import IntegrityError
        from .models import JournalAction
        from .services.competences import retirer_competence

        attribution = attribuer_competence(**self.donnees)

        with patch(
            "planning.services.journal.JournalAction.objects.create",
            side_effect=IntegrityError("Erreur simulee"),
        ):
            with self.assertRaises(ValidationError):
                retirer_competence(
                    attribution_id=attribution.pk,
                    validateur_id=self.validateur.pk,
                )

        self.assertEqual(CompetenceAgent.objects.count(), 1)
        self.assertEqual(JournalAction.objects.count(), 1)


class GestionCollectiveCompetencesTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.validateur = User.objects.create(
            username="administrateur",
            is_superuser=True,
        )

        self.profils = [
            ProfilAgent.objects.create(
                utilisateur=User.objects.create(username=matricule)
            )
            for matricule in ("000123", "000124")
        ]

        self.competence = Competence.objects.get(code="cod1")

        self.operations = [
            {
                "action": "attribuer",
                "profil_id": profil.pk,
                "competence_id": self.competence.pk,
            }
            for profil in self.profils
        ]

    def appliquer(self, operations):
        from .services.competences import (
            appliquer_modifications_collectives,
        )

        return appliquer_modifications_collectives(
            operations=operations,
            validateur_id=self.validateur.pk,
        )

    def test_attributions_collectives(self):
        from .models import JournalAction

        resultat = self.appliquer(self.operations)

        self.assertEqual(resultat["attributions"], 2)
        self.assertEqual(CompetenceAgent.objects.count(), 2)
        self.assertEqual(JournalAction.objects.count(), 2)

    def test_annulation_complete_du_lot(self):
        from .models import JournalAction

        self.operations[1]["competence_id"] = 999999

        with self.assertRaises(ValidationError):
            self.appliquer(self.operations)

        self.assertFalse(CompetenceAgent.objects.exists())
        self.assertFalse(JournalAction.objects.exists())

    def test_modification_et_retrait(self):
        from .models import JournalAction

        self.appliquer(self.operations)

        premiere, seconde = list(
            CompetenceAgent.objects.order_by("pk")
        )

        resultat = self.appliquer([
            {
                "action": "modifier",
                "attribution_id": premiere.pk,
                "date_validation": "2026-01-01",
                "date_expiration": "2027-01-01",
            },
            {
                "action": "retirer",
                "attribution_id": seconde.pk,
            },
        ])

        premiere.refresh_from_db()

        self.assertEqual(resultat["modifications"], 1)
        self.assertEqual(resultat["retraits"], 1)
        self.assertEqual(CompetenceAgent.objects.count(), 1)
        self.assertEqual(
            premiere.date_expiration,
            date(2027, 1, 1),
        )
        self.assertEqual(JournalAction.objects.count(), 4)

    def test_action_inconnue(self):
        with self.assertRaises(ValidationError):
            self.appliquer([{"action": "inconnue"}])

    def test_lot_vide(self):
        self.assertEqual(
            self.appliquer([]),
            {
                "attributions": 0,
                "modifications": 0,
                "retraits": 0,
                "inchanges": 0,
            },
        )

    def test_permissions_collectives(self):
        from django.core.exceptions import PermissionDenied
        from django.contrib.auth.models import Permission
        from .models import JournalAction

        self.validateur.is_superuser = False
        self.validateur.save(update_fields=["is_superuser"])

        permission = Permission.objects.get(
            content_type__app_label="planning",
            codename="add_competenceagent",
        )

        self.validateur.user_permissions.add(permission)

        self.appliquer(self.operations)

        attribution = CompetenceAgent.objects.first()

        with self.assertRaises(PermissionDenied):
            self.appliquer([
                {
                    "action": "retirer",
                    "attribution_id": attribution.pk,
                }
            ])

        self.assertEqual(CompetenceAgent.objects.count(), 2)
        self.assertEqual(JournalAction.objects.count(), 2)

    def test_modification_collective_sans_changement(self):
        from .models import JournalAction

        self.appliquer(self.operations)

        attribution = CompetenceAgent.objects.first()

        resultat = self.appliquer([
            {
                "action": "modifier",
                "attribution_id": attribution.pk,
                "date_validation": None,
                "date_expiration": None,
            }
        ])

        self.assertEqual(resultat["modifications"], 0)
        self.assertEqual(resultat["inchanges"], 1)
        self.assertEqual(JournalAction.objects.count(), 2)
