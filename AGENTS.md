# Instructions permanentes pour Codex — Dispo

## Mission

Dispo est une application de gestion des disponibilités
et d'anticipation collective pour les centres de secours.

Devise : Déclarer simplement, anticiper collectivement.

Le responsable du projet définit les besoins fonctionnels,
les orientations et les validations de versions.

Codex assure la réalisation technique des tâches confiées.
Il ne doit pas inventer de nouvelles exigences métier.

Communiquer en français.
Conserver les conventions de nommage du projet.

## Prise de connaissance

Avant tout nouveau chantier, consulter les documents
pertinents parmi :

- README.md
- CONTRIBUTING.md
- SECURITY.md
- CHANGELOG.md
- ROADMAP.md
- docs/VISION.md
- docs/STRATEGIE_DEVELOPPEMENT.md
- docs/ARCHITECTURE.md
- docs/MODELE_DONNEES.md
- docs/AUTORISATIONS.md
- docs/SECURITE_COMPTES.md
- docs/IMPORT_EXPORT_AGENTS.md
- docs/PASSATION_CODEX.md

Lire les sources et les tests avant de modifier le code.

En cas de contradiction entre la documentation et les
sources, signaler le problème et vérifier les décisions
fonctionnelles avant de choisir une solution.

## Architecture technique

- Monolithe Django modulaire.
- Python 3.13 dans Docker.
- Django et dépendances selon requirements.lock.
- SQLite.
- Gunicorn et WhiteNoise.
- Interface web responsive.
- Priorité aux solutions simples et maintenables.
- Ne pas introduire de nouvelle infrastructure sans accord.

## Principes fonctionnels

Dispo doit être générique et configurable.

Ne jamais imposer dans le moteur métier :

- Des compétences propres à un SDIS.
- Des règles opérationnelles particulières.
- Des horaires fixes de surveillance.
- Des effectifs minimaux prédéfinis.
- Des véhicules ou équipages imposés.
- Des tests de couverture obligatoires.

Les compétences, périodes, seuils et règles de couverture
doivent provenir de la configuration de l'installation.

Les exemples métier ne constituent pas des valeurs imposées.

Sans règle active, afficher les disponibilités sans
évaluation de couverture.

Distinguer une absence de déclaration d'une indisponibilité.

Ne jamais transformer Dispo en système de déclenchement
opérationnel des secours.

Les prévisions destinées à NEXSIS doivent faciliter
le travail du responsable, sans intégration non autorisée.

## Gestion des agents

- Matricules conservés comme chaînes de caractères.
- Préserver les zéros initiaux.
- Adresses e-mail obligatoires et uniques.
- Aucune génération automatique d'adresse e-mail.
- Les changements d'adresse e-mail suivent une procédure
  distincte des imports.
- Ne jamais écraser les mots de passe ou les droits
  administratifs par import.
- Ne jamais supprimer les agents absents d'un fichier.
- Confirmer explicitement les retraits de qualifications.
- Utiliser exclusivement des données fictives en développement.

## Sécurité applicative

- Appliquer le principe du moindre privilège.
- Centraliser les contrôles d'autorisation.
- Vérifier les droits côté serveur.
- Ne jamais se fier uniquement aux restrictions visuelles.
- Protéger les opérations sensibles contre le CSRF.
- Utiliser des transactions pour les écritures liées.
- Contrôler les conflits et les modifications concurrentes.
- Journaliser les opérations administratives pertinentes.
- Protéger les données personnelles et les secrets.
- Ne pas affaiblir les protections pour faire passer un test.

Ne jamais consulter ou divulguer les secrets des autres
applications, les clés SSH ou les jetons d'authentification.

Ne jamais afficher le contenu complet du fichier .env.

## Environnement de développement

Le développement est effectué exclusivement sur AsthePC.

- Répertoire : ~/Projets/dispo
- Projet Docker : dispo-local
- Image Docker : dispo-local-web
- Adresse locale : http://localhost:18000
- Configuration privée : .env
- Surcharge locale : docker-compose.override.yml
- SELinux reste actif.
- Les courriels sont simulés dans la console.

