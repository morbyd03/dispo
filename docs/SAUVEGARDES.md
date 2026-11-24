# Sauvegarde et restauration

Les données de Dispo sont stockées dans une base SQLite
située dans un volume Docker persistant.

## Effectuer une sauvegarde

Depuis le répertoire du projet :

    ./scripts/backup.sh

Les sauvegardes sont enregistrées dans le dossier backups/.

La sauvegarde utilise l'API native de SQLite et peut être
réalisée sans interrompre l'application.

L'intégrité de la base sauvegardée est vérifiée.

## Sauvegardes automatiques

Exemple de tâche cron quotidienne à 3 heures :

    0 3 * * * /opt/dispo/scripts/backup.sh

Adapter le chemin au répertoire réel de l'installation.

Si un nom de projet Docker Compose spécifique est utilisé,
définir également COMPOSE_PROJECT_NAME.

## Restauration

Sélectionner une sauvegarde :

    ls -lh backups/

Lancer la restauration :

    ./scripts/restore.sh backups/dispo_DATE.sqlite3

Une confirmation explicite est demandée.

Le script effectue une sauvegarde préventive, arrête
l'application, vérifie la base sélectionnée, restaure
les données et redémarre Dispo.

Prévoir une interruption temporaire du service.

En cas d'échec de restauration, consulter les messages
d'erreur avant de redémarrer manuellement l'application.

## Éléments complémentaires à sauvegarder

La sauvegarde SQLite ne contient pas :

- Le fichier .env.
- La clé secrète Django.
- La configuration SMTP.
- Le logo personnalisé.
- La configuration du reverse proxy.

Ces éléments doivent être sauvegardés séparément,
dans un emplacement sécurisé.

## Confidentialité

Les sauvegardes contiennent des données personnelles
et opérationnelles.

Elles ne doivent jamais être publiées sur GitHub.

Restreindre les accès et conserver des copies chiffrées
sur un support indépendant du serveur.

Définir une durée de conservation adaptée aux besoins
et aux obligations applicables.

Tester régulièrement la restauration des sauvegardes.
