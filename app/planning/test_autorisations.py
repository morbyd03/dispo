from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.test import TestCase, RequestFactory
from django.urls import reverse


class AdministrationTechniqueTests(TestCase):

    def setUp(self):
        self.User = get_user_model()
        self.factory = RequestFactory()

    def autorise(self, utilisateur):
        request = self.factory.get("/admin/")
        request.user = utilisateur

        return admin.site.has_permission(request)

    def test_anonyme_refuse(self):
        self.assertFalse(
            self.autorise(AnonymousUser())
        )

    def test_agent_ordinaire_refuse(self):
        agent = self.User.objects.create(
            username="000123",
        )

        self.assertFalse(self.autorise(agent))

    def test_administrateur_dispo_refuse(self):
        agent = self.User.objects.create(
            username="000123",
        )

        groupe, _ = Group.objects.get_or_create(
            name="Administrateurs Dispo"
        )

        agent.groups.add(groupe)

        self.assertFalse(self.autorise(agent))

    def test_staff_non_superutilisateur_refuse(self):
        agent = self.User.objects.create(
            username="000123",
            is_staff=True,
        )

        self.assertFalse(self.autorise(agent))

    def test_superutilisateur_actif_autorise(self):
        agent = self.User.objects.create(
            username="administrateur",
            is_staff=True,
            is_superuser=True,
        )

        self.assertTrue(self.autorise(agent))

    def test_superutilisateur_inactif_refuse(self):
        agent = self.User.objects.create(
            username="administrateur",
            is_staff=True,
            is_superuser=True,
            is_active=False,
        )

        self.assertFalse(self.autorise(agent))

    def test_superutilisateur_non_staff_refuse(self):
        agent = self.User.objects.create(
            username="administrateur",
            is_superuser=True,
            is_staff=False,
        )

        self.assertFalse(self.autorise(agent))

    def test_acces_direct_admin_refuse(self):
        agent = self.User.objects.create(
            username="000123",
            is_staff=True,
        )

        self.client.force_login(agent)

        for destination in (
            "admin:index",
            "admin:auth_user_changelist",
            "admin:auth_user_add",
            "admin:auth_group_changelist",
        ):
            with self.subTest(destination=destination):
                reponse = self.client.get(
                    reverse(destination),
                    secure=True,
                )

                self.assertEqual(
                    reponse.status_code,
                    302,
                )

                self.assertIn(
                    reverse("admin:login"),
                    reponse.url,
                )

    def test_classe_administration_dediee(self):
        from config.admin_site import AdministrationTechnique

        self.assertIsInstance(
            admin.site,
            AdministrationTechnique,
        )

    def test_modeles_authentification_enregistres(self):
        from django.contrib.auth.models import Group

        self.assertTrue(
            admin.site.is_registered(self.User)
        )

        self.assertTrue(
            admin.site.is_registered(Group)
        )

    def test_modeles_planning_enregistres(self):
        from .models import (
            Grade,
            FonctionAgent,
            ProfilAgent,
            Competence,
            CompetenceAgent,
            JournalAction,
        )

        for modele in (
            Grade,
            FonctionAgent,
            ProfilAgent,
            Competence,
            CompetenceAgent,
            JournalAction,
        ):
            with self.subTest(modele=modele):
                self.assertTrue(
                    admin.site.is_registered(modele)
                )


