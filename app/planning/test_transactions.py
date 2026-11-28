from django.db import connection, transaction
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext


class TransactionsTests(TransactionTestCase):

    def test_mode_transactionnel(self):
        self.assertEqual(
            connection.settings_dict["OPTIONS"]["transaction_mode"],
            "IMMEDIATE",
        )

    def test_transactions_automatiques_desactivees(self):
        self.assertFalse(
            connection.settings_dict["ATOMIC_REQUESTS"]
        )

    def test_ouverture_transaction_immediate(self):
        with CaptureQueriesContext(connection) as requetes:
            with transaction.atomic():
                pass

        commandes = [
            requete["sql"].strip().upper()
            for requete in requetes.captured_queries
        ]

        self.assertIn("BEGIN IMMEDIATE", commandes)

    def test_delai_verrouillage(self):
        with connection.cursor() as curseur:
            curseur.execute("PRAGMA busy_timeout")
            delai = curseur.fetchone()[0]

        self.assertEqual(delai, 20000)

    def test_transactions_imbriquees(self):
        with CaptureQueriesContext(connection) as requetes:
            with transaction.atomic():
                with transaction.atomic():
                    pass

        commandes = [
            requete["sql"].strip().upper()
            for requete in requetes.captured_queries
        ]

        self.assertEqual(
            commandes.count("BEGIN IMMEDIATE"),
            1,
        )

        self.assertTrue(
            any(
                commande.startswith("SAVEPOINT")
                for commande in commandes
            )
        )
