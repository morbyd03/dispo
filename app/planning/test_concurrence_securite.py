from unittest import skipUnless

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import connections, connection
from django.test import TransactionTestCase

from .models import SecuriteCompte
from .services.securite import (
    revoquer_acces_compte,
    version_securite_compte,
)


@skipUnless(
    connection.settings_dict["TEST"]["NAME"]
    == "/data/test_concurrence.sqlite3",
    "Necessite settings_concurrence",
)
class ConcurrenceSecuriteTests(TransactionTestCase):

    def setUp(self):
        self.agent = get_user_model().objects.create_user(
            username="00123",
        )

        self.assertEqual(
            connection.settings_dict["NAME"],
            "/data/test_concurrence.sqlite3",
        )

    def revoquer_en_parallele(self, nombre):
        barriere = Barrier(nombre)
        utilisateur_id = self.agent.pk

        def revoquer():
            try:
                barriere.wait(timeout=10)

                return revoquer_acces_compte(
                    utilisateur_id
                )

            finally:
                connections.close_all()

        with ThreadPoolExecutor(
            max_workers=nombre
        ) as pool:
            operations = [
                pool.submit(revoquer)
                for _ in range(nombre)
            ]

            return sorted(
                operation.result(timeout=30)
                for operation in operations
            )

    def test_creation_concurrente_securite_compte(self):
        self.assertFalse(
            SecuriteCompte.objects.filter(
                utilisateur=self.agent
            ).exists()
        )

        self.assertEqual(
            self.revoquer_en_parallele(2),
            [1, 2],
        )

        self.assertEqual(
            SecuriteCompte.objects.filter(
                utilisateur=self.agent
            ).count(),
            1,
        )

        self.assertEqual(
            version_securite_compte(self.agent.pk),
            2,
        )

    def test_incrementations_concurrentes(self):
        revoquer_acces_compte(self.agent.pk)

        self.assertEqual(
            self.revoquer_en_parallele(5),
            [2, 3, 4, 5, 6],
        )

        self.assertEqual(
            version_securite_compte(self.agent.pk),
            6,
        )

    def test_revocations_concurrentes_sans_perte(self):
        self.assertEqual(
            self.revoquer_en_parallele(10),
            list(range(1, 11)),
        )

        self.assertEqual(
            version_securite_compte(self.agent.pk),
            10,
        )
