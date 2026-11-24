#!/bin/sh

set -eu

echo "=== Dispo : initialisation ==="

echo "Preparation du logo..."

python - <<'PYTHON'
import os
import shutil
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.conf import settings

destination = Path("/tmp/dispo-branding")

if destination.exists():
    shutil.rmtree(destination)

destination.mkdir(mode=0o700)

if settings.DISPO_LOGO:
    try:
        shutil.copyfile(
            settings.BRANDING_DIR / settings.DISPO_LOGO,
            destination / settings.DISPO_LOGO,
        )
    except PermissionError:
        raise SystemExit(
            "ERREUR : logo personnalise inaccessible. "
            "Verifier les permissions du dossier branding (755) "
            "et du fichier image (644)."
        ) from None
    print("Logo personnalise prepare.")
else:
    print("Utilisation du logo generique.")
PYTHON

echo "Application des migrations..."
python manage.py migrate --noinput

echo "Initialisation des droits..."
python manage.py initialiser_dispo

echo "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput --clear

echo "Verification de la configuration..."
python manage.py check

echo "=== Dispo : demarrage ==="

exec "$@"
