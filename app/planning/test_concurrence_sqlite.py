import sqlite3

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event

from django.test import SimpleTestCase


class ConcurrenceSQLiteTests(SimpleTestCase):

    def setUp(self):
        self.repertoire = TemporaryDirectory()
        self.addCleanup(self.repertoire.cleanup)

        self.chemin = str(
            Path(self.repertoire.name) / "concurrence.sqlite3"
        )

        connexion = self.connexion()

        try:
            connexion.execute(
                "CREATE TABLE securite ("
                "id INTEGER PRIMARY KEY, "
                "version INTEGER NOT NULL)"
            )

            connexion.execute(
                "INSERT INTO securite VALUES (1, 0)"
            )
        finally:
            connexion.close()

    def connexion(self, timeout=5):
        return sqlite3.connect(
            self.chemin,
            timeout=timeout,
            isolation_level=None,
        )

    def version(self, connexion):
        return connexion.execute(
            "SELECT version FROM securite WHERE id = 1"
        ).fetchone()[0]

    def incrementer(self, connexion):
        connexion.execute(
            "UPDATE securite "
            "SET version = version + 1 WHERE id = 1"
        )

    def test_ecritures_concurrentes_serialisees(self):
        verrou_acquis = Event()
        seconde_demarre = Event()

        def premiere_transaction():
            connexion = self.connexion()

            try:
                connexion.execute("BEGIN IMMEDIATE")

                self.incrementer(connexion)
                verrou_acquis.set()

                if not seconde_demarre.wait(3):
                    raise RuntimeError(
                        "Seconde transaction non demarree"
                    )

                connexion.commit()

            finally:
                connexion.close()

        def seconde_transaction():
            connexion = self.connexion()

            try:
                if not verrou_acquis.wait(3):
                    raise RuntimeError(
                        "Premier verrou non acquis"
                    )

                seconde_demarre.set()

                connexion.execute("BEGIN IMMEDIATE")

                version = self.version(connexion)

                self.incrementer(connexion)
                connexion.commit()

                return version

            finally:
                connexion.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            premiere = pool.submit(premiere_transaction)
            seconde = pool.submit(seconde_transaction)

            premiere.result(timeout=10)

            self.assertEqual(
                seconde.result(timeout=10),
                1,
            )

        connexion = self.connexion()

        try:
            self.assertEqual(self.version(connexion), 2)
        finally:
            connexion.close()

    def test_verrou_exclusif_des_ouverture(self):
        premiere = self.connexion()
        seconde = self.connexion(timeout=0.1)

        try:
            premiere.execute("BEGIN IMMEDIATE")

            with self.assertRaisesRegex(
                sqlite3.OperationalError,
                "locked",
            ):
                seconde.execute("BEGIN IMMEDIATE")

            premiere.rollback()

            seconde.execute("BEGIN IMMEDIATE")
            self.incrementer(seconde)
            seconde.commit()

            self.assertEqual(self.version(seconde), 1)

        finally:
            premiere.close()
            seconde.close()

    def test_annulation_libere_verrou(self):
        premiere = self.connexion()
        seconde = self.connexion()

        try:
            premiere.execute("BEGIN IMMEDIATE")
            self.incrementer(premiere)

            premiere.rollback()

            seconde.execute("BEGIN IMMEDIATE")

            self.assertEqual(self.version(seconde), 0)

            self.incrementer(seconde)
            seconde.commit()

            self.assertEqual(self.version(seconde), 1)

        finally:
            premiere.close()
            seconde.close()
