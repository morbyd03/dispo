# Historique des modifications

## En développement — Unreleased

## 0.1.0 — Première version

### Fonctionnalités

- Gestion individuelle des disponibilités.
- Planning hebdomadaire collectif.
- Copie des disponibilités.
- Analyse des couvertures SSUAP et incendie.
- Gestion des agents et des qualifications.
- Gestion des dates de validité des compétences.
- Activation et réinitialisation des comptes par e-mail.
- Thèmes clair et sombre.

### Déploiement

- Installation autonome avec Docker Compose.
- Configuration par variables d'environnement.
- Initialisation automatique de la base de données.
- Catalogue initial de compétences.
- Initialisation des permissions administratives.
- Personnalisation du nom et du logo.
- Hébergement local de FullCalendar.
- Verrouillage des dépendances Python.

### Sécurité et qualité

- Exécution du conteneur sans privilèges root.
- Publication du port HTTP sur l'interface locale.
- Validation des paramètres de configuration.
- Confiance configurable envers le reverse proxy.
- Exclusion des secrets et des données du dépôt Git.
- Suite de 42 tests automatisés validée.
- Audit des dépendances Python sans vulnérabilité connue
  détectée au 24 novembre 2026.
