# Sauvegarde et restauration

Les données de Dispo sont stockées dans une base SQLite
située dans un volume Docker persistant.

## Prérequis

Les scripts de maintenance nécessitent :

- Docker et Docker Compose.
- Python 3 avec le module sqlite3 sur l'hôte.
- Les commandes flock, mktemp, stat et ln.
- Un dossier de sauvegarde privé sur un système de fichiers
  prenant en charge les liens physiques.

## Effectuer une sauvegarde

Depuis le répertoire du projet :

    ./scripts/backup.sh

Les sauvegardes sont enregistrées dans le dossier backups/.

Un autre emplacement peut être défini avec la variable
DISPO_BACKUP_DIR.

Le dossier de sauvegarde doit avoir les permissions 700.

Les fichiers de sauvegarde sont créés avec les permissions 600.

La sauvegarde utilise l'API native de SQLite et peut être
réalisée sans interrompre l'application.

Chaque sauvegarde possède un nom unique.

L'intégrité SQLite et les relations entre les tables
sont vérifiées avant publication du fichier.

## Sauvegardes automatiques

Exemple de tâche cron quotidienne à 3 heures :

    0 3 * * * /opt/dispo/scripts/backup.sh

Adapter le chemin au répertoire réel de l'installation.

Si un nom de projet Docker Compose spécifique est utilisé,
définir également COMPOSE_PROJECT_NAME.

Les scripts ne suppriment pas automatiquement les anciennes
sauvegardes. Prévoir une politique de conservation adaptée.

## Restauration

Sélectionner une sauvegarde :

    ls -lh backups/

Lancer la restauration :

    ./scripts/restore.sh backups/dispo_DATE_SUFFIXE.sqlite3

Le script effectue les opérations suivantes :

1. Acquisition d'un verrou exclusif.
2. Copie et validation de la sauvegarde sélectionnée.
3. Demande de confirmation explicite.
4. Arrêt de Dispo.
5. Création d'une sauvegarde préventive.
6. Remplacement atomique du fichier SQLite.
7. Vérification de l'intégrité de la base.
8. Redémarrage de Dispo.

Les sauvegardes invalides sont refusées avant l'arrêt du service.

Prévoir une interruption temporaire de l'application.

## Gestion des erreurs

En cas d'échec après l'arrêt de Dispo, le script tente
automatiquement de redémarrer le service.

Ce redémarrage ne constitue pas un rollback automatique.

Consulter les messages d'erreur et les journaux :

    docker compose ps
    docker compose logs --tail=50 web

La sauvegarde préventive permet de retrouver l'état
de la base avant la restauration.

Si la base actuelle est corrompue, la sauvegarde préventive
peut échouer et nécessiter une intervention manuelle.

Une restauration entre versions différentes de Dispo
n'est pas garantie compatible.

Les sessions et les mots de passe enregistrés dans la
sauvegarde peuvent également être restaurés.

## Verrouillage

Les sauvegardes et restaurations utilisent un verrou
exclusif commun au répertoire d'installation.

Le fichier .dispo-maintenance.lock peut rester présent
après une opération. Ce comportement est normal.

Ne pas supprimer ce fichier pendant une opération.

Ce verrou ne protège pas contre les interventions Docker
manuelles ou les opérations lancées depuis un autre
répertoire d'installation.

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
