DOSSIER="${DISPO_BACKUP_DIR:-./backups}"

mkdir -p "$DOSSIER"

if [ "$(stat -c '%a' "$DOSSIER")" != "700" ]; then
    echo "Le dossier de sauvegarde doit avoir les droits 700." >&2
    exit 1
fi

exec 9> .dispo-maintenance.lock

if ! flock -n 9; then
    echo "Une operation de maintenance est deja en cours." >&2
    exit 1
fi

sauvegarder() (
    MODE="$1"

    DATE=$(date +%Y%m%d_%H%M%S)
    TEMPORAIRE=$(mktemp "$DOSSIER/.backup.XXXXXX")

    trap 'rm -f "$TEMPORAIRE"' EXIT

    SUFFIXE="${TEMPORAIRE##*.}"

    FICHIER="$DOSSIER/dispo_${DATE}_${SUFFIXE}.sqlite3"

    if [ "$MODE" = "online" ]; then
        docker compose exec -T web python - backup \
            < scripts/_sqlite_maintenance.py \
            > "$TEMPORAIRE"
    else
        docker compose run --rm -T --no-deps \
            --entrypoint python web - backup \
            < scripts/_sqlite_maintenance.py \
            > "$TEMPORAIRE"
    fi

    test -s "$TEMPORAIRE"

    python3 scripts/_sqlite_maintenance.py validate "$TEMPORAIRE"

    ln "$TEMPORAIRE" "$FICHIER"

    echo "Sauvegarde creee : $FICHIER"
)
