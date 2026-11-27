# Architecture de Dispo

## Principes directeurs

- Stabilité avant rapidité de développement.
- Simplicité avant complexité technique.
- Séparation des responsabilités.
- Normalisation des données relationnelles.
- Référentiels configurables.
- Intégrité des données garantie par la base.
- Permissions indépendantes des fonctions opérationnelles.
- Migrations sans perte de données.
- Tests automatisés adaptés à chaque domaine.

## Domaines fonctionnels

- Comptes et authentification.
- Agents, grades et fonctions.
- Compétences et qualifications.
- Disponibilités.
- Couverture opérationnelle.
- Communications internes.
- Logistique et inventaires.
- Pharmacie.

## Organisation technique

Dispo privilégie une architecture monolithique modulaire.

Les domaines métier sont séparés dans le code, tout en
partageant une application et une base relationnelle.

Les interfaces utilisent des services métier dédiés.

Les calculs de couverture ne modifient pas les référentiels
et ne déterminent pas la structure des agents.

## Configuration

Les référentiels et les futures règles de couverture
doivent être configurables sans modification du code source.

Les contraintes de sécurité et d'intégrité restent imposées
par l'application.

## Stratégie de refonte

La version v0.1.0 reste la référence stable en production.

Les anciens traitements de couverture seront temporairement
neutralisés durant la construction du nouveau socle.

Le code historique et les tests restent accessibles dans Git.

Aucune version intermédiaire incomplète ne sera déployée
en production.

## Ordre de développement

1. Structure et intégrité des données.
2. Référentiels et importation.
3. Gestion des agents et des compétences.
4. Authentification et sécurité.
5. Gestion des disponibilités.
6. Règles et calculs de couverture.
7. Validation complète et mise en production.
