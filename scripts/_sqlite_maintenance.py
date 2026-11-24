import os
import shutil
import sqlite3
import sys
import tempfile

from contextlib import closing
from pathlib import Path


BASE = Path("/data/db.sqlite3")

TABLES_REQUISES = {
    "django_migrations",
    "auth_user",
    "planning_disponibilite",
}


def ouvrir_lecture(fichier):
    return sqlite3.connect(
        fichier.resolve().as_uri() + "?mode=ro",
        uri=True,
        timeout=30,
    )


def verifier(fichier):
    with closing(ouvrir_lecture(fichier)) as connexion:
        resultats = connexion.execute(
            "PRAGMA integrity_check"
        ).fetchall()

        if resultats != [("ok",)]:
            raise RuntimeError("Integrite SQLite invalide")

        tables = {
            ligne[0]
            for ligne in connexion.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

        if not TABLES_REQUISES <= tables:
            raise RuntimeError("Ce fichier n'est pas une base Dispo")

        if connexion.execute(
            "PRAGMA foreign_key_check"
        ).fetchone():
            raise RuntimeError("Relations SQLite invalides")


def sauvegarder():
    with tempfile.TemporaryDirectory() as dossier:
        fichier = Path(dossier) / "backup.sqlite3"

        with closing(ouvrir_lecture(BASE)) as source:
            with closing(sqlite3.connect(fichier)) as destination:
                source.backup(destination)

        verifier(fichier)

        with fichier.open("rb") as flux:
            shutil.copyfileobj(flux, sys.stdout.buffer)


def restaurer():
    fd, nom = tempfile.mkstemp(
        prefix=".restore.",
        suffix=".sqlite3",
        dir=BASE.parent,
    )

    temporaire = Path(nom)

    try:
        with os.fdopen(fd, "wb") as flux:
            shutil.copyfileobj(sys.stdin.buffer, flux)
            flux.flush()
            os.fsync(flux.fileno())

        verifier(temporaire)

        if BASE.exists():
            with closing(sqlite3.connect(
                BASE.as_uri() + "?mode=rw",
                uri=True,
                timeout=30,
            )) as connexion:
                mode = connexion.execute(
                    "PRAGMA journal_mode=DELETE"
                ).fetchone()[0]

                if mode.lower() != "delete":
                    raise RuntimeError("Journal SQLite non ferme")

        for suffixe in ("-wal", "-shm", "-journal"):
            if Path(str(BASE) + suffixe).exists():
                raise RuntimeError(
                    "Journal SQLite encore present : " + suffixe
                )

        os.replace(temporaire, BASE)

        verifier(BASE)

        print("Base restauree et verifiee.")

    finally:
        temporaire.unlink(missing_ok=True)


def main():
    action = sys.argv[1]

    if action == "backup":
        sauvegarder()

    elif action == "validate":
        verifier(Path(sys.argv[2]))
        print("Sauvegarde valide.")

    elif action == "restore":
        restaurer()

    else:
        raise SystemExit("Action inconnue")


if __name__ == "__main__":
    try:
        main()
    except (OSError, sqlite3.Error, RuntimeError) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        sys.exit(1)