Morbox est réservé à l'hébergement des versions validées.

Interdiction de se connecter à Morbox ou de modifier
ses services.

WinBoat est une application indépendante.
Ne jamais agir sur ses conteneurs, images, volumes
ou réseaux.

## Autonomie

Après attribution explicite d'une tâche, Codex peut :

- Analyser les fichiers du projet.
- Modifier le code nécessaire à la tâche.
- Créer ou renforcer les tests.
- Corriger les anomalies rencontrées.
- Mettre à jour la documentation.
- Préparer les migrations.
- Préparer des commits cohérents.

Ne pas demander une validation pour chaque modification
ordinaire comprise dans une tâche autorisée.

Demander une validation humaine avant :

- Une modification importante de l'architecture.
- Une décision fonctionnelle non spécifiée.
- Une suppression irréversible.
- Une opération Docker nécessitant une sortie du sandbox.
- Une installation système.
- Un push Git.
- Une fusion de branche.
- Une publication de version.
- Un déploiement.

Ne jamais utiliser sudo.
Ne jamais désactiver le sandbox.
Ne jamais désactiver SELinux.

Ne jamais demander une autorisation permanente et générique
pour Docker, Git, SSH ou les interpréteurs de commandes.

## Docker

Le démon Docker du PC est partagé avec d'autres applications.

Toute commande Docker doit être limitée au projet Dispo
et soumise aux restrictions effectives de l'environnement.

Ne jamais utiliser :

- docker system prune
- docker volume prune
- docker image prune
- docker network prune
- docker compose down -v sans accord spécifique
- Un conteneur privilégié
- Un montage du socket Docker dans un conteneur

Ne pas modifier les configurations globales de Docker.

## Tests

Point de référence au commit 6f7c52b :

- 738 tests recensés.
- 734 réussis.
- 4 ignorés.
- Aucun échec ni erreur.
- Durée sur AsthePC : 24,655 secondes.

Commande de construction :

    docker compose -p dispo-local build --quiet

Commande de validation globale :

    docker run --rm \
        --network none \
        --tmpfs /data:rw,mode=1777 \
        -e DJANGO_SECRET_KEY=cle-fictive-reservee-aux-tests-dispo \
        -e DISPO_DOMAIN=localhost \
        --entrypoint sh \
        dispo-local-web \
        -c 'python manage.py collectstatic --noinput --verbosity 0 && python manage.py test planning --verbosity 1 --failfast'

Ces commandes nécessitent une autorisation Docker adaptée.

Exécuter les tests ciblés pendant le développement,
puis la suite globale avant de déclarer un chantier terminé.

Ne jamais supprimer, ignorer ou assouplir un test dans
le seul but de masquer une anomalie.

Distinguer les tests réussis, ignorés et non exécutés.

Vérifier git diff --check avant chaque commit.

## Git

Dépôt : https://github.com/morbyd03/dispo

Branche actuelle : fonctionnalite/profils-agents

- Préserver l'historique existant.
- Commits cohérents et rédigés en français.
- Aucun secret dans les fichiers suivis.
- Ne pas écraser les modifications du responsable du projet.
- Aucun push automatique.
- Aucun force-push.
- Aucune fusion automatique.
- Respecter la licence AGPL-3.0.

Mentionner la collaboration de ChatGPT (OpenAI) et Codex
dans la documentation et les descriptions de contribution.

## Fin de tâche

Présenter :

- Les fonctionnalités réalisées.
- Les fichiers principaux modifiés.
- Les tests exécutés et leurs résultats.
- Les décisions prises.
- Les limites et anomalies restantes.
- Les opérations nécessitant une validation humaine.

Mettre à jour la documentation concernée.

Ne pas commencer spontanément le chantier suivant.

## État actuel

La version v0.2.0 est en développement.

Le chantier import/export des agents constitue le dernier
chantier réalisé avant la transition vers Codex.

Les travaux restant à réaliser sont décrits dans
docs/PASSATION_CODEX.md.

L'installation actuelle de Codex constitue uniquement
une phase de configuration.

Aucun développement fonctionnel ne doit commencer
avant une demande explicite du responsable du projet.
