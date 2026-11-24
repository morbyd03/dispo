# Historique des modifications

## En développement — Unreleased

## 0.1.0 — Première version expérimentale — 2026-11-24

### Fonctionnalités

- Gestion individuelle des disponibilités.
- Créneaux horaires pouvant traverser minuit.
- Calendrier individuel interactif.
- Planning hebdomadaire collectif.
- Copie des disponibilités vers plusieurs journées.
- Analyse des couvertures SSUAP et incendie.
- Détection des qualifications manquantes.
- Gestion des agents et des qualifications.
- Gestion des dates de validité des compétences.
- Gestion des droits administrateurs.
- Activation des comptes par e-mail.
- Réinitialisation des mots de passe.
- Rappel de l'identifiant de connexion dans les e-mails.
- Interface adaptée aux ordinateurs et smartphones.
- Thèmes clair et sombre.
- Bandeau configurable de préproduction.

### Déploiement

- Installation autonome avec Docker Compose.
- Configuration par variables d'environnement.
- Initialisation automatique de la base de données.
- Catalogue initial de compétences.
- Initialisation des permissions administratives.
- Personnalisation du nom, du centre et du logo.
- Hébergement local de FullCalendar.
- Verrouillage des dépendances Python.
- Documentation des reverse proxies et de HTTPS.
- Installation derrière Traefik validée.
- Possibilité de disposer d'une préproduction indépendante.

### Sauvegarde et restauration

- Sauvegarde SQLite à chaud.
- Noms de sauvegardes uniques.
- Permissions restrictives.
- Verrouillage exclusif des opérations de maintenance.
- Validation des sauvegardes avant interruption du service.
- Vérification de l'intégrité SQLite et des clés étrangères.
- Sauvegarde préventive avant remplacement de la base.
- Remplacement atomique du fichier SQLite.
- Tentative de redémarrage automatique en cas d'échec.
- Documentation des procédures de récupération.

### Sécurité et qualité

- Exécution du conteneur sans privilèges root.
- Suppression des capacités Linux du conteneur.
- Interdiction de l'élévation de privilèges.
- Publication locale du port HTTP par défaut.
- Validation des paramètres de configuration.
- Confiance configurable envers le reverse proxy.
- Cookies sécurisés lorsque HTTPS est activé.
- Exclusion des secrets et des données du dépôt Git.
- Suite de 51 tests automatisés validée.
- Tests des parcours d'activation et de réinitialisation.
- Tests de sauvegarde, restauration et récupération après échec.
- Audit des dépendances Python sans vulnérabilité connue
  détectée au 24 novembre 2026.
- Inventaire des licences des composants tiers.

### Licence et documentation

- Publication sous licence GNU AGPL-3.0.
- Guides d'installation et de configuration.
- Guide de sauvegarde et de restauration.
- Politique de sécurité.
- Guide de contribution.
- Mentions des licences tierces.
- Reconnaissance du développement en collaboration
  avec ChatGPT (OpenAI).

### Limites

Cette première version est expérimentale.

Dispo constitue un outil d'aide à la gestion des disponibilités.
Il ne remplace pas les systèmes officiels d'alerte,
de mobilisation ou de gestion opérationnelle.

Les tests et audits réalisés ne constituent pas
une certification de sécurité.