class ProtectionAdministrationProfilsTests(TestCase):

    def setUp(self):
        from .models import Grade, ProfilAgent

        User = get_user_model()

        self.admin = User.objects.create(
            username="administrateur",
            is_staff=True,
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

        self.request = RequestFactory().get("/admin/")
        self.request.user = self.admin

        self.client.force_login(self.admin)

    def test_consultation_autorisee(self):
        from .admin import ProfilAgentAdmin
        from .models import ProfilAgent

        interface = ProfilAgentAdmin(
            ProfilAgent,
            admin.site,
        )

        self.assertTrue(
            interface.has_view_permission(
                self.request,
                self.profil,
            )
        )

    def test_creation_interdite(self):
        from .admin import ProfilAgentAdmin
        from .models import ProfilAgent

        interface = ProfilAgentAdmin(
            ProfilAgent,
            admin.site,
        )

        self.assertFalse(
            interface.has_add_permission(self.request)
        )

    def test_modification_interdite(self):
        from .admin import ProfilAgentAdmin
        from .models import ProfilAgent

        interface = ProfilAgentAdmin(
            ProfilAgent,
            admin.site,
        )

        self.assertFalse(
            interface.has_change_permission(
                self.request,
                self.profil,
            )
        )

    def test_suppression_interdite(self):
        from .admin import ProfilAgentAdmin
        from .models import ProfilAgent

        interface = ProfilAgentAdmin(
            ProfilAgent,
            admin.site,
        )

        self.assertFalse(
            interface.has_delete_permission(
                self.request,
                self.profil,
            )
        )

    def test_actions_collectives_interdites(self):
        from .admin import ProfilAgentAdmin
        from .models import ProfilAgent

        interface = ProfilAgentAdmin(
            ProfilAgent,
            admin.site,
        )

        self.assertEqual(
            interface.get_actions(self.request),
            {},
        )

    def test_creation_directe_refusee(self):
        reponse = self.client.post(
            reverse("admin:planning_profilagent_add"),
            {"utilisateur": self.agent.pk},
            secure=True,
        )

        self.assertEqual(reponse.status_code, 403)

    def test_modification_directe_refusee(self):
        reponse = self.client.post(
            reverse(
                "admin:planning_profilagent_change",
                args=[self.profil.pk],
            ),
            {"telephone": "0612345678"},
            secure=True,
        )

        self.assertEqual(reponse.status_code, 403)

        self.profil.refresh_from_db()

        self.assertEqual(
            self.profil.telephone,
            "0600000000",
        )

    def test_suppression_directe_refusee(self):
        from .models import ProfilAgent

        reponse = self.client.post(
            reverse(
                "admin:planning_profilagent_delete",
                args=[self.profil.pk],
            ),
            {"post": "yes"},
            secure=True,
        )

        self.assertEqual(reponse.status_code, 403)

        self.assertTrue(
            ProfilAgent.objects.filter(
                pk=self.profil.pk
            ).exists()
        )

    def test_acces_reel_superutilisateur(self):
        for destination in (
            "admin:index",
            "admin:planning_profilagent_changelist",
        ):
            with self.subTest(destination=destination):
                reponse = self.client.get(
                    reverse(destination),
                    secure=True,
                )

                self.assertEqual(
                    reponse.status_code,
                    200,
                )


class ProtectionAdministrationComptesTests(TestCase):

    def setUp(self):
        from .models import Grade, ProfilAgent

        self.User = get_user_model()

        self.admin = self.User.objects.create(
            username="administrateur",
            is_staff=True,
            is_superuser=True,
        )

        self.agent = self.User.objects.create(
            username="000123",
            first_name="Jean",
            last_name="Dupont",
            email="jean@example.com",
        )

        self.profil = ProfilAgent.objects.create(
            utilisateur=self.agent,
            grade=Grade.objects.get(code="SAP1"),
        )

        self.request = RequestFactory().get("/admin/")
        self.request.user = self.admin

        self.client.force_login(self.admin)

    def interface(self):
        from .admin import UtilisateurTechniqueAdmin

        return UtilisateurTechniqueAdmin(
            self.User,
            admin.site,
        )

    def test_suppression_agent_interdite(self):
        self.assertFalse(
            self.interface().has_delete_permission(
                self.request,
                self.agent,
            )
        )

    def test_suppression_superutilisateur_interdite(self):
        self.assertFalse(
            self.interface().has_delete_permission(
                self.request,
                self.admin,
            )
        )

    def test_actions_collectives_interdites(self):
        self.assertEqual(
            self.interface().get_actions(self.request),
            {},
        )

    def test_suppression_directe_refusee(self):
        from .models import ProfilAgent

        reponse = self.client.post(
            reverse(
                "admin:auth_user_delete",
                args=[self.agent.pk],
            ),
            {"post": "yes"},
            secure=True,
        )

        self.assertEqual(reponse.status_code, 403)

        self.assertTrue(
            self.User.objects.filter(
                pk=self.agent.pk
            ).exists()
        )

        self.assertTrue(
            ProfilAgent.objects.filter(
                pk=self.profil.pk
            ).exists()
        )

    def test_consultation_comptes_autorisee(self):
        reponse = self.client.get(
            reverse("admin:auth_user_changelist"),
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)

    def test_modification_agent_interdite(self):
        self.assertFalse(
            self.interface().has_change_permission(
                self.request,
                self.agent,
            )
        )

    def test_modification_technique_autorisee(self):
        self.assertTrue(
            self.interface().has_change_permission(
                self.request,
                self.admin,
            )
        )

    def test_creation_technique_autorisee(self):
        self.assertTrue(
            self.interface().has_add_permission(
                self.request,
            )
        )

    def test_consultation_agent_autorisee(self):
        reponse = self.client.get(
            reverse(
                "admin:auth_user_change",
                args=[self.agent.pk],
            ),
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)

    def test_modification_directe_agent_refusee(self):
        reponse = self.client.post(
            reverse(
                "admin:auth_user_change",
                args=[self.agent.pk],
            ),
            {
                "username": "999999",
                "email": "nouveau@example.com",
                "is_superuser": "on",
            },
            secure=True,
        )

        self.assertEqual(reponse.status_code, 403)

        self.agent.refresh_from_db()

        self.assertEqual(self.agent.username, "000123")
        self.assertEqual(self.agent.email, "jean@example.com")
        self.assertFalse(self.agent.is_superuser)

    def test_acces_changement_mot_de_passe_refuse(self):
        reponse = self.client.get(
            reverse(
                "admin:auth_user_password_change",
                args=[self.agent.pk],
            ),
            secure=True,
        )

        self.assertEqual(reponse.status_code, 403)

    def test_modification_mot_de_passe_refusee(self):
        ancien_mot_de_passe = self.agent.password

        reponse = self.client.post(
            reverse(
                "admin:auth_user_password_change",
                args=[self.agent.pk],
            ),
            {
                "password1": "Mot-de-passe-fictif-123!",
                "password2": "Mot-de-passe-fictif-123!",
            },
            secure=True,
        )

        self.assertEqual(reponse.status_code, 403)

        self.agent.refresh_from_db()

        self.assertEqual(
            self.agent.password,
            ancien_mot_de_passe,
        )

    def test_acces_mot_de_passe_technique_autorise(self):
        reponse = self.client.get(
            reverse(
                "admin:auth_user_password_change",
                args=[self.admin.pk],
            ),
            secure=True,
        )

        self.assertEqual(reponse.status_code, 200)


class ProtectionAdministrationReferentielsTests(TestCase):

    def setUp(self):
        from .models import Grade, FonctionAgent, Competence

        User = get_user_model()

        self.admin = User.objects.create(
            username="administrateur",
            is_staff=True,
            is_superuser=True,
        )

        self.grade = Grade.objects.get(code="SAP1")

        self.fonction = FonctionAgent.objects.create(
            nom="Fonction de test"
        )

        self.competence = Competence.objects.get(
            code="cod1"
        )

        self.objets = (
            self.grade,
            self.fonction,
            self.competence,
        )

        self.request = RequestFactory().get("/admin/")
        self.request.user = self.admin

        self.client.force_login(self.admin)

    def interface(self, objet):
        return admin.site.get_model_admin(type(objet))

    def test_creation_autorisee(self):
        for objet in self.objets:
            with self.subTest(modele=type(objet)):
                self.assertTrue(
                    self.interface(objet)
                    .has_add_permission(self.request)
                )

    def test_modification_autorisee(self):
        for objet in self.objets:
            with self.subTest(modele=type(objet)):
                self.assertTrue(
                    self.interface(objet)
                    .has_change_permission(
                        self.request,
                        objet,
                    )
                )

    def test_suppression_interdite(self):
        for objet in self.objets:
            with self.subTest(modele=type(objet)):
                self.assertFalse(
                    self.interface(objet)
                    .has_delete_permission(
                        self.request,
                        objet,
                    )
                )

    def test_actions_collectives_interdites(self):
        for objet in self.objets:
            with self.subTest(modele=type(objet)):
                self.assertEqual(
                    self.interface(objet)
                    .get_actions(self.request),
                    {},
                )

    def test_suppression_directe_refusee(self):
        for objet in self.objets:
            modele = objet._meta.model_name

            with self.subTest(modele=modele):
                reponse = self.client.post(
                    reverse(
                        f"admin:planning_{modele}_delete",
                        args=[objet.pk],
                    ),
                    {"post": "yes"},
                    secure=True,
                )

                self.assertEqual(
                    reponse.status_code,
                    403,
                )

                self.assertTrue(
                    type(objet).objects.filter(
                        pk=objet.pk
                    ).exists()
                )

    def test_codes_immuables_apres_creation(self):
        for objet in (self.grade, self.competence):
            with self.subTest(modele=type(objet)):
                self.assertIn(
                    "code",
                    self.interface(objet)
                    .get_readonly_fields(
                        self.request,
                        objet,
                    ),
                )

    def test_codes_modifiables_a_la_creation(self):
        for objet in (self.grade, self.competence):
            with self.subTest(modele=type(objet)):
                self.assertNotIn(
                    "code",
                    self.interface(objet)
                    .get_readonly_fields(
                        self.request,
                        None,
                    ),
                )

    def test_consultation_referentiels(self):
        for objet in self.objets:
            modele = objet._meta.model_name

            with self.subTest(modele=modele):
                reponse = self.client.get(
                    reverse(
                        f"admin:planning_{modele}_changelist"
                    ),
                    secure=True,
                )

                self.assertEqual(
                    reponse.status_code,
                    200,
                )
