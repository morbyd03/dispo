# Passation du développement vers Codex

Date : 28 novembre 2026.

## État du projet

- Version en développement : v0.2.0.
- Branche : fonctionnalite/profils-agents.
- Dernière version stable : v0.1.0.
- Objectif de mise en service réelle : début janvier 2027.
- Les données actuellement utilisées sont des données de test.
- Aucun déploiement de cette branche en production.

## Validation de référence

Dernière suite globale, étape 1213 :

- 738 tests recensés.
- 734 tests réussis.
- 4 tests ignorés.
- Aucun échec.
- Aucune erreur.
- Durée : 101,935 secondes.
- Code de retour : 0.

Les tests ignorés concernent notamment les diagnostics
historiques de couverture et les tests nécessitant une
configuration SQLite de concurrence spécifique.

Les tests de concurrence exécutés séparément lors des
étapes précédentes devront être relancés.

## Dernier chantier réalisé

Import et export CSV des agents :

- Import avec adresse e-mail obligatoire.
- Aucune génération automatique d'adresse e-mail.
- Conservation des matricules et de leurs zéros initiaux.
- Export de consultation et export de réimportation.
- Prévisualisation détaillée des modifications.
- Traduction des identifiants techniques en libellés.
- Stockage temporaire réservé au superutilisateur concerné.
- Durée de confirmation limitée à 30 minutes.
- Confirmation transactionnelle.
- Protection contre le rejeu.
- Confirmation spécifique des retraits de qualifications.
- Annulation explicite.
- Commande Django de purge des imports temporaires.
- Bilans prévisionnel et définitif harmonisés.
- Interfaces HTTP réservées aux superutilisateurs.
- Protection CSRF et absence de cache HTTP.
- Migration 0019 validée sur une base de test.

Tests dédiés :

- 247 tests du chantier import/export réussis.
- 24 tests HTTP d'import réussis.

Ces tests sont inclus dans la suite globale.

## Travaux restant sur le chantier import/export

- Automatiser la purge des imports temporaires.
- Tester les confirmations réellement concurrentes.
- Vérifier la concurrence entre préparation, confirmation,
  annulation et purge.
- Garantir la cohérence des référentiels entre la
  prévisualisation et la confirmation.
- Vérifier les conséquences des changements de droits
  et des révocations de comptes.
- Renforcer les limites de téléversement côté serveur.
- Vérifier la confidentialité des données dans les
  journaux et les rapports d'erreur.
- Traiter la conservation des données temporaires dans
  les sauvegardes et les fichiers SQLite.
- Effectuer la validation visuelle sur PC et mobile.
- Compléter les tests HTTP des scénarios complexes.
- Envisager la centralisation des messages Django.
- Étudier la prise en charge directe des fichiers XLSX.

Un export CSV ne constitue pas une sauvegarde complète.

## Prochains chantiers fonctionnels

- Gestion collective des qualifications.
- Connexion par adresse e-mail ou matricule.
- Protection contre les tentatives de connexion répétées.
- Planning mensuel.
- Confirmation des disponibilités déclarées.
- Distinction entre indisponibilité et absence de réponse.
- Moteur générique de couverture opérationnelle.
- Interface de configuration des règles de couverture.
- Périodes de surveillance entièrement configurables.
- Préparation des prévisions mensuelles pour NEXSIS.

## Principes fonctionnels impératifs

Dispo doit rester générique et configurable.

Ne jamais imposer dans le moteur métier :

- Des codes de compétences propres à un SDIS.
- Une doctrine opérationnelle particulière.
- Des horaires fixes de surveillance.
- Des effectifs minimaux prédéfinis.
- Des règles de couverture obligatoires.
- Des types de véhicules propres à une organisation.

Les règles historiques SSUAP et INC servent de référence
de test, mais ne doivent pas devenir des règles imposées.

En l'absence de règle de couverture active, le planning
affiche les disponibilités sans évaluation de couverture.

Les exemples discutés avec le responsable du projet
ne constituent pas des paramètres obligatoires.

## Nouvelle organisation du développement

Décision du responsable du projet :

Codex sera installé sur son PC, et non sur Morbox.

Le développement doit être effectué dans un environnement
local indépendant utilisant des données fictives.

Conserver l'architecture Django, SQLite et Docker.

GitHub reste le référentiel central du projet.

Morbox reste réservé à l'hébergement des versions validées.

