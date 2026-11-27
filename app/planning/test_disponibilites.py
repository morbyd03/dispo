from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Disponibilite, ProfilAgent, Grade
from .copie import copier_journee


class CopieJourneeTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.agent = User.objects.create_user(
            username="agent_copie",
            password="test123",
        )
        ProfilAgent.objects.create(utilisateur=self.agent, grade=Grade.objects.get(code="SAP1"))

        self.autre_agent = User.objects.create_user(
            username="autre_agent_copie",
            password="test123",
        )
        ProfilAgent.objects.create(utilisateur=self.autre_agent, grade=Grade.objects.get(code="SAP1"))

    def creer_disponibilite(self, agent, debut, fin):
        return Disponibilite.objects.create(
            profil=agent.profil_agent,
            debut=timezone.make_aware(
                datetime.fromisoformat(debut)
            ),
            fin=timezone.make_aware(
                datetime.fromisoformat(fin)
            ),
        )

    def test_copie_plusieurs_creneaux_plusieurs_dates(self):
        self.creer_disponibilite(
            self.agent,
            "2026-11-23T08:00",
            "2026-11-23T12:00",
        )
        self.creer_disponibilite(
            self.agent,
            "2026-11-23T21:00",
            "2026-11-24T06:00",
        )

        resultat = copier_journee(
            self.agent.profil_agent,
            date(2026, 11, 23),
            [
                date(2026, 11, 24),
                date(2026, 11, 25),
                date(2026, 11, 26),
                date(2026, 11, 30),
            ],
        )

        self.assertEqual(resultat["creations"], 8)
        self.assertEqual(resultat["creneaux_source"], 2)

        self.assertEqual(
            Disponibilite.objects.filter(
                profil=self.agent.profil_agent
            ).count(),
            10,
        )

    def test_copie_traverse_minuit(self):
        self.creer_disponibilite(
            self.agent,
            "2026-11-23T21:00",
            "2026-11-24T06:00",
        )

        copier_journee(
            self.agent.profil_agent,
            date(2026, 11, 23),
            [date(2026, 11, 25)],
        )

        copie = Disponibilite.objects.get(
            profil=self.agent.profil_agent,
            debut__date=date(2026, 11, 25),
        )

        self.assertEqual(
            timezone.localtime(copie.debut).hour,
            21,
        )
        self.assertEqual(
            timezone.localtime(copie.fin).date(),
            date(2026, 11, 26),
        )
        self.assertEqual(
            timezone.localtime(copie.fin).hour,
            0,
        )

    def test_remplacement_integral_journee_cible(self):
        self.creer_disponibilite(
            self.agent,
            "2026-11-23T08:00",
            "2026-11-23T12:00",
        )

        self.creer_disponibilite(
            self.agent,
            "2026-11-24T09:00",
            "2026-11-24T11:00",
        )

        self.creer_disponibilite(
            self.agent,
            "2026-11-24T14:00",
            "2026-11-24T18:00",
        )

        resultat = copier_journee(
            self.agent.profil_agent,
            date(2026, 11, 23),
            [date(2026, 11, 24)],
        )

        self.assertEqual(resultat["creations"], 1)
        self.assertEqual(resultat["doublons"], 0)

        journee = Disponibilite.objects.filter(
            profil=self.agent.profil_agent,
            debut__gte=timezone.make_aware(
                datetime(2026, 11, 24, 0, 0)
            ),
            debut__lt=timezone.make_aware(
                datetime(2026, 11, 25, 0, 0)
            ),
        ).order_by("debut")

        self.assertEqual(journee.count(), 1)

        copie = journee.first()

        self.assertEqual(
            timezone.localtime(copie.debut).hour, 8
        )
        self.assertEqual(
            timezone.localtime(copie.fin).hour, 12
        )

    def test_ne_copie_pas_autre_agent(self):
        self.creer_disponibilite(
            self.agent,
            "2026-11-23T08:00",
            "2026-11-23T12:00",
        )

        self.creer_disponibilite(
            self.autre_agent,
            "2026-11-23T14:00",
            "2026-11-23T18:00",
        )

        copier_journee(
            self.agent.profil_agent,
            date(2026, 11, 23),
            [date(2026, 11, 24)],
        )

        self.assertEqual(
            Disponibilite.objects.filter(
                profil=self.autre_agent.profil_agent
            ).count(),
            1,
        )



class CopieJourneeVueTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.agent = User.objects.create_user(
            username="agent_vue_copie",
            password="test123",
        )
        ProfilAgent.objects.create(utilisateur=self.agent, grade=Grade.objects.get(code="SAP1"))
        self.autre_agent = User.objects.create_user(
            username="autre_vue_copie",
            password="test123",
        )
        ProfilAgent.objects.create(utilisateur=self.autre_agent, grade=Grade.objects.get(code="SAP1"))
        self.url = reverse("copier_journee")

    def creer_disponibilite(self, agent, debut, fin):
        return Disponibilite.objects.create(
            profil=agent.profil_agent,
            debut=timezone.make_aware(
                datetime.fromisoformat(debut)
            ),
            fin=timezone.make_aware(
                datetime.fromisoformat(fin)
            ),
        )

    def test_connexion_obligatoire(self):
        reponse = self.client.get(
            self.url,
            secure=True,
        )
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("connexion", reponse.url)

    def test_copie_uniquement_agent_connecte(self):
        self.creer_disponibilite(
            self.agent,
            "2026-11-23T08:00",
            "2026-11-23T12:00",
        )
        self.creer_disponibilite(
            self.autre_agent,
            "2026-11-23T14:00",
            "2026-11-23T18:00",
        )

        self.client.force_login(self.agent)

        reponse = self.client.post(
            self.url,
            {
                "date_source": "2026-11-23",
                "dates_destination": "2026-11-24",
            },
            secure=True,
        )

        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(
            Disponibilite.objects.filter(
                profil=self.agent.profil_agent
            ).count(),
            2,
        )
        self.assertEqual(
            Disponibilite.objects.filter(
                profil=self.autre_agent.profil_agent
            ).count(),
            1,
        )

    def test_date_invalide_refusee(self):
        self.client.force_login(self.agent)

        reponse = self.client.post(
            self.url,
            {
                "date_source": "2026-11-23",
                "dates_destination": "date-invalide",
            },
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertContains(
            reponse,
            "Une date de destination est invalide.",
        )

    def test_copie_vers_plusieurs_dates(self):
        self.creer_disponibilite(
            self.agent,
            "2026-11-23T21:00",
            "2026-11-24T06:00",
        )

        self.client.force_login(self.agent)

        reponse = self.client.post(
            self.url,
            {
                "date_source": "2026-11-23",
                "dates_destination": (
                    "2026-11-24,2026-11-25,"
                    "2026-11-26,2026-11-30"
                ),
            },
            secure=True,
        )

        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(
            Disponibilite.objects.filter(
                profil=self.agent.profil_agent
            ).count(),
            5,
        )


class CopieJourneeDecoupageTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.agent = User.objects.create_user(
            username="agent_decoupage",
            password="test123",
        )
        ProfilAgent.objects.create(utilisateur=self.agent, grade=Grade.objects.get(code="SAP1"))

    def creer_disponibilite(self, debut, fin):
        return Disponibilite.objects.create(
            profil=self.agent.profil_agent,
            debut=timezone.make_aware(
                datetime.fromisoformat(debut)
            ),
            fin=timezone.make_aware(
                datetime.fromisoformat(fin)
            ),
        )

    def test_copie_deuxieme_jour(self):
        self.creer_disponibilite(
            "2026-11-23T21:00",
            "2026-11-24T06:00",
        )

        resultat = copier_journee(
            self.agent.profil_agent,
            date(2026, 11, 24),
            [date(2026, 11, 30)],
        )

        self.assertEqual(resultat["creations"], 1)

        copie = Disponibilite.objects.get(
            profil=self.agent.profil_agent,
            debut__date=date(2026, 11, 30),
        )

        self.assertEqual(
            timezone.localtime(copie.debut).hour,
            0,
        )
        self.assertEqual(
            timezone.localtime(copie.fin).hour,
            6,
        )

    def test_copie_journee_intermediaire(self):
        self.creer_disponibilite(
            "2026-11-23T18:00",
            "2026-11-26T08:00",
        )

        resultat = copier_journee(
            self.agent.profil_agent,
            date(2026, 11, 24),
            [date(2026, 11, 30)],
        )

        self.assertEqual(resultat["creations"], 1)

        copie = Disponibilite.objects.get(
            profil=self.agent.profil_agent,
            debut__date=date(2026, 11, 30),
        )

        self.assertEqual(
            timezone.localtime(copie.debut).hour,
            0,
        )
        self.assertEqual(
            timezone.localtime(copie.fin).date(),
            date(2026, 12, 1),
        )
        self.assertEqual(
            timezone.localtime(copie.fin).hour,
            0,
        )

    def test_copie_dernier_jour(self):
        self.creer_disponibilite(
            "2026-11-23T18:00",
            "2026-11-26T08:00",
        )

        resultat = copier_journee(
            self.agent.profil_agent,
            date(2026, 11, 26),
            [date(2026, 11, 30)],
        )

        self.assertEqual(resultat["creations"], 1)

        copie = Disponibilite.objects.get(
            profil=self.agent.profil_agent,
            debut__date=date(2026, 11, 30),
        )

        self.assertEqual(
            timezone.localtime(copie.debut).hour,
            0,
        )
        self.assertEqual(
            timezone.localtime(copie.fin).hour,
            8,
        )

class CopieChangementHeureTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.agent = User.objects.create_user(
            username="agent_changement_heure",
            password="test123",
        )
        ProfilAgent.objects.create(utilisateur=self.agent, grade=Grade.objects.get(code="SAP1"))

    def test_passage_heure_ete(self):
        Disponibilite.objects.create(
            profil=self.agent.profil_agent,
            debut=timezone.make_aware(
                datetime(2026, 3, 29, 0, 0)
            ),
            fin=timezone.make_aware(
                datetime(2026, 3, 30, 0, 0)
            ),
        )

        resultat = copier_journee(
            self.agent.profil_agent,
            date(2026, 3, 29),
            [date(2026, 3, 31)],
        )

        self.assertEqual(resultat["creations"], 1)

        copie = Disponibilite.objects.get(
            profil=self.agent.profil_agent,
            debut__date=date(2026, 3, 31),
        )

        self.assertEqual(
            timezone.localtime(copie.debut).hour,
            0,
        )
        self.assertEqual(
            timezone.localtime(copie.fin).date(),
            date(2026, 4, 1),
        )

    def test_passage_heure_hiver(self):
        Disponibilite.objects.create(
            profil=self.agent.profil_agent,
            debut=timezone.make_aware(
                datetime(2026, 10, 25, 0, 0)
            ),
            fin=timezone.make_aware(
                datetime(2026, 10, 26, 0, 0)
            ),
        )

        resultat = copier_journee(
            self.agent.profil_agent,
            date(2026, 10, 25),
            [date(2026, 10, 27)],
        )

        self.assertEqual(resultat["creations"], 1)

        copie = Disponibilite.objects.get(
            profil=self.agent.profil_agent,
            debut__date=date(2026, 10, 27),
        )

        self.assertEqual(
            timezone.localtime(copie.debut).hour,
            0,
        )
        self.assertEqual(
            timezone.localtime(copie.fin).date(),
            date(2026, 10, 28),
        )

class PreRemplissageCalendrierTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.agent = User.objects.create_user(
            username="agent_calendrier",
            password="test123",
        )
        ProfilAgent.objects.create(utilisateur=self.agent, grade=Grade.objects.get(code="SAP1"))
        self.client.force_login(self.agent)

    def test_date_et_heure_pre_remplies(self):
        reponse = self.client.get(
            reverse("ajouter_disponibilite"),
            {
                "date": "2026-11-25",
                "heure": "14:00",
            },
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)

        formulaire = reponse.context["formulaire"]

        self.assertEqual(
            formulaire["debut"].value(),
            datetime(2026, 11, 25, 14, 0),
        )
        self.assertEqual(
            formulaire["fin"].value(),
            datetime(2026, 11, 25, 15, 0),
        )


class DisponibilitesFonctionnellesTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.agent = User.objects.create_user(username="00123")
        self.autre = User.objects.create_user(username="00124")
        self.technique = User.objects.create_user(
            username="admin",
            is_superuser=True,
            is_staff=True,
        )

        grade = Grade.objects.get(code="SAP1")

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.agent,
            grade=grade,
        )

        self.autre_profil = ProfilAgent.objects.create(
            utilisateur=self.autre,
            grade=grade,
        )

        self.client.force_login(self.agent)

        self.donnees = {
            "debut_0": "2027-01-04",
            "debut_1": "21:00",
            "fin_0": "2027-01-05",
            "fin_1": "06:00",
        }

    def creer(self, profil, debut, fin):
        return Disponibilite.objects.create(
            profil=profil,
            debut=timezone.make_aware(datetime.fromisoformat(debut)),
            fin=timezone.make_aware(datetime.fromisoformat(fin)),
        )

    def test_declaration_nuit(self):
        reponse = self.client.post(
            reverse("ajouter_disponibilite"),
            self.donnees,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 302)
        dispo = Disponibilite.objects.get(profil=self.profil)
        self.assertEqual(dispo.fin - dispo.debut, timedelta(hours=9))

    def test_declaration_duree_invalide(self):
        self.donnees["fin_0"] = "2027-01-04"

        reponse = self.client.post(
            reverse("ajouter_disponibilite"),
            self.donnees,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(Disponibilite.objects.exists())

    def test_modification_propre_creneau(self):
        dispo = self.creer(
            self.profil,
            "2027-01-04T08:00",
            "2027-01-04T12:00",
        )

        reponse = self.client.post(
            reverse("modifier_disponibilite", args=[dispo.pk]),
            self.donnees,
            secure=True,
        )

        self.assertEqual(reponse.status_code, 302)
        dispo.refresh_from_db()
        self.assertEqual(timezone.localtime(dispo.debut).hour, 21)

    def test_suppression_propre_creneau(self):
        dispo = self.creer(
            self.profil,
            "2027-01-04T08:00",
            "2027-01-04T12:00",
        )

        url = reverse("supprimer_disponibilite", args=[dispo.pk])

        self.client.get(url, secure=True)
        self.assertTrue(Disponibilite.objects.filter(pk=dispo.pk).exists())

        reponse = self.client.post(url, secure=True)
        self.assertEqual(reponse.status_code, 302)
        self.assertFalse(Disponibilite.objects.filter(pk=dispo.pk).exists())

    def test_creneau_autre_agent_protege(self):
        dispo = self.creer(
            self.autre_profil,
            "2027-01-04T08:00",
            "2027-01-04T12:00",
        )

        for vue in (
            "modifier_disponibilite",
            "supprimer_disponibilite",
        ):
            url = reverse(vue, args=[dispo.pk])

            self.assertEqual(
                self.client.get(url, secure=True).status_code, 404
            )

            self.assertEqual(
                self.client.post(
                    url, self.donnees, secure=True
                ).status_code,
                404,
            )

        dispo.refresh_from_db()
        self.assertEqual(timezone.localtime(dispo.debut).hour, 8)

    def test_compte_sans_profil(self):
        self.client.force_login(self.technique)

        reponse = self.client.get(
            reverse("mes_disponibilites"),
            secure=True,
        )

        self.assertRedirects(
            reponse,
            reverse("planning_hebdomadaire"),
            fetch_redirect_response=False,
        )

        for vue in ("ajouter_disponibilite", "copier_journee"):
            self.assertEqual(
                self.client.get(reverse(vue), secure=True).status_code,
                403,
            )

    def test_planning_collectif(self):
        dispo = self.creer(
            self.autre_profil,
            "2027-01-04T21:00",
            "2027-01-05T06:00",
        )

        reponse = self.client.get(
            reverse("planning_hebdomadaire"),
            {"semaine": "2027-01-04"},
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertIn(dispo, reponse.context["jours"][0]["disponibilites"])
        self.assertIn(dispo, reponse.context["jours"][1]["disponibilites"])
        self.assertFalse(reponse.context["couverture_active"])

    def test_agent_inactif_absent_du_planning(self):
        self.creer(
            self.autre_profil,
            "2027-01-04T08:00",
            "2027-01-04T12:00",
        )

        self.autre.is_active = False
        self.autre.save(update_fields=["is_active"])

        reponse = self.client.get(
            reverse("planning_hebdomadaire"),
            {"semaine": "2027-01-04"},
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.context["jours"][0]["disponibilites"], [])

    def test_copie_source_vide_sans_suppression(self):
        dispo = self.creer(
            self.profil,
            "2027-01-05T08:00",
            "2027-01-05T12:00",
        )

        resultat = copier_journee(
            self.profil,
            date(2027, 1, 4),
            [date(2027, 1, 5)],
        )

        self.assertEqual(resultat["creations"], 0)
        self.assertTrue(Disponibilite.objects.filter(pk=dispo.pk).exists())

    def test_copie_heure_inexistante_annulee(self):
        from django.core.exceptions import ValidationError

        with timezone.override("Europe/Paris"):
            self.creer(
                self.profil,
                "2026-03-27T02:30",
                "2026-03-27T05:00",
            )

            dispo = self.creer(
                self.profil,
                "2026-03-29T08:00",
                "2026-03-29T12:00",
            )

            with self.assertRaises(ValidationError):
                copier_journee(
                    self.profil,
                    date(2026, 3, 27),
                    [date(2026, 3, 29)],
                )

            self.assertTrue(
                Disponibilite.objects.filter(pk=dispo.pk).exists()
            )
