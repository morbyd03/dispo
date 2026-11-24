#!/bin/sh

set -eu
umask 077

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

. ./scripts/_backup_common.sh

TRAVAIL=$(mktemp -d)
ARRET=0

nettoyer() {
    CODE=$?

    trap - EXIT
    set +e

    rm -rf "$TRAVAIL"

    if [ "$ARRET" = "1" ]; then
        echo "Tentative de redemarrage apres interruption..."

        if ! docker compose up -d web; then
            echo "ATTENTION : redemarrage manuel necessaire." >&2
        fi
    fi

    exit "$CODE"
}

trap nettoyer EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

echo "Verification de la sauvegarde..."

cp "$FICHIER" "$TRAVAIL/restore.sqlite3"

python3 scripts/_sqlite_maintenance.py \
    validate "$TRAVAIL/restore.sqlite3"

if ! docker compose ps --status running --services | grep -qx web; then
    echo "Dispo doit etre demarre avant la restauration."
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

echo "Arret de Dispo..."

ARRET=1
docker compose stop web

echo "Sauvegarde preventive..."

sauvegarder offline

echo "Restauration de la base..."

docker compose run --rm -T --no-deps \
    --entrypoint python web \
    -c "$(cat scripts/_sqlite_maintenance.py)" restore \
    < "$TRAVAIL/restore.sqlite3"

echo "Redemarrage de Dispo..."

docker compose up -d web

ARRET=0

echo "Restauration terminee. Verifier les journaux."