Aucun accès SSH à Morbox ne sera nécessaire pour Codex.

Ne pas transférer les secrets, les bases de production,
les identifiants SMTP ou les clés SSH du serveur.

## Autonomie attendue de Codex

Dans l'environnement de développement local :

- Analyser les sources existantes.
- Développer les fonctionnalités demandées.
- Créer et exécuter les tests.
- Corriger les erreurs constatées.
- Vérifier les migrations.
- Maintenir la documentation.
- Préparer des commits cohérents.

Une validation humaine reste nécessaire avant :

- Un push vers GitHub.
- Une fusion de branche.
- Une publication de version.
- Une modification importante de l'architecture.
- Une suppression irréversible de données.
- Un déploiement en préproduction ou en production.

Ne jamais neutraliser un test pour masquer une anomalie.
Ne jamais considérer un test ignoré comme réussi.

## Documentation à consulter

- README.md
- CONTRIBUTING.md
- SECURITY.md
- CHANGELOG.md
- docs/VISION.md
- docs/STRATEGIE_DEVELOPPEMENT.md
- docs/ARCHITECTURE.md
- docs/MODELE_DONNEES.md
- docs/AUTORISATIONS.md
- docs/SECURITE_COMPTES.md
- docs/IMPORT_EXPORT_AGENTS.md
- docs/CONFIGURATION.md
- docs/INSTALLATION.md
- docs/SAUVEGARDES.md
- docs/REVERSE_PROXY.md

La présente passation constitue un point de reprise,
et non une nouvelle spécification exhaustive.

Les décisions fonctionnelles détaillées restent à
consolider dans la documentation du projet.

## Reprise après la pause

1. Examiner l'environnement du PC.
2. Installer et configurer Codex.
3. Récupérer la branche de développement.
4. Préparer un environnement Docker local isolé.
5. Rédiger les instructions permanentes AGENTS.md.
6. Reproduire la suite globale de référence.
7. Terminer les travaux ouverts du chantier import/export.
8. Poursuivre la feuille de route v0.2.0.

## Collaboration

Projet développé avec la collaboration de ChatGPT (OpenAI).
La contribution de Codex sera également documentée.

## Configuration locale réalisée le 28 novembre 2026

Environnement AsthePC :

- Fedora Linux 44 KDE Plasma.
- AMD Ryzen 7 9800X3D.
- 32 Go de mémoire vive.
- Docker 29.10.0.
- Docker Compose 5.8.0.
- Codex CLI 0.172.0.
- Authentification Codex avec ChatGPT.
- Authentification GitHub via GitHub CLI et HTTPS.
- Dépôt local : ~/Projets/dispo.
- Projet Docker : dispo-local.
- Image Docker : dispo-local-web.
- Application : http://localhost:18000.
- Base de données locale indépendante.
- Superutilisateur local créé.
- Connexion à Dispo vérifiée.
- SELinux actif en mode Enforcing.
- Configuration privée ignorée par Git.

### Validation locale

Suite globale reproduite au commit 6f7c52b :

- 738 tests recensés.
- 734 réussis.
- 4 ignorés.
- Aucun échec ni erreur.
- Durée : 24,655 secondes.
- Code de retour : 0.

### Configuration Codex

Instructions permanentes : AGENTS.md.

Configuration utilisateur dans ~/.codex/config.toml :

    approval_policy = "on-request"
    sandbox_mode = "workspace-write"

    [sandbox_workspace_write]
    network_access = false

Contrôles réalisés :

- Lecture du projet autorisée.
- Écriture dans le projet autorisée.
- Écriture dans le dossier personnel hors projet bloquée.
- Connexion au socket Docker principal bloquée.
- Premier essai Codex en lecture seule réussi.
- Compréhension des instructions de passation vérifiée.

Ces contrôles ne constituent pas un audit exhaustif
de l'isolation du sandbox.

Les commandes Docker nécessitant une sortie du sandbox
doivent rester soumises à une approbation ponctuelle.
Ne pas accorder une autorisation Docker permanente.

WinBoat utilise le même démon Docker et doit être préservé.

### Point d'arrêt de la configuration

Aucun développement fonctionnel commencé avec Codex.

Le prochain chantier devra faire l'objet d'une demande
explicite du responsable du projet.

Priorité proposée : terminer les travaux ouverts du
chantier import/export avant les nouvelles fonctionnalités.

Aucune modification de Morbox.
