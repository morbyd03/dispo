#!/bin/sh

set -eu

cd "$(dirname "$0")/.."

if [ "$#" -ne 1 ]; then
    echo "Usage : $0 chemin/vers/sauvegarde.sqlite3"
    exit 1
fi

FICHIER="$1"

if [ ! -f "$FICHIER" ]; then
    echo "Fichier de sauvegarde introuvable."
    exit 1
fi

echo "ATTENTION : la base actuelle sera remplacee."
echo "Sauvegarde selectionnee : $FICHIER"
printf "Saisir RESTAURER pour confirmer : "
read -r confirmation

if [ "$confirmation" != "RESTAURER" ]; then
    echo "Restauration annulee."
    exit 1
fi

echo "Sauvegarde preventive..."
./scripts/backup.sh

echo "Arret de Dispo..."
docker compose stop web

echo "Restauration de la base..."

docker compose run --rm -T --no-deps \
    --entrypoint python web \
    -c '
import sqlite3
import os
import sys
from pathlib import Path

temporaire = Path("/data/.restore.sqlite3")
destination = Path("/data/db.sqlite3")

try:
    temporaire.write_bytes(sys.stdin.buffer.read())
    temporaire.chmod(0o600)

    connexion = sqlite3.connect(
        "file:/data/.restore.sqlite3?mode=ro",
        uri=True,
    )

    try:
        resultat = connexion.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if resultat != "ok":
            raise RuntimeError("Sauvegarde invalide")

        tables = {
            ligne[0]
            for ligne in connexion.execute(
                "SELECT name FROM sqlite_master WHERE type = ?",
                ("table",),
            )
        }

        if not {"django_migrations", "auth_user", "planning_disponibilite"} <= tables:
            raise RuntimeError("Ce fichier ne semble pas etre une base Dispo")

    finally:
        connexion.close()

    os.replace(temporaire, destination)

    for suffixe in ("-wal", "-shm", "-journal"):
        Path(str(destination) + suffixe).unlink(missing_ok=True)

finally:
    temporaire.unlink(missing_ok=True)

print("Base restauree.")
' < "$FICHIER"

echo "Redemarrage de Dispo..."
docker compose up -d

echo "Restauration terminee. Verifier les journaux."
