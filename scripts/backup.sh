#!/bin/sh

set -eu
umask 077

cd "$(dirname "$0")/.."

DOSSIER="${DISPO_BACKUP_DIR:-./backups}"

mkdir -p "$DOSSIER"
chmod 700 "$DOSSIER"

DATE=$(date +%Y%m%d_%H%M%S)
FICHIER="$DOSSIER/dispo_${DATE}.sqlite3"
TEMPORAIRE=$(mktemp "$DOSSIER/.backup.XXXXXX")

trap 'rm -f "$TEMPORAIRE"' EXIT

docker compose exec -T web python - > "$TEMPORAIRE" <<'PY'
import sqlite3
import tempfile
import sys
from pathlib import Path

with tempfile.TemporaryDirectory() as dossier:
    fichier = Path(dossier) / "backup.sqlite3"

    source = sqlite3.connect(
        "file:/data/db.sqlite3?mode=ro",
        uri=True,
        timeout=30,
    )

    destination = sqlite3.connect(fichier)

    try:
        source.backup(destination)

        resultat = destination.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if resultat != "ok":
            raise RuntimeError("Sauvegarde invalide")

    finally:
        destination.close()
        source.close()

    sys.stdout.buffer.write(fichier.read_bytes())
PY

test -s "$TEMPORAIRE"

mv "$TEMPORAIRE" "$FICHIER"

echo "Sauvegarde creee : $FICHIER"
